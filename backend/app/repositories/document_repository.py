"""
DocumentRepository — all database operations for the documents table.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus, DocumentType


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # -------------------------------------------------------------------------
    # Read
    # -------------------------------------------------------------------------

    def get_by_id(self, doc_id: uuid.UUID) -> Optional[Document]:
        return self._db.query(Document).filter(Document.id == doc_id).first()

    def get_by_stored_filename(self, stored_filename: str) -> Optional[Document]:
        return (
            self._db.query(Document)
            .filter(Document.stored_filename == stored_filename)
            .first()
        )

    def list_by_application(
        self,
        application_id: uuid.UUID,
        document_type: Optional[DocumentType] = None,
    ) -> List[Document]:
        q = self._db.query(Document).filter(
            Document.application_id == application_id
        )
        if document_type:
            q = q.filter(Document.document_type == document_type)
        return q.order_by(Document.created_at.asc()).all()

    def count_by_application(self, application_id: uuid.UUID) -> int:
        return (
            self._db.query(Document)
            .filter(Document.application_id == application_id)
            .count()
        )

    def get_by_application_and_type(
        self, application_id: uuid.UUID, document_type: DocumentType
    ) -> List[Document]:
        return (
            self._db.query(Document)
            .filter(
                Document.application_id == application_id,
                Document.document_type == document_type,
            )
            .order_by(Document.created_at.desc())
            .all()
        )

    def exists_checksum(self, application_id: uuid.UUID, checksum: str) -> bool:
        """Detect duplicate uploads for the same application."""
        return (
            self._db.query(Document.id)
            .filter(
                Document.application_id == application_id,
                Document.checksum_sha256 == checksum,
            )
            .first()
        ) is not None

    # -------------------------------------------------------------------------
    # Write
    # -------------------------------------------------------------------------

    def create(
        self,
        application_id: uuid.UUID,
        document_type: DocumentType,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        file_size_bytes: int,
        mime_type: str,
        checksum_sha256: str,
        financial_year: Optional[str] = None,
    ) -> Document:
        doc = Document(
            application_id=application_id,
            document_type=document_type,
            status=DocumentStatus.UPLOADED,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            checksum_sha256=checksum_sha256,
            financial_year=financial_year,
        )
        self._db.add(doc)
        self._db.flush()
        return doc

    def update_status(
        self,
        doc: Document,
        status: DocumentStatus,
        error: Optional[str] = None,
    ) -> Document:
        doc.status = status
        if error is not None:
            doc.processing_error = error
        self._db.flush()
        return doc

    def update(self, doc: Document, **fields) -> Document:
        for key, value in fields.items():
            if hasattr(doc, key) and value is not None:
                setattr(doc, key, value)
        self._db.flush()
        return doc

    def delete(self, doc: Document) -> None:
        self._db.delete(doc)
        self._db.flush()
