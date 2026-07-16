# Sprint 16: Production Hardening & Deployment

**Sprint:** 16  
**Version:** v0.16.0  
**Status:** Pending  
**Dependencies:** All previous sprints (01-15)  

---

## Overview

Sprint 16 is the final engineering sprint before Release Candidate. It is divided into **7 sub-phases** (16A–16G) to allow incremental implementation, testing, and review. Each sub-phase must pass its acceptance criteria before proceeding to the next.

---

## Sub-Phase Structure

```
16A: Infrastructure     → docker compose up → system healthy
16B: Observability      → Grafana shows all dashboards
16C: Security           → 0 critical vulnerabilities
16D: Database           → backup → restore → all data back
16E: CI/CD              → one push → automatic deployment
16F: Performance        → load test meets all targets
16G: Disaster Recovery  → chaos tests pass (Redis, PG, Exchange kill)
```

---

## Sprint 16A — Infrastructure

### Deliverables
- Docker multi-stage builds (backend: python:3.12-slim, frontend: node:20-alpine)
- Non-root user in all containers
- `.dockerignore` for both services
- `docker-compose.prod.yml` with: backend, frontend, postgres, redis, nginx, prometheus, grafana
- Volume mounts for persistent data
- Network isolation between services
- Environment variable injection from `.env.prod`
- Nginx reverse proxy with TLS termination, WebSocket proxy, gzip, static file serving
- Health check endpoints: `GET /health/live` (liveness), `GET /health/ready` (readiness)
- Docker HEALTHCHECK directives

### Acceptance Criteria
```
docker compose -f docker-compose.prod.yml up
    ↓
All services healthy
    ↓
GET /health/live → 200
GET /health/ready → 200
```

---

## Sprint 16B — Observability

### Deliverables
- Prometheus `/metrics` endpoint with:
  - Engine metrics: orders/sec, grid levels active, positions open
  - Worker metrics: heartbeat age, error count, queue depth
  - SaaS metrics: active subscriptions, revenue, affiliate conversions
  - System metrics: request latency, error rate, connection count
- Grafana dashboards:
  - **System Overview:** CPU, memory, request rate, error rate
  - **Trading:** orders/sec, fill rate, PnL, exposure
  - **Risk:** exposure vs limits, order gatekeeper stats
  - **SaaS:** subscriptions, revenue, churn
  - **Workers:** heartbeat, queue depth, DLQ size
- Structured logging (JSON: timestamp, level, logger, message, correlation_id, extra)
- Correlation ID propagation middleware
- OpenTelemetry auto-instrumentation for FastAPI
- Span propagation for async tasks (event bus, worker jobs)
- Export to Jaeger or Grafana Tempo

### Acceptance Criteria
Grafana dashboards display live data for:
- API (request rate, latency, errors)
- Trading (orders, grid, PnL)
- Workers (heartbeat, queue depth)
- Recovery (recovery events, timing)
- Notifications (queue, delivery rate)

---

## Sprint 16C — Security

### Deliverables
- Secrets management: all secrets via env vars, `.env.example` template, `.env.prod` excluded from git
- API rate limiting: per-endpoint (auth: 5/min, trading: 100/min, general: 60/min), sliding window via Redis, 429 + Retry-After
- Security headers in Nginx: HSTS, X-Content-Type-Options, X-Frame-Options, CSP
- Dependency audit: `pip audit` (backend), `npm audit` (frontend), fix all high/critical
- Container vulnerability scan: Trivy on Docker images, fail on CRITICAL
- OWASP Top 10 review:
  - A01: Broken Access Control — verify RBAC enforcement
  - A02: Cryptographic Failures — verify JWT, password hashing
  - A03: Injection — verify SQL parameterized queries
  - A04: Insecure Design — review threat model
  - A05: Security Misconfiguration — review defaults
  - A06: Vulnerable Components — dependency audit
  - A07: Auth Failures — verify login, session, MFA readiness
  - A08: Software/Data Integrity — verify CI pipeline integrity
  - A09: Logging/Monitoring — verify observability
  - A10: SSRF — verify outbound requests (exchange adapters)

### Acceptance Criteria
- Trivy scan: 0 CRITICAL vulnerabilities
- `pip audit`: 0 high/critical
- `npm audit`: 0 high/critical
- OWASP Top 10 review documented

---

## Sprint 16D — Database

### Deliverables
- Automated backup: `pg_dump` cron (daily full + hourly WAL), 30-day retention, encrypted storage
- Documented restore procedure
- Monthly restore test to staging
- RTO: <30 minutes, RPO: <1 hour
- Migration validation in CI: `alembic upgrade head` + `alembic downgrade -1` + `alembic upgrade head`
- Migration test on copy of production data (staging)

### Acceptance Criteria
```
Backup database
    ↓
Drop database
    ↓
Restore from backup
    ↓
All data present
    ↓
PASS
```

---

## Sprint 16E — CI/CD

### Deliverables
- GitHub Actions pipeline:

```text
Push
    ↓
1. Lint (ruff, eslint)
    ↓
2. Test (pytest, vitest)
    ↓
3. Build (Docker images)
    ↓
4. Security Scan (Trivy)
    ↓
5. Push (to registry)
    ↓
6. Deploy
    ├── develop → staging (auto)
    └── main → production (manual, blue-green)
```

- Branch strategy: `develop` → auto-deploy staging, `main` → manual → production
- Blue-green deployment: two environments, health check before switch, instant rollback
- Tags (`v0.16.0`, `v1.0.0-rc1`) → release artifacts

### Acceptance Criteria
One push to `develop` triggers:
```
Push → Test → Build → Scan → Deploy → Staging live
```

---

## Sprint 16F — Performance

### Deliverables
- k6 load test scripts in `tests/load/`
- Benchmark report in `docs/releases/SPRINT_16_BENCHMARKS.md`
- Include: p50, p95, p99 latencies, error rates, resource usage

### Performance Targets (MUST meet all)

| Metric            | Target     | Test Scenario |
| ----------------- | ---------- | ------------- |
| Trading Instances | >= 10,000  | Create + manage 10k instances via API |
| WebSocket         | >= 5,000   | Concurrent WS connections with event subscriptions |
| Orders/sec        | >= 1,000   | Order placement throughput via execution engine |
| Dashboard API     | < 200 ms   | Page load time (LCP) for all dashboard pages |
| Recovery          | < 30 sec   | Kill + restart all workers, measure full recovery |

### Acceptance Criteria
**If targets are not met, do NOT proceed to RC.** All 5 targets must pass.

---

## Sprint 16G — Disaster Recovery

### Deliverables
- `docs/runbook.md` with:
  - Incident severity levels (SEV1-SEV4)
  - On-call procedures
  - Escalation matrix
  - Common incident response steps
  - Post-mortem template
- Failover procedures: database (primary → replica), Redis (sentinel), worker (restart on healthy node), exchange (primary → backup adapter)
- Chaos tests with documented proof

### Acceptance Criteria
Each chaos test must show: Kill → Recover → PASS

```
Kill Redis       → Recover → PASS
Kill PostgreSQL  → Recover → PASS
Kill Exchange    → Recover → PASS
Kill All Workers → Recover → PASS (no data loss, <30s)
```

Recovery verification:
1. Kill all backend containers
2. Restore from backup
3. Verify all trading instances recover
4. Verify no order loss
5. Verify state consistency

---

## Post-Sprint 16: Release Candidate Phase

After Sprint 16 completes (v0.16.0):

```
v0.16.0 (Sprint 16 complete)
    ↓
v1.0.0-RC1 (feature freeze, bug fixing, internal test)
    ↓
v1.0.0-RC2 (load testing, security pen test, closed beta)
    ↓
v1.0.0-beta (limited production traffic, open beta)
    ↓
v1.0.0 (general availability)
```

**RC/Beta focus (no new features):**
- Bug fixing (race conditions, production timing, deployment, scaling)
- Load testing under real conditions
- Usability testing
- Security penetration testing
- Stability verification
- Documentation finalization

---

## Pre-RC Checklist

All items must be ✅ before entering RC phase:

- [ ] All tests pass
- [ ] Coverage >= 90%
- [ ] mypy clean
- [ ] ruff clean (including old warnings resolved)
- [ ] No circular dependencies
- [ ] No critical TODO/FIXME
- [ ] Trivy: 0 unmitigated Critical/High
- [ ] OWASP Top 10 reviewed
- [ ] Load test meets all targets
- [ ] Disaster recovery verified
- [ ] Deployment documentation complete

---

## File Structure (New)

```
docker/
├── backend.Dockerfile
├── frontend.Dockerfile
├── docker-compose.prod.yml
├── docker-compose.dev.yml
├── nginx/
│   ├── nginx.conf
│   └── conf.d/
│       └── utos.conf
└── .dockerignore

.github/
└── workflows/
    ├── ci.yml              (lint + test + build)
    ├── deploy-staging.yml  (develop → staging)
    └── deploy-prod.yml     (main → production, manual)

monitoring/
├── prometheus.yml
└── grafana/
    ├── dashboards/
    │   ├── system.json
    │   ├── trading.json
    │   ├── risk.json
    │   ├── saas.json
    │   └── workers.json
    └── provisioning/

backend/
└── middleware/
    ├── correlation_id.py
    ├── rate_limit.py
    └── metrics.py

tests/
└── load/
    ├── k6_trading_instances.js
    ├── k6_websocket.js
    ├── k6_orders.js
    └── k6_dashboard.js

docs/
├── runbook.md
└── releases/
    ├── SPRINT_16_RELEASE.md
    └── SPRINT_16_BENCHMARKS.md
```
