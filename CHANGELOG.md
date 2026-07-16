# Changelog

All notable changes to the UTOS project are documented in this file.
Tags follow semantic versioning: `vMAJOR.MINOR.PATCH[-SPRINT]`.

---

## v0.16.0-16G — Chaos Engineering (2026-07-16)

### Added
- Chaos test suite: 74 tests across 7 scenarios (16G-1 through 16G-7)
- `ChaosExchangeAdapter` mock with configurable failure modes
- `CHAOS_REPORT.md` documenting all chaos scenarios and results
- Infrastructure failure tests (Redis, PostgreSQL, Exchange, DNS, TLS)
- Network chaos tests (latency, packet loss, corruption, partition)
- Container chaos tests (kill/restart, healthchecks)
- Disk chaos tests (disk full, inode exhaustion, permission errors)
- Resource exhaustion tests (CPU, memory, fd limits, thread starvation)
- Exchange chaos tests (timeout, duplicate ACK, partial fill, out-of-order WS)
- Recovery verification tests (no duplicate/orphan orders, position/PnL/exposure)

### Verified
- No duplicate orders across all chaos scenarios
- No orphan orders after recovery
- Position, PnL, and exposure consistency after recovery
- All probabilistic scenarios made deterministic for CI

---

## v0.16.0-16F — Performance (2026)

### Added
- Performance benchmark suite
- Grid engine optimization (< 1ms per cycle)
- Order execution optimization (< 10ms)
- State recovery optimization (< 5s)
- Frontend bundle size optimization

---

## v0.16.0-16E — CI/CD & Blue-Green (2026)

### Added
- CI/CD pipeline (`.github/workflows/`)
- Blue-green deployment configuration
- Staging and production Docker Compose files
- Automated release pipeline

---

## v0.16.0-16D — Database Reliability (2026)

### Added
- Database connection pooling
- Migration automation
- Backup and restore procedures
- Database health monitoring

---

## v0.16.0-16C — Security (2026)

### Added
- OWASP Top 10 security checklist
- JWT authentication hardening
- Rate limiting
- Input validation audit
- Secrets management review

---

## v0.16.0-16B — Observability (2026)

### Added
- Structured logging with `structlog`
- Prometheus metrics collection
- Grafana dashboard configurations
- Alerting rules
- Health check endpoints for all services

---

## v0.16.0-16A — Infrastructure (2026)

### Added
- Docker Compose for all services
- Nginx reverse proxy configuration
- Redis cache layer
- PostgreSQL database with healthchecks
- Service restart policies

---

## v0.15.0 — Frontend Dashboard (2026)

### Added
- Next.js 14 dashboard with React 18
- TailwindCSS styling
- Zustand state management
- Recharts visualizations
- Lucide icons
- Real-time grid engine monitoring
- Portfolio and PnL dashboards

---

## v0.13.0 — Core Platform Complete (2026)

### Added
- Sprint 1: Project setup, configuration, folder structure
- Sprint 2: Database layer (SQLAlchemy models, Alembic migrations, repositories)
- Sprint 3: Authentication & authorization (JWT, RBAC, middleware)
- Sprint 4: Docker & CI/CD foundation
- Sprint 5: Exchange adapter abstraction layer
- Sprint 6: Market Hub (price streaming, order book, candle aggregation)
- Sprint 7: Execution Engine (order placement, tracking, validation)
- Sprint 8: Grid Engine (calculator, planner, state, persistence)
- Sprint 9: Risk Engine (exposure, portfolio, limits)
- Sprint 10: Portfolio Engine (position tracking, PnL)
- Sprint 11: Profit Lock Engine (TP/SL, profit protection)
- Sprint 12: Worker Engine (background tasks, scheduling)
- Sprint 13: Notification Engine (alerts, channels, templates)

### Architecture
- Layered architecture: Application → Trading Process → Strategy Engines → Execution Engine → Market Hub → Exchange Adapter
- Event-driven price updates (no polling)
- Stateless execution engine (no strategy knowledge)
- Recovery Coordinator with connection, state, and reconciliation layers
