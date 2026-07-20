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
        # Get the directory containing this file
        migrations_dir = os.path.dirname(os.path.abspath(__file__))

        # Create Alembic configuration
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", migrations_dir)
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
        # Get the directory containing this file
        migrations_dir = os.path.dirname(os.path.abspath(__file__))

        # Create Alembic configuration
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", migrations_dir)
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
        # Get the directory containing this file
        migrations_dir = os.path.dirname(os.path.abspath(__file__))

        # Create Alembic configuration
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", migrations_dir)
        alembic_cfg.set_main_option("sqlalchemy.url", get_database_url())

        # Get current revision
        revision = command.current(alembic_cfg)
        return revision

    except Exception as e:
        logger.error(f"Failed to get current revision: {e}")
        return None
