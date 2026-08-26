"""
OCR endpoints — trigger extraction, retrieve results, aggregate by application.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import get_client_ip, get_current_user, require_analyst
from app.models.user import User
from app.schemas.ocr import ApplicationOCRSummary, OCRResultResponse, OCRTriggerResponse
from app.services.ocr_service import OCRService

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /ocr/extract/{document_id}
# ---------------------------------------------------------------------------

@router.post(
    "/extract/{document_id}",
    response_model=OCRResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Run OCR extraction on an uploaded document",
    description=(
        "Extracts text from the document and parses up to 25 financial fields. "
        "Idempotent — running again overwrites the previous result. "
        "The document status transitions: uploaded → processing → extracted | failed."
    ),
)
def extract_document(
    request: Request,
    document_id: uuid.UUID,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> OCRResultResponse:
    return OCRService(db).extract_document(
        document_id=document_id,
        triggered_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )


# ---------------------------------------------------------------------------
# GET /ocr/result/{document_id}
# ---------------------------------------------------------------------------

@router.get(
    "/result/{document_id}",
    response_model=OCRResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve the OCR extraction result for a document",
)
def get_ocr_result(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OCRResultResponse:
    return OCRService(db).get_ocr_result(document_id)


# ---------------------------------------------------------------------------
# GET /ocr/application/{application_id}
# ---------------------------------------------------------------------------

@router.get(
    "/application/{application_id}",
    response_model=ApplicationOCRSummary,
    status_code=status.HTTP_200_OK,
    summary="Get merged OCR summary across all documents for an application",
    description=(
        "Merges extracted financial fields from all documents, "
        "preferring the value with the highest extraction confidence for each field. "
        "Use this endpoint to get a consolidated financial picture before ratio calculation."
    ),
)
def get_application_ocr_summary(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationOCRSummary:
    return OCRService(db).get_application_ocr_summary(application_id)


# ---------------------------------------------------------------------------
# POST /ocr/extract-all/{application_id}
# ---------------------------------------------------------------------------

@router.post(
    "/extract-all/{application_id}",
    status_code=status.HTTP_200_OK,
    summary="Run OCR on all unprocessed documents for an application",
)
def extract_all_documents(
    request: Request,
    application_id: uuid.UUID,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> dict:
    from app.repositories.document_repository import DocumentRepository
    from app.models.document import DocumentStatus

    repo = DocumentRepository(db)
    service = OCRService(db)

    docs = repo.list_by_application(application_id)
    unprocessed = [d for d in docs if d.status in (DocumentStatus.UPLOADED, DocumentStatus.FAILED)]

    results = []
    for doc in unprocessed:
        try:
            res = service.extract_document(
                document_id=doc.id,
                triggered_by=current_user,
                ip_address=get_client_ip(request),
                request_id=getattr(request.state, "request_id", "unknown"),
            )
            results.append({
                "document_id": str(doc.id),
                "filename": doc.original_filename,
                "status": "extracted",
                "fields_extracted": res.extraction_metadata.get("extracted_field_count", 0) if res.extraction_metadata else 0,
            })
        except Exception as exc:
            results.append({
                "document_id": str(doc.id),
                "filename": doc.original_filename,
                "status": "failed",
                "error": str(exc),
            })

    return {
        "application_id": str(application_id),
        "total_documents": len(docs),
        "processed": len(unprocessed),
        "results": results,
    }

