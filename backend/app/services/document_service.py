"""
DocumentService — document upload, retrieval, and lifecycle management.

Upload pipeline:
  1. Read bytes from FastAPI UploadFile
  2. Validate file size (< MAX_FILE_SIZE_MB)
  3. Validate MIME type (PDF, PNG, JPEG, TIFF only)
  4. Compute SHA-256 checksum — reject exact duplicates per application
  5. Persist file to uploads/<application_id>/<uuid>.<ext>
  6. Create Document record in DB
  7. Write audit log entry
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    UnsupportedFileTypeError,
    FileTooLargeError,
)
from app.core.logging import get_logger
from app.models.audit_log import AuditAction
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.user import User, UserRole
from app.repositories.application_repository import ApplicationRepository
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentListResponse, DocumentResponse, DocumentUploadResponse
from app.utils.file_utils import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    generate_stored_filename,
    get_upload_subdirectory,
    delete_upload_file,
)

logger = get_logger(__name__)

# Documents allowed per application (prevents spamming the same type)
MAX_DOCS_PER_APPLICATION = 20


class DocumentService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._doc_repo = DocumentRepository(db)
        self._app_repo = ApplicationRepository(db)
        self._audit = AuditLogRepository(db)

    # -------------------------------------------------------------------------
    # Upload
    # -------------------------------------------------------------------------

    async def upload_document(
        self,
        application_id: uuid.UUID,
        document_type: DocumentType,
        file: UploadFile,
        financial_year: Optional[str],
        uploaded_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> DocumentUploadResponse:
        # 1. Verify application exists
        app = self._app_repo.get_by_id(application_id)
        if not app:
            raise NotFoundError(message=f"Application '{application_id}' not found.")

        # 2. Application must not be in a terminal state
        terminal = {"approved", "rejected", "withdrawn"}
        if app.status.value in terminal:
            raise BadRequestError(
                message=(
                    f"Cannot upload documents to application "
                    f"'{app.application_number}' — it is in status '{app.status.value}'."
                )
            )

        # 3. Document count cap
        doc_count = self._doc_repo.count_by_application(application_id)
        if doc_count >= MAX_DOCS_PER_APPLICATION:
            raise BadRequestError(
                message=(
                    f"Application already has {doc_count} documents. "
                    f"Maximum allowed is {MAX_DOCS_PER_APPLICATION}."
                )
            )

        # 4. Read file bytes
        content = await file.read()
        file_size = len(content)

        # 5. File size validation
        if file_size > settings.max_file_size_bytes:
            raise FileTooLargeError(
                message=(
                    f"File '{file.filename}' is {file_size / 1024 / 1024:.1f} MB. "
                    f"Maximum allowed is {settings.MAX_FILE_SIZE_MB} MB."
                )
            )
        if file_size == 0:
            raise BadRequestError(message="Uploaded file is empty.")

        # 6. MIME type validation
        original_filename = file.filename or "unknown"
        ext = Path(original_filename).suffix.lower()
        content_type = file.content_type or ""

        if ext not in ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(
                message=(
                    f"File extension '{ext}' is not supported. "
                    f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                )
            )

        # Normalise browser MIME quirks
        normalised_mime = _normalise_mime(content_type, ext)
        if normalised_mime not in ALLOWED_MIME_TYPES:
            raise UnsupportedFileTypeError(
                message=f"MIME type '{content_type}' is not supported."
            )

        # 7. Magic-byte validation (PDF only — prevent disguised executables)
        if ext == ".pdf" and not content.startswith(b"%PDF"):
            raise UnsupportedFileTypeError(
                message="File does not appear to be a valid PDF (bad magic bytes)."
            )

        # 8. Checksum + duplicate detection
        sha256 = hashlib.sha256(content).hexdigest()
        if self._doc_repo.exists_checksum(application_id, sha256):
            raise ConflictError(
                message=(
                    "A document with identical content has already been uploaded "
                    "for this application. Duplicate files are not allowed."
                )
            )

        # 9. Persist to disk
        stored_filename = generate_stored_filename(original_filename)
        upload_dir = get_upload_subdirectory(str(application_id))
        file_path_abs = upload_dir / stored_filename
        file_path_abs.write_bytes(content)

        # Store relative path (portable across OS)
        from app.config import BASE_DIR
        relative_path = str(file_path_abs.relative_to(BASE_DIR))

        # 10. Create DB record
        doc = self._doc_repo.create(
            application_id=application_id,
            document_type=document_type,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=relative_path,
            file_size_bytes=file_size,
            mime_type=normalised_mime,
            checksum_sha256=sha256,
            financial_year=financial_year,
        )

        # 11. Audit log
        self._audit.log(
            action=AuditAction.DOCUMENT_UPLOADED,
            description=(
                f"Document '{original_filename}' ({document_type.value}) "
                f"uploaded to application '{app.application_number}'."
            ),
            user_id=uploaded_by.id,
            entity_type="document",
            entity_id=str(doc.id),
            new_values={
                "document_type": document_type.value,
                "filename": original_filename,
                "size_bytes": file_size,
                "sha256": sha256,
            },
            ip_address=ip_address,
            request_id=request_id,
        )

        logger.info(
            "Document uploaded",
            extra={
                "doc_id": str(doc.id),
                "app_id": str(application_id),
                "type": document_type.value,
                "size": file_size,
            },
        )

        from app.schemas.document import _format_bytes
        return DocumentUploadResponse(
            document_id=doc.id,
            application_id=application_id,
            document_type=document_type,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_size_bytes=file_size,
            file_size_display=_format_bytes(file_size),
            checksum_sha256=sha256,
            status=DocumentStatus.UPLOADED,
            message="Document uploaded successfully. Ready for OCR extraction.",
        )

    # -------------------------------------------------------------------------
    # Read
    # -------------------------------------------------------------------------

    def get_by_id(self, doc_id: uuid.UUID) -> Document:
        doc = self._doc_repo.get_by_id(doc_id)
        if not doc:
            raise NotFoundError(message=f"Document '{doc_id}' not found.")
        return doc

    def list_by_application(
        self,
        application_id: uuid.UUID,
        document_type: Optional[DocumentType] = None,
    ) -> DocumentListResponse:
        docs = self._doc_repo.list_by_application(application_id, document_type)
        return DocumentListResponse(
            items=[DocumentResponse.from_orm_with_size(d) for d in docs],
            total=len(docs),
        )

    def get_absolute_file_path(self, doc_id: uuid.UUID) -> Path:
        """Resolve a document's stored path to an absolute Path for streaming."""
        doc = self.get_by_id(doc_id)
        from app.config import BASE_DIR
        p = Path(doc.file_path)
        if not p.is_absolute():
            p = BASE_DIR / p
        if not p.exists():
            raise NotFoundError(
                message=f"Physical file for document '{doc_id}' not found on disk."
            )
        return p

    # -------------------------------------------------------------------------
    # Update metadata
    # -------------------------------------------------------------------------

    def update_document(
        self,
        doc_id: uuid.UUID,
        financial_year: Optional[str] = None,
        document_type: Optional[DocumentType] = None,
        updated_by: User = None,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> Document:
        doc = self.get_by_id(doc_id)
        updates = {}
        if financial_year is not None:
            updates["financial_year"] = financial_year
        if document_type is not None:
            updates["document_type"] = document_type
        if updates:
            self._doc_repo.update(doc, **updates)
        return doc

    # -------------------------------------------------------------------------
    # Delete
    # -------------------------------------------------------------------------

    def delete_document(
        self,
        doc_id: uuid.UUID,
        deleted_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> None:
        doc = self.get_by_id(doc_id)

        # Admins can force-delete at any status; other roles are blocked once
        # the document has been OCR-processed to avoid invalidating analysis.
        if doc.status == DocumentStatus.EXTRACTED and deleted_by.role != UserRole.ADMIN:
            raise BadRequestError(
                message=(
                    f"Document '{doc.original_filename}' has already been OCR-extracted. "
                    f"Deleting it would invalidate the analysis. "
                    f"If you need to replace it, upload a new version instead."
                )
            )

        # When an admin removes an annual report, cascade-delete its
        # auto-generated sub-documents (BS / P&L / CF section extracts) first
        # via raw SQL so DB-level CASCADE handles the OCR data.
        from sqlalchemy import text as _text
        self._db.execute(
            _text("DELETE FROM documents WHERE parent_document_id = :pid"),
            {"pid": str(doc.id)},
        )
        self._db.flush()

        file_path = doc.file_path
        app_id = str(doc.application_id)

        self._audit.log(
            action=AuditAction.DOCUMENT_DELETED,
            description=f"Document '{doc.original_filename}' deleted from application.",
            user_id=deleted_by.id,
            entity_type="document",
            entity_id=str(doc.id),
            old_values={
                "filename": doc.original_filename,
                "type": doc.document_type.value,
                "status": doc.status.value,
            },
            ip_address=ip_address,
            request_id=request_id,
        )

        # Raw SQL DELETE so DB-level CASCADE handles ocr_data and any other
        # child rows; the ORM would otherwise try to nullify their FKs first.
        self._db.expunge(doc)
        self._db.execute(
            _text("DELETE FROM documents WHERE id = :did"),
            {"did": str(doc_id)},
        )
        self._db.commit()

        # Remove physical file after DB record is gone
        deleted = delete_upload_file(file_path)
        if not deleted:
            logger.warning(
                "Physical file not found during document deletion",
                extra={"file_path": file_path, "doc_id": str(doc_id)},
            )

        logger.info("Document deleted", extra={"doc_id": str(doc_id), "app_id": app_id})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_mime(content_type: str, ext: str) -> str:
    """
    Browsers sometimes send incorrect MIME types. Normalise based on extension
    when the declared content_type is a generic binary type.
    """
    generic = {"application/octet-stream", "binary/octet-stream", ""}
    if content_type.strip().lower() in generic:
        _ext_map = {
            ".pdf":  "application/pdf",
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".tif":  "image/tiff",
            ".tiff": "image/tiff",
            ".bmp":  "image/bmp",
            ".txt":  "text/plain",
            ".csv":  "text/csv",
        }
        return _ext_map.get(ext.lower(), content_type)
    return content_type.strip().lower()
