#!/bin/bash
# ─────────────────────────────────────────────
# Sprint 16D-5: Disaster Recovery Test
# 
# Flow: backup → destroy → restore → verify checksum → verify data
# ─────────────────────────────────────────────

set -e

BACKUP_DIR="${BACKUP_DIR:-/tmp/utos-dr-test}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-utos}"
DB_PASS="${POSTGRES_PASSWORD:-utos_dev_password}"
DB_NAME="${POSTGRES_DB:-utos}"
TEST_DB="utos_dr_test"

export PGPASSWORD="$DB_PASS"

echo "=== UTOS Disaster Recovery Test ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# ── Step 1: Create backup ────────────────────
echo "--- Step 1: Creating backup ---"
BACKUP_FILE="$BACKUP_DIR/utos_dr_$(date +%Y%m%d_%H%M%S).sql.gz"
mkdir -p "$BACKUP_DIR"

pg_dump \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --no-owner --no-privileges --format=plain \
    | gzip > "$BACKUP_FILE"

BACKUP_SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE")
BACKUP_CHECKSUM=$(sha256sum "$BACKUP_FILE" | awk '{print $1}')

echo "Backup created: $BACKUP_FILE"
echo "Size: $BACKUP_SIZE bytes"
echo "Checksum: ${BACKUP_CHECKSUM:0:32}..."
echo ""

# ── Step 2: Destroy test database ────────────
echo "--- Step 2: Destroying test database ($TEST_DB) ---"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $TEST_DB;" 2>/dev/null || true
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $TEST_DB;" 2>/dev/null || true
echo "Test database destroyed and recreated"
echo ""

# ── Step 3: Restore from backup ──────────────
echo "--- Step 3: Restoring from backup ---"
START_TIME=$(date +%s)

gunzip -c "$BACKUP_FILE" | \
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB" \
    --quiet --no-owner --no-privileges -v ON_ERROR_STOP=1

END_TIME=$(date +%s)
RESTORE_DURATION=$((END_TIME - START_TIME))

echo "Restore completed in ${RESTORE_DURATION}s"
echo ""

# ── Step 4: Verify checksum ──────────────────
echo "--- Step 4: Verifying backup checksum ---"
CURRENT_CHECKSUM=$(sha256sum "$BACKUP_FILE" | awk '{print $1}')

if [ "$BACKUP_CHECKSUM" = "$CURRENT_CHECKSUM" ]; then
    echo "✅ Checksum verified: $CURRENT_CHECKSUM"
else
    echo "❌ Checksum mismatch!"
    echo "  Original: $BACKUP_CHECKSUM"
    echo "  Current:  $CURRENT_CHECKSUM"
    exit 1
fi
echo ""

# ── Step 5: Verify data integrity ────────────
echo "--- Step 5: Verifying data integrity ---"

TABLES=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB" -t -A -c \
    "SELECT tablename FROM pg_tables WHERE schemaname='public';")

TABLE_COUNT=0
for table in $TABLES; do
    COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB" -t -A -c \
        "SELECT count(*) FROM $table;")
    echo "  $table: $COUNT rows"
    TABLE_COUNT=$((TABLE_COUNT + 1))
done

echo ""
echo "Total tables restored: $TABLE_COUNT"

# Verify expected tables exist
EXPECTED_TABLES="users exchange_accounts trading_instances positions orders grid_profiles strategies transactions subscriptions affiliates notifications balances"
MISSING=0
for table in $EXPECTED_TABLES; do
    if ! echo "$TABLES" | grep -qw "$table"; then
        echo "❌ Missing table: $table"
        MISSING=$((MISSING + 1))
    fi
done

if [ "$MISSING" -gt 0 ]; then
    echo "❌ $MISSING tables missing after restore!"
    exit 1
fi

echo "✅ All expected tables present"
echo ""

# ── Step 6: Cleanup ──────────────────────────
echo "--- Step 6: Cleanup ---"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $TEST_DB;" 2>/dev/null || true
echo "Test database dropped"
echo ""

# ── Summary ──────────────────────────────────
echo "=== DR Test Summary ==="
echo "Backup:     ✅ ($BACKUP_SIZE bytes)"
echo "Destroy:    ✅"
echo "Restore:    ✅ (${RESTORE_DURATION}s)"
echo "Checksum:   ✅"
echo "Integrity:  ✅ ($TABLE_COUNT tables)"
echo "Result:     ✅ PASS"
echo ""
echo "Disaster recovery test completed successfully."
