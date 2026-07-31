"""
Application configuration for UTOS Trading Engine.

Loads all settings from environment variables / .env file using
pydantic-settings v2. Never has hardcoded production secrets.
"""

from typing import Annotated, List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import NoDecode


class Settings(BaseSettings):
    """Application settings — all values loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    APP_NAME: str = "UTOS Trading Engine"
    VERSION: str = "1.0.0"
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    # ── Security ───────────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(
        default="change-me-to-a-long-random-string-at-least-32-chars"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ───────────────────────────────────────────────────────────────────
    # NoDecode tells pydantic-settings' EnvSettingsSource to NOT JSON-parse the
    # raw env string; the field_validator below then splits on commas. Without
    # this, a comma-separated value like "https://a,http://b" raises
    # SettingsError because the source tries json.loads first.
    CORS_ORIGINS: Annotated[List[str], NoDecode] = Field(
        default=["http://localhost:3000"]
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v  # type: ignore[return-value]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Reject insecure defaults when APP_ENV is production."""
        if self.APP_ENV == "production":
            if self.SECRET_KEY == "change-me-to-a-long-random-string-at-least-32-chars":
                raise ValueError("SECRET_KEY must be changed from default in production")
            if len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in production")
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")
        return self

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://utos:utos_dev_password@localhost:5432/utos"
    )
    DATABASE_POOL_SIZE: int = Field(default=10)
    DATABASE_MAX_OVERFLOW: int = Field(default=20)

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: object) -> object:
        """Auto-convert postgres:// and postgresql:// to postgresql+asyncpg:// for Railway/Render compatibility."""
        if isinstance(v, str):
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    # ── Test Database ─────────────────────────────────────────────────────────
    TEST_DATABASE_URL: str = Field(
        default="postgresql+asyncpg://utos:utos_dev_password@localhost:5432/utos_test"
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    TEST_REDIS_URL: str = Field(default="redis://localhost:6379/1")

    # ── Telegram ──────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str | None = Field(default=None)

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="console")  # "console" | "json"
    LOG_FILE: str | None = Field(default=None)
    LOG_MAX_SIZE: str = Field(default="10MB")

    # ── Testing ───────────────────────────────────────────────────────────────
    TESTING: bool = Field(default=False)

    # ── OpenTelemetry ──────────────────────────────────────────────────────────
    OTEL_ENABLED: bool = Field(default=False)


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