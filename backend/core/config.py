"""
Configuration settings for UTOS Trading Engine.

This module defines all configuration settings using Pydantic for
validation and type safety.
"""

from pydantic import BaseSettings, Field
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "UTOS Trading Engine"
    VERSION: str = "2.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:password@localhost:5432/utos",
        env="DATABASE_URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_MAX_CONNECTIONS: int = Field(default=100, env="REDIS_MAX_CONNECTIONS")
    
    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-here-change-in-production",
        env="SECRET_KEY"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Exchange API
    EXCHANGE_API_TIMEOUT: int = Field(default=30, env="EXCHANGE_API_TIMEOUT")
    EXCHANGE_RATE_LIMIT_REQUESTS: int = Field(default=10, env="EXCHANGE_RATE_LIMIT_REQUESTS")
    EXCHANGE_RATE_LIMIT_WINDOW: int = Field(default=60, env="EXCHANGE_RATE_LIMIT_WINDOW")
    
    # Trading
    MAX_TRADING_INSTANCES_PER_USER: int = Field(default=100, env="MAX_TRADING_INSTANCES_PER_USER")
    MIN_INVESTMENT_AMOUNT: float = Field(default=10.0, env="MIN_INVESTMENT_AMOUNT")
    MAX_INVESTMENT_AMOUNT: float = Field(default=1000000.0, env="MAX_INVESTMENT_AMOUNT")
    
    # Grid Trading
    MIN_GRID_LEVELS: int = Field(default=2, env="MIN_GRID_LEVELS")
    MAX_GRID_LEVELS: int = Field(default=100, env="MAX_GRID_LEVELS")
    GRID_SPACING_MIN_PERCENTAGE: float = Field(default=0.1, env="GRID_SPACING_MIN_PERCENTAGE")
    GRID_SPACING_MAX_PERCENTAGE: float = Field(default=10.0, env="GRID_SPACING_MAX_PERCENTAGE")
    
    # Risk Management
    DEFAULT_MAX_POSITION_SIZE: float = Field(default=10000.0, env="DEFAULT_MAX_POSITION_SIZE")
    DEFAULT_STOP_LOSS_PERCENTAGE: float = Field(default=5.0, env="DEFAULT_STOP_LOSS_PERCENTAGE")
    DEFAULT_TAKE_PROFIT_PERCENTAGE: float = Field(default=10.0, env="DEFAULT_TAKE_PROFIT_PERCENTAGE")
    MAX_DAILY_LOSS_PERCENTAGE: float = Field(default=20.0, env="MAX_DAILY_LOSS_PERCENTAGE")
    
    # Workers
    WORKER_POOL_SIZE: int = Field(default=10, env="WORKER_POOL_SIZE")
    WORKER_MAX_TASKS_PER_CHILD: int = Field(default=1000, env="WORKER_MAX_TASKS_PER_CHILD")
    WORKER_TASK_TIMEOUT: int = Field(default=300, env="WORKER_TASK_TIMEOUT")
    
    # Events
    EVENT_BUS_MAX_EVENTS_PER_SECOND: int = Field(default=10000, env="EVENT_BUS_MAX_EVENTS_PER_SECOND")
    EVENT_RETENTION_DAYS: int = Field(default=30, env="EVENT_RETENTION_DAYS")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    LOG_FILE: Optional[str] = Field(default=None, env="LOG_FILE")
    LOG_MAX_SIZE: str = Field(default="100MB", env="LOG_MAX_SIZE")
    LOG_BACKUP_COUNT: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    # Monitoring
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")
    HEALTH_CHECK_INTERVAL: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    # Storage
    STORAGE_TYPE: str = Field(default="local", env="STORAGE_TYPE")
    STORAGE_BUCKET: Optional[str] = Field(default=None, env="STORAGE_BUCKET")
    STORAGE_REGION: Optional[str] = Field(default=None, env="STORAGE_REGION")
    STORAGE_ACCESS_KEY: Optional[str] = Field(default=None, env="STORAGE_ACCESS_KEY")
    STORAGE_SECRET_KEY: Optional[str] = Field(default=None, env="STORAGE_SECRET_KEY")
    
    # Notifications
    NOTIFICATION_ENABLED: bool = Field(default=True, env="NOTIFICATION_ENABLED")
    EMAIL_SMTP_HOST: Optional[str] = Field(default=None, env="EMAIL_SMTP_HOST")
    EMAIL_SMTP_PORT: int = Field(default=587, env="EMAIL_SMTP_PORT")
    EMAIL_SMTP_USERNAME: Optional[str] = Field(default=None, env="EMAIL_SMTP_USERNAME")
    EMAIL_SMTP_PASSWORD: Optional[str] = Field(default=None, env="EMAIL_SMTP_PASSWORD")
    
    # Feature Flags
    FEATURE_PORTFOLIO_LOCK: bool = Field(default=True, env="FEATURE_PORTFOLIO_LOCK")
    FEATURE_INFINITY_GRID: bool = Field(default=True, env="FEATURE_INFINITY_GRID")
    FEATURE_ADAPTIVE_GRID: bool = Field(default=True, env="FEATURE_ADAPTIVE_GRID")
    FEATURE_DCA_STRATEGY: bool = Field(default=True, env="FEATURE_DCA_STRATEGY")
    
    # Testing
    TESTING: bool = Field(default=False, env="TESTING")
    TEST_DATABASE_URL: str = Field(
        default="postgresql://postgres:password@localhost:5432/utos_test",
        env="TEST_DATABASE_URL"
    )
    TEST_REDIS_URL: str = Field(
        default="redis://localhost:6379/1",
        env="TEST_REDIS_URL"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create settings instance
settings = Settings()


# Environment-specific settings
def get_database_url() -> str:
    """Get database URL based on environment."""
    if settings.TESTING:
        return settings.TEST_DATABASE_URL
    return settings.DATABASE_URL


def get_redis_url() -> str:
    """Get Redis URL based on environment."""
    if settings.TESTING:
        return settings.TEST_REDIS_URL
    return settings.REDIS_URL


# Validation functions
def validate_trading_parameters(
    investment_amount: float,
    grid_levels: int,
    grid_spacing_percentage: float,
) -> None:
    """Validate trading parameters."""
    if investment_amount < settings.MIN_INVESTMENT_AMOUNT:
        raise ValueError(f"Investment amount must be at least {settings.MIN_INVESTMENT_AMOUNT}")
    
    if investment_amount > settings.MAX_INVESTMENT_AMOUNT:
        raise ValueError(f"Investment amount cannot exceed {settings.MAX_INVESTMENT_AMOUNT}")
    
    if grid_levels < settings.MIN_GRID_LEVELS:
        raise ValueError(f"Grid levels must be at least {settings.MIN_GRID_LEVELS}")
    
    if grid_levels > settings.MAX_GRID_LEVELS:
        raise ValueError(f"Grid levels cannot exceed {settings.MAX_GRID_LEVELS}")
    
    if grid_spacing_percentage < settings.GRID_SPACING_MIN_PERCENTAGE:
        raise ValueError(f"Grid spacing must be at least {settings.GRID_SPACING_MIN_PERCENTAGE}%")
    
    if grid_spacing_percentage > settings.GRID_SPACING_MAX_PERCENTAGE:
        raise ValueError(f"Grid spacing cannot exceed {settings.GRID_SPACING_MAX_PERCENTAGE}%")


def is_feature_enabled(feature: str) -> bool:
    """Check if a feature is enabled."""
    feature_flag = f"FEATURE_{feature.upper()}"
    return getattr(settings, feature_flag, False)