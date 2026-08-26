"""
FastAPI application entry-point.

Startup order
─────────────
1. Logging is configured first so every subsequent log message is captured.
2. Settings are validated (config.py raises on startup if required env vars
   are missing).
3. Database connectivity is verified.
4. CORS, rate-limiting, and custom middleware are attached.
5. API routers are registered under /api/v1.
6. Custom exception handlers replace FastAPI defaults.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings, BASE_DIR
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import AuditLogMiddleware, RequestIDMiddleware
from app.database.connection import check_db_connection

# Initialise logging before any other import that might log
configure_logging()
logger = get_logger(__name__)


# =============================================================================
# Rate limiter (shared across all routes via dependency injection)
# =============================================================================

limiter = Limiter(key_func=get_remote_address)


# =============================================================================
# Application lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Runs startup checks before the app begins serving requests."""
    logger.info(
        "Starting %s v%s [%s]",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )

    # Verify database
    if check_db_connection():
        logger.info("Database connection: OK")
    else:
        logger.error(
            "Database connection FAILED. Check DATABASE_URL in .env. "
            "The application will start but database operations will fail."
        )

    # Ensure required directories exist
    settings.upload_path      # creates uploads/
    settings.report_path      # creates reports/
    settings.results_path     # creates results/
    settings.models_path      # creates models/
    settings.log_path         # creates logs/
    logger.info("Storage directories verified.")

    yield  # ←── server is live and serving requests

    logger.info("Shutting down %s.", settings.APP_NAME)


# =============================================================================
# FastAPI instance
# =============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Intelligent Corporate Lending Automation — "
        "Rule-Based Decision Systems and Machine Learning for Credit Risk Assessment."
    ),
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
    lifespan=lifespan,
)

# =============================================================================
# Rate limiter
# =============================================================================

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# =============================================================================
# Middleware (order matters — outermost runs first on request, last on response)
# =============================================================================

# GZip compression for large responses
app.add_middleware(GZipMiddleware, minimum_size=1024)

# CORS — only allow configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Total-Count"],
)

# Request ID tagging (innermost — runs first on request)
app.add_middleware(RequestIDMiddleware)

# Access logging
app.add_middleware(AuditLogMiddleware)

# =============================================================================
# Exception handlers
# =============================================================================

register_exception_handlers(app)

# =============================================================================
# Static file serving (uploaded documents, generated reports)
# =============================================================================

app.mount(
    "/uploads",
    StaticFiles(directory=str(settings.upload_path)),
    name="uploads",
)
app.mount(
    "/reports",
    StaticFiles(directory=str(settings.report_path)),
    name="reports",
)

# =============================================================================
# API routers  (imported lazily to avoid circular import on startup)
# =============================================================================

from app.api.v1.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")

# =============================================================================
# Health check (outside /api/v1 so it's not rate-limited)
# =============================================================================

@app.get("/health", tags=["System"], include_in_schema=False)
def health() -> dict:
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "db": check_db_connection(),
        "timestamp": time.time(),
    }


@app.get("/", tags=["System"], include_in_schema=False)
def root() -> dict:
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
