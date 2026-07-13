# ROADMAP

**Version:** 4.0.0  
**Last Updated:** 2026-07-13  
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
**Status:** ⏳ Pending

**Goals:**
- [ ] Implement `IExecutionEngine` and `ExecutionEngine`
- [ ] Implement order state machine
- [ ] Implement `execute_order` (via exchange adapter)
- [ ] Implement `cancel_order` and `cancel_all_orders`
- [ ] Implement order sync with exchange
- [ ] Implement order fill monitoring
- [ ] Emit order events (`ORDER_PLACED`, `ORDER_FILLED`, `ORDER_CANCELLED`, etc.)
- [ ] Write unit tests with mock exchange
- [ ] Write integration tests with exchange testnet

**Deliverables:**
- Execution engine implementation
- Order state machine
- Order events
- Execution engine tests passing

**Dependencies:** Sprint 05, Sprint 06

---

### Sprint 08: Grid Engine
**Duration:** Week 8  
**Layer:** Grid trading logic  
**Status:** ⏳ Pending

**Goals:**
- [ ] Implement `IGridEngine` and `GridEngine`
- [ ] Implement grid level calculation
- [ ] Implement grid state machine
- [ ] Implement `on_buy_filled` → place sell order
- [ ] Implement `on_sell_filled` → place buy order
- [ ] Implement grid parameter updates (when paused)
- [ ] Implement grid rebalancing
- [ ] Emit grid events (`GRID_CREATED`, `GRID_LEVEL_FILLED`, etc.)
- [ ] Write unit tests for grid calculations
- [ ] Write integration tests for grid cycles

**Deliverables:**
- Grid engine implementation
- Grid state management
- Grid events
- Grid engine tests passing

**Dependencies:** Sprint 06, Sprint 07

---

### Sprint 09: Profit Lock Engine
**Duration:** Week 9  
**Layer:** Profit lock mechanisms  
**Status:** ⏳ Pending

**Goals:**
- [ ] Implement `IProfitLock` and `ProfitLockEngine` (per-position trailing)
- [ ] Implement price/profit monitoring for triggers
- [ ] Implement lock execution (place sell order for ProfitLock)
- [ ] Implement lock level updates (trailing)
- [ ] Emit profit lock events (`PROFIT_LOCK_TRIGGERED`, `PROFIT_LOCK_UPDATED`, `PROFIT_LOCK_EXECUTED`)
- [ ] Write unit tests for trailing logic
- [ ] Write integration tests with price simulation

**Deliverables:**
- Profit lock engine (per-position)
- Trailing stop mechanisms
- Profit lock events
- Profit lock tests passing

**Dependencies:** Sprint 07, Sprint 08

---

### Sprint 10: Strategy Engine
**Duration:** Week 10  
**Layer:** Trading strategy implementations  
**Status:** ⏳ Pending

**Goals:**
- [ ] Implement `IStrategy` base class
- [ ] Implement `SmartGridStrategy`
- [ ] Implement `AdaptiveGridStrategy`
- [ ] Implement `InfinityGridStrategy`
- [ ] Implement `DCAStrategy`
- [ ] Implement strategy parameter validation
- [ ] Implement strategy context and state
- [ ] Write unit tests for each strategy
- [ ] Write integration tests with grid engine

**Deliverables:**
- All 4 strategy implementations
- Strategy parameter validation
- Strategy tests passing

**Dependencies:** Sprint 08, Sprint 09

---

### Sprint 11: Recovery
**Duration:** Week 11  
**Layer:** Error recovery  
**Status:** ⏳ Pending

**Goals:**
- [ ] Implement `IRecoveryEngine` and `RecoveryEngine`
- [ ] Implement state synchronization with exchange
- [ ] Implement order reconciliation
- [ ] Implement grid state rebuild
- [ ] Implement automatic recovery on error
- [ ] Implement manual recovery trigger
- [ ] Emit recovery events (`INSTANCE_RECOVERING, INSTANCE_RECOVERED`, etc.)
- [ ] Write unit tests for reconciliation logic
- [ ] Write integration tests for recovery scenarios

**Deliverables:**
- Recovery engine
- Reconciliation logic
- Recovery events
- Recovery tests passing

**Dependencies:** Sprint 05, Sprint 07, Sprint 08

---

## PHASE 4: STRATEGIES & WORKERS (Weeks 12-13)

### Sprint 12: Workers & Tasks
**Duration:** Week 12  
**Layer:** Background processing  
**Status:** ⏳ Pending

**Goals:**
- [ ] Implement `IWorker` base class
- [ ] Implement `OrderWorker` (order fill monitoring)
- [ ] Implement `PriceWorker` (price update dispatching)
- [ ] Implement `GridWorker` (grid management)
- [ ] Implement `NotificationWorker`
- [ ] Implement `HealthWorker`
- [ ] Set up Celery for task scheduling
- [ ] Implement task definitions
- [ ] Write unit tests for all workers
- [ ] Write integration tests for task processing

**Deliverables:**
- All worker implementations
- Celery task definitions
- Worker tests passing

**Dependencies:** Sprint 04, Sprint 05, Sprint 07

---

## PHASE 5: FRONTEND (Week 13)

### Sprint 13: Frontend
**Duration:** Week 13  
**Layer:** User interface  
**Status:** ⏳ Pending

**Goals:**
- [ ] Set up Next.js project with TailwindCSS
- [ ] Implement authentication pages (login, register)
- [ ] Implement dashboard layout
- [ ] Implement exchange account management UI
- [ ] Implement grid profile management UI
- [ ] Implement Trading Instance management UI
- [ ] Implement order list and details UI
- [ ] Implement portfolio overview UI
- [ ] Implement notification system
- [ ] Implement WebSocket integration for real-time updates
- [ ] Implement Zustand stores
- [ ] Write component tests (vitest)
- [ ] Write E2E tests (Playwright)

**Deliverables:**
- Complete frontend application
- Real-time updates via WebSocket
- Frontend tests passing

**Dependencies:** All backend sprints (01-12)

---

## PHASE 6: DEPLOYMENT & TESTING (Week 14)

### Sprint 14: Deployment & Testing
**Duration:** Week 14  
**Layer:** Production readiness  
**Status:** ⏳ Pending

**Goals:**
- [ ] Set up Kubernetes manifests
- [ ] Configure CI/CD pipeline (GitHub Actions)
- [ ] Set up Docker images for backend and frontend
- [ ] Configure Nginx ingress
- [ ] Set up Prometheus and Grafana monitoring
- [ ] Configure Sentry for error tracking
- [ ] Set up backup automation
- [ ] Perform load testing
- [ ] Perform security audit
- [ ] Deploy to staging
- [ ] Run full E2E test suite on staging
- [ ] Deploy to production (blue-green)
- [ ] Verify production health

**Deliverables:**
- Kubernetes deployment
- CI/CD pipeline
- Monitoring and alerting
- Production deployment
- All tests passing

**Dependencies:** All previous sprints

---

## MILESTONES

| Milestone | Sprint | Description |
|-----------|--------|-------------|
| M1: Foundation Complete | 04 | Core infrastructure, DB, kernel, event bus |
| M2: Exchange Ready | 05 | Can connect to exchanges, manage trading process lifecycle |
| M3: Market & Execution Ready | 07 | Market data hub + order execution engine |
| M4: Trading Engine Complete | 11 | Full trading cycle: grid, execute, profit lock, recover |
| M5: Strategies Ready | 10 | All strategies implemented and tested |
| M6: System Complete | 12 | All backend layers done |
| M7: Product Ready | 13 | Frontend complete |
| M8: Production Live | 14 | Deployed and monitored |

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
