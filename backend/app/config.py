"""
Central application configuration loaded from environment variables via .env.
All paths are resolved relative to the project root so the codebase is
portable across Windows, Linux, and macOS without code changes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root is three levels up from this file:
#   backend/app/config.py  →  backend/app/  →  backend/  →  project_root/
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    APP_NAME: str = "Corporate Lending Automation"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # -------------------------------------------------------------------------
    # Security
    # -------------------------------------------------------------------------
    SECRET_KEY: str = "insecure-default-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/corporate_lending"

    # -------------------------------------------------------------------------
    # Redis & Celery
    # -------------------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # -------------------------------------------------------------------------
    # File Storage (relative to project root)
    # -------------------------------------------------------------------------
    UPLOAD_DIR: str = "uploads"
    REPORT_DIR: str = "reports"
    RESULTS_DIR: str = "results"
    LOG_DIR: str = "logs"
    MODELS_DIR: str = "models"
    DATASET_PATH: str = "datasets/company_bankruptcy_prediction.csv"

    # -------------------------------------------------------------------------
    # OCR
    # -------------------------------------------------------------------------
    TESSERACT_CMD: str = "tesseract"
    TESSERACT_LANG: str = "eng"
    OCR_DPI: int = 300
    MAX_FILE_SIZE_MB: int = 50

    # -------------------------------------------------------------------------
    # Machine Learning
    # -------------------------------------------------------------------------
    ML_RANDOM_STATE: int = 42
    TEST_SIZE: float = 0.2
    CV_FOLDS: int = 5

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    RATE_LIMIT_PER_MINUTE: int = 60

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Computed properties
    # -------------------------------------------------------------------------

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def upload_path(self) -> Path:
        p = BASE_DIR / self.UPLOAD_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def report_path(self) -> Path:
        p = BASE_DIR / self.REPORT_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def results_path(self) -> Path:
        p = BASE_DIR / self.RESULTS_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def models_path(self) -> Path:
        p = BASE_DIR / self.MODELS_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def log_path(self) -> Path:
        p = BASE_DIR / self.LOG_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def dataset_path(self) -> Path:
        return BASE_DIR / self.DATASET_PATH

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"


# Single shared instance — import this everywhere.
settings = Settings()
