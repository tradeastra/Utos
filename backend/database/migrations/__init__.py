"""
Database migrations package for UTOS Trading Engine.

This package contains all database migration scripts.
"""

import os

from alembic import command
from alembic.config import Config
from core.config import get_database_url
from core.logging import get_logger

logger = get_logger(__name__)


def run_migrations():
    """Run all pending database migrations."""
    try:
        # __file__ = backend/database/migrations/__init__.py
        # Need backend/ root, then join with alembic/
        migrations_dir = os.path.dirname(os.path.abspath(__file__))  # backend/database/migrations
        database_dir = os.path.dirname(migrations_dir)               # backend/database
        backend_dir = os.path.dirname(database_dir)                  # backend
        alembic_dir = os.path.join(backend_dir, "alembic")           # backend/alembic

        # Create Alembic configuration
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", alembic_dir)
        alembic_cfg.set_main_option("sqlalchemy.url", get_database_url())

        # Run migrations
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")

    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        raise


def create_migration(message: str):
    """Create a new migration."""
    try:
        migrations_dir = os.path.dirname(os.path.abspath(__file__))
        database_dir = os.path.dirname(migrations_dir)
        backend_dir = os.path.dirname(database_dir)
        alembic_dir = os.path.join(backend_dir, "alembic")

        # Create Alembic configuration
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", alembic_dir)
        alembic_cfg.set_main_option("sqlalchemy.url", get_database_url())

        # Create migration
        command.revision(alembic_cfg, message=message, autogenerate=True)
        logger.info(f"Migration created: {message}")

    except Exception as e:
        logger.error(f"Migration creation failed: {e}")
        raise


def get_current_revision():
    """Get current database revision."""
    try:
        migrations_dir = os.path.dirname(os.path.abspath(__file__))
        database_dir = os.path.dirname(migrations_dir)
        backend_dir = os.path.dirname(database_dir)
        alembic_dir = os.path.join(backend_dir, "alembic")

        # Create Alembic configuration
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", alembic_dir)
        alembic_cfg.set_main_option("sqlalchemy.url", get_database_url())

        # Get current revision
        revision = command.current(alembic_cfg)
        return revision

    except Exception as e:
        logger.error(f"Failed to get current revision: {e}")
        return None
