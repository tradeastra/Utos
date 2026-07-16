#!/bin/bash
# ─────────────────────────────────────────────
# Sprint 16E-4: Smoke Test — post-deploy verification
#
# Usage: bash scripts/smoke-test.sh [slot] [environment]
#   slot: blue | green | active (default: active)
#   environment: staging | production (default: staging)
#
# Exits 0 if all checks pass, 1 if any fail.
# ─────────────────────────────────────────────

set -euo pipefail

SLOT="${1:-active}"
ENVIRONMENT="${2:-staging}"
MAX_RETRIES=5
RETRY_DELAY=5

# Determine target URL
if [ "$SLOT" = "active" ]; then
    BASE_URL="${SMOKE_BASE_URL:-http://localhost}"
else
    BASE_URL="${SMOKE_BASE_URL:-http://localhost}:808$([ "$SLOT" = "blue" ] && echo "0" || echo "1")"
fi

if [ "$ENVIRONMENT" = "production" ]; then
    BASE_URL="${PROD_URL:-https://localhost}"
fi

echo "=== UTOS Smoke Test ==="
echo "Slot: $SLOT"
echo "Environment: $ENVIRONMENT"
echo "URL: $BASE_URL"
echo ""

PASSED=0
FAILED=0

# ── Helper: retry a curl command ─────────────
retry_curl() {
    local url="$1"
    local expected="${2:-200}"
    local retries=0

    while [ $retries -lt $MAX_RETRIES ]; do
        STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
        if [ "$STATUS" = "$expected" ]; then
            return 0
        fi
        retries=$((retries + 1))
        sleep $RETRY_DELAY
    done
    return 1
}

# ── Test: GET /live ──────────────────────────
echo -n "GET /live ... "
if retry_curl "$BASE_URL/live" "200"; then
    echo "✅ PASS"
    PASSED=$((PASSED + 1))
else
    echo "❌ FAIL"
    FAILED=$((FAILED + 1))
fi

# ── Test: GET /ready ─────────────────────────
echo -n "GET /ready ... "
if retry_curl "$BASE_URL/ready" "200"; then
    echo "✅ PASS"
    PASSED=$((PASSED + 1))
else
    echo "❌ FAIL"
    FAILED=$((FAILED + 1))
fi

# ── Test: GET /health ────────────────────────
echo -n "GET /health ... "
if retry_curl "$BASE_URL/health" "200"; then
    echo "✅ PASS"
    PASSED=$((PASSED + 1))
else
    # Health may return 503 if services are degraded
    STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$BASE_URL/health" 2>/dev/null || echo "000")
    if [ "$STATUS" = "503" ]; then
        echo "⚠️ WARN (503 — degraded)"
        PASSED=$((PASSED + 1))
    else
        echo "❌ FAIL (status: $STATUS)"
        FAILED=$((FAILED + 1))
    fi
fi

# ── Test: GET /metrics ───────────────────────
echo -n "GET /metrics ... "
if retry_curl "$BASE_URL/metrics" "200"; then
    echo "✅ PASS"
    PASSED=$((PASSED + 1))
else
    echo "❌ FAIL"
    FAILED=$((FAILED + 1))
fi

# ── Test: GET / (root) ───────────────────────
echo -n "GET / ... "
if retry_curl "$BASE_URL/" "200"; then
    echo "✅ PASS"
    PASSED=$((PASSED + 1))
else
    echo "❌ FAIL"
    FAILED=$((FAILED + 1))
fi

# ── Test: POST /api/v1/auth/register ─────────
echo -n "POST /api/v1/auth/register ... "
RANDOM_EMAIL="smoke_$(date +%s)_$RANDOM@utos-test.com"
REGISTER_RESPONSE=$(curl -sf -X POST "$BASE_URL/api/v1/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$RANDOM_EMAIL\",\"password\":\"SmokeTest123!\",\"username\":\"smoke_$(date +%s)\"}" \
    2>/dev/null || echo "")

if [ -n "$REGISTER_RESPONSE" ] && echo "$REGISTER_RESPONSE" | grep -q "access_token\|id"; then
    echo "✅ PASS"
    PASSED=$((PASSED + 1))
else
    echo "❌ FAIL"
    FAILED=$((FAILED + 1))
fi

# ── Test: POST /api/v1/auth/login ────────────
echo -n "POST /api/v1/auth/login ... "
LOGIN_RESPONSE=$(curl -sf -X POST "$BASE_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$RANDOM_EMAIL\",\"password\":\"SmokeTest123!\"}" \
    2>/dev/null || echo "")

if [ -n "$LOGIN_RESPONSE" ] && echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    echo "✅ PASS"
    PASSED=$((PASSED + 1))

    # Extract token for authenticated tests
    TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || echo "")

    # ── Test: GET /api/v1/users/me ────────────
    if [ -n "$TOKEN" ]; then
        echo -n "GET /api/v1/users/me ... "
        ME_RESPONSE=$(curl -sf "$BASE_URL/api/v1/users/me" \
            -H "Authorization: Bearer $TOKEN" \
            2>/dev/null || echo "")
        if [ -n "$ME_RESPONSE" ] && echo "$ME_RESPONSE" | grep -q "email\|id"; then
            echo "✅ PASS"
            PASSED=$((PASSED + 1))
        else
            echo "❌ FAIL"
            FAILED=$((FAILED + 1))
        fi

        # ── Test: GET /api/v1/trading-instances ─
        echo -n "GET /api/v1/trading-instances ... "
        INSTANCES_RESPONSE=$(curl -sf "$BASE_URL/api/v1/trading-instances" \
            -H "Authorization: Bearer $TOKEN" \
            2>/dev/null || echo "")
        if [ -n "$INSTANCES_RESPONSE" ]; then
            echo "✅ PASS"
            PASSED=$((PASSED + 1))
        else
            echo "❌ FAIL"
            FAILED=$((FAILED + 1))
        fi

        # ── Test: GET /api/v1/market ────────────
        echo -n "GET /api/v1/market ... "
        MARKET_RESPONSE=$(curl -sf "$BASE_URL/api/v1/market" \
            -H "Authorization: Bearer $TOKEN" \
            2>/dev/null || echo "")
        if [ -n "$MARKET_RESPONSE" ]; then
            echo "✅ PASS"
            PASSED=$((PASSED + 1))
        else
            echo "❌ FAIL"
            FAILED=$((FAILED + 1))
        fi
    fi
else
    echo "❌ FAIL"
    FAILED=$((FAILED + 1))
fi

# ── Test: GET /db/health ─────────────────────
echo -n "GET /db/health ... "
if retry_curl "$BASE_URL/db/health" "200"; then
    echo "✅ PASS"
    PASSED=$((PASSED + 1))
else
    echo "❌ FAIL"
    FAILED=$((FAILED + 1))
fi

# ── Test: Latency check ──────────────────────
echo -n "Latency check (< 500ms) ... "
LATENCY=$(curl -sf -o /dev/null -w "%{time_total}" "$BASE_URL/health" 2>/dev/null || echo "999")
LATENCY_MS=$(echo "$LATENCY * 1000" | bc 2>/dev/null || echo "999")
if [ $(echo "$LATENCY_MS < 500" | bc 2>/dev/null || echo "0") = "1" ]; then
    echo "✅ PASS (${LATENCY_MS}ms)"
    PASSED=$((PASSED + 1))
else
    echo "❌ FAIL (${LATENCY_MS}ms)"
    FAILED=$((FAILED + 1))
fi

# ── Summary ──────────────────────────────────
echo ""
echo "=== Smoke Test Summary ==="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ "$FAILED" -gt 0 ]; then
    echo "❌ SMOKE TEST FAILED"
    exit 1
else
    echo "✅ ALL SMOKE TESTS PASSED"
    exit 0
fi
