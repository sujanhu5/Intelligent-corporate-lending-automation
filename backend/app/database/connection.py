"""
SQLAlchemy async-compatible session factory and dependency.

Uses synchronous psycopg2 driver (psycopg2-binary) for simplicity; swap to
asyncpg + create_async_engine if async DB is required in a later phase.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# NullPool is used during testing to avoid connection leaks.
# Switch to QueuePool (the default) for production by removing pool_class.

_engine_kwargs = dict(
    echo=settings.DEBUG,          # logs every SQL statement when DEBUG=True
    pool_pre_ping=True,           # verify connections before handing them out
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,            # recycle connections every 30 min
)

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # prevents lazy-load after commit
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session and guarantee it is closed when the request
    handler (or background task) finishes — even if it raises.

    Usage::

        @router.get("/...")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Context-manager variant (for use outside FastAPI request cycle)
# ---------------------------------------------------------------------------

@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context-manager version for scripts, workers, and tests."""
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Health check helper
# ---------------------------------------------------------------------------

def check_db_connection() -> bool:
    """Return True if the database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database connection check failed", exc_info=exc)
        return False
