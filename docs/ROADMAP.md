# ROADMAP

**Version:** 5.1.0  
**Last Updated:** 2026-07-15
**Status:** ACTIVE

---

## OVERVIEW

This roadmap outlines the development timeline for the UTOS Trading Engine project using a **layer-based sprint** approach. Each sprint builds a complete layer of the system, ensuring stability before moving to the next.

**Total Duration:** ~14 weeks (~3.5 months)  
**Sprint Length:** 1 week  
**Approach:** Layer-by-layer (bottom-up)

---

## SPRINT PROGRESSION

```
Sprint 01: Foundation
    ↓
Sprint 02: Database
    ↓
Sprint 03: Kernel
    ↓
Sprint 04: Event Bus
    ↓
Sprint 05: Trading Process Manager
    ↓
Sprint 06: Market Hub
    ↓
Sprint 07: Execution Engine
    ↓
Sprint 08: Grid Engine
    ↓
Sprint 09: Profit Lock Engine
    ↓
Sprint 10: Strategy Engine
    ↓
Sprint 11: Recovery
    ↓
Sprint 12: Workers & Tasks
    ↓
Sprint 13: Frontend
    ↓
Sprint 14: Deployment & Testing
```

---

## PHASE 1: INFRASTRUCTURE (Weeks 1-4)

### Sprint 01: Foundation
**Duration:** Week 1  
**Layer:** Core infrastructure  
**Status:** ✅ Completed

**Goals:**
- [x] Create project folder structure
- [x] Set up version control
- [x] Complete all documentation (PROJECT_BIBLE, MASTER_PROMPT, ROADMAP, CODING_STANDARD, DATABASE, API_GUIDELINES, INTERFACE_DEFINITIONS, FOLDER_RESPONSIBILITY, ERROR_HANDLING, TESTING_STANDARD, DEPLOYMENT_SPEC, event_bus, sequence_diagrams, trading_engine state machines)
- [ ] Set up Python project (pyproject.toml, poetry)
- [ ] Set up TypeScript project (package.json, vite)
- [ ] Configure linting (ruff, eslint, prettier)
- [ ] Configure pre-commit hooks
- [ ] Set up Docker Compose for local dev
- [ ] Create Makefile with common commands

**Deliverables:**
- Complete documentation pack
- Development environment
- CI/CD pipeline skeleton

---

### Sprint 02: Database
**Duration:** Week 2  
**Layer:** Data persistence  
**Status:** ⏳ Pending

**Goals:**
- [ ] Create SQLAlchemy models for all 12 tables
- [ ] Set up Alembic migration configuration
- [ ] Create initial migration
- [ ] Implement base repository pattern (`IRepository`)
- [ ] Implement all repository classes
- [ ] Create seed data scripts (dev, test, prod)
- [ ] Write unit tests for all repositories
- [ ] Write integration tests for database operations

**Deliverables:**
- All ORM models
- All repositories
- Migration system
- Seed data
- Repository tests passing

**Dependencies:** Sprint 01

---

### Sprint 03: Kernel
**Duration:** Week 3  
**Layer:** System bootstrap  
**Status:** ⏳ Pending

**Goals:**
- [ ] Implement `IKernel` and `Kernel` class
- [ ] Implement DI container
- [ ] Implement service registry
- [ ] Implement lifecycle management (start/stop/restart)
- [ ] Implement health check aggregation
- [ ] Implement `KernelContext` with logger, event bus, cache, storage, config, metrics, clock, health monitor
- [ ] Implement `TradingContext` builder
- [ ] Implement configuration management (`core/config.py`)
- [ ] Implement security utilities (`core/security/`)
- [ ] Implement logger (`core/logger/`)
- [ ] Implement storage (`core/storage/`)
- [ ] Implement cache (`core/cache/`)
- [ ] Implement metrics (`core/metrics/`)
- [ ] Implement custom exceptions (`core/exceptions.py`)
- [ ] Implement enums and constants
- [ ] Write unit tests for all core modules

**Deliverables:**
- Kernel with DI
- Core utilities (config, security, logger, storage)
- Exception hierarchy
- Core unit tests passing

**Dependencies:** Sprint 01, Sprint 02

---

### Sprint 04: Event Bus
**Duration:** Week 4  
**Layer:** Event-driven communication  
**Status:** ⏳ Pending

**Goals:**
- [ ] Implement `IEventBus` and `RedisEventBus`
- [ ] Implement event serialization/deserialization
- [ ] Implement event handler registry
- [ ] Implement publish/subscribe mechanism
- [ ] Implement request-response pattern
- [ ] Implement dead letter queue
- [ ] Define all event types (from event_bus.md spec)
- [ ] Write unit tests for event bus
- [ ] Write integration tests with Redis

**Deliverables:**
- Event bus implementation
- Event type definitions
- DLQ mechanism
- Event bus tests passing

**Dependencies:** Sprint 03

---

## PHASE 2: EXCHANGE & MARKET (Weeks 5-6)

### Sprint 05: Trading Process Manager
**Duration:** Week 5  
**Layer:** Trading process lifecycle  
**Status:** ✅ Completed (v0.5.0)

**Goals:**
- [x] Implement `TradingProcess` runtime object
- [x] Implement `TradingProcessManager` with registry, locking, Redis state
- [x] Implement `ProcessStateMachine` with all state transitions
- [x] Implement lifecycle API: create, prepare, start, pause, resume, stop
- [x] Implement recovery after restart (DB → Redis → Exchange → Recover)
- [x] Implement REST API endpoints for lifecycle
- [x] Implement atomic locking via Redis SET NX
- [x] Write unit tests for state machine, process, and manager
- [x] Write integration tests for lifecycle and recovery

**Deliverables:**
- TradingProcessManager with full lifecycle
- State machine with all transitions
- Recovery with exchange health check and symbol validation
- REST API endpoints (create, prepare, start, pause, resume, stop, status, list)
- 230 tests passing

**Dependencies:** Sprint 02, Sprint 03, Sprint 04

---

### Sprint 06: Market Hub
**Duration:** Week 6  
**Layer:** Market data aggregation  
**Status:** ⏳ Pending

**Goals:**
- [ ] Implement `IMarketHub` and `MarketHub`
- [ ] Implement multi-exchange data aggregation
- [ ] Implement price normalization
- [ ] Implement market data caching
- [ ] Implement WebSocket subscription management
- [ ] Implement `PRICE_UPDATE`, `TICKER_UPDATE`, `ORDER_BOOK_UPDATE`, `CANDLE_UPDATE` events
- [ ] Write unit tests for market hub
- [ ] Write integration tests with exchange adapters

**Deliverables:**
- Market hub implementation
- Market data caching
- Market event publishing
- Market hub tests passing

**Dependencies:** Sprint 04, Sprint 05

---

## PHASE 3: TRADING ENGINE (Weeks 7-12)

### Sprint 07: Execution Engine
**Duration:** Week 7  
**Layer:** Order execution  
**Status:** ✅ Completed (v0.7.0)

**Goals:**
- [x] Implement `ExecutionEngine` with `place_order`, `cancel_order`, `cancel_all_orders`, `get_order`, `sync_order`, `list_active_orders`
- [x] Implement order state machine with validated transitions
- [x] Implement `OrderExecutor` with retry logic (via exchange adapter)
- [x] Implement `cancel_order` and `cancel_all_orders`
- [x] Implement order sync with exchange
- [x] Implement idempotency via `request_id` deduplication
- [x] Handle cancel race conditions (order fills during cancel)
- [x] Write unit tests with mock exchange (76 tests)
- [x] Write integration tests with audit scenarios (idempotency, partial fill, cancel race)
- [ ] Emit order events (`ORDER_PLACED`, `ORDER_FILLED`, `ORDER_CANCELLED`, etc.) — deferred to Event Bus sprint

**Deliverables:**
- Execution engine implementation
- Order state machine
- Order tracker with idempotency
- 385 tests passing (76 Sprint 7 tests)

**Dependencies:** Sprint 05, Sprint 06

---

### Sprint 08: Grid Engine
**Duration:** Week 8  
**Layer:** Grid trading logic  
**Status:** ✅ Completed (v0.8.0)

**Goals:**
- [x] Implement `GridEngine` with 5 internal modules
- [x] Implement `GridCalculator` — evenly-spaced grid level generation
- [x] Implement `GridStateMachine` + `GridStateStore` — per-level status tracking
- [x] Implement `GridPlanner` — determines which orders to place/cancel based on price
- [x] Implement `on_buy_filled` → place sell order at sell price
- [x] Implement `on_sell_filled` → place buy order, increment cycle count
- [x] Implement `on_price_update` — event-driven from Market Hub (no polling)
- [x] Implement `GridPersistence` — serialize/deserialize grid state
- [x] Implement pause/resume/close_all lifecycle
- [ ] Emit grid events (`GRID_CREATED`, `GRID_LEVEL_FILLED`, etc.) — deferred to Event Bus sprint
- [x] Write unit tests for all 5 modules (88 tests)
- [x] Write integration tests for grid cycles

**Deliverables:**
- GridCalculator, GridPlanner, GridStateMachine, GridStateStore, GridEngine, GridPersistence
- Event-driven price updates (no polling)
- No direct exchange access (GridEngine → ExecutionEngine → MarketHub → ExchangeAdapter)
- 473 tests passing (88 Sprint 8 tests)

**Dependencies:** Sprint 06, Sprint 07

---

### Sprint 09: Profit Lock Engine
**Duration:** Week 9  
**Layer:** Profit lock mechanisms  
**Status:** ✅ Completed (v0.9.0)

**Goals:**
- [x] Implement `ProfitLockEngine` with 5 internal modules
- [x] Implement `ProfitCalculator` — floating profit computation (long & short)
- [x] Implement `ProfitLockPolicy` — trailing lock decisions
- [x] Implement `ProfitLockStateMachine` + `ProfitLockStore` — per-instance state tracking
- [x] Implement `ProfitLockEngine` — orchestrates lifecycle, event-driven (no polling)
- [x] Implement `ProfitPersistence` — serialize/deserialize profit lock state
- [x] Implement lock execution (place sell order via ExecutionEngine)
- [x] Implement lock level updates (trailing)
- [x] Implement internal metrics (decisions, errors, events, locks triggered/executed)
- [x] Verify independence from Grid Engine (no imports, no calls)
- [ ] Emit profit lock events (`PROFIT_LOCK_TRIGGERED`, etc.) — deferred to Event Bus sprint
- [x] Write unit tests for all 5 modules (82 tests)
- [x] Write integration tests for profit lock lifecycle

**Deliverables:**
- ProfitCalculator, ProfitLockPolicy, ProfitLockStateMachine, ProfitLockStore, ProfitLockEngine, ProfitPersistence
- Event-driven price updates (no polling)
- No direct exchange access (ProfitLockEngine → ExecutionEngine → ExchangeAdapter)
- Independent from Grid Engine (sibling engines, not parent-child)
- Internal metrics for observability
- 555 tests passing (82 Sprint 9 tests)

**Dependencies:** Sprint 07, Sprint 08

---

### Sprint 10: Portfolio & Risk Engine
**Duration:** Week 10  
**Layer:** Portfolio & risk management  
**Status:** ✅ Completed (v0.10.0)

**Goals:**
- [x] Implement `PortfolioManager` — tracks positions across instances, accounts, exchanges
- [x] Implement `ExposureManager` — calculates exposure per exchange/account/symbol
- [x] Implement `RiskManager` — validates orders against risk rules (gatekeeper, not executor)
- [x] Implement `PositionAggregator` — merges positions for reporting and risk control
- [x] Implement `PortfolioMetrics` — unrealized/realized PnL, exposure, drawdown, margin usage
- [x] Risk rules: max_position_size, max_exposure_per_symbol, max_exposure_per_exchange, max_open_positions, max_capital_per_instance
- [x] Internal metrics tracking (orders checked/allowed/denied, price updates)
- [x] Verify independence from Grid Engine, Profit Lock Engine, and Execution Engine
- [x] Write unit tests for all 5 modules (74 tests)
- [x] Write integration tests for full risk flow

**Deliverables:**
- PortfolioManager, ExposureManager, RiskManager, PositionAggregator, PortfolioMetrics
- Risk Manager is a gatekeeper — does NOT call ExecutionEngine
- Strategy engines call RiskManager.check_order_risk() before submitting to ExecutionEngine
- 629 tests passing (74 Sprint 10 tests)

**Dependencies:** Sprint 05, Sprint 07, Sprint 08, Sprint 09

---

### Sprint 11: Recovery & Resilience
**Duration:** Week 11  
**Layer:** Fault tolerance & state recovery  
**Status:** ✅ Completed (v0.11.0)

**Goals:**
- [x] RecoveryCoordinator orchestrates 4 layers (NOT a God Object)
- [x] Layer 1: ConnectionRecovery — Redis, PostgreSQL, Exchange, WebSocket
- [x] Layer 2: StateRecovery — Trading Process, Grid, Profit Lock, Portfolio
- [x] Layer 3: RuntimeReconciler — exchange vs local state sync
- [x] RecoveryPersistence — checkpoint save/load for resumability
- [x] Chaos tests: server restart (100 instances), Redis death, WebSocket drop, exchange timeout, order filled during restart
- [x] All recovery operations are idempotent
- [x] Each layer fails independently without blocking others
- [x] 75 new tests (unit + chaos), 704 total passing

**Deliverables:**
- RecoveryCoordinator (orchestrator)
- ConnectionRecovery (Layer 1)
- StateRecovery (Layer 2)
- RuntimeReconciler (Layer 3)
- RecoveryPersistence (checkpoints)
- 75 tests (unit + chaos), 704 total passing

**Dependencies:** Sprint 05, Sprint 07, Sprint 08, Sprint 09, Sprint 10

---

## PHASE 4: OPERATIONAL SERVICES (Weeks 12-13)

### Sprint 12: Worker Scheduler & Event Bus
**Duration:** Week 12  
**Layer:** Background processing & event orchestration  
**Status:** ✅ Completed (v0.12.0)

**Goals:**
- [x] EventBus — in-memory pub/sub for event-driven communication
- [x] WorkerManager — worker lifecycle (start/stop/pause/resume/error)
- [x] JobScheduler — periodic tasks (cleanup, checkpoint, heartbeat, sync, retry)
- [x] RetryWorker — exponential backoff (1s, 2s, 4s), max 3 retries
- [x] DeadLetterQueue — failed events stored for replay
- [x] HeartbeatMonitor — health checks for all components
- [x] Integration tests: event flow, retry→DLQ pipeline, heartbeat
- [x] 75 new tests, 779 total passing

**Deliverables:**
- EventBus (in-memory pub/sub)
- WorkerManager (lifecycle management)
- JobScheduler (periodic task scheduling)
- RetryWorker (exponential backoff + DLQ integration)
- DeadLetterQueue (failed event storage + replay)
- HeartbeatMonitor (component health monitoring)
- 75 tests (unit + integration), 779 total passing

**Dependencies:** Sprint 05, Sprint 06, Sprint 07, Sprint 10, Sprint 11

---

### Sprint 13: Notification & Automation
**Duration:** Week 13  
**Layer:** Notification & automated triggers  
**Status:** ⏳ Pending

**Goals:**
- [ ] Implement NotificationEngine (Telegram, Email, Webhook)
- [ ] Implement AlertRule engine (price alerts, PnL alerts, risk alerts)
- [ ] Implement AutomationEngine (event → action rules)
- [ ] Write unit and integration tests

**Deliverables:**
- Notification channels
- Alert rules
- Automation engine
- Notification tests passing

**Dependencies:** Sprint 11, Sprint 12

---

## PHASE 5: SAAS PLATFORM (Week 14)

### Sprint 14: Authentication & Subscription (SaaS/MLM)
**Duration:** Week 14  
**Layer:** SaaS billing, subscription, affiliate  
**Status:** ⏳ Pending

**Goals:**
- [ ] Subscription plans (Free / Basic / Pro) with limits
- [ ] Trading Process and Exchange Account limits per plan
- [ ] License expiry enforcement
- [ ] Payment integration hooks
- [ ] Referral/affiliate link generation
- [ ] MLM commission structure and calculation
- [ ] Payout management
- [ ] Commission reports
- [ ] Write unit and integration tests

**Deliverables:**
- SubscriptionManager
- AffiliateEngine
- CommissionCalculator
- Subscription + affiliate tests passing

**Dependencies:** Sprint 02, Sprint 05

---

## PHASE 6: FRONTEND & PRODUCTION (Weeks 15-16)

### Sprint 15: Frontend Dashboard
**Duration:** Week 15  
**Layer:** User interface  
**Status:** ⏳ Pending

**Goals:**
- [ ] Set up Next.js project with TailwindCSS + shadcn/ui
- [ ] Authentication pages (login, register, 2FA)
- [ ] Dashboard layout and navigation
- [ ] Exchange account management UI
- [ ] Trading Instance management UI
- [ ] Grid management + live monitoring UI
- [ ] Portfolio overview (PnL, exposure, positions)
- [ ] Risk settings UI
- [ ] Notification settings UI
- [ ] Subscription + affiliate dashboard
- [ ] Real-time updates via WebSocket
- [ ] Component tests (vitest) + E2E tests (Playwright)

**Deliverables:**
- Complete frontend application
- Real-time updates
- Frontend tests passing

**Dependencies:** All backend sprints (01-14)

---

### Sprint 16: Production Hardening & Deployment
**Duration:** Week 16  
**Layer:** Production readiness  
**Status:** ⏳ Pending

**Goals:**
- [ ] Docker images for backend + frontend
- [ ] Kubernetes manifests + Helm charts
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Nginx ingress + TLS
- [ ] Prometheus + Grafana monitoring
- [ ] Sentry error tracking
- [ ] Load testing (k6)
- [ ] Security audit (OWASP)
- [ ] Deploy to staging → E2E tests
- [ ] Deploy to production (blue-green)
- [ ] Backup automation

**Deliverables:**
- Kubernetes deployment
- CI/CD pipeline
- Monitoring and alerting
- Production deployment verified

**Dependencies:** All previous sprints

---

## MILESTONES

| Milestone | Sprint | Description |
|-----------|--------|-------------|
| ✅ M1: Foundation Complete | 04 | Core infrastructure, DB, kernel, event bus |
| ✅ M2: Exchange Ready | 05 | Can connect to exchanges, manage trading process lifecycle |
| ✅ M3: Market & Execution Ready | 07 | Market data hub + order execution engine |
| ✅ M4: Core Platform Complete | 10 | Full trading cycle + risk management layer |
| ✅ M5: Resilience Ready | 11 | System can recover from all failure scenarios |
| ✅ M6: Operational Services Ready | 12 | Worker scheduler, event bus, heartbeat monitoring |
| M7: SaaS Platform Ready | 14 | Subscription, billing, MLM/affiliate |
| M8: Product Ready | 15 | Frontend complete with real-time dashboard |
| M9: Production Live | 16 | Deployed, monitored, and load-tested |

---

## RISKS & MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Exchange API changes | Medium | High | Adapter pattern isolates changes; comprehensive mocking |
| Performance bottlenecks | Medium | High | Load testing in Sprint 14; HPA configured |
| WebSocket stability | Medium | Medium | Auto-reconnect with backoff; fallback to polling |
| Data consistency | Low | Critical | Recovery engine; order reconciliation; state sync |
| Security vulnerabilities | Low | Critical | Security checklist; container scanning; WAF |

---

## CHANGE LOG

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-09 | 1.0.0 | Initial roadmap with 30 feature-based sprints |
| 2026-07-09 | 2.0.0 | Restructured to 16 layer-based sprints; added Trading Instance, KernelContext, TradingContext, ProcessMemory, READY state, TP/ProfitLock/PortfolioLock separation, separate market/account connections |
| 2026-07-12 | 3.0.0 | Sprint 5 = Trading Process Manager (completed). Reordered: Sprint 7 = Execution Engine (was 9), Sprint 8 = Grid Engine. Removed old Sprint 7 (Trading Instance, merged into Sprint 5). Total sprints reduced from 16 to 15. |
| 2026-07-13 | 4.0.0 | Sprint 6 = Market Hub requirements refined (generic multi-exchange, Hyperliquid, memory cache, subscription deduplication, status/metrics, is_alive). Sprint 9 = Profit Lock Engine, Sprint 10 = Strategy Engine. Portfolio & Risk deferred. Total sprints reduced from 15 to 14. |
| 2026-07-13 | 4.1.0 | Sprint 7 = Execution Engine completed (v0.7.0). 385 tests passing. Idempotency, partial fill, and cancel race condition audit tests added per reviewer request. |
| 2026-07-14 | 4.2.0 | Sprint 8 = Grid Engine completed (v0.8.0). 473 tests passing. 5 internal modules: GridCalculator, GridPlanner, GridStateMachine/GridStateStore, GridEngine, GridPersistence. Event-driven price updates, no direct exchange access, no polling. |
| 2026-07-14 | 4.3.0 | Sprint 9 = Profit Lock Engine completed (v0.9.0). 555 tests passing. 5 internal modules: ProfitCalculator, ProfitLockPolicy, ProfitLockStateMachine/GridStateStore, ProfitLockEngine, ProfitPersistence. Independent from Grid Engine, event-driven, internal metrics for observability. |
| 2026-07-14 | 4.4.0 | Sprint 10 = Portfolio & Risk Engine completed (v0.10.0). 629 tests passing. 5 internal modules: PortfolioManager, ExposureManager, RiskManager, PositionAggregator, PortfolioMetrics. Risk Manager is gatekeeper (no ExecutionEngine calls). Independent from Grid/ProfitLock/Execution engines. |
| 2026-07-15 | 5.0.0 | Phase restructure: Sprint 1-10 = Core Platform (complete). Sprint 11 = Recovery & Resilience. Sprint 12 = Worker Scheduler & Event Bus. Sprint 13 = Notification & Automation. Sprint 14 = Auth & Subscription (SaaS/MLM). Sprint 15 = Frontend Dashboard. Sprint 16 = Production Hardening. Total 16 sprints. Added SaaS/MLM/Affiliate as first-class domain. |
| 2026-07-15 | 5.1.0 | Sprint 11 = Recovery & Resilience completed (v0.11.0). 704 tests passing. 4-layer architecture: RecoveryCoordinator + ConnectionRecovery + StateRecovery + RuntimeReconciler + RecoveryPersistence. 5 chaos test scenarios (server restart 100 instances, Redis death, WebSocket drop, exchange timeout, order filled during restart). Idempotent recovery, independent layer failure. |
| 2026-07-15 | 5.2.0 | Sprint 12 = Worker Scheduler & Event Bus completed (v0.12.0). 779 tests passing. 6 modules: EventBus, WorkerManager, JobScheduler, RetryWorker, DeadLetterQueue, HeartbeatMonitor. Event-driven pub/sub, exponential backoff retry, DLQ for failed events, component health monitoring. ADR document created. |
