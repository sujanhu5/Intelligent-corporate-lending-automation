"""
Risk scorer — combines ML probability of default with rule engine context
to produce a composite 0–100 risk score and a labelled risk level.

Formula (from feature_config.json risk_scoring section):
  risk_score = probability_weight * (prob * 100) + rule_engine_weight * rule_contribution

Rule contribution:
  - no rules triggered        →   0
  - advisory rules triggered  →  50
  - mandatory rules failed    → 100  (though ML is skipped in that case)

Risk level from score:
  0–20   → very_low
  21–40  → low
  41–60  → medium
  61–80  → high
  81–100 → very_high
"""

from __future__ import annotations

from typing import Any, Dict, Tuple


_DEFAULT_PROB_WEIGHT = 0.70
_DEFAULT_RULE_WEIGHT = 0.30

_RISK_LEVELS = [
    (20.0,  "very_low"),
    (40.0,  "low"),
    (60.0,  "medium"),
    (80.0,  "high"),
    (100.0, "very_high"),
]

# Rule contribution scores
_RULE_CONTRIBUTION = {
    "pass":          0.0,
    "manual_review": 50.0,
    "reject":        100.0,
}


def compute_risk_score(
    probability_of_default: float,
    rule_outcome: str,
    risk_scoring_config: Dict[str, Any],
) -> Tuple[float, str]:
    """
    Calculate the composite risk score and level.

    Args:
        probability_of_default: Float in [0, 1] from the ML model.
        rule_outcome:           "pass" | "manual_review" | "reject".
        risk_scoring_config:    The 'risk_scoring' section from feature_config.json.

    Returns:
        (risk_score_0_to_100, risk_level_string)
    """
    prob_weight: float = risk_scoring_config.get("probability_weight", _DEFAULT_PROB_WEIGHT)
    rule_weight: float = risk_scoring_config.get("rule_engine_weight", _DEFAULT_RULE_WEIGHT)

    ml_contribution = probability_of_default * 100.0
    rule_contribution = _RULE_CONTRIBUTION.get(rule_outcome, 0.0)

    raw_score = prob_weight * ml_contribution + rule_weight * rule_contribution
    score = round(max(0.0, min(100.0, raw_score)), 2)

    return score, get_risk_level(score)


def get_risk_level(score: float) -> str:
    """Map a 0–100 score to a labelled risk level."""
    for threshold, label in _RISK_LEVELS:
        if score <= threshold:
            return label
    return "very_high"


def build_recommendation(
    probability_of_default: float,
    risk_score: float,
    risk_level: str,
    rule_outcome: str,
    mandatory_failures: list,
    advisory_triggers: list,
    model_key: str,
) -> str:
    """
    Compose a recommendation paragraph for the loan officer.

    The recommendation integrates rule engine results + ML prediction
    into a single actionable paragraph.
    """
    model_label = {
        "logistic_regression": "Logistic Regression",
        "random_forest": "Random Forest",
        "xgboost": "XGBoost",
    }.get(model_key, model_key)

    pct = round(probability_of_default * 100, 1)
    score_str = f"{risk_score:.1f}/100"

    lines = []

    if rule_outcome == "reject":
        failed = ", ".join(mandatory_failures[:3])
        extra = f" and {len(mandatory_failures) - 3} more" if len(mandatory_failures) > 3 else ""
        lines.append(
            f"RECOMMENDATION: DECLINE — The loan application has been automatically rejected "
            f"by the rule engine. The following mandatory banking rules were violated: "
            f"{failed}{extra}. The ML pipeline was not executed."
        )
    elif risk_level == "very_high":
        lines.append(
            f"RECOMMENDATION: DECLINE — The composite risk score of {score_str} is in the "
            f"'Very High' range. The {model_label} model estimates a {pct}% probability of default. "
            "This application should be declined unless exceptional mitigating circumstances exist."
        )
    elif risk_level == "high":
        lines.append(
            f"RECOMMENDATION: MANUAL REVIEW — The composite risk score of {score_str} is in the "
            f"'High' range. The {model_label} model estimates a {pct}% probability of default. "
            "Detailed due diligence and collateral assessment are strongly recommended before approval."
        )
    elif risk_level == "medium" or rule_outcome == "manual_review":
        advisory = (
            f" Additionally, {len(advisory_triggers)} advisory rule(s) triggered: "
            + ", ".join(advisory_triggers[:3])
            + "."
        ) if advisory_triggers else ""
        lines.append(
            f"RECOMMENDATION: CONDITIONAL APPROVAL — The composite risk score of {score_str} "
            f"is in the 'Medium' range. The {model_label} model estimates a {pct}% probability "
            f"of default.{advisory} Approval may be considered with appropriate covenants, "
            "enhanced collateral requirements, or a reduced loan amount."
        )
    elif risk_level == "low":
        lines.append(
            f"RECOMMENDATION: APPROVE WITH STANDARD TERMS — The composite risk score of "
            f"{score_str} is in the 'Low' range. The {model_label} model estimates a {pct}% "
            "probability of default. Standard loan terms are appropriate."
        )
    else:  # very_low
        lines.append(
            f"RECOMMENDATION: APPROVE — The composite risk score of {score_str} is in the "
            f"'Very Low' range. The {model_label} model estimates a {pct}% probability of default. "
            "This application represents a low-risk lending opportunity."
        )

    return " ".join(lines)
