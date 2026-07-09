"""
Base database configuration for UTOS Trading Engine.

This module defines the base database configuration and session management.
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator

from core.config import get_database_url
from core.logging import get_logger

logger = get_logger(__name__)

# Create base class for all models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()

# Database engine
engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,  # Set to True for SQL logging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def drop_tables():
    """Drop all database tables."""
    Base.metadata.drop_all(bind=engine)
    logger.info("Database tables dropped successfully")


def get_session() -> Session:
    """Get a new database session."""
    return SessionLocal()


# Test database configuration
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def get_test_db() -> Generator[Session, None, None]:
    """Get test database session."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
