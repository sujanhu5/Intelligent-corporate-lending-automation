"""
Pydantic schemas for document upload and management endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.document import DocumentStatus, DocumentType


# =============================================================================
# Response schemas
# =============================================================================

class DocumentResponse(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    document_type: DocumentType
    status: DocumentStatus
    original_filename: str
    stored_filename: str
    file_size_bytes: int
    mime_type: str
    checksum_sha256: Optional[str]
    financial_year: Optional[str]
    processing_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Derived: human-readable file size
    file_size_display: Optional[str] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_size(cls, doc) -> "DocumentResponse":
        r = cls.model_validate(doc)
        r.file_size_display = _format_bytes(doc.file_size_bytes)
        return r


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    """Returned immediately after a successful upload."""
    document_id: uuid.UUID
    application_id: uuid.UUID
    document_type: DocumentType
    original_filename: str
    stored_filename: str
    file_size_bytes: int
    file_size_display: str
    checksum_sha256: str
    status: DocumentStatus
    message: str


# =============================================================================
# Update schema (only financial_year is patchable post-upload)
# =============================================================================

class DocumentUpdate(BaseModel):
    financial_year: Optional[str] = None
    document_type: Optional[DocumentType] = None

    model_config = {"str_strip_whitespace": True}


# =============================================================================
# Helpers
# =============================================================================

def _format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
