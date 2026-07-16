#!/bin/bash
# ─────────────────────────────────────────────
# Sprint 16E-5: Automatic Rollback
#
# Monitors the active deployment slot and rolls back
# if health checks fail, 5xx rate exceeds threshold,
# or latency exceeds threshold.
#
# Usage: bash scripts/auto-rollback.sh [environment]
#   environment: staging | production (default: staging)
#
# Designed to run as a Docker sidecar or cron job.
# ─────────────────────────────────────────────

set -euo pipefail

ENVIRONMENT="${1:-staging}"
CHECK_INTERVAL="${ROLLBACK_CHECK_INTERVAL:-10}"   # seconds between checks
FAILURE_THRESHOLD="${ROLLBACK_FAILURE_THRESHOLD:-3}"  # consecutive failures before rollback
LATENCY_THRESHOLD_MS="${ROLLBACK_LATENCY_THRESHOLD:-2000}"  # ms
ERROR_RATE_THRESHOLD="${ROLLBACK_ERROR_RATE:-0.05}"  # 5% 5xx rate

# Determine URLs
if [ "$ENVIRONMENT" = "production" ]; then
    BASE_URL="${PROD_URL:-https://localhost}"
else
    BASE_URL="${STAGING_URL:-http://localhost}"
fi

COMPOSE_FILE="docker/docker-compose.${ENVIRONMENT}.yml"
ACTIVE_SLOT_FILE="/opt/utos/active-slot"

echo "=== UTOS Auto-Rollback Monitor ==="
echo "Environment: $ENVIRONMENT"
echo "URL: $BASE_URL"
echo "Check interval: ${CHECK_INTERVAL}s"
echo "Failure threshold: $FAILURE_THRESHOLD consecutive failures"
echo "Latency threshold: ${LATENCY_THRESHOLD_MS}ms"
echo "Error rate threshold: $(echo "$ERROR_RATE_THRESHOLD * 100" | bc)%"
echo ""

FAILURE_COUNT=0

while true; do
    # ── Get current active slot ───────────────
    CURRENT_SLOT=$(cat "$ACTIVE_SLOT_FILE" 2>/dev/null || echo "blue")

    if [ "$CURRENT_SLOT" = "blue" ]; then
        PREVIOUS_SLOT="green"
    else
        PREVIOUS_SLOT="blue"
    fi

    # ── Health check ──────────────────────────
    HEALTH_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/health" 2>/dev/null || echo "000")
    HEALTH_LATENCY=$(curl -sf -o /dev/null -w "%{time_total}" "$BASE_URL/health" 2>/dev/null || echo "999")
    LATENCY_MS=$(echo "$HEALTH_LATENCY * 1000" | bc 2>/dev/null || echo "999")

    # ── Check /ready ──────────────────────────
    READY_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/ready" 2>/dev/null || echo "000")

    # ── Check /live ───────────────────────────
    LIVE_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/live" 2>/dev/null || echo "000")

    # ── Evaluate health ───────────────────────
    HEALTHY=true

    if [ "$HEALTH_STATUS" != "200" ] && [ "$HEALTH_STATUS" != "503" ]; then
        echo "[$(date -u +%H:%M:%S)] WARN: /health returned $HEALTH_STATUS"
        HEALTHY=false
    fi

    if [ "$READY_STATUS" != "200" ]; then
        echo "[$(date -u +%H:%M:%S)] WARN: /ready returned $READY_STATUS"
        HEALTHY=false
    fi

    if [ "$LIVE_STATUS" != "200" ]; then
        echo "[$(date -u +%H:%M:%S)] CRITICAL: /live returned $LIVE_STATUS"
        HEALTHY=false
    fi

    if [ $(echo "$LATENCY_MS > $LATENCY_THRESHOLD_MS" | bc 2>/dev/null || echo "0") = "1" ]; then
        echo "[$(date -u +%H:%M:%S)] WARN: Latency ${LATENCY_MS}ms exceeds ${LATENCY_THRESHOLD_MS}ms"
        HEALTHY=false
    fi

    # ── Check error rate from Prometheus ──────
    # Query Prometheus for 5xx rate over last 5 minutes
    if [ -n "${PROMETHEUS_URL:-}" ]; then
        ERROR_QUERY="sum(rate(utos_http_requests_total{status=~\"5..\"}[5m])) / sum(rate(utos_http_requests_total[5m]))"
        ERROR_RATE=$(curl -sf "$PROMETHEUS_URL/api/v1/query?query=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$ERROR_QUERY'))")" 2>/dev/null | python3 -c "import sys,json; r=json.load(sys.stdin); print(r['data']['result'][0]['value'][1] if r['data']['result'] else '0')" 2>/dev/null || echo "0")

        if [ $(echo "$ERROR_RATE > $ERROR_RATE_THRESHOLD" | bc 2>/dev/null || echo "0") = "1" ]; then
            echo "[$(date -u +%H:%M:%S)] WARN: Error rate $(echo "$ERROR_RATE * 100" | bc)% exceeds $(echo "$ERROR_RATE_THRESHOLD * 100" | bc)%"
            HEALTHY=false
        fi
    fi

    # ── Act on health status ──────────────────
    if [ "$HEALTHY" = "true" ]; then
        if [ "$FAILURE_COUNT" -gt 0 ]; then
            echo "[$(date -u +%H:%M:%S)] OK: Health recovered (failures reset from $FAILURE_COUNT)"
        fi
        FAILURE_COUNT=0
    else
        FAILURE_COUNT=$((FAILURE_COUNT + 1))
        echo "[$(date -u +%H:%M:%S)] Failure count: $FAILURE_COUNT / $FAILURE_THRESHOLD"

        if [ "$FAILURE_COUNT" -ge "$FAILURE_THRESHOLD" ]; then
            echo "[$(date -u +%H:%M:%S)] CRITICAL: Threshold reached — initiating rollback"

            # Check if previous slot is available
            PREV_RUNNING=$(docker compose -f "$COMPOSE_FILE" ps --status running backend-$PREVIOUS_SLOT 2>/dev/null | grep -c "backend-$PREVIOUS_SLOT" || echo "0")

            if [ "$PREV_RUNNING" -gt 0 ]; then
                echo "[$(date -u +%H:%M:%S)] Rolling back to $PREVIOUS_SLOT..."

                # Switch active slot
                echo "$PREVIOUS_SLOT" > "$ACTIVE_SLOT_FILE"
                docker compose -f "$COMPOSE_FILE" restart nginx

                sleep 5

                # Verify rollback
                ROLLBACK_HEALTH=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/health" 2>/dev/null || echo "000")
                if [ "$ROLLBACK_HEALTH" = "200" ] || [ "$ROLLBACK_HEALTH" = "503" ]; then
                    echo "[$(date -u +%H:%M:%S)] Rollback successful — $PREVIOUS_SLOT is now active"
                    # Stop the failed slot
                    docker compose -f "$COMPOSE_FILE" stop backend-$CURRENT_SLOT frontend-$CURRENT_SLOT 2>/dev/null || true
                    FAILURE_COUNT=0
                else
                    echo "[$(date -u +%H:%M:%S)] CRITICAL: Rollback verification failed — manual intervention required"
                fi
            else
                echo "[$(date -u +%H:%M:%S)] CRITICAL: Previous slot ($PREVIOUS_SLOT) not running — cannot rollback automatically"
            fi
        fi
    fi

    sleep "$CHECK_INTERVAL"
done
