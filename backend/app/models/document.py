"""ORM model — documents table."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, PgEnum

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.ocr_data import OCRData


class DocumentType(str, enum.Enum):
    BALANCE_SHEET = "balance_sheet"
    PROFIT_LOSS = "profit_loss"
    CASH_FLOW = "cash_flow"
    AUDITOR_REPORT = "auditor_report"
    GST_REPORT = "gst_report"
    BANK_STATEMENT = "bank_statement"
    ANNUAL_REPORT = "annual_report"
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_type: Mapped[DocumentType] = mapped_column(
        PgEnum(DocumentType, name="document_type"), nullable=False
    )
    status: Mapped[DocumentStatus] = mapped_column(
        PgEnum(DocumentStatus, name="document_status"),
        nullable=False,
        default=DocumentStatus.UPLOADED,
    )

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Financial year the document covers
    financial_year: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Annual report section tracking: sub-documents extracted from an annual report
    parent_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    page_range_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_range_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application", back_populates="documents"
    )
    ocr_data: Mapped[Optional["OCRData"]] = relationship(
        "OCRData", back_populates="document", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} type={self.document_type} status={self.status}>"
