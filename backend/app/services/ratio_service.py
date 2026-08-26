"""
RatioService — orchestrates financial ratio calculation for one application.

Pipeline:
  1. Retrieve merged OCR data (combined_fields from ApplicationOCRSummary)
  2. Run calculator.calculate_all()  → RatioSet
  3. Run interpreter.interpret()     → RatioInterpretation per ratio
  4. Determine overall_health()
  5. Persist FinancialRatio record
  6. Mark application pipeline stage: ratios_calculated
  7. Write audit log
  8. Return RatioCalculationResponse
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.logging import get_logger
from app.models.audit_log import AuditAction
from app.models.financial_ratio import FinancialRatio
from app.models.user import User
from app.repositories.application_repository import ApplicationRepository
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.ratio import RatioCalculationResponse, RatioDetail, RatioSummaryResponse
from app.services.ocr_service import OCRService
from ratios.calculator import calculate_all, RatioSet
from ratios.interpreter import interpret, overall_health, RatioInterpretation

logger = get_logger(__name__)

# Ratios highlighted on the dashboard summary card
_KEY_METRIC_NAMES = [
    "current_ratio",
    "debt_equity_ratio",
    "net_profit_margin",
    "return_on_assets",
    "interest_coverage_ratio",
    "debt_service_coverage_ratio",
]


class RatioService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._app_repo = ApplicationRepository(db)
        self._doc_repo = DocumentRepository(db)
        self._audit = AuditLogRepository(db)

    # -------------------------------------------------------------------------
    # Calculate
    # -------------------------------------------------------------------------

    def calculate_for_application(
        self,
        application_id: uuid.UUID,
        financial_year: Optional[str],
        calculated_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> RatioCalculationResponse:
        """
        Merge OCR data from all documents → calculate → interpret → persist.
        Idempotent — re-running overwrites the existing FinancialRatio record.
        """
        app = self._app_repo.get_by_id(application_id)
        if not app:
            raise NotFoundError(message=f"Application '{application_id}' not found.")

        if not app.ocr_completed:
            raise BadRequestError(
                message=(
                    f"Application '{app.application_number}' has not completed OCR extraction. "
                    "Run OCR on all documents before calculating ratios."
                )
            )

        # ── Step 1: Get merged financial fields ──────────────────────────────
        ocr_svc = OCRService(self._db)
        ocr_summary = ocr_svc.get_application_ocr_summary(application_id)
        fields = ocr_summary.combined_fields

        if not any(v is not None for v in fields.values()):
            raise BadRequestError(
                message="No financial data was extracted from any document. "
                        "Ensure OCR extraction has completed successfully."
            )

        # ── Step 2: Calculate ratios ─────────────────────────────────────────
        ratio_set: RatioSet = calculate_all(fields)

        # ── Step 3: Interpret each ratio ─────────────────────────────────────
        interpretations: Dict[str, RatioInterpretation] = {}
        for name, ratio_result in ratio_set.ratios.items():
            interpretations[name] = interpret(ratio_result)

        # ── Step 4: Overall health ───────────────────────────────────────────
        health_label, health_note = overall_health(interpretations)

        # ── Step 5: Build JSON-serialisable ratios dict for DB ───────────────
        ratios_json = _build_ratios_json(ratio_set, interpretations)

        # ── Step 6: Persist FinancialRatio ───────────────────────────────────
        fr = self._upsert_financial_ratio(
            application_id=application_id,
            financial_year=financial_year,
            extracted_financials=fields,
            ratios=ratios_json,
            overall_health=health_label,
            health_notes=health_note,
            metadata={
                "calculated_by": calculated_by.email,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "missing_fields": ratio_set.missing_fields,
                "warnings": ratio_set.warnings,
                "ocr_confidence": ocr_summary.overall_confidence,
            },
        )

        # ── Step 7: Mark pipeline stage ──────────────────────────────────────
        self._app_repo.mark_pipeline_stage(app, "ratios_calculated")

        # Also update the application's aggregate risk score (preliminary)
        critical_count = sum(
            1 for i in interpretations.values()
            if isinstance(i, RatioInterpretation) and i.risk_level in ("very_high", "high")
        )
        preliminary_risk = min(100, critical_count * 10)
        self._app_repo.update(app, risk_score=preliminary_risk)

        # ── Step 8: Audit log ────────────────────────────────────────────────
        computed = sum(1 for r in ratio_set.ratios.values() if r.value is not None)
        self._audit.log(
            action=AuditAction.RATIOS_CALCULATED,
            description=(
                f"Financial ratios calculated for application '{app.application_number}'. "
                f"{computed}/20 ratios computed. Overall health: {health_label}."
            ),
            user_id=calculated_by.id,
            entity_type="financial_ratio",
            entity_id=str(fr.id),
            new_values={
                "computed_ratios": computed,
                "overall_health": health_label,
                "critical_count": critical_count,
            },
            ip_address=ip_address,
            request_id=request_id,
        )

        logger.info(
            "Ratio calculation complete",
            extra={
                "app_id": str(application_id),
                "computed": computed,
                "health": health_label,
            },
        )

        return self._build_response(fr, ratio_set, interpretations)

    # -------------------------------------------------------------------------
    # Read
    # -------------------------------------------------------------------------

    def get_for_application(self, application_id: uuid.UUID) -> RatioCalculationResponse:
        fr = self._get_latest_ratio_record(application_id)
        if not fr:
            raise NotFoundError(
                message=f"No ratio data found for application '{application_id}'. "
                        "Run calculation first via POST /ratios/calculate/{application_id}."
            )
        ratio_set = calculate_all(fr.extracted_financials or {})
        interpretations = {n: interpret(r) for n, r in ratio_set.ratios.items()}
        return self._build_response(fr, ratio_set, interpretations)

    def get_summary(self, application_id: uuid.UUID) -> RatioSummaryResponse:
        fr = self._get_latest_ratio_record(application_id)
        if not fr or not fr.ratios:
            return RatioSummaryResponse(
                application_id=application_id,
                overall_health=None,
                calculated_count=0,
                critical_ratios=[],
                high_risk_ratios=[],
                key_metrics={},
            )

        ratios = fr.ratios
        critical = [n for n, r in ratios.items() if r.get("risk_level") == "very_high"]
        high = [n for n, r in ratios.items() if r.get("risk_level") == "high"]
        key_metrics = {
            name: ratios[name]["value"] if name in ratios else None
            for name in _KEY_METRIC_NAMES
        }
        calc_count = sum(1 for r in ratios.values() if r.get("value") is not None)

        return RatioSummaryResponse(
            application_id=application_id,
            overall_health=fr.overall_health,
            calculated_count=calc_count,
            critical_ratios=critical,
            high_risk_ratios=high,
            key_metrics=key_metrics,
        )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_latest_ratio_record(self, application_id: uuid.UUID) -> Optional[FinancialRatio]:
        return (
            self._db.query(FinancialRatio)
            .filter(FinancialRatio.application_id == application_id)
            .order_by(FinancialRatio.created_at.desc())
            .first()
        )

    def _upsert_financial_ratio(self, **kwargs) -> FinancialRatio:
        existing = self._get_latest_ratio_record(kwargs["application_id"])
        if existing:
            for k, v in kwargs.items():
                if hasattr(existing, k):
                    setattr(existing, k, v)
            self._db.flush()
            return existing
        metadata = kwargs.pop("metadata", None)
        fr = FinancialRatio(**kwargs, calculation_metadata=metadata)
        self._db.add(fr)
        self._db.flush()
        return fr

    def _build_response(
        self,
        fr: FinancialRatio,
        ratio_set: RatioSet,
        interpretations: Dict[str, RatioInterpretation],
    ) -> RatioCalculationResponse:
        details = []
        for name, ratio_result in ratio_set.ratios.items():
            interp = interpretations.get(name)
            if interp:
                details.append(
                    RatioDetail(
                        name=name,
                        display_name=interp.display_name,
                        value=interp.value,
                        unit=interp.unit,
                        formula=interp.formula,
                        risk_level=interp.risk_level,
                        health_signal=interp.health_signal,
                        interpretation=interp.interpretation,
                        benchmark_min=interp.benchmark_min,
                        benchmark_max=interp.benchmark_max,
                        benchmark_note=interp.benchmark_note,
                        components=ratio_result.components,
                    )
                )

        computed = sum(1 for r in ratio_set.ratios.values() if r.value is not None)
        meta = fr.calculation_metadata or {}

        return RatioCalculationResponse(
            id=fr.id,
            application_id=fr.application_id,
            financial_year=fr.financial_year,
            overall_health=fr.overall_health,
            health_notes=fr.health_notes,
            ratios=details,
            missing_fields=meta.get("missing_fields", ratio_set.missing_fields),
            warnings=meta.get("warnings", ratio_set.warnings),
            calculated_count=computed,
            total_ratios=len(ratio_set.ratios),
            created_at=fr.created_at,
            updated_at=fr.updated_at,
        )


def _build_ratios_json(
    ratio_set: RatioSet,
    interpretations: Dict[str, RatioInterpretation],
) -> Dict[str, Any]:
    """Serialise ratio results + interpretations into the JSONB structure."""
    out: Dict[str, Any] = {}
    for name, r in ratio_set.ratios.items():
        interp = interpretations.get(name)
        out[name] = {
            "value": r.value,
            "formula": r.formula,
            "unit": r.unit,
            "is_percentage": r.is_percentage,
            "risk_level": interp.risk_level if interp else "unknown",
            "health_signal": interp.health_signal if interp else "neutral",
            "interpretation": interp.interpretation if interp else "",
            "benchmark_min": interp.benchmark_min if interp else None,
            "benchmark_max": interp.benchmark_max if interp else None,
            "components": r.components,
        }
    return out
