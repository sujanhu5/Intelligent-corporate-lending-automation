"""
Celery worker task definitions.

The broker and result backend are configured from .env (CELERY_BROKER_URL /
CELERY_RESULT_BACKEND). Redis is the default; when Redis is not running the
workers fail to start, but the FastAPI application itself is unaffected — all
pipeline stages can still be invoked synchronously through the API.

Starting workers (from the backend/ directory):
    celery -A workers worker --loglevel=info --pool=solo   # Windows (no fork)
    celery -A workers worker --loglevel=info               # Linux / macOS

Monitoring:
    celery -A workers flower                               # web dashboard
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from celery import Celery
from celery.utils.log import get_task_logger

from app.config import settings

# ---------------------------------------------------------------------------
# Celery application
# ---------------------------------------------------------------------------

celery_app = Celery(
    "corporate_lending",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,                 # re-queue on worker crash
    worker_prefetch_multiplier=1,        # one task at a time per worker
    task_routes={
        "workers.run_pipeline_task": {"queue": "pipeline"},
        "workers.run_batch_pipeline_task": {"queue": "pipeline"},
        "workers.train_models_task": {"queue": "ml"},
        "workers.ocr_document_task": {"queue": "ocr"},
    },
)

logger = get_task_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db_session():
    """Create a fresh SQLAlchemy session for a worker task."""
    from app.database.connection import SessionLocal
    return SessionLocal()


def _get_system_user(db):
    """Return the first admin user to use as the 'triggered_by' actor for async tasks."""
    from app.models.user import User, UserRole
    return (
        db.query(User)
        .filter(User.role == UserRole.ADMIN)
        .order_by(User.created_at.asc())
        .first()
    )


# ---------------------------------------------------------------------------
# Task: run the full pipeline for one application
# ---------------------------------------------------------------------------

@celery_app.task(
    name="workers.run_pipeline_task",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=300,   # 5-minute warning
    time_limit=600,        # hard kill after 10 min
)
def run_pipeline_task(
    self,
    application_id: str,
    triggered_by_id: Optional[str] = None,
    generate_report: bool = True,
) -> Dict[str, Any]:
    """
    Async version of POST /pipeline/run/{application_id}.
    Enqueue this task instead of calling the endpoint when you want
    pipeline execution to happen in a background worker.
    """
    from app.services.pipeline_service import PipelineService
    from app.models.user import User

    db = _get_db_session()
    try:
        app_uuid = uuid.UUID(application_id)
        if triggered_by_id:
            user = db.query(User).filter(User.id == uuid.UUID(triggered_by_id)).first()
        else:
            user = _get_system_user(db)

        if not user:
            raise ValueError("No triggering user found; cannot run pipeline.")

        service = PipelineService(db)
        result = service.run_full_pipeline(
            application_id=app_uuid,
            triggered_by=user,
            ip_address="celery-worker",
            request_id=self.request.id or "unknown",
            generate_report=generate_report,
        )
        logger.info(
            "Pipeline task completed: %s in %.2fs (failed_stage=%s)",
            application_id,
            result.total_duration_seconds,
            result.failed_stage or "none",
        )
        return {
            "application_id": application_id,
            "summary": result.summary,
            "failed_stage": result.failed_stage,
            "final_status": result.final_status,
            "final_decision": result.final_decision,
            "duration_seconds": result.total_duration_seconds,
        }
    except Exception as exc:
        db.rollback()
        logger.error("Pipeline task failed for %s: %s", application_id, exc)
        raise self.retry(exc=exc) from exc
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task: batch-process pending applications
# ---------------------------------------------------------------------------

@celery_app.task(
    name="workers.run_batch_pipeline_task",
    bind=True,
    max_retries=1,
    soft_time_limit=1800,   # 30 minutes
    time_limit=3600,
)
def run_batch_pipeline_task(
    self,
    application_ids: Optional[List[str]] = None,
    limit: int = 25,
    triggered_by_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process many applications asynchronously. When application_ids is None,
    the pipeline service picks up the backlog automatically.
    """
    from app.services.pipeline_service import PipelineService
    from app.models.user import User

    db = _get_db_session()
    try:
        if triggered_by_id:
            user = db.query(User).filter(User.id == uuid.UUID(triggered_by_id)).first()
        else:
            user = _get_system_user(db)

        if not user:
            raise ValueError("No triggering user found; cannot run batch pipeline.")

        ids = [uuid.UUID(aid) for aid in application_ids] if application_ids else None
        service = PipelineService(db)
        result = service.run_batch(
            application_ids=ids,
            triggered_by=user,
            limit=limit,
            ip_address="celery-worker",
            request_id=self.request.id or "unknown",
        )
        logger.info(
            "Batch pipeline task completed: %d/%d succeeded in %.2fs",
            result.succeeded,
            result.requested,
            result.duration_seconds,
        )
        return {
            "requested": result.requested,
            "succeeded": result.succeeded,
            "failed": result.failed,
            "skipped": result.skipped,
            "duration_seconds": result.duration_seconds,
        }
    except Exception as exc:
        db.rollback()
        logger.error("Batch pipeline task failed: %s", exc)
        raise self.retry(exc=exc) from exc
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task: OCR one document
# ---------------------------------------------------------------------------

@celery_app.task(
    name="workers.ocr_document_task",
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    soft_time_limit=120,
    time_limit=180,
)
def ocr_document_task(
    self,
    document_id: str,
    triggered_by_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Extract text and financial fields from one uploaded document."""
    from app.services.ocr_service import OCRService
    from app.models.user import User

    db = _get_db_session()
    try:
        doc_uuid = uuid.UUID(document_id)
        if triggered_by_id:
            user = db.query(User).filter(User.id == uuid.UUID(triggered_by_id)).first()
        else:
            user = _get_system_user(db)

        if not user:
            raise ValueError("No triggering user found for OCR task.")

        service = OCRService(db)
        result = service.extract_document(
            document_id=doc_uuid,
            triggered_by=user,
            ip_address="celery-worker",
            request_id=self.request.id or "unknown",
        )
        logger.info("OCR task completed for document %s (confidence=%.1f%%)", document_id, result.confidence * 100)
        return {
            "document_id": document_id,
            "confidence": result.confidence,
            "field_count": len(result.extracted_fields),
        }
    except Exception as exc:
        db.rollback()
        logger.error("OCR task failed for document %s: %s", document_id, exc)
        raise self.retry(exc=exc) from exc
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task: train ML models
# ---------------------------------------------------------------------------

@celery_app.task(
    name="workers.train_models_task",
    bind=True,
    max_retries=1,
    soft_time_limit=3600,   # training can take a while
    time_limit=7200,
)
def train_models_task(
    self,
    triggered_by_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Re-train all ML models from the dataset configured in .env.
    Equivalent to running: python ml/trainer.py
    """
    import sys
    from pathlib import Path

    # Resolve the ml/ directory relative to this file (backend/workers/__init__.py)
    backend_dir = Path(__file__).resolve().parent.parent
    ml_dir = backend_dir / "ml"
    if str(ml_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    try:
        from ml.trainer import ModelTrainer  # type: ignore[import]
        trainer = ModelTrainer()
        metrics = trainer.train_all()
        logger.info(
            "Model training complete. Best: %s (ROC-AUC %.4f)",
            metrics.get("best_model"),
            metrics.get("best_roc_auc", 0),
        )
        return metrics
    except Exception as exc:
        logger.error("Model training task failed: %s", exc)
        raise self.retry(exc=exc) from exc


# ---------------------------------------------------------------------------
# Periodic tasks (beat schedule)
# ---------------------------------------------------------------------------

celery_app.conf.beat_schedule = {
    # Process any application that has been sitting in draft/submitted for >1h
    "auto-process-backlog": {
        "task": "workers.run_batch_pipeline_task",
        "schedule": 3600.0,   # every hour
        "kwargs": {"limit": 10},
    },
}
