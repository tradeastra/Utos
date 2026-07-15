# Sprint 16: Production Hardening & Deployment

**Sprint:** 16  
**Version:** v0.16.0  
**Status:** Pending  
**Dependencies:** All previous sprints (01-15)  

---

## Overview

Sprint 16 is the final sprint before Release Candidate. It covers infrastructure, observability, security, database operations, CI/CD, performance benchmarks, and disaster recovery. The goal is to make UTOS production-ready.

---

## 1. Infrastructure

### Docker Production Images
- Multi-stage builds for backend (Python) and frontend (Next.js)
- Minimal base images (python:3.12-slim, node:20-alpine)
- Non-root user in containers
- `.dockerignore` for both services

### Docker Compose Production
- `docker-compose.prod.yml` with:
  - backend (FastAPI + uvicorn)
  - frontend (Next.js)
  - postgres
  - redis
  - nginx
  - prometheus
  - grafana
- Volume mounts for persistent data
- Network isolation between services
- Environment variable injection from `.env.prod`

### Nginx Reverse Proxy
- TLS termination (Let's Encrypt / self-signed for staging)
- WebSocket proxy support (`Upgrade` headers)
- Gzip compression
- Static file serving for frontend
- Rate limiting at proxy level

### Health Check Endpoints
- `GET /health/live` — process alive (liveness probe)
- `GET /health/ready` — dependencies connected, ready to serve (readiness probe)
- Docker HEALTHCHECK directives
- Kubernetes-compatible (if future migration needed)

---

## 2. Observability

### Prometheus Metrics
Expose `/metrics` endpoint with:
- **Engine metrics:** orders/sec, grid levels active, positions open
- **Worker metrics:** heartbeat age, error count, queue depth
- **SaaS metrics:** active subscriptions, revenue, affiliate conversions
- **System metrics:** request latency, error rate, connection count
- Use `prometheus_client` Python library

### Grafana Dashboards
- **System Overview:** CPU, memory, request rate, error rate
- **Trading Dashboard:** orders/sec, fill rate, PnL, exposure
- **Risk Dashboard:** exposure vs limits, order gatekeeper stats
- **SaaS Dashboard:** subscriptions, revenue, churn
- **Worker Dashboard:** heartbeat, queue depth, DLQ size
- Provisioned via Grafana dashboard JSON files

### Structured Logging
- JSON format with fields: `timestamp`, `level`, `logger`, `message`, `correlation_id`, `extra`
- Correlation ID propagation across requests (middleware)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- No sensitive data in logs (API keys, passwords, tokens)

### OpenTelemetry Tracing
- Auto-instrumentation for FastAPI
- Span propagation for async tasks (event bus, worker jobs)
- Export to Jaeger or Grafana Tempo
- Trace key flows: order placement, grid cycle, recovery sequence

---

## 3. Security

### Secrets Management
- All secrets via environment variables (no hardcoded values)
- `.env.example` template with all required vars documented
- `.env.prod` excluded from git
- Docker secrets or env_file for production

### API Rate Limiting
- Per-endpoint rate limits (auth: 5/min, trading: 100/min, general: 60/min)
- Sliding window via Redis
- 429 response with `Retry-After` header

### Security Headers + CSP
- `Strict-Transport-Security`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy` for frontend
- Configured in Nginx

### Dependency Audit
- `pip audit` for backend
- `npm audit` for frontend
- Fix or document all high/critical vulnerabilities
- Run in CI pipeline

### Container Vulnerability Scan
- Trivy scan on Docker images
- Fail CI on CRITICAL vulnerabilities
- Weekly scheduled scan

### OWASP Top 10 Review
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

---

## 4. Database

### Automated Backup
- `pg_dump` cron job (daily full + hourly incremental via WAL)
- Backup retention: 30 days
- Encrypted backup storage
- Backup verification (restore to test DB)

### Restore Test
- Documented restore procedure
- Monthly restore test to staging
- RTO: <30 minutes, RPO: <1 hour

### Migration Validation
- Alembic migration runs in CI before tests
- `alembic upgrade head` + `alembic downgrade -1` + `alembic upgrade head` (idempotency check)
- Migration on copy of production data (staging)

---

## 5. CI/CD

### GitHub Actions Pipeline

```
Push to develop / main
    ↓
1. Lint (ruff, eslint)
    ↓
2. Test (pytest, vitest)
    ↓
3. Build (Docker images)
    ↓
4. Scan (Trivy)
    ↓
5. Push (to registry)
    ↓
6. Deploy
    ├── develop → staging
    └── main → production (blue-green)
```

### Branch Strategy
- `develop` → auto-deploy to staging
- `main` → manual approval → deploy to production
- Tags (`v0.16.0`, `v1.0.0-rc1`) → release artifacts

### Blue-Green Deployment
- Two production environments (blue/green)
- Health check before switch
- Instant rollback capability
- Zero-downtime switch via Nginx upstream change

---

## 6. Performance Benchmarks

### Load Testing with k6

| Metric                | Target    | Test Scenario |
| --------------------- | --------- | ------------- |
| Trading Instances     | 10,000+   | Create + manage 10k instances via API |
| WebSocket Connections | 5,000+    | Concurrent WS connections with event subscriptions |
| Orders/sec            | 1,000+    | Order placement throughput via execution engine |
| Recovery Time         | <30 sec   | Kill + restart all workers, measure full recovery |
| Dashboard Latency     | <200 ms   | Page load time (LCP) for all dashboard pages |

### Benchmark Report
- k6 test scripts in `tests/load/`
- Results documented in `docs/releases/SPRINT_16_BENCHMARKS.md`
- Include: p50, p95, p99 latencies, error rates, resource usage

---

## 7. Disaster Recovery

### Runbook
- `docs/runbook.md` with:
  - Incident severity levels (SEV1-SEV4)
  - On-call procedures
  - Escalation matrix
  - Common incident response steps
  - Post-mortem template

### Failover Procedure
- Database failover (primary → replica)
- Redis failover (sentinel)
- Worker failover (restart on healthy node)
- Exchange connection failover (primary → backup adapter)

### Recovery Verification
- Simulated disaster test:
  1. Kill all backend containers
  2. Restore from backup
  3. Verify all trading instances recover
  4. Verify no order loss
  5. Verify state consistency
- Document recovery time and data integrity

---

## 8. Post-Sprint 16: Release Candidate Phase

After Sprint 16 completes (v0.16.0):

```
v0.16.0 (Sprint 16 complete)
    ↓
v1.0.0-RC1 (feature freeze, bug fixing)
    ↓
v1.0.0-RC2 (load testing, security pen test)
    ↓
v1.0.0-beta (limited production traffic)
    ↓
v1.0.0 (general availability)
```

**RC/Beta focus:**
- Bug fixing (no new features)
- Load testing under real conditions
- Usability testing
- Security penetration testing
- Stability verification
- Documentation finalization

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

---

## Acceptance Criteria

1. `docker compose -f docker-compose.prod.yml up` starts all services
2. All health check endpoints return 200
3. Prometheus scrapes metrics successfully
4. Grafana dashboards display data
5. CI pipeline passes on develop branch
6. Staging deployment succeeds
7. k6 load tests meet all benchmark targets
8. Trivy scan shows 0 CRITICAL vulnerabilities
9. `pip audit` and `npm audit` show 0 high/critical
10. Backup + restore test succeeds
11. Recovery verification test passes (no data loss)
12. Runbook documented and reviewed
