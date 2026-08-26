"""
AnnualReportService — processes a complete annual report PDF by:

  1. Running the analyzer to detect financial statement sections
  2. Creating virtual sub-documents for each detected section (BS, P&L, CF)
  3. Running targeted OCR extraction on each section's page range
  4. Feeding extracted data through the existing pipeline

The sub-documents share the same physical file as the parent annual report
but record which pages they cover (page_range_start/end). The existing
OCR service and downstream pipeline (ratios → rules → ML → report) remain
unchanged — they operate on the sub-documents just like any other document.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.core.exceptions import BadRequestError, NotFoundError, OCRError
from app.core.logging import get_logger
from app.models.audit_log import AuditAction
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.ocr_data import OCRData
from app.repositories.application_repository import ApplicationRepository
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.document_repository import DocumentRepository
from ocr.annual_report_analyzer import (
    AnalysisResult,
    DetectedSection,
    SectionType,
    analyze_annual_report,
)
from ocr.parser import parse_financials, FINANCIAL_FIELDS

logger = get_logger(__name__)

_SECTION_TYPE_TO_DOC_TYPE = {
    SectionType.BALANCE_SHEET: DocumentType.BALANCE_SHEET,
    SectionType.PROFIT_LOSS: DocumentType.PROFIT_LOSS,
    SectionType.CASH_FLOW: DocumentType.CASH_FLOW,
}

_SECTION_LABELS = {
    SectionType.BALANCE_SHEET: "Balance Sheet",
    SectionType.PROFIT_LOSS: "Profit & Loss Statement",
    SectionType.CASH_FLOW: "Cash Flow Statement",
}


@dataclass
class SectionExtractionResult:
    section_type: str
    document_id: str
    page_range: str
    fields_extracted: int
    confidence: float
    title_found: str
    variant: str


@dataclass
class AnnualReportProcessingResult:
    parent_document_id: str
    application_id: str
    total_pages: int
    sections_detected: int
    sections_processed: List[SectionExtractionResult] = field(default_factory=list)
    analysis_method: str = "unknown"
    company_name: Optional[str] = None
    financial_year: Optional[str] = None
    unit_context: Optional[str] = None
    overall_confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    has_all_statements: bool = False
    combined_fields: Dict[str, Optional[float]] = field(default_factory=dict)
    total_fields_extracted: int = 0


class AnnualReportService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._doc_repo = DocumentRepository(db)
        self._app_repo = ApplicationRepository(db)
        self._audit = AuditLogRepository(db)

    def process_annual_report(
        self,
        document_id: uuid.UUID,
        triggered_by,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> AnnualReportProcessingResult:
        """
        Full processing pipeline for an annual report document:
        1. Analyze PDF to detect sections
        2. Create sub-documents for each section
        3. Extract financial data from each section
        4. Mark all sub-documents as EXTRACTED
        5. Mark parent as EXTRACTED
        """
        doc = self._doc_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError(message=f"Document '{document_id}' not found.")

        if doc.document_type != DocumentType.ANNUAL_REPORT:
            raise BadRequestError(
                message=f"Document '{document_id}' is not an annual report "
                        f"(type: {doc.document_type.value})."
            )

        # Mark parent as processing
        self._doc_repo.update_status(doc, DocumentStatus.PROCESSING)
        self._audit.log(
            action=AuditAction.OCR_STARTED,
            description=f"Annual report analysis started for '{doc.original_filename}'.",
            user_id=triggered_by.id,
            entity_type="document",
            entity_id=str(doc.id),
            ip_address=ip_address,
            request_id=request_id,
        )

        try:
            # Resolve file path
            file_path = BASE_DIR / doc.file_path

            # Step 1: Analyze the PDF
            analysis = analyze_annual_report(str(file_path))

            if not analysis.sections:
                self._doc_repo.update_status(
                    doc, DocumentStatus.FAILED,
                    error="No financial statement sections detected in the annual report."
                )
                raise OCRError(
                    message="Annual report analysis found no financial statement sections. "
                            "The PDF may not contain standard financial statements."
                )

            # Update financial year on the parent if detected
            if analysis.financial_year and not doc.financial_year:
                self._doc_repo.update(doc, financial_year=analysis.financial_year)

            # Step 2: Create sub-documents and extract data from each section
            section_results: List[SectionExtractionResult] = []
            combined_fields: Dict[str, Optional[float]] = {f: None for f in FINANCIAL_FIELDS}
            combined_confidences: Dict[str, float] = {}

            for section in analysis.sections:
                sub_result = self._process_section(
                    parent_doc=doc,
                    section=section,
                    analysis=analysis,
                    triggered_by=triggered_by,
                    ip_address=ip_address,
                    request_id=request_id,
                )
                section_results.append(sub_result)

                # Merge fields (best confidence wins)
                sub_doc = self._doc_repo.get_by_id(uuid.UUID(sub_result.document_id))
                if sub_doc and sub_doc.ocr_data and sub_doc.ocr_data.extracted_fields:
                    meta = sub_doc.ocr_data.extraction_metadata or {}
                    field_conf = meta.get("field_confidence", {})
                    for fname in FINANCIAL_FIELDS:
                        val = sub_doc.ocr_data.extracted_fields.get(fname)
                        if val is None:
                            continue
                        conf = field_conf.get(fname, 0.5)
                        if combined_fields[fname] is None or conf > combined_confidences.get(fname, 0):
                            combined_fields[fname] = val
                            combined_confidences[fname] = conf

            # Step 3: Create a combined OCR record on the parent annual report
            total_extracted = sum(1 for v in combined_fields.values() if v is not None)
            self._create_parent_ocr_record(
                doc=doc,
                combined_fields=combined_fields,
                combined_confidences=combined_confidences,
                analysis=analysis,
                section_results=section_results,
            )

            # Step 4: Mark parent as extracted
            self._doc_repo.update_status(doc, DocumentStatus.EXTRACTED)

            # Step 5: Check if all application docs are extracted
            self._mark_application_ocr_complete(doc.application_id)

            self._audit.log(
                action=AuditAction.OCR_COMPLETED,
                description=(
                    f"Annual report analysis completed for '{doc.original_filename}'. "
                    f"{len(analysis.sections)} sections detected, "
                    f"{total_extracted}/{len(FINANCIAL_FIELDS)} fields extracted."
                ),
                user_id=triggered_by.id,
                entity_type="document",
                entity_id=str(doc.id),
                new_values={
                    "sections": len(analysis.sections),
                    "fields_extracted": total_extracted,
                    "method": analysis.analysis_method,
                },
                ip_address=ip_address,
                request_id=request_id,
            )

            return AnnualReportProcessingResult(
                parent_document_id=str(doc.id),
                application_id=str(doc.application_id),
                total_pages=analysis.total_pages,
                sections_detected=len(analysis.sections),
                sections_processed=section_results,
                analysis_method=analysis.analysis_method,
                company_name=analysis.company_name,
                financial_year=analysis.financial_year,
                unit_context=analysis.unit_context.source_text if analysis.unit_context else None,
                overall_confidence=analysis.overall_confidence,
                warnings=analysis.warnings,
                has_all_statements=analysis.has_all_statements,
                combined_fields=combined_fields,
                total_fields_extracted=total_extracted,
            )

        except OCRError:
            raise
        except Exception as exc:
            error_msg = str(exc)
            self._doc_repo.update_status(doc, DocumentStatus.FAILED, error=error_msg)
            self._audit.log(
                action=AuditAction.OCR_FAILED,
                description=f"Annual report analysis failed: {error_msg}",
                user_id=triggered_by.id,
                entity_type="document",
                entity_id=str(doc.id),
                ip_address=ip_address,
                request_id=request_id,
            )
            logger.error("Annual report processing failed",
                         extra={"doc_id": str(document_id), "error": error_msg})
            raise OCRError(message=f"Annual report processing failed: {error_msg}") from exc

    def _process_section(
        self,
        parent_doc: Document,
        section: DetectedSection,
        analysis: AnalysisResult,
        triggered_by,
        ip_address: str,
        request_id: str,
    ) -> SectionExtractionResult:
        """
        Create a sub-document for a detected section and run OCR extraction
        on the section's text.
        """
        doc_type = _SECTION_TYPE_TO_DOC_TYPE[section.section_type]
        section_label = _SECTION_LABELS[section.section_type]

        # Create sub-document record (points to the same physical file)
        import hashlib
        section_hash = hashlib.sha256(
            f"{parent_doc.checksum_sha256}:{section.section_type.value}:{section.start_page}".encode()
        ).hexdigest()

        sub_doc = Document(
            application_id=parent_doc.application_id,
            document_type=doc_type,
            status=DocumentStatus.PROCESSING,
            original_filename=f"{section_label} (pp. {section.start_page}-{section.end_page}) — {parent_doc.original_filename}",
            stored_filename=f"section_{section.section_type.value}_{parent_doc.stored_filename}",
            file_path=parent_doc.file_path,
            file_size_bytes=parent_doc.file_size_bytes,
            mime_type=parent_doc.mime_type,
            checksum_sha256=section_hash,
            financial_year=analysis.financial_year or parent_doc.financial_year,
            parent_document_id=parent_doc.id,
            page_range_start=section.start_page,
            page_range_end=section.end_page,
        )
        self._db.add(sub_doc)
        self._db.flush()

        logger.info(
            "Processing annual report section",
            extra={
                "section": section.section_type.value,
                "pages": f"{section.start_page}-{section.end_page}",
                "sub_doc_id": str(sub_doc.id),
            },
        )

        try:
            # Parse the section's pre-extracted text
            parsed = parse_financials(section.text)

            # Create OCR record for the sub-document
            ocr_record = OCRData(
                document_id=sub_doc.id,
                raw_text=section.text,
                confidence_score=section.confidence * 100,
                page_count=section.page_count,
                extracted_fields=parsed.fields,
                extraction_metadata={
                    "extraction_method": "annual_report_analyzer",
                    "analysis_method": analysis.analysis_method,
                    "section_type": section.section_type.value,
                    "variant": section.variant.value,
                    "title_found": section.title_found,
                    "page_range": f"{section.start_page}-{section.end_page}",
                    "parent_document_id": str(parent_doc.id),
                    "section_confidence": section.confidence,
                    "extracted_field_count": parsed.extracted_count,
                    "overall_parse_confidence": parsed.overall_confidence,
                    "warnings": parsed.warnings,
                    "field_confidence": parsed.confidence,
                    "unit_context": {
                        "unit": analysis.unit_context.unit if analysis.unit_context else "unknown",
                        "multiplier": analysis.unit_context.multiplier if analysis.unit_context else 1.0,
                        "currency": analysis.unit_context.currency if analysis.unit_context else "unknown",
                    } if analysis.unit_context else None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            self._db.add(ocr_record)
            self._db.flush()

            sub_doc.status = DocumentStatus.EXTRACTED
            self._db.flush()

            return SectionExtractionResult(
                section_type=section.section_type.value,
                document_id=str(sub_doc.id),
                page_range=f"{section.start_page}-{section.end_page}",
                fields_extracted=parsed.extracted_count,
                confidence=section.confidence,
                title_found=section.title_found,
                variant=section.variant.value,
            )

        except Exception as exc:
            sub_doc.status = DocumentStatus.FAILED
            sub_doc.processing_error = str(exc)[:500]
            self._db.flush()
            logger.error(
                "Section extraction failed",
                extra={
                    "section": section.section_type.value,
                    "sub_doc_id": str(sub_doc.id),
                    "error": str(exc),
                },
            )
            return SectionExtractionResult(
                section_type=section.section_type.value,
                document_id=str(sub_doc.id),
                page_range=f"{section.start_page}-{section.end_page}",
                fields_extracted=0,
                confidence=0.0,
                title_found=section.title_found,
                variant=section.variant.value,
            )

    def _create_parent_ocr_record(
        self,
        doc: Document,
        combined_fields: Dict[str, Optional[float]],
        combined_confidences: Dict[str, float],
        analysis: AnalysisResult,
        section_results: List[SectionExtractionResult],
    ) -> None:
        """Create a combined OCR record on the parent annual report document."""
        existing = (
            self._db.query(OCRData)
            .filter(OCRData.document_id == doc.id)
            .first()
        )

        combined_text = "\n\n".join(s.text for s in analysis.sections)
        total_pages = sum(s.page_count for s in analysis.sections)
        avg_conf = (
            sum(s.confidence for s in analysis.sections) / len(analysis.sections)
            if analysis.sections else 0.0
        )

        metadata = {
            "extraction_method": "annual_report_analyzer",
            "analysis_method": analysis.analysis_method,
            "total_report_pages": analysis.total_pages,
            "sections_analyzed": len(analysis.sections),
            "toc_found": analysis.toc_found,
            "company_name": analysis.company_name,
            "financial_year": analysis.financial_year,
            "unit_context": analysis.unit_context.source_text if analysis.unit_context else None,
            "field_confidence": combined_confidences,
            "warnings": analysis.warnings,
            "sections": [
                {
                    "type": sr.section_type,
                    "pages": sr.page_range,
                    "fields_extracted": sr.fields_extracted,
                    "confidence": sr.confidence,
                    "title": sr.title_found,
                    "variant": sr.variant,
                    "document_id": sr.document_id,
                }
                for sr in section_results
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if existing:
            existing.raw_text = combined_text
            existing.confidence_score = avg_conf * 100
            existing.page_count = total_pages
            existing.extracted_fields = combined_fields
            existing.extraction_metadata = metadata
            self._db.flush()
        else:
            record = OCRData(
                document_id=doc.id,
                raw_text=combined_text,
                confidence_score=avg_conf * 100,
                page_count=total_pages,
                extracted_fields=combined_fields,
                extraction_metadata=metadata,
            )
            self._db.add(record)
            self._db.flush()

    def _mark_application_ocr_complete(self, application_id: uuid.UUID) -> None:
        """Check if all non-child documents are extracted and advance pipeline."""
        docs = self._doc_repo.list_by_application(application_id)
        # Only check top-level documents (not sub-documents created from annual reports)
        top_level = [d for d in docs if d.parent_document_id is None]
        if not top_level or any(d.status != DocumentStatus.EXTRACTED for d in top_level):
            return
        app = self._app_repo.get_by_id(application_id, load_company=False)
        if app and not app.ocr_completed:
            self._app_repo.mark_pipeline_stage(app, "ocr_completed")

    def get_analysis_status(self, document_id: uuid.UUID) -> dict:
        """Return the analysis status and section details for an annual report."""
        doc = self._doc_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError(message=f"Document '{document_id}' not found.")

        # Find sub-documents
        sub_docs = (
            self._db.query(Document)
            .filter(Document.parent_document_id == document_id)
            .order_by(Document.page_range_start)
            .all()
        )

        sections = []
        for sd in sub_docs:
            ocr = sd.ocr_data
            meta = ocr.extraction_metadata if ocr else {}
            sections.append({
                "id": str(sd.id),
                "section_type": sd.document_type.value,
                "page_range": f"{sd.page_range_start}-{sd.page_range_end}",
                "status": sd.status.value,
                "fields_extracted": meta.get("extracted_field_count", 0) if meta else 0,
                "confidence": meta.get("section_confidence", 0) if meta else 0,
                "title": meta.get("title_found", "") if meta else "",
                "variant": meta.get("variant", "unknown") if meta else "unknown",
            })

        parent_meta = {}
        if doc.ocr_data and doc.ocr_data.extraction_metadata:
            parent_meta = doc.ocr_data.extraction_metadata

        return {
            "document_id": str(doc.id),
            "status": doc.status.value,
            "original_filename": doc.original_filename,
            "total_pages": parent_meta.get("total_report_pages"),
            "analysis_method": parent_meta.get("analysis_method"),
            "company_name": parent_meta.get("company_name"),
            "financial_year": parent_meta.get("financial_year") or doc.financial_year,
            "unit_context": parent_meta.get("unit_context"),
            "toc_found": parent_meta.get("toc_found", False),
            "sections": sections,
            "warnings": parent_meta.get("warnings", []),
        }
