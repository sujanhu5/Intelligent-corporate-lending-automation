"""
Master API router — aggregates all v1 sub-routers.
Each sub-module is imported here; the actual route handlers live in
separate files to maintain single-responsibility.
"""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    users,
    companies,
    applications,
    documents,
    ocr,
    ratios,
    rules,
    predictions,
    reports,
    analytics,
    pipeline,
)

api_router = APIRouter()

api_router.include_router(auth.router,         prefix="/auth",         tags=["Authentication"])
api_router.include_router(users.router,        prefix="/users",        tags=["Users"])
api_router.include_router(companies.router,    prefix="/companies",    tags=["Companies"])
api_router.include_router(applications.router, prefix="/applications", tags=["Applications"])
api_router.include_router(documents.router,    prefix="/documents",    tags=["Documents"])
api_router.include_router(ocr.router,          prefix="/ocr",          tags=["OCR"])
api_router.include_router(ratios.router,       prefix="/ratios",       tags=["Financial Ratios"])
api_router.include_router(rules.router,        prefix="/rules",        tags=["Rule Engine"])
api_router.include_router(predictions.router,  prefix="/predictions",  tags=["ML Predictions"])
api_router.include_router(reports.router,      prefix="/reports",      tags=["Reports"])
api_router.include_router(analytics.router,    prefix="/analytics",    tags=["Analytics"])
api_router.include_router(pipeline.router,     prefix="/pipeline",     tags=["Pipeline"])
