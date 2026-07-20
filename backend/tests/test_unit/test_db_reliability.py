"""
Tests for Sprint 16D: Database Reliability — backup manager,
restore manager, migration validator, and db health service.
"""

import hashlib
from datetime import UTC, datetime

import pytest
from core.backup import BackupManager, BackupMetadata
from core.migration_check import MigrationValidator


class TestBackupManager:
    """Test backup manager logic (without actual pg_dump)."""

    def test_backup_metadata_dataclass(self):
        meta = BackupMetadata(
            backup_id="20250716_120000",
            timestamp=datetime.now(tz=UTC).isoformat(),
            database="utos",
            size_bytes=1024,
            size_compressed_bytes=512,
            checksum_sha256="abc123",
            pg_dump_version="pg_dump 16.0",
            schema_version="abc123",
            compression="gzip",
            status="completed",
            duration_seconds=1.5,
            file_path="/backups/test.sql.gz",
        )
        assert meta.backup_id == "20250716_120000"
        assert meta.status == "completed"
        assert meta.size_bytes == 1024

    def test_backup_metadata_serialization(self, tmp_path):
        meta = BackupMetadata(
            backup_id="test123",
            timestamp=datetime.now(tz=UTC).isoformat(),
            database="utos",
            size_bytes=100,
            size_compressed_bytes=50,
            checksum_sha256="deadbeef",
            pg_dump_version="pg_dump 16.0",
            schema_version="rev001",
            compression="gzip",
            status="completed",
            duration_seconds=0.5,
            file_path=str(tmp_path / "test.sql.gz"),
        )
        mgr = BackupManager(backup_dir=str(tmp_path))
        mgr._write_metadata(meta)
        meta_file = tmp_path / "utos_test123.meta.json"
        assert meta_file.exists()
        loaded = mgr._read_metadata(meta_file)
        assert loaded is not None
        assert loaded.backup_id == "test123"
        assert loaded.checksum_sha256 == "deadbeef"

    def test_checksum_computation(self, tmp_path):
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"hello world")
        mgr = BackupManager(backup_dir=str(tmp_path))
        checksum = mgr._compute_checksum(test_file)
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert checksum == expected

    def test_verify_checksum_valid(self, tmp_path):
        test_file = tmp_path / "test.sql.gz"
        test_file.write_bytes(b"backup content")
        checksum = hashlib.sha256(b"backup content").hexdigest()
        meta = BackupMetadata(
            backup_id="verify_test",
            timestamp=datetime.now(tz=UTC).isoformat(),
            database="utos",
            size_bytes=14,
            size_compressed_bytes=14,
            checksum_sha256=checksum,
            pg_dump_version="pg_dump 16.0",
            schema_version="rev001",
            compression="gzip",
            status="completed",
            duration_seconds=0.1,
            file_path=str(test_file),
        )
        mgr = BackupManager(backup_dir=str(tmp_path))
        mgr._write_metadata(meta)
        assert mgr.verify_checksum("verify_test") is True

    def test_verify_checksum_invalid(self, tmp_path):
        test_file = tmp_path / "test.sql.gz"
        test_file.write_bytes(b"backup content")
        meta = BackupMetadata(
            backup_id="verify_fail",
            timestamp=datetime.now(tz=UTC).isoformat(),
            database="utos",
            size_bytes=14,
            size_compressed_bytes=14,
            checksum_sha256="wrong_checksum",
            pg_dump_version="pg_dump 16.0",
            schema_version="rev001",
            compression="gzip",
            status="completed",
            duration_seconds=0.1,
            file_path=str(test_file),
        )
        mgr = BackupManager(backup_dir=str(tmp_path))
        mgr._write_metadata(meta)
        assert mgr.verify_checksum("verify_fail") is False

    def test_list_backups(self, tmp_path):
        mgr = BackupManager(backup_dir=str(tmp_path))
        for i in range(3):
            meta = BackupMetadata(
                backup_id=f"list_test_{i}",
                timestamp=datetime.now(tz=UTC).isoformat(),
                database="utos",
                size_bytes=100,
                size_compressed_bytes=50,
                checksum_sha256=f"hash_{i}",
                pg_dump_version="pg_dump 16.0",
                schema_version="rev001",
                compression="gzip",
                status="completed",
                duration_seconds=0.1,
                file_path="",
            )
            mgr._write_metadata(meta)
        backups = mgr.list_backups()
        assert len(backups) == 3

    def test_get_latest_backup(self, tmp_path):
        mgr = BackupManager(backup_dir=str(tmp_path))
        # Create a failed backup first
        meta_failed = BackupMetadata(
            backup_id="older_failed",
            timestamp="2025-01-01T00:00:00+00:00",
            database="utos",
            size_bytes=0,
            size_compressed_bytes=0,
            checksum_sha256="",
            pg_dump_version="",
            schema_version="",
            compression="gzip",
            status="failed",
            duration_seconds=0.1,
            file_path="",
        )
        mgr._write_metadata(meta_failed)

        meta_ok = BackupMetadata(
            backup_id="newer_ok",
            timestamp="2025-07-16T12:00:00+00:00",
            database="utos",
            size_bytes=100,
            size_compressed_bytes=50,
            checksum_sha256="abc",
            pg_dump_version="pg_dump 16.0",
            schema_version="rev001",
            compression="gzip",
            status="completed",
            duration_seconds=0.1,
            file_path="",
        )
        mgr._write_metadata(meta_ok)

        latest = mgr.get_latest_backup()
        assert latest is not None
        assert latest.backup_id == "newer_ok"
        assert latest.status == "completed"

    def test_get_latest_backup_none(self, tmp_path):
        mgr = BackupManager(backup_dir=str(tmp_path))
        assert mgr.get_latest_backup() is None

    def test_get_backup_age_hours_none(self, tmp_path):
        mgr = BackupManager(backup_dir=str(tmp_path))
        assert mgr.get_backup_age_hours() is None

    def test_get_backup_age_hours_recent(self, tmp_path):
        mgr = BackupManager(backup_dir=str(tmp_path))
        meta = BackupMetadata(
            backup_id="age_test",
            timestamp=datetime.now(tz=UTC).isoformat(),
            database="utos",
            size_bytes=100,
            size_compressed_bytes=50,
            checksum_sha256="abc",
            pg_dump_version="pg_dump 16.0",
            schema_version="rev001",
            compression="gzip",
            status="completed",
            duration_seconds=0.1,
            file_path="",
        )
        mgr._write_metadata(meta)
        age = mgr.get_backup_age_hours()
        assert age is not None
        assert age < 1  # Less than 1 hour old

    def test_retention_deletes_old_backups(self, tmp_path):
        mgr = BackupManager(
            backup_dir=str(tmp_path),
            retention_days=1,
            retention_count=10,
        )
        # Create old backup
        old_file = tmp_path / "utos_old.sql.gz"
        old_file.write_bytes(b"old")
        old_meta = BackupMetadata(
            backup_id="old",
            timestamp="2024-01-01T00:00:00+00:00",
            database="utos",
            size_bytes=3,
            size_compressed_bytes=3,
            checksum_sha256="old_hash",
            pg_dump_version="pg_dump 16.0",
            schema_version="rev001",
            compression="gzip",
            status="completed",
            duration_seconds=0.1,
            file_path=str(old_file),
        )
        mgr._write_metadata(old_meta)

        # Create recent backup
        new_file = tmp_path / "utos_new.sql.gz"
        new_file.write_bytes(b"new")
        new_meta = BackupMetadata(
            backup_id="new",
            timestamp=datetime.now(tz=UTC).isoformat(),
            database="utos",
            size_bytes=3,
            size_compressed_bytes=3,
            checksum_sha256="new_hash",
            pg_dump_version="pg_dump 16.0",
            schema_version="rev001",
            compression="gzip",
            status="completed",
            duration_seconds=0.1,
            file_path=str(new_file),
        )
        mgr._write_metadata(new_meta)

        import asyncio

        deleted = asyncio.run(mgr.apply_retention())
        assert deleted >= 1
        assert not old_file.exists()
        assert new_file.exists()


class TestMigrationValidator:
    """Test migration validator logic."""

    def test_compatibility_check_returns_list(self):
        validator = MigrationValidator()
        warnings = validator.check_compatibility()
        assert isinstance(warnings, list)

    def test_get_current_revision(self):
        validator = MigrationValidator()
        # This may return None if DB is not connected — that's fine
        rev = validator.get_current_revision()
        # Just verify it doesn't crash
        assert rev is None or isinstance(rev, str)


@pytest.mark.asyncio
class TestDatabaseHealthEndpoint:
    async def test_db_health_endpoint_returns_200(self, client):
        r = await client.get("/db/health")
        assert r.status_code == 200
        body = r.json()
        assert "status" in body
        assert "timestamp" in body
        assert "pool" in body
        assert "slow_queries" in body
        assert "replication_lag_seconds" in body
        assert "migration_version" in body
        assert "backup_age_hours" in body

    async def test_db_health_has_backup_freshness(self, client):
        r = await client.get("/db/health")
        body = r.json()
        assert "backup_fresh" in body
        assert isinstance(body["backup_fresh"], bool)
