"""
Document upload and management endpoints.

Upload flow:
  POST /documents/upload/{application_id}
      → multipart/form-data: file, document_type, financial_year?
      → validates MIME type, file size, magic bytes, duplicate SHA-256
      → stores at uploads/<app_id>/<uuid>.<ext>
      → creates Document record and audit log
      → returns DocumentUploadResponse
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import get_client_ip, get_current_user, require_analyst
from app.models.document import DocumentType
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /documents/upload/{application_id}
# ---------------------------------------------------------------------------

@router.post(
    "/upload/{application_id}",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a financial document for a loan application",
    description=(
        "Accepted formats: PDF, PNG, JPEG, TIFF. "
        "Maximum file size is controlled by MAX_FILE_SIZE_MB in .env. "
        "Duplicate files (same SHA-256) within the same application are rejected."
    ),
)
async def upload_document(
    request: Request,
    application_id: uuid.UUID,
    file: UploadFile = File(..., description="Financial document file"),
    document_type: DocumentType = Form(..., description="Type of financial document"),
    financial_year: Optional[str] = Form(
        default=None,
        description="Financial year the document covers, e.g. 'FY2023-24'",
    ),
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    service = DocumentService(db)
    return await service.upload_document(
        application_id=application_id,
        document_type=document_type,
        file=file,
        financial_year=financial_year,
        uploaded_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )


# ---------------------------------------------------------------------------
# GET /documents/application/{application_id}
# ---------------------------------------------------------------------------

@router.get(
    "/application/{application_id}",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all documents uploaded for a loan application",
)
def list_application_documents(
    application_id: uuid.UUID,
    document_type: Optional[DocumentType] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    return DocumentService(db).list_by_application(
        application_id=application_id,
        document_type=document_type,
    )


# ---------------------------------------------------------------------------
# GET /documents/{doc_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{doc_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get document metadata",
)
def get_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    doc = DocumentService(db).get_by_id(doc_id)
    return DocumentResponse.from_orm_with_size(doc)


# ---------------------------------------------------------------------------
# GET /documents/{doc_id}/download
# ---------------------------------------------------------------------------

@router.get(
    "/{doc_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download the original uploaded file",
    response_class=FileResponse,
)
def download_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    service = DocumentService(db)
    doc = service.get_by_id(doc_id)
    abs_path = service.get_absolute_file_path(doc_id)
    return FileResponse(
        path=str(abs_path),
        filename=doc.original_filename,
        media_type=doc.mime_type,
    )


# ---------------------------------------------------------------------------
# PATCH /documents/{doc_id}
# ---------------------------------------------------------------------------

@router.patch(
    "/{doc_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update document metadata (financial year, document type)",
)
def update_document(
    request: Request,
    doc_id: uuid.UUID,
    body: DocumentUpdate,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    service = DocumentService(db)
    doc = service.update_document(
        doc_id=doc_id,
        financial_year=body.financial_year,
        document_type=body.document_type,
        updated_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return DocumentResponse.from_orm_with_size(doc)


# ---------------------------------------------------------------------------
# DELETE /documents/{doc_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/{doc_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete an uploaded document (not allowed after OCR extraction)",
)
def delete_document(
    request: Request,
    doc_id: uuid.UUID,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> MessageResponse:
    DocumentService(db).delete_document(
        doc_id=doc_id,
        deleted_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return MessageResponse(message=f"Document '{doc_id}' has been deleted.")


# ---------------------------------------------------------------------------
# GET /documents/{doc_id}/verify-checksum
# ---------------------------------------------------------------------------

@router.get(
    "/{doc_id}/verify-checksum",
    status_code=status.HTTP_200_OK,
    summary="Verify that the stored file matches its recorded SHA-256 checksum",
)
def verify_checksum(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    import hashlib
    service = DocumentService(db)
    doc = service.get_by_id(doc_id)
    abs_path = service.get_absolute_file_path(doc_id)

    actual_sha256 = hashlib.sha256(abs_path.read_bytes()).hexdigest()
    matches = actual_sha256 == doc.checksum_sha256

    return {
        "document_id": str(doc_id),
        "filename": doc.original_filename,
        "recorded_sha256": doc.checksum_sha256,
        "actual_sha256": actual_sha256,
        "integrity_ok": matches,
        "message": "File integrity verified." if matches else "WARNING: File checksum mismatch — file may have been tampered with.",
    }

