"""
Domain-specific exceptions and FastAPI exception handlers.
All HTTP errors are raised as these typed exceptions so the handler
can format a consistent JSON error envelope across the entire API.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


# =============================================================================
# Base
# =============================================================================

class AppException(Exception):
    """Base class for all application-level exceptions."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: Optional[str] = None,
        detail: Optional[Any] = None,
        error_code: Optional[str] = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.detail = detail
        if error_code:
            self.error_code = error_code
        super().__init__(self.message)


# =============================================================================
# 4xx Client Errors
# =============================================================================

class BadRequestError(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "BAD_REQUEST"
    message = "Invalid request."


class AuthenticationError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTHENTICATION_FAILED"
    message = "Authentication credentials are invalid or missing."


class PermissionDeniedError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action."


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"
    message = "The requested resource was not found."


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"
    message = "A conflict occurred with existing data."


class UnprocessableError(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "UNPROCESSABLE"
    message = "The provided data could not be processed."


class FileTooLargeError(AppException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    error_code = "FILE_TOO_LARGE"
    message = "The uploaded file exceeds the maximum allowed size."


class UnsupportedFileTypeError(AppException):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    error_code = "UNSUPPORTED_FILE_TYPE"
    message = "The uploaded file type is not supported."


# =============================================================================
# 5xx Server Errors
# =============================================================================

class OCRError(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "OCR_FAILED"
    message = "OCR extraction failed."


class MLPipelineError(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "ML_PIPELINE_FAILED"
    message = "Machine learning prediction pipeline failed."


class ReportGenerationError(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "REPORT_GENERATION_FAILED"
    message = "PDF report generation failed."


class DatasetValidationError(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "DATASET_INVALID"
    message = "Dataset validation failed."


class ModelNotTrainedError(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "MODEL_NOT_TRAINED"
    message = "ML models have not been trained yet. Run the training pipeline first."


# =============================================================================
# Error response builder
# =============================================================================

def _error_envelope(
    error_code: str,
    message: str,
    status_code: int,
    detail: Any = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "status": status_code,
        },
    }
    if detail is not None:
        payload["error"]["detail"] = detail
    return payload


# =============================================================================
# Exception handlers — register on the FastAPI app
# =============================================================================

def _sanitize_errors(errors: list) -> list:
    """Convert any bytes values in validation errors to strings for JSON serialization."""
    sanitized = []
    for err in errors:
        clean = {}
        for k, v in err.items():
            if isinstance(v, bytes):
                clean[k] = v.decode("utf-8", errors="replace")
            elif isinstance(v, dict):
                clean[k] = {
                    dk: dv.decode("utf-8", errors="replace") if isinstance(dv, bytes) else dv
                    for dk, dv in v.items()
                }
            else:
                clean[k] = v
        sanitized.append(clean)
    return sanitized


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_envelope(exc.error_code, exc.message, exc.status_code, exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = _sanitize_errors(exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_envelope(
                "VALIDATION_ERROR",
                "Request validation failed.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                errors,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        import traceback
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.error("Unhandled exception", exc_info=exc, extra={"path": str(request.url)})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_envelope(
                "INTERNAL_ERROR",
                "An internal server error occurred.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )
