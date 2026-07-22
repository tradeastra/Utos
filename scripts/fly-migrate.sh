#!/usr/bin/env bash
# ─────────────────────────────────────────────
# Fly.io Alembic Migration Script
#
# Usage:
#   ./scripts/fly-migrate.sh          # upgrade head
#   ./scripts/fly-migrate.sh status   # check migration status
#   ./scripts/fly-migrate.sh downgrade -1  # rollback one revision
#   ./scripts/fly-migrate.sh revision --autogenerate -m "description"
#
# Prerequisites:
#   - flyctl installed and authenticated (flyctl auth login)
#   - DATABASE_URL secret set on Fly.io app
# ─────────────────────────────────────────────

set -euo pipefail

APP_NAME="${FLY_APP_NAME:-utos-staging-backend}"
WORKDIR="/app/backend"

# Available commands
ACTION="${1:-upgrade}"
shift || true

case "$ACTION" in
  upgrade)
    ALEMBIC_CMD="alembic upgrade head"
    ;;
  status)
    ALEMBIC_CMD="alembic current"
    ;;
  downgrade)
    ALEMBIC_CMD="alembic downgrade ${1:--1}"
    ;;
  revision)
    MSG="${2:-auto}"
    ALEMBIC_CMD="alembic revision --autogenerate -m \"${MSG}\""
    ;;
  history)
    ALEMBIC_CMD="alembic history --verbose"
    ;;
  *)
    echo "Usage: $0 {upgrade|status|downgrade|revision|history}"
    echo ""
    echo "Commands:"
    echo "  upgrade              Run alembic upgrade head (default)"
    echo "  status               Show current migration revision"
    echo "  downgrade [N]        Rollback N revisions (default: 1)"
    echo "  revision [message]   Create new autogenerate migration"
    echo "  history              Show migration history"
    exit 1
    ;;
esac

echo "=========================================="
echo "  Fly.io Alembic Migration"
echo "  App:     ${APP_NAME}"
echo "  Workdir: ${WORKDIR}"
echo "  Command: ${ALEMBIC_CMD}"
echo "=========================================="

# ── Key: use sh -c so shell builtins (cd) and operators (&&) work ──
flyctl ssh console \
  -a "${APP_NAME}" \
  --command "sh -c 'cd ${WORKDIR} && PYTHONPATH=/app/backend ${ALEMBIC_CMD}'"

echo ""
echo "Migration command completed."
