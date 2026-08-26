"""ORM model — rules table.

Each row is one editable banking rule. Rules are evaluated by the rule engine
in priority order. Rules are categorised as mandatory (auto-reject on failure)
or advisory (trigger manual review).
"""

from __future__ import annotations

import enum
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, PgEnum


class RuleCategory(str, enum.Enum):
    LIQUIDITY = "liquidity"
    SOLVENCY = "solvency"
    PROFITABILITY = "profitability"
    CASH_FLOW = "cash_flow"
    LEVERAGE = "leverage"
    COVERAGE = "coverage"
    QUALITATIVE = "qualitative"
    REGULATORY = "regulatory"


class RuleAction(str, enum.Enum):
    REJECT = "reject"
    MANUAL_REVIEW = "manual_review"
    FLAG = "flag"          # flag for attention but continue pipeline


class Operator(str, enum.Enum):
    LT = "lt"    # less than
    LTE = "lte"  # less than or equal
    GT = "gt"    # greater than
    GTE = "gte"  # greater than or equal
    EQ = "eq"    # equal
    NEQ = "neq"  # not equal
    IS_NEGATIVE = "is_negative"   # value < 0
    IS_POSITIVE = "is_positive"   # value > 0


class Rule(Base):
    __tablename__ = "rules"

    # Display
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[RuleCategory] = mapped_column(
        PgEnum(RuleCategory, name="rule_category"), nullable=False
    )

    # Condition: the ratio/metric field name (must match a key in FinancialRatio.ratios)
    metric_field: Mapped[str] = mapped_column(String(100), nullable=False)

    # Operator + threshold define the condition that triggers the action
    operator: Mapped[Operator] = mapped_column(
        PgEnum(Operator, name="rule_operator"), nullable=False
    )
    threshold: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)

    # Action when condition evaluates to True
    action: Mapped[RuleAction] = mapped_column(
        PgEnum(RuleAction, name="rule_action"), nullable=False
    )

    # A mandatory rule that fails causes immediate rejection without ML
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Enabled/disabled without deletion
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Priority — lower number = evaluated first
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # Human-readable failure message shown in the report
    failure_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pass_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Extra configuration (e.g. minimum years in business for qualitative rules)
    extra_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    def evaluate(self, value: Optional[float]) -> bool:
        """
        Returns True if the rule condition is met (i.e., the rule TRIGGERS
        and the associated action should fire). Returns False if the metric
        is within acceptable limits.
        """
        if value is None:
            # Cannot evaluate — treat as triggered for safety
            return True

        if self.operator == Operator.LT:
            return value < (self.threshold or 0)
        elif self.operator == Operator.LTE:
            return value <= (self.threshold or 0)
        elif self.operator == Operator.GT:
            return value > (self.threshold or 0)
        elif self.operator == Operator.GTE:
            return value >= (self.threshold or 0)
        elif self.operator == Operator.EQ:
            return value == (self.threshold or 0)
        elif self.operator == Operator.NEQ:
            return value != (self.threshold or 0)
        elif self.operator == Operator.IS_NEGATIVE:
            return value < 0
        elif self.operator == Operator.IS_POSITIVE:
            return value > 0
        return False

    def __repr__(self) -> str:
        return f"<Rule id={self.id} name={self.name!r} active={self.is_active}>"
