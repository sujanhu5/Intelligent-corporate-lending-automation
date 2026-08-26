"""ORM model — audit_logs table.

Records every significant action performed by users or automated pipeline
stages. Used for compliance, forensics, and the activity feed on the dashboard.
"""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, PgEnum

if TYPE_CHECKING:
    from app.models.user import User


class AuditAction(str, enum.Enum):
    # Auth
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    PASSWORD_CHANGED = "password_changed"

    # Company
    COMPANY_CREATED = "company_created"
    COMPANY_UPDATED = "company_updated"

    # Application
    APPLICATION_CREATED = "application_created"
    APPLICATION_UPDATED = "application_updated"
    APPLICATION_SUBMITTED = "application_submitted"
    APPLICATION_WITHDRAWN = "application_withdrawn"
    DECISION_MADE = "decision_made"

    # Documents
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_DELETED = "document_deleted"

    # Pipeline
    OCR_STARTED = "ocr_started"
    OCR_COMPLETED = "ocr_completed"
    OCR_FAILED = "ocr_failed"
    RATIOS_CALCULATED = "ratios_calculated"
    RULES_EVALUATED = "rules_evaluated"
    ML_PREDICTED = "ml_predicted"
    REPORT_GENERATED = "report_generated"
    PIPELINE_COMPLETED = "pipeline_completed"

    # Admin
    RULE_CREATED = "rule_created"
    RULE_UPDATED = "rule_updated"
    RULE_DELETED = "rule_deleted"
    MODEL_TRAINED = "model_trained"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # The entity affected (application, company, document, etc.)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    action: Mapped[AuditAction] = mapped_column(
        PgEnum(AuditAction, name="audit_action"), nullable=False, index=True
    )

    # Human-readable description
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Machine-readable before/after state for change tracking
    old_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationship
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} entity={self.entity_type}:{self.entity_id}>"
