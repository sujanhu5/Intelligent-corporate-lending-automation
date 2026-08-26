"""
ML Prediction endpoints.

Admin routes:
  POST  /predictions/train              — Train all models from the dataset
  GET   /predictions/model-status       — Check training status and metrics

Analyst+ routes:
  POST  /predictions/predict/{application_id} — Run ML prediction for an application
  GET   /predictions/{application_id}         — Retrieve stored prediction result
  GET   /predictions/{application_id}/summary — Lightweight summary for dashboard
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import get_client_ip, get_current_user, require_admin, require_analyst
from app.models.user import User
from app.schemas.prediction import (
    ModelStatusResponse,
    PredictionResponse,
    PredictionSummaryResponse,
    TrainingResponse,
)
from app.services.prediction_service import PredictionService

router = APIRouter()


# ---------------------------------------------------------------------------
# Train all models (admin only)
# ---------------------------------------------------------------------------

@router.post(
    "/train",
    response_model=TrainingResponse,
    status_code=status.HTTP_200_OK,
    summary="Train all ML models from the dataset",
    description=(
        "Trains Logistic Regression, Random Forest, and XGBoost on the configured "
        "dataset. Applies mutual-information feature selection (top 30), SMOTE for "
        "class imbalance, and 5-fold cross-validation. Persists model pkl files and "
        "metadata.json to the configured models directory. "
        "**This operation is CPU-intensive and may take several minutes.**"
    ),
)
def train_models(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TrainingResponse:
    return PredictionService(db).train_models(
        trained_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )


# ---------------------------------------------------------------------------
# Model status (any authenticated user)
# ---------------------------------------------------------------------------

@router.get(
    "/model-status",
    response_model=ModelStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check ML model training status",
    description=(
        "Returns whether trained models exist and, if so, their training metadata: "
        "best model name, ROC-AUC, training date, and per-model metrics."
    ),
)
def model_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModelStatusResponse:
    return PredictionService(db).get_model_status()


# ---------------------------------------------------------------------------
# Predict for application
# ---------------------------------------------------------------------------

@router.post(
    "/predict/{application_id}",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Run the ML prediction pipeline for an application",
    description=(
        "Maps the application's computed financial ratios to the model's trained "
        "feature space and runs inference using the best-performing model "
        "(selected by ROC-AUC from the most recent training run). "
        "Computes SHAP explanations, a composite risk score (0–100) weighted by "
        "both ML probability and rule engine outcome, and generates a recommendation.\n\n"
        "**Pre-conditions:** ratios must be calculated and rules must be evaluated.\n\n"
        "If mandatory rules failed (ml_should_run=False), the ML pipeline is skipped "
        "and a HIGH_RISK/100 record is created automatically. "
        "Idempotent — re-running overwrites the prior prediction."
    ),
)
def predict(
    request: Request,
    application_id: uuid.UUID,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> PredictionResponse:
    return PredictionService(db).predict_for_application(
        application_id=application_id,
        predicted_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )


# ---------------------------------------------------------------------------
# Retrieve stored prediction
# ---------------------------------------------------------------------------

@router.get(
    "/{application_id}",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve the stored ML prediction for an application",
)
def get_prediction(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PredictionResponse:
    return PredictionService(db).get_prediction(application_id)


# ---------------------------------------------------------------------------
# Summary for dashboard
# ---------------------------------------------------------------------------

@router.get(
    "/{application_id}/summary",
    response_model=PredictionSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Lightweight prediction summary for dashboard cards",
)
def get_prediction_summary(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PredictionSummaryResponse:
    return PredictionService(db).get_prediction_summary(application_id)
