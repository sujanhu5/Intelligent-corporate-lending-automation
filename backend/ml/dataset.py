"""
Dataset loader and validator for the ML training pipeline.

Responsibilities:
  - Load the CSV from the configured path (never hardcoded).
  - Validate structure: target column present, minimum row count, no all-NaN columns.
  - Separate features from target, apply minimal preprocessing (drop constant
    columns, drop columns with >50% missing values).
  - Return a DatasetBundle that the feature engineering step consumes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.core.exceptions import DatasetValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)

_MIN_ROWS = 100
_MAX_MISSING_RATIO = 0.50       # drop columns with >50% missing values
_CONSTANT_VARIANCE_THRESHOLD = 1e-8  # drop near-zero-variance columns


@dataclass
class DatasetBundle:
    """All artefacts produced by the dataset loading step."""
    X: pd.DataFrame                          # features only, cleaned
    y: pd.Series                             # target (0/1)
    feature_names: List[str]                 # column names in X
    target_column: str
    total_rows: int
    dropped_columns: List[str] = field(default_factory=list)
    class_counts: Dict[int, int] = field(default_factory=dict)


def load_dataset(
    path: Path,
    config: Dict[str, Any],
) -> DatasetBundle:
    """
    Load and validate the training dataset.

    Args:
        path:   Absolute path to the CSV file.
        config: The 'dataset' section from feature_config.json.

    Returns:
        DatasetBundle ready for feature engineering.

    Raises:
        DatasetValidationError: on any structural problem.
    """
    target_col: str = config.get("target_column", "Bankrupt?")

    if not path.exists():
        raise DatasetValidationError(
            message=(
                f"Dataset file not found at '{path}'. "
                "Ensure DATASET_PATH in .env points to the correct CSV file."
            )
        )

    logger.info("Loading dataset", extra={"path": str(path)})

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise DatasetValidationError(
            message=f"Failed to read dataset CSV: {exc}"
        ) from exc

    # Strip leading/trailing whitespace from column names (common CSV artifact)
    df.columns = df.columns.str.strip()

    if target_col not in df.columns:
        available = list(df.columns[:10])
        raise DatasetValidationError(
            message=(
                f"Target column '{target_col}' not found in the dataset. "
                f"First 10 columns: {available}. "
                "Update 'target_column' in config/feature_config.json."
            )
        )

    if len(df) < _MIN_ROWS:
        raise DatasetValidationError(
            message=(
                f"Dataset has only {len(df)} rows — minimum {_MIN_ROWS} required "
                "for reliable model training."
            )
        )

    # ── Separate target ───────────────────────────────────────────────────────
    y = df[target_col].astype(int)
    X = df.drop(columns=[target_col])

    # ── Drop non-numeric columns (we have no categorical encoding in config) ──
    non_numeric = X.select_dtypes(exclude=[np.number]).columns.tolist()
    if non_numeric:
        X = X.drop(columns=non_numeric)
        logger.debug("Dropped non-numeric columns", extra={"columns": non_numeric})

    dropped: List[str] = list(non_numeric)

    # ── Drop columns with >50% missing values ────────────────────────────────
    missing_ratio = X.isnull().mean()
    high_missing = missing_ratio[missing_ratio > _MAX_MISSING_RATIO].index.tolist()
    if high_missing:
        X = X.drop(columns=high_missing)
        dropped.extend(high_missing)
        logger.debug(
            "Dropped high-missing columns",
            extra={"count": len(high_missing)},
        )

    # ── Drop near-zero-variance columns ──────────────────────────────────────
    variance = X.var(numeric_only=True)
    near_zero_var = variance[variance < _CONSTANT_VARIANCE_THRESHOLD].index.tolist()
    if near_zero_var:
        X = X.drop(columns=near_zero_var)
        dropped.extend(near_zero_var)

    class_counts = dict(y.value_counts().sort_index().astype(int))

    logger.info(
        "Dataset loaded",
        extra={
            "rows": len(df),
            "features_after_cleaning": X.shape[1],
            "dropped": len(dropped),
            "class_distribution": class_counts,
        },
    )

    return DatasetBundle(
        X=X,
        y=y,
        feature_names=list(X.columns),
        target_column=target_col,
        total_rows=len(df),
        dropped_columns=dropped,
        class_counts=class_counts,
    )


def load_feature_config(config_path: Path) -> Dict[str, Any]:
    """Load feature_config.json from the given path."""
    if not config_path.exists():
        raise DatasetValidationError(
            message=f"Feature config file not found: '{config_path}'."
        )
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)
