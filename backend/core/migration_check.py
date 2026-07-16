"""
Migration validation module for UTOS Trading Engine.

Provides:
- dry-run migration (generate SQL without executing)
- rollback simulation
- migration timing
- compatibility check
"""

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, asdict

from core.config import settings, get_database_url
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MigrationValidationResult:
    """Result of a migration validation run."""
    timestamp: str
    current_revision: str
    target_revision: str
    dry_run_sql: str
    dry_run_statements: int
    rollback_sql: str
    rollback_possible: bool
    upgrade_duration_ms: float
    downgrade_duration_ms: float
    compatibility_warnings: list
    status: str
    errors: list


class MigrationValidator:
    """Validate Alembic migrations before deployment."""

    def __init__(self):
        self.migrations_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "database", "migrations",
        )

    def _get_alembic_config(self, url: Optional[str] = None):
        """Build Alembic config for the current environment."""
        from alembic.config import Config
        cfg = Config()
        cfg.set_main_option("script_location", self.migrations_dir)
        cfg.set_main_option("sqlalchemy.url", url or get_database_url())
        return cfg

    async def dry_run_upgrade(self, target: str = "head") -> dict:
        """Generate SQL for migration without executing.

        Args:
            target: Target revision (default: head).

        Returns:
            Dict with generated SQL, statement count, and status.
        """
        result = {
            "target": target,
            "sql": "",
            "statement_count": 0,
            "status": "started",
            "errors": [],
        }

        try:
            from alembic import command
            import io
            from contextlib import redirect_stdout

            cfg = self._get_alembic_config()

            # Capture SQL output via offline mode
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                command.upgrade(cfg, target, sql=True)

            sql = buffer.getvalue()
            result["sql"] = sql
            result["statement_count"] = sql.count(";\n") + (1 if sql.strip() else 0)
            result["status"] = "completed"

            logger.info(
                f"Dry-run upgrade to {target}: {result['statement_count']} statements"
            )

        except Exception as exc:
            result["status"] = "failed"
            result["errors"].append(str(exc))
            logger.error(f"Dry-run upgrade failed: {exc}")

        return result

    async def dry_run_downgrade(self, target: str = "-1") -> dict:
        """Generate SQL for rollback without executing.

        Args:
            target: Target revision (default: -1, one step back).

        Returns:
            Dict with generated SQL, statement count, and status.
        """
        result = {
            "target": target,
            "sql": "",
            "statement_count": 0,
            "rollback_possible": False,
            "status": "started",
            "errors": [],
        }

        try:
            from alembic import command
            import io
            from contextlib import redirect_stdout

            cfg = self._get_alembic_config()

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                command.downgrade(cfg, target, sql=True)

            sql = buffer.getvalue()
            result["sql"] = sql
            result["statement_count"] = sql.count(";\n") + (1 if sql.strip() else 0)
            result["rollback_possible"] = True
            result["status"] = "completed"

            logger.info(
                f"Dry-run downgrade to {target}: {result['statement_count']} statements"
            )

        except Exception as exc:
            result["status"] = "failed"
            result["errors"].append(str(exc))
            result["rollback_possible"] = False
            logger.error(f"Dry-run downgrade failed: {exc}")

        return result

    async def time_upgrade(self, target: str = "head") -> dict:
        """Measure actual migration execution time.

        WARNING: This executes the migration against the configured database.

        Returns:
            Dict with duration and status.
        """
        result = {
            "target": target,
            "duration_ms": 0,
            "status": "started",
            "errors": [],
        }

        start = time.perf_counter()
        try:
            from alembic import command
            cfg = self._get_alembic_config()
            command.upgrade(cfg, target)
            result["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
            result["status"] = "completed"
            logger.info(f"Upgrade to {target} took {result['duration_ms']}ms")
        except Exception as exc:
            result["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
            result["status"] = "failed"
            result["errors"].append(str(exc))
            logger.error(f"Timed upgrade failed: {exc}")

        return result

    def get_current_revision(self) -> Optional[str]:
        """Get current Alembic revision."""
        try:
            from database.migrations import get_current_revision
            return get_current_revision()
        except Exception as exc:
            logger.error(f"Failed to get current revision: {exc}")
            return None

    def check_compatibility(self) -> list:
        """Check for compatibility issues between models and migrations.

        Returns:
            List of warning strings (empty if all good).
        """
        warnings = []

        try:
            from database.base import Base
            from models import (
                User, ExchangeAccount, TradingInstance, Position,
                Order, GridProfile, Strategy, Transaction,
                Subscription, Affiliate, Notification, Balance,
            )

            # Check all models are registered on Base.metadata
            expected_models = [
                "users", "exchange_accounts", "trading_instances",
                "positions", "orders", "grid_profiles", "strategies",
                "transactions", "subscriptions", "affiliates",
                "notifications", "balances",
            ]

            registered_tables = set(Base.metadata.tables.keys())
            for table in expected_models:
                if table not in registered_tables:
                    warnings.append(f"Table '{table}' not registered in Base.metadata")

            # Check for models without primary keys
            for table_name, table in Base.metadata.tables.items():
                if not list(table.primary_key.columns):
                    warnings.append(f"Table '{table_name}' has no primary key")

        except Exception as exc:
            warnings.append(f"Compatibility check error: {exc}")

        return warnings

    async def full_validation(self) -> MigrationValidationResult:
        """Run full migration validation suite.

        Returns:
            MigrationValidationResult with all checks.
        """
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        current_rev = self.get_current_revision() or "unknown"
        errors = []
        warnings = self.check_compatibility()

        # Dry-run upgrade
        upgrade_result = await self.dry_run_upgrade("head")
        if upgrade_result["status"] == "failed":
            errors.extend(upgrade_result["errors"])

        # Dry-run downgrade
        downgrade_result = await self.dry_run_downgrade("-1")
        if downgrade_result["status"] == "failed":
            errors.extend(downgrade_result["errors"])

        status = "passed" if not errors else "failed"

        return MigrationValidationResult(
            timestamp=timestamp,
            current_revision=current_rev,
            target_revision="head",
            dry_run_sql=upgrade_result["sql"][:5000],
            dry_run_statements=upgrade_result["statement_count"],
            rollback_sql=downgrade_result["sql"][:5000],
            rollback_possible=downgrade_result["rollback_possible"],
            upgrade_duration_ms=0,
            downgrade_duration_ms=0,
            compatibility_warnings=warnings,
            status=status,
            errors=errors,
        )


# Singleton
migration_validator = MigrationValidator()
