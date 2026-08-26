"""
Pydantic schemas for the end-to-end pipeline orchestrator.

The orchestrator runs the same services the individual endpoints call, so a
pipeline run is observationally identical to invoking each stage by hand — it
just removes the six round-trips.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StageResult(BaseModel):
    """Outcome of one pipeline stage."""
    stage: str
    status: str = Field(description="completed | skipped | failed")
    detail: Optional[str] = None
    duration_seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return self.status in {"completed", "skipped"}


class PipelineRunResponse(BaseModel):
    """Returned by POST /pipeline/run/{application_id}."""
    application_id: uuid.UUID
    application_number: str
    started_at: str
    finished_at: str
    total_duration_seconds: float

    stages: List[StageResult]
    completed_stages: int
    skipped_stages: int
    failed_stage: Optional[str] = None

    # Terminal state after the run
    final_status: str
    final_decision: str
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    rule_outcome: Optional[str] = None
    ml_executed: bool = False
    report_id: Optional[uuid.UUID] = None

    summary: str


class PipelineStageState(BaseModel):
    """One stage's readiness in the status view."""
    stage: str
    label: str
    complete: bool
    can_run: bool
    blocked_reason: Optional[str] = None


class PipelineStatusResponse(BaseModel):
    """Returned by GET /pipeline/status/{application_id}."""
    application_id: uuid.UUID
    application_number: str
    status: str
    final_decision: str
    document_count: int
    documents_extracted: int
    stages: List[PipelineStageState]
    next_stage: Optional[str] = None
    is_complete: bool
    can_run_pipeline: bool


class BatchPipelineItem(BaseModel):
    application_id: uuid.UUID
    application_number: str
    status: str
    detail: Optional[str] = None


class BatchPipelineResponse(BaseModel):
    """Returned by POST /pipeline/run-batch."""
    requested: int
    succeeded: int
    failed: int
    skipped: int
    items: List[BatchPipelineItem]
    duration_seconds: float


class PipelineMetrics(BaseModel):
    """Aggregate throughput metrics for the analytics dashboard."""
    stage_completion: Dict[str, int]
    stage_conversion: Dict[str, float]
    avg_duration_seconds: Optional[float] = None
    bottleneck_stage: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
