"""
RuleRepository — all database operations for the rules table.
"""

from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.rule import Rule, RuleCategory


class RuleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # -------------------------------------------------------------------------
    # Read
    # -------------------------------------------------------------------------

    def get_by_id(self, rule_id: uuid.UUID) -> Optional[Rule]:
        return self._db.query(Rule).filter(Rule.id == rule_id).first()

    def get_by_name(self, name: str) -> Optional[Rule]:
        return (
            self._db.query(Rule)
            .filter(Rule.name == name.strip())
            .first()
        )

    def list_active_ordered(self) -> List[Rule]:
        """Return all active rules sorted by priority ascending (lowest = first evaluated)."""
        return (
            self._db.query(Rule)
            .filter(Rule.is_active.is_(True))
            .order_by(Rule.priority.asc(), Rule.name.asc())
            .all()
        )

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[RuleCategory] = None,
        is_mandatory: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[Rule], int]:
        q = self._db.query(Rule)

        if category is not None:
            q = q.filter(Rule.category == category)
        if is_mandatory is not None:
            q = q.filter(Rule.is_mandatory.is_(is_mandatory))
        if is_active is not None:
            q = q.filter(Rule.is_active.is_(is_active))

        total = q.count()
        items = (
            q.order_by(Rule.priority.asc(), Rule.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    # -------------------------------------------------------------------------
    # Write
    # -------------------------------------------------------------------------

    def create(self, **kwargs) -> Rule:
        rule = Rule(**kwargs)
        self._db.add(rule)
        self._db.flush()
        return rule

    def update(self, rule: Rule, **kwargs) -> Rule:
        for key, value in kwargs.items():
            if hasattr(rule, key) and value is not None:
                setattr(rule, key, value)
        self._db.flush()
        return rule

    def set_active(self, rule: Rule, is_active: bool) -> Rule:
        rule.is_active = is_active
        self._db.flush()
        return rule

    def delete(self, rule: Rule) -> None:
        """Hard delete — use set_active(False) for soft deactivation."""
        self._db.delete(rule)
        self._db.flush()
