from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "YouTube Summary Studio"
    app_env: str = "development"
    database_url: str = "sqlite:///./app.db"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"
    embedding_provider: str = "google"
    embedding_model: str = "text-embedding-004"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    app_secret: str = "development-secret"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def is_gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
