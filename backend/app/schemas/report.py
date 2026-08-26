"""
Pydantic schemas for the report generation endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.report import ReportStatus


class ReportResponse(BaseModel):
    """Returned after generating or retrieving a report."""
    id: uuid.UUID
    application_id: uuid.UUID
    status: ReportStatus
    filename: str
    file_path: str
    file_size_bytes: Optional[int]
    version: int
    generated_by: Optional[str]
    generation_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int
