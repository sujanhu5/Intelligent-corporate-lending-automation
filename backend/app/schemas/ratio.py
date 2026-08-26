"""
Pydantic schemas for financial ratio endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class RatioDetail(BaseModel):
    """Single ratio with all display fields."""
    name: str
    display_name: str
    value: Optional[float]
    unit: str
    formula: str
    risk_level: str
    health_signal: str        # positive | neutral | negative
    interpretation: str
    benchmark_min: Optional[float]
    benchmark_max: Optional[float]
    benchmark_note: str = ""
    components: Dict[str, Optional[float]] = {}


class RatioCalculationResponse(BaseModel):
    """Full ratio calculation result for one application."""
    id: uuid.UUID
    application_id: uuid.UUID
    financial_year: Optional[str]
    overall_health: Optional[str]
    health_notes: Optional[str]
    ratios: List[RatioDetail]
    missing_fields: List[str] = []
    warnings: List[str] = []
    calculated_count: int
    total_ratios: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RatioSummaryResponse(BaseModel):
    """Lightweight summary for dashboard cards."""
    application_id: uuid.UUID
    overall_health: Optional[str]
    calculated_count: int
    critical_ratios: List[str]        # ratio names with very_high risk
    high_risk_ratios: List[str]       # ratio names with high risk
    key_metrics: Dict[str, Optional[float]]   # selected key ratios for quick view
