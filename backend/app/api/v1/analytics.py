"""
Analytics endpoints — aggregate statistics for dashboards and reporting.

All endpoints are read-only (GET). They query the database directly via
SQLAlchemy and return JSON; no dedicated service layer is needed because
the logic is pure query composition without side-effects.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import get_current_user
from app.models.application import Application, ApplicationStatus, FinalDecision, LoanPurpose
from app.models.company import Company
from app.models.prediction import Prediction, RiskLevel
from app.models.rule import Rule, RuleCategory
from app.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas (lightweight — analytics responses are one-off shapes)
# ---------------------------------------------------------------------------

class ApplicationTrend(BaseModel):
    date: str
    submitted: int
    approved: int
    rejected: int


class RiskDistribution(BaseModel):
    risk_level: str
    count: int
    percentage: float


class IndustryBreakdown(BaseModel):
    industry: str
    count: int
    total_loan_amount: float
    avg_risk_score: Optional[float]


class LoanPurposeBreakdown(BaseModel):
    purpose: str
    count: int
    total_amount: float
    approval_rate: float


class PipelineFunnelStage(BaseModel):
    stage: str
    label: str
    count: int
    conversion_rate: Optional[float]


class RuleTriggerStat(BaseModel):
    rule_id: str
    rule_name: str
    category: str
    trigger_count: int
    is_mandatory: bool


class AnalyticsSummary(BaseModel):
    total_applications: int
    total_approved: int
    total_rejected: int
    total_manual_review: int
    total_pending: int
    approval_rate: float
    avg_risk_score: Optional[float]
    avg_loan_amount_requested: Optional[float]
    total_loan_amount_approved: float
    avg_processing_days: Optional[float]
    models_trained: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _date_range(days: int) -> date:
    return date.today() - timedelta(days=days)


# ---------------------------------------------------------------------------
# GET /analytics/summary
# ---------------------------------------------------------------------------

@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    status_code=status.HTTP_200_OK,
    summary="High-level KPI summary",
)
def analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyticsSummary:
    total = db.query(func.count(Application.id)).scalar() or 0
    approved = (
        db.query(func.count(Application.id))
        .filter(Application.final_decision == FinalDecision.APPROVED)
        .scalar() or 0
    )
    rejected = (
        db.query(func.count(Application.id))
        .filter(Application.final_decision == FinalDecision.REJECTED)
        .scalar() or 0
    )
    manual = (
        db.query(func.count(Application.id))
        .filter(Application.final_decision == FinalDecision.MANUAL_REVIEW)
        .scalar() or 0
    )
    pending = (
        db.query(func.count(Application.id))
        .filter(Application.final_decision == FinalDecision.PENDING)
        .scalar() or 0
    )
    avg_risk = (
        db.query(func.avg(Application.risk_score))
        .filter(Application.risk_score.isnot(None))
        .scalar()
    )
    avg_loan = (
        db.query(func.avg(Application.loan_amount_requested))
        .filter(Application.loan_amount_requested.isnot(None))
        .scalar()
    )
    total_approved_amount = (
        db.query(func.sum(Application.loan_amount_requested))
        .filter(Application.final_decision == FinalDecision.APPROVED)
        .scalar()
    )

    # Average days from creation to decision (approximated by updated_at)
    avg_days_raw = (
        db.query(
            func.avg(
                func.extract(
                    "epoch",
                    Application.updated_at - Application.created_at,
                ) / 86400.0
            )
        )
        .filter(Application.final_decision != FinalDecision.PENDING)
        .scalar()
    )

    # Check if any model has been trained
    from pathlib import Path
    from app.config import settings
    models_trained = any(settings.models_path.glob("*.pkl"))

    return AnalyticsSummary(
        total_applications=total,
        total_approved=approved,
        total_rejected=rejected,
        total_manual_review=manual,
        total_pending=pending,
        approval_rate=round(approved / total * 100, 1) if total else 0.0,
        avg_risk_score=round(float(avg_risk), 2) if avg_risk is not None else None,
        avg_loan_amount_requested=round(float(avg_loan), 2) if avg_loan is not None else None,
        total_loan_amount_approved=float(total_approved_amount) if total_approved_amount else 0.0,
        avg_processing_days=round(float(avg_days_raw), 1) if avg_days_raw is not None else None,
        models_trained=models_trained,
    )


# ---------------------------------------------------------------------------
# GET /analytics/trends
# ---------------------------------------------------------------------------

@router.get(
    "/trends",
    response_model=List[ApplicationTrend],
    status_code=status.HTTP_200_OK,
    summary="Daily application submission and decision trends",
)
def application_trends(
    days: int = Query(default=30, ge=7, le=365, description="Look-back window in days."),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ApplicationTrend]:
    since = _date_range(days)
    rows = (
        db.query(
            func.date_trunc("day", Application.created_at).label("day"),
            func.count(Application.id).label("submitted"),
            func.sum(
                case((Application.final_decision == FinalDecision.APPROVED, 1), else_=0)
            ).label("approved"),
            func.sum(
                case((Application.final_decision == FinalDecision.REJECTED, 1), else_=0)
            ).label("rejected"),
        )
        .filter(Application.created_at >= since)
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [
        ApplicationTrend(
            date=row.day.strftime("%Y-%m-%d"),
            submitted=row.submitted or 0,
            approved=int(row.approved or 0),
            rejected=int(row.rejected or 0),
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# GET /analytics/risk-distribution
# ---------------------------------------------------------------------------

@router.get(
    "/risk-distribution",
    response_model=List[RiskDistribution],
    status_code=status.HTTP_200_OK,
    summary="Distribution of ML risk levels across decided applications",
)
def risk_distribution(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RiskDistribution]:
    rows = (
        db.query(Prediction.risk_level, func.count(Prediction.id).label("cnt"))
        .group_by(Prediction.risk_level)
        .all()
    )
    total = sum(r.cnt for r in rows)
    order = [RiskLevel.VERY_LOW, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.VERY_HIGH]
    counts: Dict[str, int] = {r.risk_level.value if hasattr(r.risk_level, "value") else str(r.risk_level): r.cnt for r in rows}
    return [
        RiskDistribution(
            risk_level=level.value,
            count=counts.get(level.value, 0),
            percentage=round(counts.get(level.value, 0) / total * 100, 1) if total else 0.0,
        )
        for level in order
    ]


# ---------------------------------------------------------------------------
# GET /analytics/industry-breakdown
# ---------------------------------------------------------------------------

@router.get(
    "/industry-breakdown",
    response_model=List[IndustryBreakdown],
    status_code=status.HTTP_200_OK,
    summary="Loan volume and risk by industry sector",
)
def industry_breakdown(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[IndustryBreakdown]:
    rows = (
        db.query(
            Company.industry,
            func.count(Application.id).label("cnt"),
            func.sum(Application.loan_amount_requested).label("total_amount"),
            func.avg(Application.risk_score).label("avg_risk"),
        )
        .join(Company, Application.company_id == Company.id)
        .group_by(Company.industry)
        .order_by(func.count(Application.id).desc())
        .all()
    )
    return [
        IndustryBreakdown(
            industry=row.industry.value if hasattr(row.industry, "value") else str(row.industry),
            count=row.cnt,
            total_loan_amount=float(row.total_amount or 0),
            avg_risk_score=round(float(row.avg_risk), 2) if row.avg_risk is not None else None,
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# GET /analytics/loan-purpose-breakdown
# ---------------------------------------------------------------------------

@router.get(
    "/loan-purpose-breakdown",
    response_model=List[LoanPurposeBreakdown],
    status_code=status.HTTP_200_OK,
    summary="Application counts and approval rates by loan purpose",
)
def loan_purpose_breakdown(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[LoanPurposeBreakdown]:
    rows = (
        db.query(
            Application.loan_purpose,
            func.count(Application.id).label("cnt"),
            func.sum(Application.loan_amount_requested).label("total_amount"),
            func.sum(
                case((Application.final_decision == FinalDecision.APPROVED, 1), else_=0)
            ).label("approved_cnt"),
        )
        .group_by(Application.loan_purpose)
        .order_by(func.count(Application.id).desc())
        .all()
    )
    return [
        LoanPurposeBreakdown(
            purpose=row.loan_purpose.value if hasattr(row.loan_purpose, "value") else str(row.loan_purpose),
            count=row.cnt,
            total_amount=float(row.total_amount or 0),
            approval_rate=round(int(row.approved_cnt or 0) / row.cnt * 100, 1) if row.cnt else 0.0,
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# GET /analytics/pipeline-funnel
# ---------------------------------------------------------------------------

@router.get(
    "/pipeline-funnel",
    response_model=List[PipelineFunnelStage],
    status_code=status.HTTP_200_OK,
    summary="Application counts at each pipeline stage (funnel view)",
)
def pipeline_funnel(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[PipelineFunnelStage]:
    stage_defs = [
        ("submitted",        "Submitted",          ApplicationStatus.SUBMITTED),
        ("ocr_complete",     "OCR Extracted",      ApplicationStatus.OCR_COMPLETE),
        ("ratio_calculated", "Ratios Calculated",  ApplicationStatus.RATIO_CALCULATED),
        ("rule_evaluated",   "Rules Evaluated",    ApplicationStatus.RULE_EVALUATED),
        ("ml_predicted",     "ML Predicted",       ApplicationStatus.ML_PREDICTED),
        ("report_generated", "Report Generated",   ApplicationStatus.REPORT_GENERATED),
        ("decided",          "Final Decision",     None),
    ]

    # Count applications that have passed each stage (>= current stage ordinal)
    status_order = [
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.OCR_PROCESSING,
        ApplicationStatus.OCR_COMPLETE,
        ApplicationStatus.RATIO_CALCULATED,
        ApplicationStatus.RULE_EVALUATED,
        ApplicationStatus.ML_PREDICTED,
        ApplicationStatus.REPORT_GENERATED,
        ApplicationStatus.APPROVED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.MANUAL_REVIEW,
        ApplicationStatus.WITHDRAWN,
    ]
    status_values = [s.value for s in status_order]

    def count_at_or_past(status_val: str) -> int:
        idx = status_values.index(status_val)
        past = status_values[idx:]
        return (
            db.query(func.count(Application.id))
            .filter(Application.status.in_(past))
            .scalar() or 0
        )

    decided_count = (
        db.query(func.count(Application.id))
        .filter(Application.final_decision != FinalDecision.PENDING)
        .scalar() or 0
    )

    submitted_count = count_at_or_past("submitted")
    results: List[PipelineFunnelStage] = []
    prev_count: Optional[int] = None

    for key, label, st in stage_defs:
        if st is not None:
            cnt = count_at_or_past(st.value)
        else:
            cnt = decided_count

        conv = round(cnt / prev_count * 100, 1) if prev_count else None
        results.append(PipelineFunnelStage(stage=key, label=label, count=cnt, conversion_rate=conv))
        prev_count = cnt if cnt else prev_count

    return results


# ---------------------------------------------------------------------------
# GET /analytics/rule-triggers
# ---------------------------------------------------------------------------

@router.get(
    "/rule-triggers",
    response_model=List[RuleTriggerStat],
    status_code=status.HTTP_200_OK,
    summary="Which rules fire most often (from audit_logs JSON)",
    description=(
        "Counts how many times each rule has triggered based on rule_results "
        "stored on applications. Returns rules ordered by trigger frequency."
    ),
)
def rule_trigger_stats(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RuleTriggerStat]:
    # Rule evaluation results are persisted per application inside the latest
    # financial_ratios row, at calculation_metadata -> 'rule_evaluation' -> 'results'.
    # Each element already carries rule_name / category / is_mandatory, so no join
    # with the rules table is needed (and this stays correct for deleted rules).
    raw_sql = """
        SELECT
            elem->>'rule_id'                             AS rule_id,
            MAX(elem->>'rule_name')                      AS rule_name,
            MAX(elem->>'category')                       AS category,
            bool_or((elem->>'is_mandatory')::boolean)    AS is_mandatory,
            COUNT(*)                                     AS trigger_count
        FROM financial_ratios fr,
             jsonb_array_elements(
                 COALESCE(fr.calculation_metadata->'rule_evaluation'->'results', '[]'::jsonb)
             ) AS elem
        WHERE (elem->>'triggered') = 'true'
        GROUP BY elem->>'rule_id'
        ORDER BY trigger_count DESC
        LIMIT :limit
    """
    from sqlalchemy import text
    rows = db.execute(text(raw_sql), {"limit": limit}).fetchall()

    return [
        RuleTriggerStat(
            rule_id=row.rule_id or "unknown",
            rule_name=row.rule_name or "Deleted Rule",
            category=row.category or "unknown",
            trigger_count=row.trigger_count,
            is_mandatory=bool(row.is_mandatory),
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# GET /analytics/pipeline-metrics
# ---------------------------------------------------------------------------

@router.get(
    "/pipeline-metrics",
    status_code=status.HTTP_200_OK,
    summary="Stage completion counts and conversion rates",
)
def pipeline_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    total = db.query(func.count(Application.id)).scalar() or 0
    ocr_done = db.query(func.count(Application.id)).filter(Application.ocr_completed.is_(True)).scalar() or 0
    ratios_done = db.query(func.count(Application.id)).filter(Application.ratios_calculated.is_(True)).scalar() or 0
    rules_done = db.query(func.count(Application.id)).filter(Application.rules_evaluated.is_(True)).scalar() or 0
    ml_done = db.query(func.count(Application.id)).filter(Application.ml_predicted.is_(True)).scalar() or 0
    report_done = db.query(func.count(Application.id)).filter(Application.report_generated.is_(True)).scalar() or 0

    stage_counts = {
        "total": total,
        "ocr_completed": ocr_done,
        "ratios_calculated": ratios_done,
        "rules_evaluated": rules_done,
        "ml_predicted": ml_done,
        "report_generated": report_done,
    }

    def conv(a: int, b: int) -> Optional[float]:
        return round(a / b * 100, 1) if b else None

    return {
        "stage_completion": stage_counts,
        "stage_conversion": {
            "ocr": conv(ocr_done, total),
            "ratios": conv(ratios_done, ocr_done),
            "rules": conv(rules_done, ratios_done),
            "ml": conv(ml_done, rules_done),
            "report": conv(report_done, ml_done),
        },
        "bottleneck_stage": _find_bottleneck(stage_counts),
    }


def _find_bottleneck(counts: Dict[str, int]) -> Optional[str]:
    stages = ["ocr_completed", "ratios_calculated", "rules_evaluated", "ml_predicted", "report_generated"]
    drops = {}
    prev = counts.get("total", 0)
    for s in stages:
        curr = counts.get(s, 0)
        if prev:
            drops[s] = (prev - curr) / prev
        prev = curr
    if not drops:
        return None
    return max(drops, key=lambda k: drops[k])
