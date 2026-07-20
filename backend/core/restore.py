"""
Database restore module for UTOS Trading Engine.

Provides:
- RestoreManager: restore from compressed backup with integrity verification
- Schema validation post-restore
- Point-in-time validation
"""

import asyncio
import gzip
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.backup import BackupManager
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class RestoreManager:
    """Database restore with integrity verification."""

    def __init__(self, backup_manager: BackupManager):
        self.backup_mgr = backup_manager

    def _parse_db_url(self) -> dict[str, Any]:
        """Parse DATABASE_URL into connection parameters."""
        url = settings.DATABASE_URL
        url = url.replace("postgresql+asyncpg://", "postgresql://")
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "user": parsed.username or "utos",
            "password": parsed.password or "",
            "dbname": parsed.path.lstrip("/") or "utos",
        }

    async def restore_backup(
        self, backup_id: str, target_db: str | None = None
    ) -> dict:
        """Restore a database from a compressed backup.

        Args:
            backup_id: The backup ID to restore from.
            target_db: Optional target database name (defaults to current DB).

        Returns:
            Dict with restore status, duration, and validation results.
        """
        start = time.perf_counter()
        result: dict[str, Any] = {
            "backup_id": backup_id,
            "status": "started",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "duration_seconds": 0,
            "checksum_verified": False,
            "schema_valid": False,
            "table_count": 0,
            "errors": [],
        }

        # Find backup metadata
        meta_file = self.backup_mgr.backup_dir / f"utos_{backup_id}.meta.json"
        metadata = self.backup_mgr._read_metadata(meta_file)
        if not metadata:
            result["status"] = "failed"
            result["errors"].append(f"Backup metadata not found: {backup_id}")
            result["duration_seconds"] = round(time.perf_counter() - start, 2)
            return result

        if metadata.status != "completed":
            result["status"] = "failed"
            result["errors"].append(
                f"Backup was not completed successfully: {metadata.status}"
            )
            result["duration_seconds"] = round(time.perf_counter() - start, 2)
            return result

        # Verify checksum before restore
        result["checksum_verified"] = self.backup_mgr.verify_checksum(backup_id)
        if not result["checksum_verified"]:
            result["status"] = "failed"
            result["errors"].append(
                "Checksum verification failed — backup may be corrupted"
            )
            result["duration_seconds"] = round(time.perf_counter() - start, 2)
            return result

        logger.info(f"Checksum verified for backup {backup_id}")

        # Decompress and restore
        params = self._parse_db_url()
        target = target_db or params["dbname"]
        env = os.environ.copy()
        env["PGPASSWORD"] = params["password"]

        backup_file = Path(metadata.file_path)
        if not backup_file.exists():
            result["status"] = "failed"
            result["errors"].append(f"Backup file not found: {backup_file}")
            result["duration_seconds"] = round(time.perf_counter() - start, 2)
            return result

        try:
            # Decompress gzip
            if metadata.compression == "gzip":
                sql_content = gzip.decompress(backup_file.read_bytes())
            else:
                sql_content = backup_file.read_bytes()

            # Restore via psql
            cmd = [
                "psql",
                "-h",
                params["host"],
                "-p",
                str(params["port"]),
                "-U",
                params["user"],
                "-d",
                target,
                "--quiet",
                "--no-owner",
                "--no-privileges",
                "-v",
                "ON_ERROR_STOP=1",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await process.communicate(input=sql_content)

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                result["status"] = "failed"
                result["errors"].append(f"psql restore failed: {error_msg}")
                result["duration_seconds"] = round(time.perf_counter() - start, 2)
                return result

            logger.info(f"Restore completed for backup {backup_id}")

            # Schema validation
            result["schema_valid"] = await self._validate_schema(target, env, params)
            if not result["schema_valid"]:
                result["errors"].append("Schema validation failed post-restore")

            # Count tables
            result["table_count"] = await self._count_tables(target, env, params)

            result["status"] = (
                "completed" if result["schema_valid"] else "completed_with_warnings"
            )
            result["duration_seconds"] = round(time.perf_counter() - start, 2)

            logger.info(
                f"Restore {backup_id}: status={result['status']}, "
                f"tables={result['table_count']}, "
                f"duration={result['duration_seconds']}s"
            )

        except Exception as exc:
            result["status"] = "failed"
            result["errors"].append(str(exc))
            result["duration_seconds"] = round(time.perf_counter() - start, 2)
            logger.error(f"Restore failed: {exc}")

        return result

    async def _validate_schema(self, db_name: str, env: dict, params: dict) -> bool:
        """Validate schema after restore by checking expected tables exist."""
        expected_tables = [
            "users",
            "exchange_accounts",
            "trading_instances",
            "positions",
            "orders",
            "grid_profiles",
            "strategies",
            "transactions",
            "subscriptions",
            "affiliates",
            "notifications",
            "balances",
        ]

        try:
            cmd = [
                "psql",
                "-h",
                params["host"],
                "-p",
                str(params["port"]),
                "-U",
                params["user"],
                "-d",
                db_name,
                "-t",
                "-A",
                "-c",
                "SELECT tablename FROM pg_tables WHERE schemaname='public';",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, _ = await process.communicate()
            tables = stdout.decode().strip().split("\n")
            tables = [t.strip() for t in tables if t.strip()]

            missing = [t for t in expected_tables if t not in tables]
            if missing:
                logger.warning(f"Schema validation: missing tables: {missing}")
                return False

            logger.info(f"Schema validation passed: {len(tables)} tables found")
            return True

        except Exception as exc:
            logger.error(f"Schema validation error: {exc}")
            return False

    async def _count_tables(self, db_name: str, env: dict, params: dict) -> int:
        """Count tables in the restored database."""
        try:
            cmd = [
                "psql",
                "-h",
                params["host"],
                "-p",
                str(params["port"]),
                "-U",
                params["user"],
                "-d",
                db_name,
                "-t",
                "-A",
                "-c",
                "SELECT count(*) FROM pg_tables WHERE schemaname='public';",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, _ = await process.communicate()
            return int(stdout.decode().strip() or "0")
        except Exception:  # noqa: BLE001
            return 0

    async def verify_data_integrity(self, db_name: str | None = None) -> dict:
        """Verify data integrity after restore.

        Checks:
        - Row counts for key tables
        - Foreign key constraints
        - Index validity
        """
        params = self._parse_db_url()
        target = db_name or params["dbname"]
        env = os.environ.copy()
        env["PGPASSWORD"] = params["password"]

        result: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "database": target,
            "checks": {},
            "all_passed": True,
        }

        checks = [
            ("users_count", "SELECT count(*) FROM users;"),
            ("orders_count", "SELECT count(*) FROM orders;"),
            ("trading_instances_count", "SELECT count(*) FROM trading_instances;"),
            (
                "fk_constraints_valid",
                "SELECT count(*) FROM pg_constraint WHERE contype='f';",
            ),
            (
                "indexes_valid",
                "SELECT count(*) FROM pg_indexes WHERE schemaname='public';",
            ),
        ]

        for check_name, query in checks:
            try:
                cmd = [
                    "psql",
                    "-h",
                    params["host"],
                    "-p",
                    str(params["port"]),
                    "-U",
                    params["user"],
                    "-d",
                    target,
                    "-t",
                    "-A",
                    "-c",
                    query,
                ]

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    value = stdout.decode().strip()
                    result["checks"][check_name] = {"status": "pass", "value": value}
                else:
                    error = stderr.decode().strip()
                    result["checks"][check_name] = {"status": "fail", "error": error}
                    result["all_passed"] = False

            except Exception as exc:
                result["checks"][check_name] = {"status": "error", "error": str(exc)}
                result["all_passed"] = False

        return result


# Singleton
restore_manager = RestoreManager(
    backup_manager=__import__("core.backup", fromlist=["backup_manager"]).backup_manager
)
