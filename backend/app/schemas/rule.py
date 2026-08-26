"""
Pydantic schemas for rule CRUD and rule engine evaluation endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.company import Industry
from app.models.rule import Operator, RuleAction, RuleCategory


# ---------------------------------------------------------------------------
# CRUD schemas
# ---------------------------------------------------------------------------

class RuleCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    category: RuleCategory
    metric_field: str = Field(..., min_length=1, max_length=100)
    operator: Operator
    threshold: Optional[float] = Field(default=None)
    action: RuleAction
    is_mandatory: bool = True
    is_active: bool = True
    priority: int = Field(default=100, ge=1, le=9999)
    failure_message: Optional[str] = Field(default=None, max_length=1000)
    pass_message: Optional[str] = Field(default=None, max_length=1000)
    industry: Optional[Industry] = None
    extra_config: Optional[Dict[str, Any]] = None

    @field_validator("threshold")
    @classmethod
    def threshold_required_for_comparison_operators(
        cls, v: Optional[float], info: Any
    ) -> Optional[float]:
        op = info.data.get("operator")
        no_threshold_ops = {Operator.IS_NEGATIVE, Operator.IS_POSITIVE}
        if op not in no_threshold_ops and v is None:
            raise ValueError(
                f"threshold is required for operator '{op}'. "
                "Only 'is_negative' and 'is_positive' operators can omit it."
            )
        return v


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    category: Optional[RuleCategory] = None
    metric_field: Optional[str] = Field(default=None, min_length=1, max_length=100)
    operator: Optional[Operator] = None
    threshold: Optional[float] = None
    action: Optional[RuleAction] = None
    is_mandatory: Optional[bool] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(default=None, ge=1, le=9999)
    failure_message: Optional[str] = Field(default=None, max_length=1000)
    pass_message: Optional[str] = Field(default=None, max_length=1000)
    industry: Optional[Industry] = None
    extra_config: Optional[Dict[str, Any]] = None


class RuleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    category: RuleCategory
    metric_field: str
    operator: Operator
    threshold: Optional[float]
    action: RuleAction
    is_mandatory: bool
    is_active: bool
    priority: int
    failure_message: Optional[str]
    pass_message: Optional[str]
    industry: Optional[Industry] = None
    extra_config: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RuleListResponse(BaseModel):
    items: List[RuleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# Rule engine evaluation schemas
# ---------------------------------------------------------------------------

class RuleResultItem(BaseModel):
    """Per-rule evaluation result returned to the API consumer."""
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


class RuleEngineResponse(BaseModel):
    """Overall result of the rule engine evaluation for one application."""
    application_id: uuid.UUID
    overall_outcome: str        # "pass" | "manual_review" | "reject"
    ml_should_run: bool
    evaluated_at: str           # ISO-8601 UTC string
    total_rules: int
    triggered_count: int
    mandatory_failures: List[str]
    advisory_triggers: List[str]
    passed_rules: List[str]
    skipped_rules: List[str]
    results: List[RuleResultItem]
    rejection_reason: Optional[str] = None   # Set when outcome == "reject"
