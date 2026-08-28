"""
Predictor — loads trained model artefacts and runs inference for one sample.

Responsibilities:
  - Load model pkl (with embedded scaler + feature names) from disk.
  - Build a feature vector from computed financial ratios.
  - Predict probability of default.
  - Compute SHAP values for explainability.
  - Generate a natural-language explanation of the top contributing factors.

Model files are loaded lazily and cached in module-level dicts to avoid
redundant disk I/O across multiple prediction requests within the same
FastAPI process lifetime.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import shap

from app.core.exceptions import ModelNotTrainedError
from app.core.logging import get_logger
from ml.features import FeatureArtifacts, build_prediction_vector

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Ratio name → dataset feature name mapping (best-effort)
# ---------------------------------------------------------------------------
# When predicting, we have our 20 computed financial ratios. This map
# translates them to the closest equivalent column in the training dataset.
# Unmapped ratios fall back to the training-set median for that feature.

RATIO_TO_DATASET_FEATURE: Dict[str, str] = {
    "current_ratio":              "Current Ratio",
    "quick_ratio":                "Quick Ratio",
    "debt_equity_ratio":          "Total debt/Total net worth",
    "debt_ratio":                 "Debt ratio %",
    "return_on_assets":           "ROA(A) before interest and % after tax",
    "return_on_equity":           "Net Income to Stockholder's Equity",
    "interest_coverage_ratio":    "Interest Coverage Ratio (Interest expense to EBIT)",
    "asset_turnover":             "Total Asset Turnover",
    "inventory_turnover":         "Inventory Turnover Rate (times)",
    "receivable_turnover":        "Accounts Receivable Turnover",
    "cash_flow_ratio":            "Cash Flow to Liability",
    "operating_cash_flow_ratio":  "CFO to Assets",
    "gross_profit_margin":        "Gross Profit to Sales",
    "operating_margin":           "Operating Profit Rate",
    "net_profit_margin":          "Net Income to Total Assets",
    "ebitda_margin":              "Operating Gross Margin",
    "financial_leverage":         "Degree of Financial Leverage (DFL)",
    "debt_service_coverage_ratio":"Cash Flow to Liability",   # closest proxy
    "working_capital":            "Working Capital to Total Assets",
    "current_asset_ratio":        "Current Assets/Total Assets",
}

# Clean, human-readable display names for our own financial ratios. These are
# what appear in the SHAP table and the credit report — never the raw foreign
# dataset column names — so every explanation reflects the applicant's own
# genuine metrics.
RATIO_DISPLAY_NAMES: Dict[str, str] = {
    "current_ratio":              "Current Ratio",
    "quick_ratio":                "Quick Ratio",
    "debt_equity_ratio":          "Debt-to-Equity Ratio",
    "debt_ratio":                 "Debt Ratio",
    "return_on_assets":           "Return on Assets",
    "return_on_equity":           "Return on Equity",
    "interest_coverage_ratio":    "Interest Coverage Ratio",
    "asset_turnover":             "Asset Turnover",
    "inventory_turnover":         "Inventory Turnover",
    "receivable_turnover":        "Receivable Turnover",
    "cash_flow_ratio":            "Cash Flow Ratio",
    "operating_cash_flow_ratio":  "Operating Cash Flow Ratio",
    "gross_profit_margin":        "Gross Profit Margin",
    "operating_margin":           "Operating Margin",
    "net_profit_margin":          "Net Profit Margin",
    "ebitda_margin":              "EBITDA Margin",
    "financial_leverage":         "Financial Leverage",
    "debt_service_coverage_ratio":"Debt Service Coverage Ratio",
    "working_capital":            "Working Capital to Total Assets",
    "current_asset_ratio":        "Current Asset Ratio",
}

# Cache: model_key → loaded artifact dict
_model_cache: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class PredictionBundle:
    """Everything returned by a single predict() call."""

    def __init__(
        self,
        probability_of_default: float,
        shap_values: Dict[str, float],
        feature_importance: Dict[str, float],
        input_features: Dict[str, float],
        explanation_text: str,
        model_key: str,
    ) -> None:
        self.probability_of_default = probability_of_default
        self.shap_values = shap_values
        self.feature_importance = feature_importance
        self.input_features = input_features
        self.explanation_text = explanation_text
        self.model_key = model_key


def predict_for_application(
    ratio_values: Dict[str, Optional[float]],
    models_path: Path,
    model_key: str,
    top_shap_features: int = 15,
) -> PredictionBundle:
    """
    Build a feature vector from financial ratios and run inference.

    Args:
        ratio_values:     Dict of ratio_name → float value (our 20 computed ratios).
        models_path:      Directory where model pkl files are stored.
        model_key:        One of: "logistic_regression", "random_forest", "xgboost".
        top_shap_features: Number of top SHAP features to return.

    Returns:
        PredictionBundle with probability, SHAP values, and explanation.

    Raises:
        ModelNotTrainedError: if the required model file doesn't exist.
    """
    artifact = _load_artifact(models_path, model_key)
    model = artifact["model"]
    scaler = artifact["scaler"]
    feature_names: List[str] = artifact["feature_names"]
    feature_medians: Dict[str, float] = artifact["feature_medians"]

    # Reconstruct FeatureArtifacts (we only need selected_features/scaler/medians)
    fa = FeatureArtifacts(
        selected_features=feature_names,
        scaler=scaler,
        feature_medians=feature_medians,
        mi_scores={},
    )

    # ── Build and scale feature vector ───────────────────────────────────────
    X_scaled, populated = build_prediction_vector(
        ratio_values, fa, RATIO_TO_DATASET_FEATURE
    )

    # ── Predict probability ───────────────────────────────────────────────────
    if hasattr(model, "predict_proba"):
        prob = float(model.predict_proba(X_scaled)[0, 1])
    else:
        # Decision function fallback (SVM etc.)
        raw = float(model.decision_function(X_scaled)[0])
        prob = 1.0 / (1.0 + np.exp(-raw))   # sigmoid

    prob = max(0.0, min(1.0, prob))

    # ── SHAP explanation (over the raw dataset features) ──────────────────────
    shap_dict, _ = _compute_shap(model, X_scaled, feature_names, model_key)

    # ── Restrict + relabel to the applicant's GENUINE ratios ──────────────────
    # Only surface SHAP for features that were populated from real company data
    # and label them with our clean ratio names. Median-filled dataset columns
    # (identical for every applicant) are dropped so the explanation is truly
    # specific to this company rather than the same generic list every time.
    genuine_shap: Dict[str, float] = {}
    genuine_inputs: Dict[str, float] = {}
    for dataset_feature, ratio_name in populated.items():
        display = RATIO_DISPLAY_NAMES.get(ratio_name, ratio_name.replace("_", " ").title())
        sval = shap_dict.get(dataset_feature, 0.0)
        # If two ratios collide on one dataset feature, keep the larger |SHAP|.
        if display not in genuine_shap or abs(sval) > abs(genuine_shap[display]):
            genuine_shap[display] = sval
            rv = ratio_values.get(ratio_name)
            genuine_inputs[display] = float(rv) if rv is not None and np.isfinite(rv) else 0.0

    # Fallback: if nothing mapped (e.g. no ratios available), degrade gracefully
    # to the humanised raw features so the report is never blank.
    if not genuine_shap:
        genuine_shap = {
            _humanise(f): v for f, v in shap_dict.items()
        }

    top_shap = dict(
        sorted(genuine_shap.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_shap_features]
    )
    importance_dict = {k: abs(v) for k, v in top_shap.items()}

    # ── Natural-language explanation (uses the genuine ratio names) ───────────
    explanation = _build_explanation(prob, top_shap, model_key)

    logger.info(
        "Prediction complete",
        extra={
            "model": model_key,
            "prob_of_default": round(prob, 4),
            "genuine_features": len(populated),
            "top_driver": next(iter(top_shap), "N/A"),
        },
    )

    return PredictionBundle(
        probability_of_default=prob,
        shap_values=top_shap,
        feature_importance=importance_dict,
        input_features=genuine_inputs,
        explanation_text=explanation,
        model_key=model_key,
    )


def invalidate_cache() -> None:
    """Clear the in-memory model cache. Call after retraining."""
    _model_cache.clear()
    logger.info("Model cache invalidated")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _load_artifact(models_path: Path, model_key: str) -> Dict[str, Any]:
    if model_key in _model_cache:
        return _model_cache[model_key]

    _filename_map = {
        "logistic_regression": "logistic.pkl",
        "random_forest": "random_forest.pkl",
        "xgboost": "xgboost.pkl",
    }
    filename = _filename_map.get(model_key)
    if not filename:
        raise ModelNotTrainedError(
            message=f"Unknown model key '{model_key}'. "
            "Valid options: logistic_regression, random_forest, xgboost."
        )

    pkl_path = models_path / filename
    if not pkl_path.exists():
        raise ModelNotTrainedError(
            message=(
                f"Model '{model_key}' has not been trained yet. "
                "Run POST /predictions/train to train all models before predicting."
            )
        )

    artifact = joblib.load(pkl_path)
    _model_cache[model_key] = artifact
    logger.debug("Model loaded from disk", extra={"model": model_key, "path": str(pkl_path)})
    return artifact


def _compute_shap(
    model: Any,
    X_scaled: np.ndarray,
    feature_names: List[str],
    model_key: str,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Compute SHAP values for the single sample X_scaled."""
    try:
        if model_key in ("random_forest", "xgboost"):
            explainer = shap.TreeExplainer(model)
            sv = explainer.shap_values(X_scaled)
            # TreeExplainer for binary classifiers returns list[array] or single array
            if isinstance(sv, list):
                shap_arr = sv[1][0]   # class-1 SHAP values for sample 0
            else:
                shap_arr = sv[0]      # single output
        else:
            # Logistic Regression → LinearExplainer
            background = shap.maskers.Independent(X_scaled, max_samples=1)
            explainer = shap.LinearExplainer(model, background)
            sv = explainer.shap_values(X_scaled)
            shap_arr = sv[0] if sv.ndim == 2 else sv

        shap_dict = {
            fname: float(shap_arr[i])
            for i, fname in enumerate(feature_names)
        }
    except Exception as exc:
        logger.warning("SHAP computation failed", extra={"error": str(exc)})
        shap_dict = {fname: 0.0 for fname in feature_names}

    # Feature importance (absolute SHAP for single sample)
    importance_dict = {k: abs(v) for k, v in shap_dict.items()}
    return shap_dict, importance_dict


def _build_explanation(
    probability: float,
    top_shap: Dict[str, float],
    model_key: str,
) -> str:
    """Generate a brief natural-language explanation for the prediction."""
    pct = round(probability * 100, 1)
    model_label = {
        "logistic_regression": "Logistic Regression",
        "random_forest": "Random Forest",
        "xgboost": "XGBoost",
    }.get(model_key, model_key)

    if probability >= 0.7:
        risk_sentence = (
            f"The {model_label} model assigns a high probability of default ({pct}%), "
            "indicating significant credit risk."
        )
    elif probability >= 0.4:
        risk_sentence = (
            f"The {model_label} model assigns a moderate probability of default ({pct}%), "
            "warranting careful review."
        )
    else:
        risk_sentence = (
            f"The {model_label} model assigns a low probability of default ({pct}%), "
            "suggesting acceptable credit risk."
        )

    # Keys are already clean, applicant-specific ratio names. Positive SHAP
    # pushes toward default (higher risk); negative SHAP reduces it.
    positive_drivers = [
        k for k, v in sorted(top_shap.items(), key=lambda kv: kv[1], reverse=True)
        if v > 0.01
    ][:3]
    negative_drivers = [
        k for k, v in sorted(top_shap.items(), key=lambda kv: kv[1])
        if v < -0.01
    ][:3]

    parts = [risk_sentence]

    if positive_drivers:
        driver_str = ", ".join(f"'{f}'" for f in positive_drivers)
        parts.append(f"Key factors increasing default risk: {driver_str}.")
    if negative_drivers:
        driver_str = ", ".join(f"'{f}'" for f in negative_drivers)
        parts.append(f"Mitigating factors reducing default risk: {driver_str}.")

    if not positive_drivers and not negative_drivers:
        parts.append(
            "No single financial ratio dominates the assessment — the outcome "
            "reflects the combined effect of the applicant's overall profile."
        )

    return " ".join(parts)


def _humanise(feature_name: str) -> str:
    """Convert a dataset column name to a short readable label."""
    # Already readable in most cases — just strip excessive parentheses
    name = feature_name
    if "(" in name and len(name) > 40:
        name = name[:name.index("(")].strip()
    return name
