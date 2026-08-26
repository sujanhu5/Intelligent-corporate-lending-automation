"""
PredictionService — orchestrates model training and application-level prediction.

Training pipeline:
  POST /predictions/train
    1. Validate dataset exists.
    2. Call ml.trainer.train_all() — trains LR, RF, XGBoost, persists pkl + metadata.json.
    3. Invalidate the in-process model cache.
    4. Write audit log.
    5. Return TrainingResponse.

Prediction pipeline:
  POST /predictions/predict/{application_id}
    1. Guard: application must exist + rules must have been evaluated.
    2. Load rule evaluation result to check ml_should_run flag.
    3. If ml_should_run is False → create a skipped Prediction record and return.
    4. Validate models are trained.
    5. Load the latest FinancialRatio record → extract ratio values.
    6. Call ml.predictor.predict_for_application() with best model.
    7. Compute composite risk score via ml.risk_scorer.
    8. Build recommendation text.
    9. Persist Prediction record (upsert).
    10. Update Application.risk_score + mark pipeline stage ml_predicted.
    11. Write audit log.
    12. Return PredictionResponse.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.core.exceptions import BadRequestError, ModelNotTrainedError, NotFoundError
from app.core.logging import get_logger
from app.models.application import ApplicationStatus
from app.models.audit_log import AuditAction
from app.models.financial_ratio import FinancialRatio
from app.models.prediction import ModelUsed, Prediction, PredictionOutcome, RiskLevel
from app.models.user import User
from app.repositories.application_repository import ApplicationRepository
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.prediction_repository import PredictionRepository
from app.schemas.prediction import (
    ModelStatusResponse,
    PredictionResponse,
    PredictionSummaryResponse,
    TrainingResponse,
)
from ml.predictor import PredictionBundle, invalidate_cache, predict_for_application
from ml.risk_scorer import build_recommendation, compute_risk_score, get_risk_level
from ml.trainer import (
    TrainingResult,
    load_training_metadata,
    models_are_trained,
    train_all,
)

logger = get_logger(__name__)

_FEATURE_CONFIG_PATH = BASE_DIR / "config" / "feature_config.json"


class PredictionService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._app_repo = ApplicationRepository(db)
        self._pred_repo = PredictionRepository(db)
        self._audit = AuditLogRepository(db)

    # =========================================================================
    # Model training
    # =========================================================================

    def train_models(
        self,
        trained_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> TrainingResponse:
        """Train all three models from scratch and persist artefacts."""
        dataset_path: Path = settings.dataset_path
        models_path: Path = settings.models_path

        import json as _json
        import ml.dataset as _ds
        feature_config = _ds.load_feature_config(_FEATURE_CONFIG_PATH)
        training_config = feature_config.get("training", {})

        result: TrainingResult = train_all(
            dataset_path=dataset_path,
            feature_config_path=_FEATURE_CONFIG_PATH,
            models_path=models_path,
            random_state=settings.ML_RANDOM_STATE,
            test_size=settings.TEST_SIZE,
            cv_folds=settings.CV_FOLDS,
            apply_smote_flag=training_config.get("handle_imbalance", True),
        )

        # Invalidate the in-memory model cache so next prediction loads fresh pkl
        invalidate_cache()

        self._audit.log(
            action=AuditAction.MODEL_TRAINED,
            description=(
                f"All ML models retrained by {trained_by.email}. "
                f"Best model: {result.best_model} (ROC-AUC={result.best_roc_auc:.4f}). "
                f"Training samples: {result.train_samples}, "
                f"Test samples: {result.test_samples}."
            ),
            user_id=trained_by.id,
            new_values={
                "best_model": result.best_model,
                "best_roc_auc": result.best_roc_auc,
                "train_samples": result.train_samples,
                "smote_applied": result.smote_applied,
            },
            ip_address=ip_address,
            request_id=request_id,
        )

        logger.info(
            "Model training complete",
            extra={"best_model": result.best_model, "roc_auc": result.best_roc_auc},
        )

        return TrainingResponse(
            trained_at=result.trained_at,
            dataset_path=str(result.dataset_path),
            total_samples=result.total_samples,
            train_samples=result.train_samples,
            test_samples=result.test_samples,
            smote_applied=result.smote_applied,
            class_distribution_original=result.class_distribution_original,
            selected_features=result.selected_features,
            dropped_correlated_count=result.dropped_correlated_count,
            best_model=result.best_model,
            best_roc_auc=result.best_roc_auc,
            models=result.models,
        )

    def get_model_status(self) -> ModelStatusResponse:
        """Check whether models are trained and return metadata."""
        models_path = settings.models_path
        trained = models_are_trained(models_path)
        if not trained:
            return ModelStatusResponse(
                models_trained=False,
                trained_at=None,
                best_model=None,
                best_roc_auc=None,
                selected_feature_count=None,
                total_training_samples=None,
                model_metrics=None,
            )

        meta = load_training_metadata(models_path) or {}
        return ModelStatusResponse(
            models_trained=True,
            trained_at=meta.get("trained_at"),
            best_model=meta.get("best_model"),
            best_roc_auc=meta.get("best_roc_auc"),
            selected_feature_count=len(meta.get("selected_features", [])),
            total_training_samples=meta.get("total_samples"),
            model_metrics=meta.get("models"),
        )

    # =========================================================================
    # Application prediction
    # =========================================================================

    def predict_for_application(
        self,
        application_id: uuid.UUID,
        predicted_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> PredictionResponse:
        # ── 1. Load application ───────────────────────────────────────────────
        app = self._app_repo.get_by_id(application_id)
        if not app:
            raise NotFoundError(message=f"Application '{application_id}' not found.")

        if not app.rules_evaluated:
            raise BadRequestError(
                message=(
                    f"Application '{app.application_number}' has not had rule evaluation "
                    "completed. Run POST /rules/evaluate/{application_id} first."
                )
            )

        # ── 2. Load rule evaluation result ────────────────────────────────────
        fr = self._get_latest_ratio(application_id)
        if not fr:
            raise BadRequestError(
                message=f"No financial ratio record found for application '{app.application_number}'."
            )

        meta = fr.calculation_metadata or {}
        rule_eval = meta.get("rule_evaluation", {})
        rule_outcome: str = rule_eval.get("overall_outcome", "pass")
        ml_should_run: bool = rule_eval.get("ml_should_run", True)
        mandatory_failures: List[str] = rule_eval.get("mandatory_failures", [])
        advisory_triggers: List[str] = rule_eval.get("advisory_triggers", [])

        # ── 3. Handle mandatory-rejection bypass ──────────────────────────────
        if not ml_should_run:
            skip_reason = (
                f"ML pipeline skipped — mandatory rule(s) failed: "
                + ", ".join(mandatory_failures)
                + "."
            )
            pred = self._pred_repo.upsert(
                application_id=application_id,
                model_used=ModelUsed.LOGISTIC_REGRESSION,   # placeholder
                probability_of_default=1.0,
                outcome=PredictionOutcome.HIGH_RISK,
                risk_score=100.0,
                risk_level=RiskLevel.VERY_HIGH,
                ml_executed=False,
                skip_reason=skip_reason,
                recommendation=skip_reason,
                explanation_text=skip_reason,
                model_metrics=None,
            )
            self._app_repo.mark_pipeline_stage(app, "ml_predicted")
            self._write_audit(
                app, pred, predicted_by, rule_outcome,
                skipped=True, ip_address=ip_address, request_id=request_id,
            )
            return PredictionResponse.model_validate(pred)

        # ── 4. Validate models are trained ────────────────────────────────────
        if not models_are_trained(settings.models_path):
            raise ModelNotTrainedError(
                message=(
                    "No trained ML models found. "
                    "An administrator must run POST /predictions/train before predictions can be made."
                )
            )

        # ── 5. Extract ratio values ───────────────────────────────────────────
        ratio_values: Dict[str, Optional[float]] = {}
        if fr.ratios:
            for ratio_name, ratio_data in fr.ratios.items():
                if isinstance(ratio_data, dict):
                    ratio_values[ratio_name] = ratio_data.get("value")

        # ── 6. Determine best model from metadata ─────────────────────────────
        meta_json = load_training_metadata(settings.models_path) or {}
        best_model_key = meta_json.get("best_model", "xgboost")
        model_metrics_all: Dict[str, Any] = meta_json.get("models", {})

        # ── 7. Run ML prediction ──────────────────────────────────────────────
        bundle: PredictionBundle = predict_for_application(
            ratio_values=ratio_values,
            models_path=settings.models_path,
            model_key=best_model_key,
        )

        # ── 8. Compute composite risk score ───────────────────────────────────
        import json as _json
        feature_config = _json.loads((_FEATURE_CONFIG_PATH).read_text(encoding="utf-8"))
        risk_scoring_config = feature_config.get("risk_scoring", {})

        risk_score, risk_level_str = compute_risk_score(
            probability_of_default=bundle.probability_of_default,
            rule_outcome=rule_outcome,
            risk_scoring_config=risk_scoring_config,
        )
        risk_level = RiskLevel(risk_level_str)
        outcome = (
            PredictionOutcome.HIGH_RISK
            if bundle.probability_of_default >= 0.5
            else PredictionOutcome.LOW_RISK
        )

        # ── 9. Build recommendation ───────────────────────────────────────────
        recommendation = build_recommendation(
            probability_of_default=bundle.probability_of_default,
            risk_score=risk_score,
            risk_level=risk_level_str,
            rule_outcome=rule_outcome,
            mandatory_failures=mandatory_failures,
            advisory_triggers=advisory_triggers,
            model_key=best_model_key,
        )

        # ── 10. Persist prediction ────────────────────────────────────────────
        model_used = _key_to_model_used(best_model_key)
        pred = self._pred_repo.upsert(
            application_id=application_id,
            model_used=model_used,
            model_version=meta_json.get("trained_at", "unknown")[:10],
            probability_of_default=bundle.probability_of_default,
            outcome=outcome,
            risk_score=risk_score,
            risk_level=risk_level,
            shap_values=bundle.shap_values,
            feature_importance=bundle.feature_importance,
            input_features=bundle.input_features,
            explanation_text=bundle.explanation_text,
            recommendation=recommendation,
            ml_executed=True,
            model_metrics=model_metrics_all,
        )

        # ── 11. Update application ────────────────────────────────────────────
        self._app_repo.update(app, risk_score=risk_score)
        self._app_repo.mark_pipeline_stage(app, "ml_predicted")

        # Update status only if not already in manual_review or rejected
        if app.status not in (ApplicationStatus.REJECTED, ApplicationStatus.MANUAL_REVIEW):
            self._app_repo.update(app, status=ApplicationStatus.ML_PREDICTED)

        # ── 12. Audit log ─────────────────────────────────────────────────────
        self._write_audit(
            app, pred, predicted_by, rule_outcome,
            skipped=False, ip_address=ip_address, request_id=request_id,
        )

        logger.info(
            "ML prediction complete",
            extra={
                "app_id": str(application_id),
                "model": best_model_key,
                "risk_score": risk_score,
                "risk_level": risk_level_str,
            },
        )

        return PredictionResponse.model_validate(pred)

    def get_prediction(self, application_id: uuid.UUID) -> PredictionResponse:
        app = self._app_repo.get_by_id(application_id)
        if not app:
            raise NotFoundError(message=f"Application '{application_id}' not found.")

        pred = self._pred_repo.get_latest_for_application(application_id)
        if not pred:
            raise NotFoundError(
                message=(
                    f"No ML prediction found for application '{app.application_number}'. "
                    "Run POST /predictions/predict/{application_id} first."
                )
            )
        return PredictionResponse.model_validate(pred)

    def get_prediction_summary(
        self, application_id: uuid.UUID
    ) -> PredictionSummaryResponse:
        pred = self._pred_repo.get_latest_for_application(application_id)
        if not pred:
            return PredictionSummaryResponse(
                application_id=application_id,
                risk_score=None,
                risk_level=None,
                probability_of_default=None,
                outcome=None,
                model_used=None,
                ml_executed=False,
                recommendation_headline=None,
                created_at=None,
            )
        # Extract first sentence of recommendation as headline
        rec = pred.recommendation or ""
        headline = rec.split(".")[0] + "." if "." in rec else rec[:120]
        return PredictionSummaryResponse(
            application_id=application_id,
            risk_score=float(pred.risk_score),
            risk_level=pred.risk_level,
            probability_of_default=float(pred.probability_of_default),
            outcome=pred.outcome,
            model_used=pred.model_used,
            ml_executed=pred.ml_executed,
            recommendation_headline=headline,
            created_at=pred.created_at,
        )

    # =========================================================================
    # Helpers
    # =========================================================================

    def _get_latest_ratio(self, application_id: uuid.UUID) -> Optional[FinancialRatio]:
        return (
            self._db.query(FinancialRatio)
            .filter(FinancialRatio.application_id == application_id)
            .order_by(FinancialRatio.created_at.desc())
            .first()
        )

    def _write_audit(
        self,
        app: Any,
        pred: Prediction,
        user: User,
        rule_outcome: str,
        skipped: bool,
        ip_address: str,
        request_id: str,
    ) -> None:
        self._audit.log(
            action=AuditAction.ML_PREDICTED,
            description=(
                f"ML prediction {'skipped (mandatory rule failure)' if skipped else 'completed'} "
                f"for application '{app.application_number}'. "
                f"Risk score: {float(pred.risk_score):.1f}/100 ({pred.risk_level.value}). "
                f"Rule outcome: {rule_outcome}."
            ),
            user_id=user.id,
            entity_type="prediction",
            entity_id=str(pred.id),
            new_values={
                "risk_score": float(pred.risk_score),
                "risk_level": pred.risk_level.value,
                "probability_of_default": float(pred.probability_of_default),
                "outcome": pred.outcome.value,
                "ml_executed": pred.ml_executed,
            },
            ip_address=ip_address,
            request_id=request_id,
        )


def _key_to_model_used(key: str) -> ModelUsed:
    mapping = {
        "logistic_regression": ModelUsed.LOGISTIC_REGRESSION,
        "random_forest": ModelUsed.RANDOM_FOREST,
        "xgboost": ModelUsed.XGBOOST,
    }
    return mapping.get(key, ModelUsed.XGBOOST)
