"""ORM model — reports table."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, PgEnum

if TYPE_CHECKING:
    from app.models.application import Application


class ReportStatus(str, enum.Enum):
    GENERATING = "generating"
    COMPLETE = "complete"
    FAILED = "failed"


class Report(Base):
    __tablename__ = "reports"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[ReportStatus] = mapped_column(
        PgEnum(ReportStatus, name="report_status"),
        nullable=False,
        default=ReportStatus.GENERATING,
    )

    # File details
    filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Report version (multiple reports can exist for one application)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    generated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # user email

    generation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    application: Mapped["Application"] = relationship(
        "Application", back_populates="reports"
    )

    def __repr__(self) -> str:
        return f"<Report id={self.id} application_id={self.application_id} v{self.version}>"
