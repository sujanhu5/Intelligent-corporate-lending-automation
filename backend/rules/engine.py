"""
Rule Engine — stateless evaluator.

Evaluates a list of Rule objects against a dictionary of metric values
(ratio name → float). Returns a structured RuleEngineResult that the
service layer persists and the report generator reads.

Evaluation contract:
  - Rule.evaluate(value) returns True when the condition is triggered
    (i.e., the metric is in a bad state) and the action should fire.
  - A None metric value is treated as "triggered" (conservative: data
    gaps are unsafe, not safe).
  - Rules are evaluated in priority order (lowest int first).
  - If ANY mandatory rule triggers → overall_outcome = "reject",
    ml_should_run = False (ML pipeline is skipped entirely).
  - If no mandatory rule triggers but ≥1 advisory rule triggers →
    overall_outcome = "manual_review", ml_should_run = True.
  - If all rules pass → overall_outcome = "pass", ml_should_run = True.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.rule import Operator, Rule, RuleAction


@dataclass
class RuleResult:
    """Result for one evaluated rule."""
    rule_id: str
    rule_name: str
    category: str
    metric_field: str
    operator: str
    threshold: Optional[float]
    metric_value: Optional[float]
    triggered: bool
    is_mandatory: bool
    action: str
    priority: int
    message: str


@dataclass
class RuleEngineResult:
    """Aggregated output from one evaluation pass."""
    overall_outcome: str          # "pass" | "manual_review" | "reject"
    ml_should_run: bool
    evaluated_at: str             # ISO-8601 UTC
    total_rules: int
    triggered_count: int
    mandatory_failures: List[str]   # names of mandatory rules that triggered
    advisory_triggers: List[str]    # names of advisory rules that triggered
    passed_rules: List[str]         # names of rules that did not trigger
    skipped_rules: List[str]        # rules where metric was None
    results: List[RuleResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a JSON-safe dict for JSONB storage."""
        return {
            "overall_outcome": self.overall_outcome,
            "ml_should_run": self.ml_should_run,
            "evaluated_at": self.evaluated_at,
            "total_rules": self.total_rules,
            "triggered_count": self.triggered_count,
            "mandatory_failures": self.mandatory_failures,
            "advisory_triggers": self.advisory_triggers,
            "passed_rules": self.passed_rules,
            "skipped_rules": self.skipped_rules,
            "results": [
                {
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "category": r.category,
                    "metric_field": r.metric_field,
                    "operator": r.operator,
                    "threshold": r.threshold,
                    "metric_value": r.metric_value,
                    "triggered": r.triggered,
                    "is_mandatory": r.is_mandatory,
                    "action": r.action,
                    "priority": r.priority,
                    "message": r.message,
                }
                for r in self.results
            ],
        }


def evaluate_rules(
    rules: List[Rule],
    ratios: Dict[str, Any],
) -> RuleEngineResult:
    """
    Evaluate all rules against the computed ratio values.

    Args:
        rules:  Active Rule ORM objects, already sorted by priority ascending.
        ratios: The FinancialRatio.ratios JSONB dict:
                { "current_ratio": {"value": 1.85, ...}, ... }

    Returns:
        RuleEngineResult with per-rule detail and aggregated outcome.
    """
    results: List[RuleResult] = []
    mandatory_failures: List[str] = []
    advisory_triggers: List[str] = []
    passed_rules: List[str] = []
    skipped_rules: List[str] = []

    for rule in rules:
        metric_entry = ratios.get(rule.metric_field, {})
        if isinstance(metric_entry, dict):
            metric_value: Optional[float] = metric_entry.get("value")
        else:
            metric_value = None

        value_was_none = metric_value is None
        triggered = rule.evaluate(metric_value)

        message = _build_message(rule, metric_value, triggered)

        result = RuleResult(
            rule_id=str(rule.id),
            rule_name=rule.name,
            category=rule.category.value,
            metric_field=rule.metric_field,
            operator=rule.operator.value,
            threshold=float(rule.threshold) if rule.threshold is not None else None,
            metric_value=metric_value,
            triggered=triggered,
            is_mandatory=rule.is_mandatory,
            action=rule.action.value,
            priority=rule.priority,
            message=message,
        )
        results.append(result)

        if value_was_none:
            skipped_rules.append(rule.name)

        if triggered:
            if rule.is_mandatory:
                mandatory_failures.append(rule.name)
            else:
                advisory_triggers.append(rule.name)
        else:
            if not value_was_none:
                passed_rules.append(rule.name)

    # ── Determine overall outcome ────────────────────────────────────────────
    if mandatory_failures:
        overall_outcome = "reject"
        ml_should_run = False
    elif advisory_triggers:
        overall_outcome = "manual_review"
        ml_should_run = True
    else:
        overall_outcome = "pass"
        ml_should_run = True

    return RuleEngineResult(
        overall_outcome=overall_outcome,
        ml_should_run=ml_should_run,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        total_rules=len(rules),
        triggered_count=len(mandatory_failures) + len(advisory_triggers),
        mandatory_failures=mandatory_failures,
        advisory_triggers=advisory_triggers,
        passed_rules=passed_rules,
        skipped_rules=skipped_rules,
        results=results,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_OPERATOR_PHRASES: Dict[str, str] = {
    Operator.LT.value:          "is below the minimum threshold of",
    Operator.LTE.value:         "is at or below the minimum threshold of",
    Operator.GT.value:          "exceeds the maximum threshold of",
    Operator.GTE.value:         "meets or exceeds the maximum threshold of",
    Operator.EQ.value:          "equals the trigger value of",
    Operator.NEQ.value:         "does not equal the required value of",
    Operator.IS_NEGATIVE.value: "is negative (below zero)",
    Operator.IS_POSITIVE.value: "is positive (above zero)",
}

_FIELD_DISPLAY: Dict[str, str] = {
    "current_ratio":              "Current Ratio",
    "quick_ratio":                "Quick Ratio",
    "debt_equity_ratio":          "Debt-to-Equity Ratio",
    "debt_ratio":                 "Debt Ratio",
    "gross_profit_margin":        "Gross Profit Margin",
    "operating_margin":           "Operating Margin",
    "net_profit_margin":          "Net Profit Margin",
    "return_on_assets":           "Return on Assets",
    "return_on_equity":           "Return on Equity",
    "interest_coverage_ratio":    "Interest Coverage Ratio",
    "cash_flow_ratio":            "Cash Flow Ratio",
    "operating_cash_flow_ratio":  "Operating Cash Flow Ratio",
    "debt_service_coverage_ratio":"Debt Service Coverage Ratio",
    "asset_turnover":             "Asset Turnover",
    "inventory_turnover":         "Inventory Turnover",
    "receivable_turnover":        "Receivable Turnover",
    "ebitda_margin":              "EBITDA Margin",
    "financial_leverage":         "Financial Leverage",
    "working_capital":            "Working Capital",
    "current_asset_ratio":        "Current Asset Ratio",
}


def _build_message(rule: Rule, value: Optional[float], triggered: bool) -> str:
    """Produce a human-readable message for a rule evaluation result."""
    field_name = _FIELD_DISPLAY.get(rule.metric_field, rule.metric_field.replace("_", " ").title())

    if value is None:
        if triggered:
            return (
                f"'{field_name}' could not be extracted from the financial documents. "
                "The rule was triggered as a precaution — missing data cannot be considered safe."
            )
        return f"'{field_name}' is unavailable — rule skipped (non-mandatory)."

    value_fmt = _fmt_value(value)

    if triggered:
        # Use the rule's custom failure message if configured
        if rule.failure_message:
            return rule.failure_message.replace("{value}", value_fmt).replace(
                "{threshold}", _fmt_value(rule.threshold)
            )
        op_phrase = _OPERATOR_PHRASES.get(rule.operator.value, f"fails the '{rule.operator.value}' check against")
        threshold_str = (
            f" {_fmt_value(rule.threshold)}"
            if rule.operator.value not in (Operator.IS_NEGATIVE.value, Operator.IS_POSITIVE.value)
            else ""
        )
        return (
            f"{field_name} ({value_fmt}){op_phrase}{threshold_str}. "
            f"Action: {rule.action.value.replace('_', ' ')}."
        )
    else:
        if rule.pass_message:
            return rule.pass_message.replace("{value}", value_fmt)
        op_phrase = _OPERATOR_PHRASES.get(rule.operator.value, "passes")
        return f"{field_name} ({value_fmt}) — rule condition not triggered. Acceptable."


def _fmt_value(v: Optional[float]) -> str:
    if v is None:
        return "N/A"
    if abs(v) >= 1_000_000:
        return f"{v:,.0f}"
    if v == int(v):
        return f"{int(v)}"
    return f"{v:.4f}".rstrip("0").rstrip(".")
