"""
File system utilities: secure filename generation, checksum calculation,
MIME type validation, and file storage helpers.
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, Set

from app.config import settings
from app.core.exceptions import FileTooLargeError, UnsupportedFileTypeError

# Allowed MIME types for document uploads
ALLOWED_MIME_TYPES: Set[str] = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
    "image/bmp",
    "text/plain",
    "text/csv",
}

ALLOWED_EXTENSIONS: Set[str] = {
    ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp",
    ".txt", ".csv",
}


def validate_file_type(filename: str, content_type: str) -> None:
    """Raise UnsupportedFileTypeError if the file type is not allowed."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            message=f"File extension '{ext}' is not supported. "
                    f"Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )
    if content_type not in ALLOWED_MIME_TYPES:
        raise UnsupportedFileTypeError(
            message=f"MIME type '{content_type}' is not supported."
        )


def validate_file_size(size_bytes: int) -> None:
    """Raise FileTooLargeError if the file exceeds the configured limit."""
    if size_bytes > settings.max_file_size_bytes:
        raise FileTooLargeError(
            message=(
                f"File size ({size_bytes / 1024 / 1024:.1f} MB) exceeds "
                f"the maximum allowed size ({settings.MAX_FILE_SIZE_MB} MB)."
            )
        )


def generate_stored_filename(original_filename: str) -> str:
    """
    Return a unique, filesystem-safe filename derived from a UUID.
    Preserves the original extension.
    """
    ext = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


def get_upload_subdirectory(application_id: str) -> Path:
    """
    Returns the upload directory for a specific application.
    Files are stored in uploads/<application_id>/ to avoid a flat, unmaintainable
    directory with thousands of files.
    """
    sub = settings.upload_path / application_id
    sub.mkdir(parents=True, exist_ok=True)
    return sub


async def save_upload_file(
    file_content: bytes,
    application_id: str,
    original_filename: str,
) -> tuple[str, str, int, str]:
    """
    Persist an uploaded file to disk.

    Returns:
        Tuple of (stored_filename, relative_file_path, size_bytes, sha256_checksum)
    """
    stored_filename = generate_stored_filename(original_filename)
    upload_dir = get_upload_subdirectory(application_id)
    file_path = upload_dir / stored_filename

    file_path.write_bytes(file_content)

    size_bytes = len(file_content)
    sha256 = hashlib.sha256(file_content).hexdigest()

    # Store relative path so the record is portable
    relative_path = str(file_path.relative_to(settings.upload_path.parent))
    return stored_filename, relative_path, size_bytes, sha256


def delete_upload_file(file_path_str: str) -> bool:
    """
    Delete an uploaded file. Returns True if deleted, False if not found.
    Accepts a relative path (relative to project root) or absolute path.
    """
    path = Path(file_path_str)
    if not path.is_absolute():
        from app.config import BASE_DIR
        path = BASE_DIR / path

    if path.exists():
        path.unlink()
        return True
    return False


def calculate_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def get_absolute_path(relative_path: str) -> Path:
    """Convert a stored relative path back to an absolute Path for serving."""
    from app.config import BASE_DIR
    path = Path(relative_path)
    if path.is_absolute():
        return path
    return BASE_DIR / path
