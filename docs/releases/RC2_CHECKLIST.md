# RC2 Release Checklist

**Date:** 2026-07-16  
**Release Candidate:** RC2  
**Previous Tag:** v0.17.0-RC1  
**Target Tag:** v0.17.0-RC2  

---

## RC2 Scope

RC2 is **not** a development sprint. It is operational validation only.

**Allowed:**
- Bug fixes from RC1 soak test
- Performance tuning
- Documentation additions
- Security patches

**Not allowed:**
- New features
- Architecture changes
- State machine changes
- Public interface changes

---

## RC2 Exit Criteria

| Criteria | Target | Status |
|----------|--------|--------|
| Test suite | 100% pass (1100+ tests) | ⬜ Pending |
| Soak test | 24–72h without memory/resource leak | ⬜ Pending |
| Chaos suite | 100% pass (74 tests) | ⬜ Pending |
| Security scan | No Critical/High unaddressed | ⬜ Pending |
| Blue-Green deployment | Successful without downtime | ⬜ Pending |
| Backup & restore | Verified successfully | ⬜ Pending |
| Sandbox trading | All core scenarios pass | ⬜ Pending |

---

## 1. Staging Validation

### Deploy RC1 to staging using blue-green configuration.

| Item | Status | Notes |
|------|--------|-------|
| Blue-green deployment | ⬜ | `docker/docker-compose.bluegreen.yml` |
| HTTPS via Nginx | ⬜ | Nginx reverse proxy with TLS |
| PostgreSQL | ⬜ | `postgres:16-alpine` with healthcheck |
| Redis | ⬜ | `redis:7-alpine` with maxmemory 256mb |
| Prometheus metrics | ⬜ | `/metrics` endpoint |
| Grafana dashboards | ⬜ | Configured in 16B |
| Tempo tracing | ⬜ | OTEL exporter configured |
| Backup service | ⬜ | `backend/core/backup.py` |
| Smoke test pass | ⬜ | `scripts/smoke-test.sh` |
| All services healthy | ⬜ | Docker healthchecks passing |

### Deployment Steps

```bash
# 1. Build images
docker compose -f docker/docker-compose.bluegreen.yml build

# 2. Deploy blue slot
IMAGE_TAG=v0.17.0-RC1 docker compose -f docker/docker-compose.bluegreen.yml up -d backend-blue frontend-blue

# 3. Run smoke tests against blue
bash scripts/smoke-test.sh blue staging

# 4. Switch nginx to blue
# (update active-slot file)

# 5. Deploy green slot (for future switch)
IMAGE_TAG=v0.17.0-RC1 docker compose -f docker/docker-compose.bluegreen.yml up -d backend-green frontend-green

# 6. Verify both slots healthy
docker compose -f docker/docker-compose.bluegreen.yml ps
```

---

## 2. Soak Test (24–72h)

### Monitor for resource leaks and degradation.

| Metric | Target | Status | Notes |
|--------|--------|--------|-------|
| Memory growth | < 10% over 24h | ⬜ | No gradual increase |
| WebSocket connections | Stable count | ⬜ | No connection leaks |
| File descriptors | < 80% of limit | ⬜ | No fd leaks |
| DB connection pool | Stable, no exhaustion | ⬜ | Pool size consistent |
| Retry queue | Drains to 0 | ⬜ | No stuck retries |
| Dead letter queue | No unexpected growth | ⬜ | DLQ monitored |
| CPU usage | < 70% average | ⬜ | No sustained spikes |
| Response time | < 500ms p99 | ⬜ | No latency degradation |
| Recovery events | Expected only | ⬜ | No unexpected recoveries |
| Error rate | < 0.1% | ⬜ | No error storms |

### Monitoring Commands

```bash
# Memory usage per container
docker stats --no-stream

# File descriptors
ls /proc/$(docker inspect --format '{{.State.Pid}}' utos-backend-blue-1)/fd | wc -l

# Redis info
docker compose exec redis redis-cli info memory

# PostgreSQL connections
docker compose exec postgres psql -U utos -c "SELECT count(*) FROM pg_stat_activity;"

# Prometheus metrics
curl http://localhost/metrics | grep utos_

# Check for OOM kills
docker inspect --format '{{.State.OOMKilled}}' utos-backend-blue-1
```

### Soak Test Duration

| Duration | Status | Start | End |
|----------|--------|-------|-----|
| 24h (minimum) | ⬜ | — | — |
| 48h (recommended) | ⬜ | — | — |
| 72h (ideal) | ⬜ | — | — |

---

## 3. Sandbox / Paper Trading Validation

### Core Trading Scenarios

| Scenario | Status | Notes |
|----------|--------|-------|
| Create order | ⬜ | Order placed on exchange sandbox |
| Cancel order | ⬜ | Order cancelled successfully |
| Partial fill | ⬜ | Partial fill handled correctly |
| Full fill | ⬜ | Full fill handled correctly |
| Reconnect | ⬜ | WebSocket reconnect after drop |
| Restart server | ⬜ | Recovery after server restart |
| Recovery | ⬜ | RecoveryCoordinator restores state |
| Profit lock | ⬜ | TP/SL triggers correctly |
| Grid cycle | ⬜ | Complete buy→fill→sell→fill cycle |
| Risk rejection | ⬜ | Risk limits block excessive orders |

### State Consistency Verification

After each scenario, verify:

| Check | Status | Notes |
|-------|--------|-------|
| Local state == exchange state | ⬜ | Orders match |
| Portfolio positions match | ⬜ | Quantities and entry prices |
| Exposure consistent | ⬜ | Within risk limits |
| PnL consistent | ⬜ | Matches exchange calculation |
| No duplicate orders | ⬜ | Idempotency verified |
| No orphan orders | ⬜ | Reconciler detects none |

### Sandbox Test Procedure

```bash
# 1. Configure sandbox exchange credentials
export EXCHANGE_API_KEY=sandbox_key
export EXCHANGE_API_SECRET=sandbox_secret
export EXCHANGE_TESTNET=true

# 2. Start system in sandbox mode
docker compose -f docker/docker-compose.staging.yml up -d

# 3. Create trading instance
curl -X POST http://localhost/api/v1/trading-instances \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","strategy":"smart_grid",...}'

# 4. Monitor grid cycles
watch -n 5 'curl -s http://localhost/api/v1/trading-instances/$INSTANCE_ID/status -H "Authorization: Bearer $TOKEN"'

# 5. Run reconciliation
curl -X POST http://localhost/api/v1/trading-instances/$INSTANCE_ID/reconcile \
  -H "Authorization: Bearer $TOKEN"

# 6. Verify state consistency
curl http://localhost/api/v1/trading-instances/$INSTANCE_ID/verify \
  -H "Authorization: Bearer $TOKEN"
```

---

## 4. Final Security Review

| Scan | Status | Findings | Notes |
|------|--------|----------|-------|
| pip-audit | ✅ | 19 residual (all transitive) | Down from 77 → 19. Residual are starlette/pyasn1/ecdsa/pytest constrained by upstream |
| npm audit | ✅ | 10 residual (dev deps) | Down from 13 → 10. Critical Next.js cache poisoning fixed. Remaining are esbuild/glob/minimatch in dev deps |
| Trivy (Docker images) | ⬜ | — | Run on built images |
| Secret scan | ✅ | 0 | No hardcoded secrets in repo |
| Dependency CVEs | ✅ | 0 Critical/High in production deps | Residual are transitive or dev-only |

### Security Scan Results

**Python (pip-audit):**
- Started with 77 vulnerabilities across 12 packages
- Fixed: fastapi 0.104.1→0.118.0, python-jose 3.3.0→3.4.0, requests 2.31.0→2.33.0, orjson 3.9.10→3.11.6, aiohttp 3.9.1→3.14.1, black 23.11.0→26.3.1, click 8.1.7→8.3.3, python-multipart 0.0.6→0.0.9
- Residual 19: starlette (10, requires v1.x — breaking change), pyasn1 (1, constrained by python-jose<0.5.0), ecdsa (1, transitive via python-jose), pytest (1, requires v9 but pytest-asyncio needs <9)
- **Accepted risk:** All residual are transitive dependencies with version constraints that cannot be resolved without major breaking changes

**Node.js (npm audit):**
- Started with 13 vulnerabilities (2 critical, 7 high, 4 moderate)
- Fixed: Next.js 14.2.5→14.2.35 (critical cache poisoning + DoS fixed)
- Residual 10: esbuild (moderate, dev-only), glob (high, dev-only via eslint), minimatch (high, dev-only), next (high, requires v16 — breaking change)
- **Accepted risk:** All residual are in dev dependencies or require major version jump

### Security Scan Commands

```bash
# Python dependencies
pip-audit -r backend/requirements.txt --strict

# Node dependencies
cd frontend && npm audit --production

# Docker images (if Trivy installed)
trivy image ghcr.io/andra2112s/utos-backend:v0.17.0-RC1
trivy image ghcr.io/andra2112s/utos-frontend:v0.17.0-RC1

# Secret scan (if trufflehog installed)
trufflehog filesystem --directory . --exclude-paths=.git,node_modules
```

---

## 5. Backup & Restore Verification

| Item | Status | Notes |
|------|--------|-------|
| Database backup | ⬜ | `pg_dump` completes successfully |
| Backup integrity | ⬜ | Restore to test DB, verify data |
| Point-in-time recovery | ⬜ | WAL archiving verified |
| Redis persistence | ⬜ | RDB/AOF configured |
| Configuration backup | ⬜ | Environment variables documented |
| Restore procedure | ⬜ | Documented and tested |

### Backup & Restore Commands

```bash
# Database backup
docker compose exec postgres pg_dump -U utos utos | gzip > backup_$(date +%Y%m%d).sql.gz

# Database restore
gunzip -c backup_20260716.sql.gz | docker compose exec -T postgres psql -U utos utos_test

# Redis backup
docker compose exec redis redis-cli SAVE
docker cp utos-redis-1:/data/dump.rdb redis_backup_$(date +%Y%m%d).rdb

# Verify backup
docker compose exec postgres psql -U utos utos_test -c "SELECT count(*) FROM trading_instances;"
```

---

## 6. Blue-Green Deployment Verification

| Item | Status | Notes |
|------|--------|-------|
| Blue slot healthy | ⬜ | All services passing healthcheck |
| Green slot healthy | ⬜ | All services passing healthcheck |
| Switch blue→green | ⬜ | No downtime during switch |
| Switch green→blue | ⬜ | Rollback successful |
| Nginx upstream switch | ⬜ | Active-slot file updated |
| Smoke test after switch | ⬜ | All smoke tests pass |
| Zero downtime | ⬜ | No 5xx errors during switch |

---

## Sign-off

| Role | Status | Date |
|------|--------|------|
| Engineering | ⬜ | — |
| Architecture | ⬜ | — |
| Security | ⬜ | — |
| Operations | ⬜ | — |

---

## Next Steps

1. **Beta:** Deploy to staging with sandbox/paper trading, collect telemetry for several days
2. **v1.0.0:** Full pipeline validation on clean clone, automated artifacts, blue-green deploy to production

```
v0.17.0-RC1
        │
        ▼
24–72h Soak Test
        │
        ▼
Sandbox / Paper Trading Validation
        │
        ▼
v0.17.0-RC2  ← this checklist
        │
        ▼
Beta (operasional terbatas)
        │
        ▼
v1.0.0
```
