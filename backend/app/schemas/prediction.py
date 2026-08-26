"""
Pydantic schemas for ML prediction and model training endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.prediction import ModelUsed, PredictionOutcome, RiskLevel


# ---------------------------------------------------------------------------
# Training schemas
# ---------------------------------------------------------------------------

class ModelMetricsSchema(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    cv_roc_auc_mean: float
    cv_roc_auc_std: float


class TrainingResponse(BaseModel):
    """Returned by POST /predictions/train."""
    trained_at: str
    dataset_path: str
    total_samples: int
    train_samples: int
    test_samples: int
    smote_applied: bool
    class_distribution_original: Dict[str, int]
    selected_features: List[str]
    dropped_correlated_count: int
    best_model: str
    best_roc_auc: float
    models: Dict[str, Dict[str, float]]   # model_key → metric_name → value


class ModelStatusResponse(BaseModel):
    """Returned by GET /predictions/model-status."""
    model_config = {"protected_namespaces": ()}

    models_trained: bool
    trained_at: Optional[str]
    best_model: Optional[str]
    best_roc_auc: Optional[float]
    selected_feature_count: Optional[int]
    total_training_samples: Optional[int]
    model_metrics: Optional[Dict[str, Dict[str, float]]]


# ---------------------------------------------------------------------------
# Prediction schemas
# ---------------------------------------------------------------------------

class PredictionResponse(BaseModel):
    """Full prediction result for one application."""
    id: uuid.UUID
    application_id: uuid.UUID
    model_used: ModelUsed
    model_version: Optional[str]

    # Core prediction
    probability_of_default: float = Field(
        description="Probability of default in [0, 1]"
    )
    outcome: PredictionOutcome

    # Risk score
    risk_score: float = Field(description="Composite risk score, 0–100")
    risk_level: RiskLevel

    # SHAP — top contributing features
    shap_values: Optional[Dict[str, float]]
    feature_importance: Optional[Dict[str, float]]

    # Human-readable output
    explanation_text: Optional[str]
    recommendation: Optional[str]

    # Whether ML ran
    ml_executed: bool
    skip_reason: Optional[str]

    # Model comparison metrics (all 3 models from training run)
    model_metrics: Optional[Dict[str, Any]]

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class PredictionSummaryResponse(BaseModel):
    """Lightweight summary for dashboard cards."""
    application_id: uuid.UUID
    risk_score: Optional[float]
    risk_level: Optional[RiskLevel]
    probability_of_default: Optional[float]
    outcome: Optional[PredictionOutcome]
    model_used: Optional[ModelUsed]
    ml_executed: bool
    recommendation_headline: Optional[str]
    created_at: Optional[datetime]
