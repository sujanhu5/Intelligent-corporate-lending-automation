"""
Pipeline orchestration endpoints.

Three routes cover the full lifecycle:
  GET  /pipeline/status/{app_id}   — inspect stage readiness and current position
  POST /pipeline/run/{app_id}      — execute all remaining stages in order
  POST /pipeline/run-batch         — bulk-process many (or all pending) applications
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import get_client_ip, get_current_user, require_analyst, require_officer
from app.models.user import User
from app.schemas.pipeline import BatchPipelineResponse, PipelineRunResponse, PipelineStatusResponse
from app.services.pipeline_service import PipelineService

router = APIRouter()


def _service(db: Session) -> PipelineService:
    return PipelineService(db)


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class BatchRunBody(BaseModel):
    application_ids: Optional[List[uuid.UUID]] = None
    limit: int = 25
    generate_report: bool = True


# ---------------------------------------------------------------------------
# GET /pipeline/status/{application_id}
# ---------------------------------------------------------------------------

@router.get(
    "/status/{application_id}",
    response_model=PipelineStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Pipeline status for an application",
    description=(
        "Returns which stages have completed, which can run next, and whether "
        "the full pipeline is done. No state is changed."
    ),
)
def get_pipeline_status(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PipelineStatusResponse:
    return _service(db).get_status(application_id)


# ---------------------------------------------------------------------------
# POST /pipeline/run/{application_id}
# ---------------------------------------------------------------------------

@router.post(
    "/run/{application_id}",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Run the full pipeline for one application",
    description=(
        "Executes every incomplete stage in order: submit → OCR → ratios → rules → ML → report. "
        "Already-complete stages are skipped. A mandatory rule failure stops the pipeline before "
        "ML (that is a successful run, not an error). The endpoint is safe to retry."
    ),
)
def run_pipeline(
    application_id: uuid.UUID,
    request: Request,
    generate_report: bool = Query(default=True, description="Include report generation stage."),
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> PipelineRunResponse:
    ip = get_client_ip(request)
    request_id = request.headers.get("X-Request-ID", "unknown")
    return _service(db).run_full_pipeline(
        application_id=application_id,
        triggered_by=current_user,
        ip_address=ip,
        request_id=request_id,
        generate_report=generate_report,
    )


# ---------------------------------------------------------------------------
# POST /pipeline/run-batch
# ---------------------------------------------------------------------------

@router.post(
    "/run-batch",
    response_model=BatchPipelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Run the pipeline for multiple applications",
    description=(
        "When `application_ids` is provided, processes exactly those applications. "
        "When omitted, automatically selects up to `limit` pending applications "
        "(those with documents but no final decision). Errors on individual items "
        "are captured in the response rather than aborting the batch."
    ),
)
def run_batch_pipeline(
    request: Request,
    body: BatchRunBody = Body(default_factory=BatchRunBody),
    current_user: User = Depends(require_officer),
    db: Session = Depends(get_db),
) -> BatchPipelineResponse:
    ip = get_client_ip(request)
    request_id = request.headers.get("X-Request-ID", "unknown")
    return _service(db).run_batch(
        application_ids=body.application_ids,
        triggered_by=current_user,
        limit=body.limit,
        ip_address=ip,
        request_id=request_id,
    )


# ---------------------------------------------------------------------------
# POST /pipeline/reset-stage/{application_id}
# ---------------------------------------------------------------------------

@router.post(
    "/reset-stage/{application_id}",
    status_code=status.HTTP_200_OK,
    summary="Reset a pipeline stage and all downstream stages",
    description=(
        "Resets the specified stage and all stages after it, allowing "
        "re-execution. Useful for re-running OCR after uploading new documents, "
        "recalculating ratios, or re-evaluating rules."
    ),
)
def reset_pipeline_stage(
    application_id: uuid.UUID,
    stage: str = Query(..., description="Stage to reset: ocr, ratios, rules, ml, report"),
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> dict:
    stage_map = {
        "ocr": "ocr_completed",
        "ratios": "ratios_calculated",
        "rules": "rules_evaluated",
        "ml": "ml_predicted",
        "report": "report_generated",
    }
    if stage not in stage_map:
        from app.core.exceptions import BadRequestError
        raise BadRequestError(message=f"Invalid stage: {stage}. Valid: {', '.join(stage_map.keys())}")

    from app.repositories.application_repository import ApplicationRepository
    app_repo = ApplicationRepository(db)
    app = app_repo.get_by_id(application_id)
    if not app:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(message=f"Application '{application_id}' not found.")

    app_repo.reset_pipeline_from(app, stage_map[stage])
    db.commit()

    return {
        "application_id": str(application_id),
        "reset_from": stage,
        "message": f"Pipeline reset from '{stage}' stage. You can now re-run this and all subsequent stages.",
    }
