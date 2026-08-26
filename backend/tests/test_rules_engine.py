"""Unit tests for the rule engine evaluator (no DB needed)."""

import pytest
from unittest.mock import MagicMock
from rules.engine import evaluate_rules, RuleResult, RuleEngineResult


def _make_rule(name, field, operator, threshold=None, is_mandatory=True, action="reject", priority=10):
    rule = MagicMock()
    rule.id = f"fake-{name}"
    rule.name = name
    rule.metric_field = field
    rule.operator = MagicMock(value=operator)
    rule.threshold = threshold
    rule.is_mandatory = is_mandatory
    rule.action = MagicMock(value=action)
    rule.category = MagicMock(value="liquidity")
    rule.priority = priority
    rule.failure_message = None
    rule.pass_message = None
    return rule


class TestEvaluateRules:
    def test_all_pass(self):
        rules = [
            _make_rule("Current Ratio", "current_ratio", "gte", 1.0),
        ]
        rules[0].evaluate.return_value = False

        ratios = {"current_ratio": {"value": 2.5}}
        result = evaluate_rules(rules, ratios)

        assert result.overall_outcome == "pass"
        assert result.ml_should_run is True
        assert result.triggered_count == 0
        assert len(result.passed_rules) == 1

    def test_mandatory_failure_rejects(self):
        rules = [
            _make_rule("Current Ratio", "current_ratio", "lt", 1.0, is_mandatory=True),
        ]
        rules[0].evaluate.return_value = True

        ratios = {"current_ratio": {"value": 0.5}}
        result = evaluate_rules(rules, ratios)

        assert result.overall_outcome == "reject"
        assert result.ml_should_run is False
        assert len(result.mandatory_failures) == 1

    def test_advisory_trigger_manual_review(self):
        rules = [
            _make_rule("Profit Margin", "net_profit_margin", "lt", 0.05,
                        is_mandatory=False, action="manual_review"),
        ]
        rules[0].evaluate.return_value = True

        ratios = {"net_profit_margin": {"value": 0.02}}
        result = evaluate_rules(rules, ratios)

        assert result.overall_outcome == "manual_review"
        assert result.ml_should_run is True
        assert len(result.advisory_triggers) == 1

    def test_missing_metric_triggers_mandatory(self):
        rules = [
            _make_rule("Current Ratio", "current_ratio", "gte", 1.0),
        ]
        rules[0].evaluate.return_value = True

        ratios = {}
        result = evaluate_rules(rules, ratios)

        assert result.overall_outcome == "reject"
        assert len(result.skipped_rules) == 1

    def test_multiple_rules_mixed(self):
        mandatory = _make_rule("M1", "current_ratio", "gte", 1.0, is_mandatory=True)
        mandatory.evaluate.return_value = False

        advisory = _make_rule("A1", "net_profit_margin", "lt", 0.05,
                              is_mandatory=False, action="manual_review")
        advisory.evaluate.return_value = True

        ratios = {
            "current_ratio": {"value": 2.0},
            "net_profit_margin": {"value": 0.01},
        }
        result = evaluate_rules([mandatory, advisory], ratios)

        assert result.overall_outcome == "manual_review"
        assert result.ml_should_run is True

    def test_mandatory_overrides_advisory(self):
        mandatory = _make_rule("M1", "current_ratio", "lt", 1.0, is_mandatory=True)
        mandatory.evaluate.return_value = True

        advisory = _make_rule("A1", "net_profit_margin", "lt", 0.05,
                              is_mandatory=False, action="manual_review")
        advisory.evaluate.return_value = True

        ratios = {
            "current_ratio": {"value": 0.5},
            "net_profit_margin": {"value": 0.01},
        }
        result = evaluate_rules([mandatory, advisory], ratios)

        assert result.overall_outcome == "reject"
        assert result.ml_should_run is False

    def test_result_serialization(self):
        rules = [
            _make_rule("Test Rule", "current_ratio", "gte", 1.0),
        ]
        rules[0].evaluate.return_value = False

        ratios = {"current_ratio": {"value": 2.0}}
        result = evaluate_rules(rules, ratios)

        d = result.to_dict()
        assert isinstance(d, dict)
        assert "overall_outcome" in d
        assert "results" in d
        assert len(d["results"]) == 1

    def test_empty_rules(self):
        result = evaluate_rules([], {})
        assert result.overall_outcome == "pass"
        assert result.ml_should_run is True
        assert result.total_rules == 0
