"""
ReportService — orchestrates PDF report generation for one application.

Pipeline:
  1. Validate: application must have at least ratios calculated.
  2. Load all relevant data: application, company, documents, OCR fields,
     financial ratios, rule evaluation, ML prediction.
  3. Assign a monotonically increasing version number.
  4. Create a Report DB record with status=GENERATING.
  5. Call reports.builder.build_report() to write the PDF.
  6. Update Report record with status=COMPLETE and file size.
  7. Mark application pipeline stage report_generated.
  8. Write audit log.
  9. Return ReportResponse.

If build_report() raises an exception, the Report record is marked FAILED
and the exception is re-raised as ReportGenerationError.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import BadRequestError, NotFoundError, ReportGenerationError
from app.core.logging import get_logger
from app.models.application import ApplicationStatus
from app.models.audit_log import AuditAction
from app.models.financial_ratio import FinancialRatio
from app.models.report import ReportStatus
from app.models.user import User
from app.repositories.application_repository import ApplicationRepository
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.report_repository import ReportRepository
from app.schemas.report import ReportListResponse, ReportResponse
from reports.builder import build_report

logger = get_logger(__name__)


class ReportService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._app_repo = ApplicationRepository(db)
        self._doc_repo = DocumentRepository(db)
        self._report_repo = ReportRepository(db)
        self._audit = AuditLogRepository(db)

    # =========================================================================
    # Generate
    # =========================================================================

    def generate_report(
        self,
        application_id: uuid.UUID,
        generated_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> ReportResponse:
        # ── 1. Load application ───────────────────────────────────────────────
        app = self._app_repo.get_by_id(application_id)
        if not app:
            raise NotFoundError(message=f"Application '{application_id}' not found.")

        if not app.ratios_calculated:
            raise BadRequestError(
                message=(
                    f"Application '{app.application_number}' has not had financial ratios "
                    "calculated. At minimum, ratio calculation must be complete before "
                    "generating a report."
                )
            )

        # ── 2. Load all data ──────────────────────────────────────────────────
        company = app.company
        documents = list(app.documents)
        fr = self._get_latest_ratio(application_id)
        prediction_rec = self._get_latest_prediction(application_id)

        # Build plain-dict representations for the builder (no ORM objects)
        app_data = self._serialize_application(app, generated_by.email)
        company_data = self._serialize_company(company)
        doc_list = self._serialize_documents(documents)
        ocr_fields = (fr.extracted_financials or {}) if fr else {}
        ratios_list = self._serialize_ratios(fr)
        overall_health = fr.overall_health if fr else None
        rule_eval_dict = self._extract_rule_eval(fr)
        prediction_dict = self._serialize_prediction(prediction_rec)

        # ── 3. Determine version number ───────────────────────────────────────
        version = self._report_repo.next_version(application_id)

        # ── 4. Create GENERATING record ───────────────────────────────────────
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = (
            f"credit_report_{app.application_number.replace('-', '_')}"
            f"_v{version}_{timestamp}.pdf"
        )
        rel_path = filename
        abs_path: Path = settings.report_path / filename

        report_rec = self._report_repo.create(
            application_id=application_id,
            status=ReportStatus.GENERATING,
            filename=filename,
            file_path=rel_path,
            version=version,
            generated_by=generated_by.email,
        )

        # ── 5. Build PDF ──────────────────────────────────────────────────────
        try:
            build_report(
                output_path=abs_path,
                app_data=app_data,
                company_data=company_data,
                documents=doc_list,
                ocr_fields=ocr_fields,
                ratios=ratios_list,
                overall_health=overall_health,
                rule_evaluation=rule_eval_dict,
                prediction=prediction_dict,
                generated_by=generated_by.email,
            )
        except Exception as exc:
            self._report_repo.mark_failed(report_rec, str(exc))
            logger.error(
                "Report generation failed",
                extra={"app_id": str(application_id), "error": str(exc)},
            )
            raise ReportGenerationError(
                message=f"PDF generation failed: {exc}"
            ) from exc

        # ── 6. Mark COMPLETE ──────────────────────────────────────────────────
        file_size = abs_path.stat().st_size
        self._report_repo.mark_complete(report_rec, file_size)

        # ── 7. Mark pipeline stage ────────────────────────────────────────────
        self._app_repo.mark_pipeline_stage(app, "report_generated")
        if app.status not in (ApplicationStatus.REJECTED, ApplicationStatus.MANUAL_REVIEW,
                               ApplicationStatus.APPROVED):
            self._app_repo.update(app, status=ApplicationStatus.REPORT_GENERATED)

        # ── 8. Audit log ──────────────────────────────────────────────────────
        self._audit.log(
            action=AuditAction.REPORT_GENERATED,
            description=(
                f"Credit assessment report v{version} generated for "
                f"application '{app.application_number}'. "
                f"File: '{filename}' ({file_size / 1024:.1f} KB)."
            ),
            user_id=generated_by.id,
            entity_type="report",
            entity_id=str(report_rec.id),
            new_values={
                "version": version,
                "filename": filename,
                "file_size_bytes": file_size,
            },
            ip_address=ip_address,
            request_id=request_id,
        )

        logger.info(
            "Report generated",
            extra={
                "app_id": str(application_id),
                "version": version,
                "size_kb": round(file_size / 1024, 1),
            },
        )

        return ReportResponse.model_validate(report_rec)

    # =========================================================================
    # Read
    # =========================================================================

    def get_latest_report(self, application_id: uuid.UUID) -> ReportResponse:
        app = self._app_repo.get_by_id(application_id)
        if not app:
            raise NotFoundError(message=f"Application '{application_id}' not found.")

        report = self._report_repo.get_latest_for_application(application_id)
        if not report:
            raise NotFoundError(
                message=(
                    f"No report found for application '{app.application_number}'. "
                    "Run POST /reports/generate/{application_id} first."
                )
            )
        return ReportResponse.model_validate(report)

    def list_reports(self, application_id: uuid.UUID) -> ReportListResponse:
        app = self._app_repo.get_by_id(application_id)
        if not app:
            raise NotFoundError(message=f"Application '{application_id}' not found.")

        reports = self._report_repo.list_for_application(application_id)
        return ReportListResponse(
            items=[ReportResponse.model_validate(r) for r in reports],
            total=len(reports),
        )

    def get_report_path(self, report_id: uuid.UUID) -> Path:
        """Return the absolute path to the PDF file for download."""
        report = self._report_repo.get_by_id(report_id)
        if not report:
            raise NotFoundError(message=f"Report '{report_id}' not found.")
        if report.status != ReportStatus.COMPLETE:
            raise BadRequestError(
                message=f"Report '{report_id}' is not yet complete (status: {report.status.value})."
            )
        abs_path = settings.report_path / report.file_path
        if not abs_path.exists():
            raise NotFoundError(
                message=f"Report file not found on disk. It may have been deleted."
            )
        return abs_path

    # =========================================================================
    # Serialization helpers (ORM → plain dict for the builder)
    # =========================================================================

    def _serialize_application(self, app: Any, generated_by_email: str) -> Dict[str, Any]:
        return {
            "application_number": app.application_number,
            "loan_amount_requested": float(app.loan_amount_requested),
            "loan_purpose": app.loan_purpose.value,
            "loan_tenure_months": app.loan_tenure_months,
            "interest_rate_requested": float(app.interest_rate_requested) if app.interest_rate_requested else None,
            "collateral_description": app.collateral_description,
            "collateral_value": float(app.collateral_value) if app.collateral_value else None,
            "status": app.status.value,
            "final_decision": app.final_decision.value,
            "risk_score": float(app.risk_score) if app.risk_score else None,
            "decision_reason": app.decision_reason,
            "officer_notes": app.officer_notes,
            "assigned_officer": str(app.assigned_officer_id) if app.assigned_officer_id else "Not assigned",
        }

    def _serialize_company(self, company: Any) -> Dict[str, Any]:
        if not company:
            return {}
        return {
            "name": company.name,
            "registration_number": company.registration_number,
            "tax_id": company.tax_id,
            "gst_number": company.gst_number,
            "company_type": company.company_type.value if company.company_type else None,
            "industry": company.industry.value if company.industry else None,
            "incorporation_date": company.incorporation_date,
            "country_of_incorporation": company.country_of_incorporation,
            "registered_address": company.registered_address,
            "city": company.city,
            "state": company.state,
            "contact_email": company.contact_email,
            "contact_phone": company.contact_phone,
            "annual_turnover": float(company.annual_turnover) if company.annual_turnover else None,
            "number_of_employees": company.number_of_employees,
        }

    def _serialize_documents(self, documents: List[Any]) -> List[Dict[str, Any]]:
        return [
            {
                "document_type": doc.document_type.value,
                "original_filename": doc.original_filename,
                "file_size_bytes": doc.file_size_bytes,
                "financial_year": doc.financial_year,
                "status": doc.status.value,
            }
            for doc in documents
        ]

    def _serialize_ratios(self, fr: Optional[FinancialRatio]) -> List[Dict[str, Any]]:
        if not fr or not fr.ratios:
            return []
        result = []
        for name, data in fr.ratios.items():
            if isinstance(data, dict):
                result.append({
                    "name": name,
                    "display_name": name.replace("_", " ").title(),
                    "value": data.get("value"),
                    "unit": data.get("unit", ""),
                    "formula": data.get("formula", ""),
                    "risk_level": data.get("risk_level", "unknown"),
                    "health_signal": data.get("health_signal", "neutral"),
                    "interpretation": data.get("interpretation", ""),
                    "benchmark_min": data.get("benchmark_min"),
                    "benchmark_max": data.get("benchmark_max"),
                })
        return result

    def _extract_rule_eval(self, fr: Optional[FinancialRatio]) -> Dict[str, Any]:
        if not fr or not fr.calculation_metadata:
            return {}
        return fr.calculation_metadata.get("rule_evaluation", {})

    def _serialize_prediction(self, pred: Optional[Any]) -> Dict[str, Any]:
        if not pred:
            return {}
        return {
            "model_used": pred.model_used.value if pred.model_used else None,
            "probability_of_default": float(pred.probability_of_default),
            "outcome": pred.outcome.value if pred.outcome else None,
            "risk_score": float(pred.risk_score),
            "risk_level": pred.risk_level.value if pred.risk_level else None,
            "shap_values": pred.shap_values or {},
            "feature_importance": pred.feature_importance or {},
            "explanation_text": pred.explanation_text,
            "recommendation": pred.recommendation,
            "ml_executed": pred.ml_executed,
            "skip_reason": pred.skip_reason,
            "model_metrics": pred.model_metrics or {},
        }

    # =========================================================================
    # DB query helpers
    # =========================================================================

    def _get_latest_ratio(self, application_id: uuid.UUID) -> Optional[FinancialRatio]:
        return (
            self._db.query(FinancialRatio)
            .filter(FinancialRatio.application_id == application_id)
            .order_by(FinancialRatio.created_at.desc())
            .first()
        )

    def _get_latest_prediction(self, application_id: uuid.UUID) -> Optional[Any]:
        from app.models.prediction import Prediction
        return (
            self._db.query(Prediction)
            .filter(Prediction.application_id == application_id)
            .order_by(Prediction.created_at.desc())
            .first()
        )
