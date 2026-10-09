"""Application configuration powered by environment variables."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Centralized settings for the IPL 2026 FastAPI backend."""

    APP_NAME: str = "IPL 2026 Match Prediction API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = False

    # Database: defaults to local SQLite; automatically upgrades postgres:// for Neon/Supabase/Render
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{(ROOT_DIR / 'backend' / 'ipl_predictions.db').as_posix()}"
    )

    # Paths to ML artifact & dataset
    MODEL_ARTIFACT_PATH: str = os.getenv(
        "MODEL_ARTIFACT_PATH",
        str(ROOT_DIR / "ml" / "artifacts" / "ipl_model_v1.joblib"),
    )
    METRICS_PATH: str = os.getenv(
        "METRICS_PATH",
        str(ROOT_DIR / "ml" / "artifacts" / "metrics.json"),
    )
    DATASET_PATH: str = os.getenv(
        "DATASET_PATH",
        str(ROOT_DIR / "IPL.csv"),
    )

    # Security, CORS, Rate Limiting & Caching
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,https://ipl-2026-predictor.vercel.app,*",
    )
    RATE_LIMIT_PREDICT: str = os.getenv("RATE_LIMIT_PREDICT", "60/minute")
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        """Normalize postgres:// URLs from Render/Railway/Neon to postgresql://."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql://", 1)
        return url

    @property
    def cors_origin_list(self) -> List[str]:
        origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        return origins if origins else ["*"]


settings = Settings()
