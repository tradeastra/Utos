# Go-Live Checklist

**Date:** 2026-07-17  
**Purpose:** Operational checklist yang harus dipenuhi sebelum deployment ke production  
**Target:** v1.0.0 release

---

## Overview

Dokumen ini adalah acuan akhir sebelum melakukan go-live ke production. Setiap item harus diverifikasi dan ditandai sebelum tag `v1.0.0` dibuat.

---

## 1. Environment Configuration

| # | Item | Status | Verification | Notes |
|---|------|--------|--------------|-------|
| 1 | Production `.env` file configured | ⬜ | All required vars present | No default passwords |
| 2 | `SECRET_KEY` is strong and unique | ⬜ | 32+ random bytes | Not from dev/staging |
| 3 | `POSTGRES_PASSWORD` is strong | ⬜ | 16+ random chars | Not default value |
| 4 | `REDIS_PASSWORD` set | ⬜ | Non-empty | If Redis exposed |
| 5 | `EXCHANGE_API_KEY` configured | ⬜ | Valid production key | Not sandbox key |
| 6 | `EXCHANGE_API_SECRET` configured | ⬜ | Valid production secret | Not sandbox secret |
| 7 | `EXCHANGE_TESTNET` = false | ⬜ | Production mode | Not testnet |
| 8 | `APP_ENV` = production | ⬜ | Production mode | |
| 9 | `DEBUG` = false | ⬜ | No debug output | |
| 10 | `LOG_FORMAT` = json | ⬜ | Structured logging | |
| 11 | `CORS_ORIGINS` set correctly | ⬜ | Production domain only | Not wildcard |

---

## 2. Domain, TLS, DNS

| # | Item | Status | Verification | Notes |
|---|------|--------|--------------|-------|
| 1 | Production domain registered | ⬜ | DNS resolves | |
| 2 | TLS certificate active | ⬜ | Valid > 30 days | Let's Encrypt or paid CA |
| 3 | TLS certificate auto-renewal | ⬜ | Cron/certbot configured | |
| 4 | HTTPS redirect configured | ⬜ | HTTP → HTTPS | Nginx config |
| 5 | HSTS header enabled | ⬜ | Strict-Transport-Security | |
| 6 | DNS records correct | ⬜ | A/CNAME pointing to server | |
| 7 | Subdomains configured | ⬜ | api., app., grafana. | If applicable |

---

## 3. Database

| # | Item | Status | Verification | Notes |
|---|------|--------|--------------|-------|
| 1 | PostgreSQL running | ⬜ | `pg_isready` returns OK | |
| 2 | Migrations applied | ⬜ | `alembic upgrade head` | |
| 3 | Connection pool sized correctly | ⬜ | Max connections < PostgreSQL max | |
| 4 | Backup schedule active | ⬜ | Cron or pg_cron configured | |
| 5 | Backup tested (restore) | ⬜ | Restore to test DB successful | |
| 6 | WAL archiving enabled | ⬜ | Point-in-time recovery | |
| 7 | Database monitoring active | ⬜ | Prometheus postgres exporter | |

---

## 4. Redis

| # | Item | Status | Verification | Notes |
|---|------|--------|--------------|-------|
| 1 | Redis running | ⬜ | `redis-cli ping` returns PONG | |
| 2 | Maxmemory configured | ⬜ | 256mb+ with LRU eviction | |
| 3 | Persistence enabled | ⬜ | RDB or AOF | |
| 4 | Redis password set | ⬜ | AUTH required | If exposed |
| 5 | Redis monitoring active | ⬜ | Prometheus redis exporter | |

---

## 5. Monitoring & Alerting

| # | Item | Status | Verification | Notes |
|---|------|--------|--------------|-------|
| 1 | Prometheus scraping | ⬜ | `/metrics` endpoint returns data | |
| 2 | Grafana dashboards loaded | ⬜ | System, trading, infrastructure | |
| 3 | Tempo tracing active | ⬜ | OTEL exporter receiving data | |
| 4 | Alert: high latency | ⬜ | p99 > 1000ms for 5min | |
| 5 | Alert: high error rate | ⬜ | > 1% for 5min | |
| 6 | Alert: database down | ⬜ | PostgreSQL unreachable | |
| 7 | Alert: Redis down | ⬜ | Redis unreachable | |
| 8 | Alert: backup failure | ⬜ | Backup not completed in 24h | |
| 9 | Alert: recovery triggered | ⬜ | Unexpected recovery event | |
| 10 | Alert: memory pressure | ⬜ | > 90% of container limit | |
| 11 | Alert: disk space | ⬜ | > 85% disk usage | |
| 12 | Alert notification channel | ⬜ | Slack/email/PagerDuty configured | |

---

## 6. Deployment

| # | Item | Status | Verification | Notes |
|---|------|--------|--------------|-------|
| 1 | Docker images built | ⬜ | Tagged with v1.0.0 | |
| 2 | Images pushed to registry | ⬜ | GHCR or private registry | |
| 3 | Blue-green config ready | ⬜ | `docker-compose.bluegreen.yml` | |
| 4 | Nginx config verified | ⬜ | Upstream, TLS, health check | |
| 5 | Smoke test passes | ⬜ | `scripts/smoke-test.sh` all green | |
| 6 | Rollback procedure tested | ⬜ | Switch green→blue successful | |
| 7 | Automatic rollback armed | ⬜ | Monitor script running | |
| 8 | Zero-downtime switch verified | ⬜ | No 5xx during switch | |

---

## 7. Security

| # | Item | Status | Verification | Notes |
|---|------|--------|--------------|-------|
| 1 | No hardcoded secrets in repo | ⬜ | Secret scan clean | |
| 2 | All secrets via environment | ⬜ | No secrets in code/config files | |
| 3 | JWT secret is production-grade | ⬜ | 32+ random bytes | |
| 4 | Rate limiting active | ⬜ | Auth + API endpoints | |
| 5 | CORS restricted to production domain | ⬜ | No wildcard origins | |
| 6 | HTTPS enforced | ⬜ | No HTTP endpoints exposed | |
| 7 | Container security hardened | ⬜ | no-new-privileges, cap_drop ALL | |
| 8 | Network isolation | ⬜ | frontend-net / backend-net separate | |
| 9 | pip-audit: no unaccepted Critical/High | ⬜ | See ACCEPTED_RISKS.md | |
| 10 | npm audit: no unaccepted Critical/High | ⬜ | See ACCEPTED_RISKS.md | |
| 11 | SBOM generated and attached to release | ⬜ | SPDX + CycloneDX via Syft | `scripts/generate-sbom.sh v1.0.0` |

---

## 8. Backup & Disaster Recovery

| # | Item | Status | Verification | Notes |
|---|------|--------|--------------|-------|
| 1 | Database backup automated | ⬜ | Cron job or pg_cron | |
| 2 | Backup retention policy | ⬜ | 7 daily + 4 weekly | |
| 3 | Backup encryption | ⬜ | At rest | |
| 4 | Restore procedure documented | ⬜ | Step-by-step runbook | |
| 5 | Restore tested | ⬜ | Verified on test environment | |
| 6 | Redis backup | ⬜ | RDB snapshot scheduled | |
| 7 | Configuration backup | ⬜ | .env, nginx.conf, docker-compose | |
| 8 | RTO defined | ⬜ | Recovery Time Objective | |
| 9 | RPO defined | ⬜ | Recovery Point Objective | |

---

## 9. Operations Runbook

| # | Item | Status | Location | Notes |
|---|------|--------|----------|-------|
| 1 | Server restart procedure | ⬜ | `docs/operations/` | |
| 2 | Database failover procedure | ⬜ | `docs/operations/` | |
| 3 | Recovery procedure | ⬜ | `docs/operations/` | |
| 4 | Rollback procedure | ⬜ | `docs/operations/` | |
| 5 | Exchange reconnect procedure | ⬜ | `docs/operations/` | |
| 6 | Alert response procedures | ⬜ | `docs/operations/` | |
| 7 | On-call rotation | ⬜ | Team schedule | |
| 8 | Incident escalation | ⬜ | Escalation matrix | |

---

## 10. Final Validation

| # | Item | Status | Verification | Notes |
|---|------|--------|--------------|-------|
| 1 | Full test suite passes | ⬜ | 1100+ tests, 0 failures | |
| 2 | Chaos suite passes | ⬜ | 74 tests, 0 failures | |
| 3 | Benchmark within targets | ⬜ | Grid < 1ms, Execution < 10ms | |
| 4 | Soak test 72h clean | ⬜ | No memory/resource leak | |
| 5 | Sandbox trading all scenarios | ⬜ | 12/12 scenarios pass | |
| 6 | Beta exit criteria met | ⬜ | See BETA_CHECKLIST.md | |
| 7 | Accepted risks documented | ⬜ | See ACCEPTED_RISKS.md | |
| 8 | CHANGELOG updated | ⬜ | v1.0.0 entry | |
| 9 | Release notes written | ⬜ | `docs/releases/v1.0.0.md` | |
| 10 | Git tag v1.0.0 ready | ⬜ | On main branch, clean state | |

---

## Go-Live Decision

| Role | Name | Decision | Date |
|------|------|----------|------|
| Engineering Lead | — | ⬜ Go / ⬜ No-Go | — |
| Architecture Lead | — | ⬜ Go / ⬜ No-Go | — |
| Security Lead | — | ⬜ Go / ⬜ No-Go | — |
| Operations Lead | — | ⬜ Go / ⬜ No-Go | — |
| Product Owner | — | ⬜ Go / ⬜ No-Go | — |

**Unanimous Go → tag v1.0.0 → deploy to production**

---

## Post Go-Live

| # | Item | Status | Timeframe | Notes |
|---|------|--------|-----------|-------|
| 1 | Monitor closely | ⬜ | First 24h | Watch all alerts |
| 2 | Verify production telemetry | ⬜ | First 1h | Prometheus/Grafana receiving |
| 3 | Verify first backup | ⬜ | First 24h | Backup completed successfully |
| 4 | Verify first recovery drill | ⬜ | First 7 days | Scheduled recovery test |
| 5 | Retrospective | ⬜ | First 7 days | Lessons learned |
