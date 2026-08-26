"""
Custom ASGI/Starlette middleware:
  - RequestIDMiddleware   — attaches X-Request-ID to every request/response
  - AuditLogMiddleware    — logs method, path, status, duration for every request
"""

from __future__ import annotations

import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique UUID to every request.
    The ID is available via request.state.request_id and echoed in the
    X-Request-ID response header so clients can correlate log entries.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Logs one structured line per request with timing information.
    Skipped for health-check endpoints to avoid log noise.
    """

    _SKIP_PATHS = frozenset({"/health", "/metrics", "/favicon.ico"})

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "HTTP request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "request_id": getattr(request.state, "request_id", "-"),
                "client_ip": request.client.host if request.client else "-",
            },
        )
        return response
