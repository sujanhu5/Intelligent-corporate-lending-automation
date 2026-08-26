"""
OCRService — orchestrates the full extraction pipeline for one document:
  1. Retrieve document record and resolve file path
  2. Set document status → PROCESSING
  3. Call extractor.extract_text()   → ExtractionResult
  4. Call parser.parse_financials()  → ParsedFinancials
  5. Persist OCRData record (raw text + extracted fields + metadata)
  6. Set document status → EXTRACTED (or FAILED on error)
  7. Write audit log
  8. Return structured OCRResultResponse
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.core.exceptions import NotFoundError, OCRError
from app.core.logging import get_logger
from app.models.audit_log import AuditAction
from app.models.document import DocumentStatus
from app.models.ocr_data import OCRData
from app.models.user import User
from app.repositories.application_repository import ApplicationRepository
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.ocr import (
    ApplicationOCRSummary,
    ExtractedFieldItem,
    FIELD_DISPLAY_NAMES,
    OCRResultResponse,
    OCRTriggerResponse,
)
from ocr.extractor import extract_text
from ocr.parser import parse_financials, FINANCIAL_FIELDS

logger = get_logger(__name__)


class OCRService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._doc_repo = DocumentRepository(db)
        self._app_repo = ApplicationRepository(db)
        self._audit = AuditLogRepository(db)

    # -------------------------------------------------------------------------
    # Trigger extraction (synchronous — async/Celery version in Module 9)
    # -------------------------------------------------------------------------

    def extract_document(
        self,
        document_id: uuid.UUID,
        triggered_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> OCRResultResponse:
        """
        Run OCR extraction on a single document synchronously.
        Idempotent — re-running overwrites any existing OCRData for the document.
        Annual reports are delegated to AnnualReportService for section-aware extraction.
        """
        doc = self._doc_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError(message=f"Document '{document_id}' not found.")

        # Annual reports need section-aware extraction
        from app.models.document import DocumentType as DT
        if doc.document_type == DT.ANNUAL_REPORT:
            return self._extract_annual_report(doc, triggered_by, ip_address, request_id)

        # Mark as processing
        self._doc_repo.update_status(doc, DocumentStatus.PROCESSING)
        self._audit.log(
            action=AuditAction.OCR_STARTED,
            description=f"OCR extraction started for '{doc.original_filename}'.",
            user_id=triggered_by.id,
            entity_type="document",
            entity_id=str(doc.id),
            ip_address=ip_address,
            request_id=request_id,
        )

        start_time = datetime.now(timezone.utc)

        try:
            # Resolve absolute path
            file_path = BASE_DIR / doc.file_path

            # ── Step 1: Extract raw text ──────────────────────────────────────
            extraction = extract_text(str(file_path))

            # ── Step 2: Parse financial fields ───────────────────────────────
            parsed = parse_financials(extraction.raw_text)

            # ── Step 3: Persist ───────────────────────────────────────────────
            ocr_record = self._upsert_ocr_data(
                doc_id=document_id,
                raw_text=extraction.raw_text,
                confidence_score=extraction.mean_confidence,
                page_count=extraction.page_count,
                extracted_fields=parsed.fields,
                metadata={
                    "extraction_method": extraction.extraction_method,
                    "duration_seconds": extraction.duration_seconds,
                    "char_count": len(extraction.raw_text),
                    "extracted_field_count": parsed.extracted_count,
                    "overall_parse_confidence": parsed.overall_confidence,
                    "warnings": extraction.warnings + parsed.warnings,
                    "timestamp": start_time.isoformat(),
                    "field_confidence": parsed.confidence,
                },
            )

            # ── Step 4: Mark document as extracted ───────────────────────────
            self._doc_repo.update_status(doc, DocumentStatus.EXTRACTED)

            # ── Step 5: Advance the application once every document is done ──
            self._mark_application_ocr_complete(doc.application_id)

        except Exception as exc:
            error_msg = str(exc)
            self._doc_repo.update_status(doc, DocumentStatus.FAILED, error=error_msg)
            self._audit.log(
                action=AuditAction.OCR_FAILED,
                description=f"OCR extraction failed for '{doc.original_filename}': {error_msg}",
                user_id=triggered_by.id,
                entity_type="document",
                entity_id=str(doc.id),
                ip_address=ip_address,
                request_id=request_id,
            )
            logger.error("OCR extraction failed", extra={"doc_id": str(document_id), "error": error_msg})
            raise OCRError(message=f"OCR extraction failed: {error_msg}") from exc

        self._audit.log(
            action=AuditAction.OCR_COMPLETED,
            description=(
                f"OCR extraction completed for '{doc.original_filename}'. "
                f"{parsed.extracted_count}/{len(FINANCIAL_FIELDS)} fields extracted."
            ),
            user_id=triggered_by.id,
            entity_type="document",
            entity_id=str(doc.id),
            new_values={
                "extracted_fields": parsed.extracted_count,
                "confidence": extraction.mean_confidence,
            },
            ip_address=ip_address,
            request_id=request_id,
        )

        logger.info(
            "OCR extraction complete",
            extra={
                "doc_id": str(document_id),
                "fields_extracted": parsed.extracted_count,
                "confidence": extraction.mean_confidence,
            },
        )

        return self._build_result_response(ocr_record, doc)

    # -------------------------------------------------------------------------
    # Annual report extraction
    # -------------------------------------------------------------------------

    def _extract_annual_report(
        self,
        doc,
        triggered_by: User,
        ip_address: str,
        request_id: str,
    ) -> OCRResultResponse:
        """Delegate annual report processing to AnnualReportService."""
        from app.services.annual_report_service import AnnualReportService
        ar_service = AnnualReportService(self._db)
        ar_service.process_annual_report(
            document_id=doc.id,
            triggered_by=triggered_by,
            ip_address=ip_address,
            request_id=request_id,
        )
        self._db.expire(doc)
        return self._build_result_response(doc.ocr_data, doc)

    # -------------------------------------------------------------------------
    # Pipeline stage advancement
    # -------------------------------------------------------------------------

    def _mark_application_ocr_complete(self, application_id: uuid.UUID) -> None:
        """
        Advance the application to OCR_COMPLETE once no document is still
        pending. Downstream stages gate on this, so a partially-extracted
        application must not pass.
        """
        docs = self._doc_repo.list_by_application(application_id)
        if not docs or any(d.status != DocumentStatus.EXTRACTED for d in docs):
            return

        app = self._app_repo.get_by_id(application_id, load_company=False)
        if app and not app.ocr_completed:
            self._app_repo.mark_pipeline_stage(app, "ocr_completed")

    # -------------------------------------------------------------------------
    # Get existing OCR result
    # -------------------------------------------------------------------------

    def get_ocr_result(self, document_id: uuid.UUID) -> OCRResultResponse:
        doc = self._doc_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError(message=f"Document '{document_id}' not found.")
        if doc.ocr_data is None:
            raise NotFoundError(
                message=f"No OCR data found for document '{document_id}'. "
                        f"Run extraction first via POST /ocr/extract/{document_id}."
            )
        return self._build_result_response(doc.ocr_data, doc)

    # -------------------------------------------------------------------------
    # Aggregate OCR across all documents for an application
    # -------------------------------------------------------------------------

    def get_application_ocr_summary(
        self, application_id: uuid.UUID
    ) -> ApplicationOCRSummary:
        docs = self._doc_repo.list_by_application(application_id)
        total = len(docs)
        extracted = sum(1 for d in docs if d.status == DocumentStatus.EXTRACTED)
        failed = sum(1 for d in docs if d.status == DocumentStatus.FAILED)
        pending = total - extracted - failed

        # Merge extracted fields — take the value from the document with the
        # highest extraction confidence for each field.
        combined: Dict[str, Optional[float]] = {f: None for f in FINANCIAL_FIELDS}
        sources: Dict[str, str] = {}
        confidences: Dict[str, float] = {}
        all_warnings = []

        for doc in docs:
            if doc.ocr_data is None or doc.ocr_data.extracted_fields is None:
                continue
            meta = doc.ocr_data.extraction_metadata or {}
            field_conf = meta.get("field_confidence", {})

            for field_name in FINANCIAL_FIELDS:
                value = doc.ocr_data.extracted_fields.get(field_name)
                if value is None:
                    continue
                conf = field_conf.get(field_name, 0.5)
                if combined[field_name] is None or conf > confidences.get(field_name, 0):
                    combined[field_name] = value
                    sources[field_name] = str(doc.id)
                    confidences[field_name] = conf

            all_warnings.extend(meta.get("warnings", []))

        avg_conf = sum(confidences.values()) / len(confidences) if confidences else 0.0

        return ApplicationOCRSummary(
            application_id=application_id,
            total_documents=total,
            extracted_documents=extracted,
            failed_documents=failed,
            pending_documents=pending,
            combined_fields=combined,
            field_sources=sources,
            overall_confidence=round(avg_conf, 3),
            warnings=list(set(all_warnings)),  # deduplicate
        )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _upsert_ocr_data(
        self,
        doc_id: uuid.UUID,
        raw_text: str,
        confidence_score: float,
        page_count: int,
        extracted_fields: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> OCRData:
        """Create or overwrite the OCRData record for a document."""
        existing = (
            self._db.query(OCRData)
            .filter(OCRData.document_id == doc_id)
            .first()
        )
        if existing:
            existing.raw_text = raw_text
            existing.confidence_score = confidence_score
            existing.page_count = page_count
            existing.extracted_fields = extracted_fields
            existing.extraction_metadata = metadata
            self._db.flush()
            return existing

        record = OCRData(
            document_id=doc_id,
            raw_text=raw_text,
            confidence_score=confidence_score,
            page_count=page_count,
            extracted_fields=extracted_fields,
            extraction_metadata=metadata,
        )
        self._db.add(record)
        self._db.flush()
        return record

    def _build_result_response(self, ocr: OCRData, doc) -> OCRResultResponse:
        """Build OCRResultResponse with per-field detail list."""
        meta = ocr.extraction_metadata or {}
        field_conf = meta.get("field_confidence", {})
        fields = ocr.extracted_fields or {}

        field_details = []
        for fname in FINANCIAL_FIELDS:
            value = fields.get(fname)
            conf = field_conf.get(fname, 0.0)
            field_details.append(
                ExtractedFieldItem(
                    field_name=fname,
                    display_name=FIELD_DISPLAY_NAMES.get(fname, fname),
                    value=value,
                    confidence=conf,
                    formatted_value=_fmt_currency(value),
                )
            )

        return OCRResultResponse(
            id=ocr.id,
            document_id=ocr.document_id,
            document_status=doc.status,
            raw_text=ocr.raw_text,
            page_count=ocr.page_count,
            confidence_score=ocr.confidence_score,
            extracted_fields=ocr.extracted_fields,
            extraction_metadata=ocr.extraction_metadata,
            field_details=field_details,
            created_at=ocr.created_at,
            updated_at=ocr.updated_at,
        )


def _fmt_currency(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    return f"RM {value:,.2f}"
