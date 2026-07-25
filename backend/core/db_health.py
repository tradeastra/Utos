"""
Database health service for UTOS Trading Engine.

Collects database health metrics:
- Connection pool stats
- Slow query count
- Replication lag
- Migration version
- Backup age
"""

import hashlib
from datetime import UTC, datetime

from core.logging import get_logger
from core.metrics import (
    utos_db_backup_age_hours,
    utos_db_connections_active,
    utos_db_migration_version,
    utos_db_pool_checked_out,
    utos_db_pool_size,
    utos_db_replication_lag_seconds,
    utos_db_slow_query_count,
)
from sqlalchemy import text

logger = get_logger(__name__)


class DatabaseHealthService:
    """Collect and expose database health metrics."""

    async def collect_pool_stats(self) -> dict:
        """Collect connection pool statistics from SQLAlchemy engine."""
        from database.base import get_engine

        stats = {
            "pool_size": 0,
            "checked_out": 0,
            "overflow": 0,
            "invalidated": 0,
        }

        try:
            engine = get_engine()
            pool = engine.pool
            stats["pool_size"] = pool.size()
            stats["checked_out"] = pool.checkedout()
            stats["overflow"] = pool.overflow()
            stats["invalidated"] = pool.invalidated()

            # Update Prometheus metrics
            utos_db_pool_size.set(stats["pool_size"])
            utos_db_pool_checked_out.set(stats["checked_out"])
            utos_db_connections_active.set(stats["checked_out"])

        except Exception as exc:
            logger.warning(f"Failed to collect pool stats: {exc}")

        return stats

    async def collect_slow_queries(self) -> int:
        """Count slow queries from pg_stat_statements (if available)."""
        try:
            from database.base import get_engine

            engine = get_engine()
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(
                        "SELECT count(*) FROM pg_stat_statements "
                        "WHERE mean_exec_time > 100;"
                    )
                )
                count = result.scalar() or 0
                utos_db_slow_query_count.set(count)
                return count
        except Exception:
            # pg_stat_statements extension may not be installed
            utos_db_slow_query_count.set(0)
            return 0

    async def collect_replication_lag(self) -> float:
        """Get replication lag in seconds (0 if not a replica)."""
        try:
            from database.base import get_engine

            engine = get_engine()
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(
                        "SELECT COALESCE("
                        "  EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())), "
                        "  0"
                        ") WHERE pg_is_in_recovery();"
                    )
                )
                lag = result.scalar() or 0.0
                utos_db_replication_lag_seconds.set(float(lag))
                return float(lag)
        except Exception:
            # Not a replica or function not available
            utos_db_replication_lag_seconds.set(0)
            return 0.0

    async def collect_migration_version(self) -> str:
        """Get current Alembic migration version and update metric."""
        try:
            from database.migrations import get_current_revision

            rev = get_current_revision()
            if rev:
                # Hash the revision string to a numeric value for Prometheus Gauge
                numeric = int(hashlib.md5(rev.encode()).hexdigest()[:8], 16) % (2**31)
                utos_db_migration_version.set(numeric)
                return rev
            utos_db_migration_version.set(0)
            return "unknown"
        except Exception:
            utos_db_migration_version.set(0)
            return "unknown"

    async def collect_backup_age(self) -> float | None:
        """Get age of latest backup in hours and update metric."""
        try:
            from core.backup import backup_manager

            age = backup_manager.get_backup_age_hours()
            if age is not None:
                utos_db_backup_age_hours.set(age)
            else:
                utos_db_backup_age_hours.set(-1)
            return age
        except Exception:
            utos_db_backup_age_hours.set(-1)
            return None

    async def collect_all(self) -> dict:
        """Collect all database health metrics at once."""
        pool_stats = await self.collect_pool_stats()
        slow_queries = await self.collect_slow_queries()
        replication_lag = await self.collect_replication_lag()
        migration_version = await self.collect_migration_version()
        backup_age = await self.collect_backup_age()

        return {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "pool": pool_stats,
            "slow_queries": slow_queries,
            "replication_lag_seconds": replication_lag,
            "migration_version": migration_version,
            "backup_age_hours": backup_age,
            "backup_fresh": backup_age is not None and backup_age < 24,
        }


# Singleton
db_health_service = DatabaseHealthService()
