"""
Database backup module for UTOS Trading Engine.

Provides:
- BackupManager: pg_dump automation with compression, checksum, retention
- Metadata file generation for each backup
- Scheduled backup support via APScheduler integration
"""

import asyncio
import hashlib
import json
import os
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BackupMetadata:
    """Metadata for a single backup."""

    backup_id: str
    timestamp: str
    database: str
    size_bytes: int
    size_compressed_bytes: int
    checksum_sha256: str
    pg_dump_version: str
    schema_version: str
    compression: str
    status: str
    duration_seconds: float
    file_path: str


class BackupManager:
    """Automated database backup with compression, checksum, and retention."""

    def __init__(
        self,
        backup_dir: str = "/tmp/backups",
        retention_days: int = 7,
        retention_count: int = 10,
        compression: str = "gzip",
    ):
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.retention_count = retention_count
        self.compression = compression
        self._ensure_backup_dir()

    def _ensure_backup_dir(self) -> None:
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _parse_db_url(self) -> dict:
        """Parse DATABASE_URL into connection parameters."""
        url = settings.DATABASE_URL
        # postgresql+asyncpg://user:pass@host:port/dbname
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

    async def create_backup(self) -> BackupMetadata:
        """Create a compressed database backup with checksum."""
        backup_id = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        timestamp = datetime.now(tz=UTC).isoformat()
        start = time.perf_counter()

        params = self._parse_db_url()
        dump_file = self.backup_dir / f"utos_{backup_id}.sql"
        compressed_file = self.backup_dir / f"utos_{backup_id}.sql.gz"

        logger.info(f"Starting backup {backup_id}")

        # Build pg_dump command
        env = os.environ.copy()
        env["PGPASSWORD"] = params["password"]

        cmd = [
            "pg_dump",
            "-h",
            params["host"],
            "-p",
            str(params["port"]),
            "-U",
            params["user"],
            "-d",
            params["dbname"],
            "--no-owner",
            "--no-privileges",
            "--format=plain",
            "--verbose",
        ]

        try:
            # Run pg_dump
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"pg_dump failed: {error_msg}")
                metadata = BackupMetadata(
                    backup_id=backup_id,
                    timestamp=timestamp,
                    database=params["dbname"],
                    size_bytes=0,
                    size_compressed_bytes=0,
                    checksum_sha256="",
                    pg_dump_version="",
                    schema_version="",
                    compression=self.compression,
                    status="failed",
                    duration_seconds=time.perf_counter() - start,
                    file_path="",
                )
                self._write_metadata(metadata)
                return metadata

            # Write dump file
            dump_file.write_bytes(stdout)
            size_bytes = dump_file.stat().st_size

            # Compress
            if self.compression == "gzip":
                import gzip

                with (
                    open(dump_file, "rb") as f_in,
                    gzip.open(compressed_file, "wb") as f_out,
                ):
                    shutil.copyfileobj(f_in, f_out)
                dump_file.unlink()
                compressed_file = dump_file

            size_compressed = compressed_file.stat().st_size

            # Checksum
            checksum = self._compute_checksum(compressed_file)

            # Get pg_dump version
            version_proc = await asyncio.create_subprocess_exec(
                "pg_dump",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            v_stdout, _ = await version_proc.communicate()
            pg_version = v_stdout.decode().strip() if v_stdout else "unknown"

            # Get schema version (Alembic)
            schema_version = await self._get_schema_version()

            duration = time.perf_counter() - start

            metadata = BackupMetadata(
                backup_id=backup_id,
                timestamp=timestamp,
                database=params["dbname"],
                size_bytes=size_bytes,
                size_compressed_bytes=size_compressed,
                checksum_sha256=checksum,
                pg_dump_version=pg_version,
                schema_version=schema_version,
                compression=self.compression,
                status="completed",
                duration_seconds=round(duration, 2),
                file_path=str(compressed_file),
            )

            self._write_metadata(metadata)
            logger.info(
                f"Backup {backup_id} completed: {size_compressed} bytes, "
                f"checksum={checksum[:16]}..., duration={duration:.1f}s"
            )

            # Apply retention policy
            await self.apply_retention()

            return metadata

        except Exception as exc:
            logger.error(f"Backup failed: {exc}")
            metadata = BackupMetadata(
                backup_id=backup_id,
                timestamp=timestamp,
                database=params.get("dbname", "unknown"),
                size_bytes=0,
                size_compressed_bytes=0,
                checksum_sha256="",
                pg_dump_version="",
                schema_version="",
                compression=self.compression,
                status="failed",
                duration_seconds=time.perf_counter() - start,
                file_path="",
            )
            self._write_metadata(metadata)
            return metadata

    def _compute_checksum(self, file_path: Path) -> str:
        """Compute SHA-256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def _get_schema_version(self) -> str:
        """Get current Alembic migration version."""
        try:
            from database.migrations import get_current_revision

            rev = get_current_revision()
            return str(rev) if rev else "unknown"
        except Exception:  # noqa: BLE001
            return "unknown"

    def _write_metadata(self, metadata: BackupMetadata) -> None:
        """Write metadata JSON file alongside backup."""
        meta_file = self.backup_dir / f"utos_{metadata.backup_id}.meta.json"
        with open(meta_file, "w") as f:
            json.dump(asdict(metadata), f, indent=2)

    def _read_metadata(self, meta_file: Path) -> BackupMetadata | None:
        """Read metadata from JSON file."""
        try:
            with open(meta_file) as f:
                data = json.load(f)
            return BackupMetadata(**data)
        except Exception:  # noqa: BLE001
            return None

    async def apply_retention(self) -> int:
        """Apply retention policy — delete old backups.

        Returns count of deleted backups.
        """
        deleted = 0
        deleted_ids = set()

        # Get all metadata files
        meta_files = sorted(self.backup_dir.glob("*.meta.json"))
        backups = []
        for mf in meta_files:
            meta = self._read_metadata(mf)
            if meta and meta.status == "completed":
                backups.append(meta)

        # Delete by age
        cutoff = datetime.now(tz=UTC) - timedelta(days=self.retention_days)
        for meta in backups:
            try:
                ts = datetime.fromisoformat(meta.timestamp)
                if ts < cutoff:
                    self._delete_backup(meta)
                    deleted += 1
                    deleted_ids.add(meta.backup_id)
            except Exception:  # noqa: BLE001
                pass

        # Delete by count (keep newest retention_count)
        remaining = [b for b in backups if b.backup_id not in deleted_ids]
        remaining.sort(key=lambda b: b.timestamp, reverse=True)
        if len(remaining) > self.retention_count:
            for meta in remaining[self.retention_count :]:
                self._delete_backup(meta)
                deleted += 1

        if deleted > 0:
            logger.info(f"Retention policy deleted {deleted} old backups")

        return deleted

    def _delete_backup(self, metadata: BackupMetadata) -> None:
        """Delete a backup file and its metadata."""
        if metadata.file_path and os.path.exists(metadata.file_path):
            os.remove(metadata.file_path)
        meta_file = self.backup_dir / f"utos_{metadata.backup_id}.meta.json"
        if meta_file.exists():
            meta_file.unlink()

    def list_backups(self) -> list[BackupMetadata]:
        """List all completed backups sorted by timestamp (newest first)."""
        meta_files = sorted(
            self.backup_dir.glob("*.meta.json"),
            reverse=True,
        )
        backups = []
        for mf in meta_files:
            meta = self._read_metadata(mf)
            if meta:
                backups.append(meta)
        return backups

    def get_latest_backup(self) -> BackupMetadata | None:
        """Get the most recent successful backup."""
        backups = self.list_backups()
        completed = [b for b in backups if b.status == "completed"]
        return completed[0] if completed else None

    def verify_checksum(self, backup_id: str) -> bool:
        """Verify checksum of a specific backup."""
        meta_file = self.backup_dir / f"utos_{backup_id}.meta.json"
        meta = self._read_metadata(meta_file)
        if not meta or not meta.file_path:
            return False
        file_path = Path(meta.file_path)
        if not file_path.exists():
            return False
        current_checksum = self._compute_checksum(file_path)
        return current_checksum == meta.checksum_sha256

    def get_backup_age_hours(self) -> float | None:
        """Get age of latest backup in hours (None if no backup)."""
        latest = self.get_latest_backup()
        if not latest:
            return None
        try:
            ts = datetime.fromisoformat(latest.timestamp)
            age = datetime.now(tz=UTC) - ts
            return age.total_seconds() / 3600
        except Exception:  # noqa: BLE001
            return None


# Singleton
backup_manager = BackupManager(
    backup_dir=os.environ.get("BACKUP_DIR", "/tmp/backups"),
    retention_days=int(os.environ.get("BACKUP_RETENTION_DAYS", "7")),
    retention_count=int(os.environ.get("BACKUP_RETENTION_COUNT", "10")),
)
