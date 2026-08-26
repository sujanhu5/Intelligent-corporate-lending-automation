"""
Declarative base class shared by all SQLAlchemy ORM models.
Importing Base here and using it in every model ensures Alembic
can auto-detect the full schema from one import.
"""

from __future__ import annotations

import enum as _enum
import uuid
from datetime import datetime, timezone
from typing import Type

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def PgEnum(enum_cls: Type[_enum.Enum], name: str) -> Enum:
    """
    Postgres ENUM column bound to the enum's *values*, not its member names.

    schema.sql declares every ENUM with lowercase labels ('admin', 'active'),
    while SQLAlchemy's default binds to member names ('ADMIN', 'ACTIVE') and
    raises LookupError on read.
    """
    return Enum(
        enum_cls,
        name=name,
        values_callable=lambda e: [member.value for member in e],
    )


class Base(DeclarativeBase):
    """
    All ORM models inherit from this class.
    Provides:
      - id   — UUID primary key (PostgreSQL native UUID type)
      - created_at / updated_at — automatic timestamps in UTC
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_dict(self) -> dict:
        """Shallow serialisation for debugging and logging."""
        result = {}
        for col in self.__table__.columns:
            val = getattr(self, col.name)
            if isinstance(val, uuid.UUID):
                val = str(val)
            elif isinstance(val, datetime):
                val = val.isoformat()
            result[col.name] = val
        return result
