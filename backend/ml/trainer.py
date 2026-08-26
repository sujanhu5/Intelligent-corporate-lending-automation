"""
ML training pipeline — trains Logistic Regression, Random Forest, and XGBoost,
computes evaluation metrics, identifies the best model by ROC-AUC, and
persists all artefacts to disk.

Persisted artefacts (in settings.models_path):
  logistic.pkl       — {"model": ..., "scaler": ..., "feature_names": [...], "medians": {...}}
  random_forest.pkl  — same structure
  xgboost.pkl        — same structure
  metadata.json      — training summary (metrics, features, class distribution, timestamps)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from xgboost import XGBClassifier

from app.core.logging import get_logger
from ml.dataset import DatasetBundle, load_dataset, load_feature_config
from ml.features import FeatureArtifacts, apply_smote, engineer_features

logger = get_logger(__name__)

@dataclass
class ModelMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    cv_roc_auc_mean: float
    cv_roc_auc_std: float


@dataclass
class TrainingResult:
    trained_at: str
    dataset_path: str
    total_samples: int
    train_samples: int
    test_samples: int
    smote_applied: bool
    class_distribution_original: Dict[str, int]
    selected_features: List[str]
    dropped_correlated_count: int
    models: Dict[str, ModelMetrics]
    best_model: str            # model key with highest roc_auc on test set
    best_roc_auc: float


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def train_all(
    dataset_path: Path,
    feature_config_path: Path,
    models_path: Path,
    random_state: int = 42,
    test_size: float = 0.2,
    cv_folds: int = 5,
    apply_smote_flag: bool = True,
) -> TrainingResult:
    """
    Full training pipeline:
      load → engineer features → SMOTE → train 3 models → evaluate → persist.

    Returns:
        TrainingResult with metrics for all models.
    """
    feature_config = load_feature_config(feature_config_path)
    dataset_config = feature_config.get("dataset", {})

    # ── Load dataset ──────────────────────────────────────────────────────────
    bundle: DatasetBundle = load_dataset(dataset_path, dataset_config)
    X_all, y_all = bundle.X, bundle.y

    # ── Train/test split ──────────────────────────────────────────────────────
    X_train_df, X_test_df, y_train, y_test = train_test_split(
        X_all, y_all, test_size=test_size, random_state=random_state, stratify=y_all
    )

    # ── Feature engineering ───────────────────────────────────────────────────
    X_train_scaled, X_test_scaled, artifacts = engineer_features(
        X_train_df, X_test_df, y_train, feature_config
    )

    # ── SMOTE (on training data only) ─────────────────────────────────────────
    smote_applied = False
    if apply_smote_flag:
        X_train_final, y_train_final = apply_smote(
            X_train_scaled, y_train.values, random_state=random_state
        )
        smote_applied = True
    else:
        X_train_final, y_train_final = X_train_scaled, y_train.values

    # ── Train all models ──────────────────────────────────────────────────────
    model_configs = feature_config.get("models", {})
    results_per_model: Dict[str, ModelMetrics] = {}
    best_model_name = "xgboost"
    best_roc_auc = -1.0

    for model_key, build_fn in _MODEL_BUILDERS.items():
        params = model_configs.get(model_key, {}).get("params", {})
        estimator = build_fn(params, random_state)

        logger.info("Training model", extra={"model": model_key})
        estimator.fit(X_train_final, y_train_final)

        metrics = _evaluate(
            estimator, X_train_final, X_test_scaled, y_train_final, y_test.values, cv_folds
        )
        results_per_model[model_key] = metrics
        logger.info(
            "Model trained",
            extra={
                "model": model_key,
                "roc_auc": round(metrics.roc_auc, 4),
                "f1": round(metrics.f1, 4),
            },
        )

        if metrics.roc_auc > best_roc_auc:
            best_roc_auc = metrics.roc_auc
            best_model_name = model_key

        # ── Persist model artifact ────────────────────────────────────────────
        filename = model_configs.get(model_key, {}).get("filename", f"{model_key}.pkl")
        _save_model_artifact(
            path=models_path / filename,
            model=estimator,
            artifacts=artifacts,
        )

    # ── Persist metadata ──────────────────────────────────────────────────────
    result = TrainingResult(
        trained_at=datetime.now(timezone.utc).isoformat(),
        dataset_path=str(dataset_path),
        total_samples=bundle.total_rows,
        train_samples=len(y_train),
        test_samples=len(y_test),
        smote_applied=smote_applied,
        class_distribution_original={str(k): v for k, v in bundle.class_counts.items()},
        selected_features=artifacts.selected_features,
        dropped_correlated_count=len(artifacts.dropped_correlated),
        models={k: _metrics_to_dict(v) for k, v in results_per_model.items()},
        best_model=best_model_name,
        best_roc_auc=best_roc_auc,
    )

    _save_metadata(models_path / "metadata.json", result, artifacts)

    logger.info(
        "Training complete",
        extra={"best_model": best_model_name, "best_roc_auc": round(best_roc_auc, 4)},
    )
    return result


def models_are_trained(models_path: Path) -> bool:
    """Return True only if all three model pkl files and metadata.json exist."""
    required = ["logistic.pkl", "random_forest.pkl", "xgboost.pkl", "metadata.json"]
    return all((models_path / f).exists() for f in required)


def load_training_metadata(models_path: Path) -> Optional[Dict[str, Any]]:
    """Load and return the metadata.json dict, or None if not present."""
    meta_path = models_path / "metadata.json"
    if not meta_path.exists():
        return None
    with meta_path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Model builders
# ---------------------------------------------------------------------------

def _build_logistic(params: Dict[str, Any], random_state: int) -> LogisticRegression:
    safe = {k: v for k, v in params.items() if k != "random_state"}
    return LogisticRegression(random_state=random_state, **safe)


def _build_random_forest(params: Dict[str, Any], random_state: int) -> RandomForestClassifier:
    safe = {k: v for k, v in params.items() if k != "random_state"}
    return RandomForestClassifier(random_state=random_state, **safe)


def _build_xgboost(params: Dict[str, Any], random_state: int) -> XGBClassifier:
    safe = {
        k: v for k, v in params.items()
        if k not in ("random_state", "use_label_encoder", "eval_metric")
    }
    return XGBClassifier(
        random_state=random_state,
        eval_metric="auc",
        use_label_encoder=False,
        verbosity=0,
        **safe,
    )


# Defined after the builder functions to avoid NameError at import time
_MODEL_BUILDERS = {
    "logistic_regression": _build_logistic,
    "random_forest": _build_random_forest,
    "xgboost": _build_xgboost,
}


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def _evaluate(
    estimator: Any,
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    cv_folds: int,
) -> ModelMetrics:
    y_pred = estimator.predict(X_test)
    if hasattr(estimator, "predict_proba"):
        y_prob = estimator.predict_proba(X_test)[:, 1]
    else:
        y_prob = estimator.decision_function(X_test)

    cv_scores = cross_val_score(
        estimator, X_train, y_train, cv=cv_folds, scoring="roc_auc"
    )

    return ModelMetrics(
        accuracy=float(accuracy_score(y_test, y_pred)),
        precision=float(precision_score(y_test, y_pred, zero_division=0)),
        recall=float(recall_score(y_test, y_pred, zero_division=0)),
        f1=float(f1_score(y_test, y_pred, zero_division=0)),
        roc_auc=float(roc_auc_score(y_test, y_prob)),
        cv_roc_auc_mean=float(cv_scores.mean()),
        cv_roc_auc_std=float(cv_scores.std()),
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _save_model_artifact(
    path: Path,
    model: Any,
    artifacts: FeatureArtifacts,
) -> None:
    artifact = {
        "model": model,
        "scaler": artifacts.scaler,
        "feature_names": artifacts.selected_features,
        "feature_medians": artifacts.feature_medians,
    }
    joblib.dump(artifact, path)
    logger.debug("Model artifact saved", extra={"path": str(path)})


def _save_metadata(
    path: Path,
    result: TrainingResult,
    artifacts: FeatureArtifacts,
) -> None:
    metadata = {
        "trained_at": result.trained_at,
        "dataset_path": result.dataset_path,
        "total_samples": result.total_samples,
        "train_samples": result.train_samples,
        "test_samples": result.test_samples,
        "smote_applied": result.smote_applied,
        "class_distribution_original": result.class_distribution_original,
        "selected_features": result.selected_features,
        "dropped_correlated_count": result.dropped_correlated_count,
        "best_model": result.best_model,
        "best_roc_auc": result.best_roc_auc,
        "models": result.models,
        "mi_scores": {k: round(v, 6) for k, v in artifacts.mi_scores.items()},
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=_json_default)


def _metrics_to_dict(m: ModelMetrics) -> Dict[str, float]:
    return {
        "accuracy": round(m.accuracy, 6),
        "precision": round(m.precision, 6),
        "recall": round(m.recall, 6),
        "f1": round(m.f1, 6),
        "roc_auc": round(m.roc_auc, 6),
        "cv_roc_auc_mean": round(m.cv_roc_auc_mean, 6),
        "cv_roc_auc_std": round(m.cv_roc_auc_std, 6),
    }


def _json_default(obj: Any) -> Any:
    if isinstance(obj, float) and (obj != obj):  # NaN
        return None
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        value = float(obj)
        return None if value != value else value
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
