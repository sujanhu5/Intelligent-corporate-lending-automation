"""
AuditLogRepository — write-only repository for creating audit log entries.
All service layer writes go through this so audit creation is consistent.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditAction, AuditLog


class AuditLogRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def log(
        self,
        action: AuditAction,
        description: str,
        user_id: Optional[UUID] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            action=action,
            description=description,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        self._db.add(entry)
        # flush so the ID is available but do NOT commit — caller owns the transaction
        self._db.flush()
        return entry
