"""
Financial ratio endpoints — trigger calculation and retrieve results.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import get_client_ip, get_current_user, require_analyst
from app.models.user import User
from app.schemas.ratio import RatioCalculationResponse, RatioSummaryResponse
from app.services.ratio_service import RatioService

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /ratios/calculate/{application_id}
# ---------------------------------------------------------------------------

@router.post(
    "/calculate/{application_id}",
    response_model=RatioCalculationResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate all financial ratios for an application",
    description=(
        "Merges OCR-extracted financials from all documents, calculates 20 ratios, "
        "interprets each with risk level and benchmark, determines overall financial "
        "health, and persists the result. Idempotent — re-running overwrites prior results."
    ),
)
def calculate_ratios(
    request: Request,
    application_id: uuid.UUID,
    financial_year: Optional[str] = Query(
        default=None,
        description="Financial year label, e.g. 'FY2023-24'",
    ),
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> RatioCalculationResponse:
    return RatioService(db).calculate_for_application(
        application_id=application_id,
        financial_year=financial_year,
        calculated_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )


# ---------------------------------------------------------------------------
# GET /ratios/application/{application_id}
# ---------------------------------------------------------------------------

@router.get(
    "/application/{application_id}",
    response_model=RatioCalculationResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve calculated ratios for an application",
)
def get_ratios(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RatioCalculationResponse:
    return RatioService(db).get_for_application(application_id)


# ---------------------------------------------------------------------------
# GET /ratios/application/{application_id}/summary
# ---------------------------------------------------------------------------

@router.get(
    "/application/{application_id}/summary",
    response_model=RatioSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a lightweight ratio summary for dashboard cards",
)
def get_ratio_summary(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RatioSummaryResponse:
    return RatioService(db).get_summary(application_id)

