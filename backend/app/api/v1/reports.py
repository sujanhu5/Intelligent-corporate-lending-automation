"""
Report generation endpoints.

  POST  /reports/generate/{application_id} — Generate a new PDF report
  GET   /reports/{application_id}          — Retrieve latest report metadata
  GET   /reports/{application_id}/list     — List all reports for an application
  GET   /reports/{report_id}/download      — Download the PDF file
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import get_client_ip, get_current_user, require_analyst
from app.models.user import User
from app.schemas.report import ReportListResponse, ReportResponse
from app.services.report_service import ReportService

router = APIRouter()


# ---------------------------------------------------------------------------
# Generate report
# ---------------------------------------------------------------------------

@router.post(
    "/generate/{application_id}",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a PDF credit assessment report",
    description=(
        "Assembles a comprehensive multi-section PDF report covering all pipeline "
        "stages: company profile, submitted documents, OCR-extracted financials, "
        "financial ratio analysis (20 ratios with risk levels), rule engine evaluation "
        "(per-rule pass/fail table), ML prediction with SHAP analysis, composite risk "
        "score, credit recommendation, and officer notes.\n\n"
        "**Pre-condition:** Financial ratios must be calculated (OCR and ratio stages "
        "must be complete). Rule evaluation and ML prediction are included if available "
        "but are not mandatory blockers.\n\n"
        "Each call generates a new versioned report. Prior versions remain accessible."
    ),
)
def generate_report(
    request: Request,
    application_id: uuid.UUID,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> ReportResponse:
    return ReportService(db).generate_report(
        application_id=application_id,
        generated_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )


# ---------------------------------------------------------------------------
# Get latest report metadata
# ---------------------------------------------------------------------------

@router.get(
    "/{application_id}",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve the latest report metadata for an application",
)
def get_latest_report(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    return ReportService(db).get_latest_report(application_id)


# ---------------------------------------------------------------------------
# List all reports for an application
# ---------------------------------------------------------------------------

@router.get(
    "/{application_id}/list",
    response_model=ReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all report versions for an application",
)
def list_reports(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    return ReportService(db).list_reports(application_id)


# ---------------------------------------------------------------------------
# Download PDF
# ---------------------------------------------------------------------------

@router.get(
    "/{report_id}/download",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
    summary="Download the PDF report file",
    description=(
        "Streams the generated PDF file for download. "
        "Returns 404 if the report has not been generated yet or the file is missing."
    ),
)
def download_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    abs_path = ReportService(db).get_report_path(report_id)
    return FileResponse(
        path=str(abs_path),
        media_type="application/pdf",
        filename=abs_path.name,
        headers={
            "Content-Disposition": f'attachment; filename="{abs_path.name}"',
            "Cache-Control": "no-store",
        },
    )
