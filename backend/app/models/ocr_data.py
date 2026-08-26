"""ORM model — ocr_data table.

Stores the raw OCR text and the structured financial fields extracted from
each uploaded document. Uses PostgreSQL JSONB for flexibility — the set of
extracted fields may grow without a schema migration.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.document import Document


class OCRData(Base):
    __tablename__ = "ocr_data"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Raw OCR output
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # OCR quality metrics
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Structured financial fields extracted by the parser.
    # Keys mirror the fields listed in the project spec.
    # All monetary values are stored in the document's currency unit.
    extracted_fields: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Extraction metadata (engine version, duration, etc.)
    extraction_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Relationship
    document: Mapped["Document"] = relationship("Document", back_populates="ocr_data")

    def get_field(self, key: str, default: Optional[float] = None) -> Optional[float]:
        """Convenience accessor for a single extracted numeric field."""
        if not self.extracted_fields:
            return default
        return self.extracted_fields.get(key, default)

    def __repr__(self) -> str:
        return f"<OCRData id={self.id} document_id={self.document_id}>"
