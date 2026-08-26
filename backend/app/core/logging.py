"""
Structured JSON logging configuration used across the entire backend.
Outputs machine-readable JSON in production and human-readable text in dev.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from pythonjsonlogger import jsonlogger  # type: ignore[import]

from app.config import settings


_CONFIGURED = False

# Attributes logging.Logger.makeRecord() refuses to let `extra` overwrite.
_RESERVED_LOGRECORD_KEYS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime"}


class _SafeExtraLogger(logging.Logger):
    """
    Prefixes `extra` keys that collide with LogRecord internals.

    Without this, logger.info(..., extra={"name": x}) raises KeyError inside
    makeRecord and turns a log statement into a failed request.
    """

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                   func=None, extra=None, sinfo=None):
        if extra:
            extra = {
                (f"extra_{k}" if k in _RESERVED_LOGRECORD_KEYS else k): v
                for k, v in extra.items()
            }
        return super().makeRecord(
            name, level, fn, lno, msg, args, exc_info, func, extra, sinfo
        )


def configure_logging() -> None:
    """
    Idempotent — safe to call multiple times.
    Sets up root logger with a file handler (JSON) and a stream handler
    whose format depends on ENVIRONMENT.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    logging.setLoggerClass(_SafeExtraLogger)

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    # Remove any handlers already attached (e.g. uvicorn defaults)
    root.handlers.clear()

    # ------------------------------------------------------------------
    # Stream handler
    # ------------------------------------------------------------------
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)

    if settings.LOG_FORMAT.lower() == "json" or settings.is_production:
        fmt = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        fmt = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    stream_handler.setFormatter(fmt)
    root.addHandler(stream_handler)

    # ------------------------------------------------------------------
    # File handler (always JSON for log aggregation)
    # ------------------------------------------------------------------
    log_file: Path = settings.log_path / "app.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(
        jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root.addHandler(file_handler)

    # Suppress noisy third-party loggers in production
    if settings.is_production:
        for noisy in ("uvicorn.access", "sqlalchemy.engine"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
