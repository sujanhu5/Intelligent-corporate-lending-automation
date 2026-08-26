"""
Feature engineering for the ML training pipeline.

Steps (in order):
  1. Median imputation for missing values.
  2. Remove highly correlated features (correlation_threshold from config).
  3. Select top-K features by mutual information with the target.
  4. StandardScaler normalisation (fitted on training data only).
  5. Optional SMOTE oversampling for class imbalance.

All fitted objects (imputer medians, scaler, selected feature names) are
returned for persistence alongside the trained model — so prediction time
can reproduce the exact same transformation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif
from sklearn.preprocessing import StandardScaler

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FeatureArtifacts:
    """All fitted artefacts produced by the feature engineering step."""
    selected_features: List[str]         # final feature names used in training
    scaler: StandardScaler               # fitted on training data
    feature_medians: Dict[str, float]    # median per feature (for imputation at predict time)
    mi_scores: Dict[str, float]          # mutual information score per feature
    dropped_correlated: List[str] = field(default_factory=list)


def engineer_features(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    config: Dict[str, Any],
) -> Tuple[np.ndarray, np.ndarray, FeatureArtifacts]:
    """
    Apply the full feature engineering pipeline to training and test sets.

    Returns:
        (X_train_scaled, X_test_scaled, FeatureArtifacts)
    """
    fs_config = config.get("feature_selection", {})
    top_k: int = fs_config.get("top_k", 30)
    corr_threshold: float = fs_config.get("correlation_threshold", 0.95)

    # ── 1. Median imputation ──────────────────────────────────────────────────
    feature_medians: Dict[str, float] = {
        col: float(X_train[col].median()) for col in X_train.columns
    }
    X_train = X_train.fillna(feature_medians)
    X_test = X_test.fillna(feature_medians)

    # ── 2. Remove highly correlated features ──────────────────────────────────
    X_train, X_test, dropped_corr = _drop_correlated(X_train, X_test, corr_threshold)

    # ── 3. Select top-K features by mutual information ────────────────────────
    k = min(top_k, X_train.shape[1])
    mi_scores_arr = mutual_info_classif(
        X_train.values, y_train.values, random_state=42
    )
    mi_scores: Dict[str, float] = dict(zip(X_train.columns, mi_scores_arr.tolist()))

    ranked = sorted(mi_scores.items(), key=lambda kv: kv[1], reverse=True)
    selected_features: List[str] = [name for name, _ in ranked[:k]]

    X_train_sel = X_train[selected_features]
    X_test_sel = X_test[selected_features]

    logger.info(
        "Feature selection complete",
        extra={
            "total_after_corr_drop": len(X_train.columns),
            "selected": k,
            "top_5_features": [name for name, _ in ranked[:5]],
        },
    )

    # ── 4. StandardScaler ─────────────────────────────────────────────────────
    scaler = StandardScaler()
    X_train_scaled: np.ndarray = scaler.fit_transform(X_train_sel.values)
    X_test_scaled: np.ndarray = scaler.transform(X_test_sel.values)

    artifacts = FeatureArtifacts(
        selected_features=selected_features,
        scaler=scaler,
        feature_medians={k: feature_medians[k] for k in selected_features},
        mi_scores={k: mi_scores[k] for k in selected_features},
        dropped_correlated=dropped_corr,
    )

    return X_train_scaled, X_test_scaled, artifacts


def apply_smote(
    X_train: np.ndarray,
    y_train: np.ndarray,
    random_state: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Apply SMOTE to oversample the minority class.
    Falls back gracefully if imbalanced-learn is not installed.
    """
    try:
        from imblearn.over_sampling import SMOTE
        smote = SMOTE(random_state=random_state)
        X_res, y_res = smote.fit_resample(X_train, y_train)
        before = dict(zip(*np.unique(y_train, return_counts=True)))
        after = dict(zip(*np.unique(y_res, return_counts=True)))
        logger.info("SMOTE applied", extra={"before": before, "after": after})
        return X_res, y_res
    except ImportError:
        logger.warning(
            "imbalanced-learn not installed — SMOTE skipped. "
            "Install with: pip install imbalanced-learn"
        )
        return X_train, y_train


def build_prediction_vector(
    ratio_values: Dict[str, Optional[float]],
    feature_artifacts: FeatureArtifacts,
    ratio_to_feature_map: Dict[str, str],
) -> np.ndarray:
    """
    Build and scale a single-sample feature vector for prediction.

    Strategy:
      1. Fill all selected features with their training-set medians.
      2. Override with actual ratio values where a mapping exists.
      3. Apply the fitted scaler.

    Returns:
        Scaled feature vector, shape (1, n_selected_features).
    """
    # Start with medians
    vector: Dict[str, float] = dict(feature_artifacts.feature_medians)

    # Override mapped features with actual computed ratio values
    for ratio_name, dataset_feature in ratio_to_feature_map.items():
        if dataset_feature in vector:
            val = ratio_values.get(ratio_name)
            if val is not None and np.isfinite(val):
                vector[dataset_feature] = float(val)

    # Build array in the exact order of selected_features
    arr = np.array(
        [vector.get(f, 0.0) for f in feature_artifacts.selected_features],
        dtype=np.float64,
    ).reshape(1, -1)

    return feature_artifacts.scaler.transform(arr)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _drop_correlated(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    threshold: float,
) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    """Remove features whose pairwise Pearson correlation exceeds threshold."""
    corr_matrix = X_train.corr(numeric_only=True).abs()
    upper = corr_matrix.where(
        np.triu(np.ones(corr_matrix.shape, dtype=bool), k=1)
    )
    to_drop = [col for col in upper.columns if any(upper[col] > threshold)]
    if to_drop:
        X_train = X_train.drop(columns=to_drop)
        X_test = X_test.drop(columns=to_drop, errors="ignore")
        logger.debug(
            "Dropped correlated features",
            extra={"count": len(to_drop)},
        )
    return X_train, X_test, to_drop
