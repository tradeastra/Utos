"""
Application configuration for UTOS Trading Engine.

Loads all settings from environment variables / .env file using
pydantic-settings v2. Never has hardcoded production secrets.
"""

from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings — all values loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "UTOS Trading Engine"
    VERSION: str = "1.0.0"
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    # ── Security ─────────────────────────────────────────────────────────────
    # No production default — must be set via environment.
    SECRET_KEY: str = Field(
        default="change-me-to-a-long-random-string-at-least-32-chars"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000"])

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v  # type: ignore[return-value]

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://utos:utos_dev_password@localhost:5432/utos"
    )
    DATABASE_POOL_SIZE: int = Field(default=10)
    DATABASE_MAX_OVERFLOW: int = Field(default=20)

    # ── Test Database ─────────────────────────────────────────────────────────
    TEST_DATABASE_URL: str = Field(
        default="postgresql+asyncpg://utos:utos_dev_password@localhost:5432/utos_test"
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    TEST_REDIS_URL: str = Field(default="redis://localhost:6379/1")

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="console")  # "console" | "json"

    # ── Testing ───────────────────────────────────────────────────────────────
    TESTING: bool = Field(default=False)


def get_settings() -> Settings:
    """Return the application settings singleton."""
    return settings


def get_database_url() -> str:
    """Return active database URL (test-aware)."""
    return settings.TEST_DATABASE_URL if settings.TESTING else settings.DATABASE_URL


def get_redis_url() -> str:
    """Return active Redis URL (test-aware)."""
    return settings.TEST_REDIS_URL if settings.TESTING else settings.REDIS_URL


settings = Settings()