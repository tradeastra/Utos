# Staging Deployment Report

**Version:** v0.17.0-RC2-attestation  
**Date:** _(fill on execution)_  
**Environment:** Staging  
**Deployed by:** _(name)_

---

## 1. Deployment Information

| Item | Value |
|------|-------|
| Git commit SHA | _ |
| Git tag | v0.17.0-RC2-attestation |
| Backend image | `ghcr.io/andra2112s/utos-backend:v0.17.0-RC2` |
| Backend image digest | `sha256:_` |
| Frontend image | `ghcr.io/andra2112s/utos-frontend:v0.17.0-RC2` |
| Frontend image digest | `sha256:_` |
| Deployment time (start) | _ |
| Deployment time (complete) | _ |
| Total duration | _ |
| Deploy method | Blue-Green (`docker-compose.bluegreen.yml`) |
| Active slot | _ (blue / green) |

---

## 2. Supply-Chain Verification

| Check | Command | Result | Notes |
|-------|---------|--------|-------|
| Image signature | `cosign verify ghcr.io/andra2112s/utos-backend:v0.17.0-RC2` | ⬜ | |
| Image signature | `cosign verify ghcr.io/andra2112s/utos-frontend:v0.17.0-RC2` | ⬜ | |
| SBOM attestation | `cosign verify-attestation --type spdxjson ghcr.io/andra2112s/utos-backend:v0.17.0-RC2` | ⬜ | |
| SBOM attestation | `cosign verify-attestation --type spdxjson ghcr.io/andra2112s/utos-frontend:v0.17.0-RC2` | ⬜ | |
| SLSA provenance | `cosign verify-attestation --type slsaprovenance ghcr.io/andra2112s/utos-backend:v0.17.0-RC2` | ⬜ | |
| SLSA provenance | `cosign verify-attestation --type slsaprovenance ghcr.io/andra2112s/utos-frontend:v0.17.0-RC2` | ⬜ | |

---

## 3. Infrastructure Health

| Service | Status | Healthcheck | Notes |
|---------|--------|-------------|-------|
| PostgreSQL | ⬜ | `pg_isready` | |
| Redis | ⬜ | `redis-cli ping` | |
| Backend (blue) | ⬜ | `GET /health` | |
| Backend (green) | ⬜ | `GET /health` | |
| Frontend (blue) | ⬜ | `GET /` | |
| Frontend (green) | ⬜ | `GET /` | |
| Nginx | ⬜ | `GET /health` | |

---

## 4. Observability Verification

| Component | Status | Verification | Notes |
|-----------|--------|--------------|-------|
| Prometheus scrape | ⬜ | `curl /metrics` returns data | |
| Grafana dashboard | ⬜ | System + trading dashboards visible | |
| Tempo tracing | ⬜ | OTEL exporter receiving traces | |
| Structured logs | ⬜ | JSON format in container logs | |
| Alert rules loaded | ⬜ | Prometheus alerting rules active | |

---

## 5. TLS / Network Verification

| Check | Status | Notes |
|-------|--------|-------|
| TLS certificate valid | ⬜ | Valid > 30 days |
| HTTPS redirect works | ⬜ | HTTP → HTTPS |
| HSTS header present | ⬜ | `Strict-Transport-Security` |
| CORS configured | ⬜ | Staging domain only |
| Network isolation | ⬜ | frontend-net / backend-net separate |

---

## 6. Smoke Test Results

**Command:** `bash scripts/smoke-test.sh active staging`

| Test | Expected | Result | Notes |
|------|----------|--------|-------|
| GET /live | 200 | ⬜ | |
| GET /ready | 200 | ⬜ | |
| GET /health | 200 | ⬜ | |
| GET /metrics | 200 | ⬜ | |
| GET / (frontend) | 200 | ⬜ | |
| POST /api/v1/auth/register | 200 + token | ⬜ | |
| POST /api/v1/auth/login | 200 + token | ⬜ | |
| GET /api/v1/users/me | 200 + user data | ⬜ | |
| GET /api/v1/trading-instances | 200 | ⬜ | |
| GET /api/v1/market | 200 | ⬜ | |
| GET /db/health | 200 | ⬜ | |
| Latency < 500ms | < 500ms | ⬜ | Actual: _ ms |

**Summary:** _ / 12 passed

---

## 7. Blue-Green Switch Test

| Step | Status | Notes |
|------|--------|-------|
| Blue slot deployed & healthy | ⬜ | |
| Green slot deployed & healthy | ⬜ | |
| Switch blue → green | ⬜ | Nginx upstream updated |
| Smoke test on green | ⬜ | All tests pass |
| Switch green → blue (rollback) | ⬜ | Nginx upstream reverted |
| Smoke test on blue | ⬜ | All tests pass |
| Zero downtime during switch | ⬜ | No 5xx errors |
| Automatic rollback monitor | ⬜ | Monitor script running |

---

## 8. Backup Verification

| Check | Status | Notes |
|-------|--------|-------|
| `pg_dump` succeeds | ⬜ | |
| Backup file non-empty | ⬜ | |
| Restore to test DB | ⬜ | Data matches |
| Redis SAVE | ⬜ | RDB snapshot created |

---

## 9. Issues Encountered

| # | Issue | Severity | Resolution | Status |
|---|-------|----------|------------|--------|
| — | — | — | — | — |

---

## 10. Sign-off

| Role | Name | Decision | Date |
|------|------|----------|------|
| Engineering | _ | ⬜ Pass / ⬜ Fail | _ |
| DevOps | _ | ⬜ Pass / ⬜ Fail | _ |

**Deployment verdict:** ⬜ APPROVED — proceed to soak test / ⬜ BLOCKED — fix issues first
