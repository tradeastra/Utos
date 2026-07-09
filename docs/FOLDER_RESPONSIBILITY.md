# FOLDER RESPONSIBILITY

**Version:** 1.0.0  
**Last Updated:** 2026-07-09  
**Status:** DRAFT

---

## 1. OVERVIEW

This document defines strict boundaries for every folder in the UTOS project. Each folder has a single responsibility. Code that does not belong in a folder **must not** be placed there.

### 1.1 Why This Matters

- **Prevents spaghetti code**: Clear boundaries stop modules from bleeding into each other
- **Enables parallel development**: Developers can work on different folders without conflicts
- **Simplifies testing**: Each folder has its own test strategy
- **Reduces coupling**: Folders communicate only through defined interfaces
- **Aids onboarding**: New developers know exactly where to look

### 1.2 Enforcement

- Code reviews must check folder placement
- Linting rules (ruff/pylint) enforce import boundaries
- CI pipeline runs a folder-structure validator
- Any violation is a **blocking review comment**

---

## 2. ROOT STRUCTURE

```
utos/
├── backend/           # Python backend (FastAPI)
├── frontend/          # TypeScript frontend (Next.js)
├── docs/              # All project documentation
├── infrastructure/    # Docker, Kubernetes, Nginx configs
├── scripts/           # Utility scripts (setup, migration, deploy)
├── tests/             # Integration & E2E tests
├── tools/             # Development tools and generators
├── .github/           # CI/CD workflows
├── docker-compose.yml # Local development environment
├── Makefile           # Common commands
└── README.md          # Project overview
```

---

## 3. BACKEND FOLDER RULES

### 3.1 Structure

```
backend/
├── adapters/          # Exchange API adapters ONLY
├── api/               # REST API routes ONLY
├── app/               # FastAPI app configuration ONLY
├── core/              # Cross-cutting concerns ONLY
├── database/          # Database setup and migrations ONLY
├── engine/            # Business logic ONLY
├── events/            # Event bus implementation ONLY
├── kernel/            # System bootstrap and DI ONLY
├── market/            # Market data aggregation ONLY
├── models/            # SQLAlchemy ORM models ONLY
├── plugins/           # Plugin system ONLY
├── repositories/      # Data access layer ONLY
├── schemas/           # Pydantic request/response schemas ONLY
├── services/          # External service integrations ONLY
├── strategies/        # Trading strategy implementations ONLY
├── tasks/             # Celery task definitions ONLY
├── utils/             # Pure utility functions ONLY
├── workers/           # Background workers ONLY
└── main.py            # Application entry point
```

### 3.2 Folder Rules

#### `adapters/`

**MAY contain**:
- Exchange adapter implementations (Binance, Bybit, OKX, etc.)
- Exchange-specific data transformations
- Exchange WebSocket handlers
- Rate limiting per exchange

**MUST NOT contain**:
- Business logic
- Database queries
- API route definitions
- Trading strategy logic

**Allowed imports from**: `core/`, `events/`, `models/` (read-only)

```
adapters/
├── __init__.py
├── base.py            # IExchangeAdapter abstract class
├── binance/
│   ├── __init__.py
│   ├── adapter.py     # BinanceExchangeAdapter
│   ├── websocket.py   # Binance WebSocket client
│   └── mapper.py      # Binance data mapper
├── bybit/
│   ├── __init__.py
│   ├── adapter.py
│   ├── websocket.py
│   └── mapper.py
└── okx/
    ├── __init__.py
    ├── adapter.py
    ├── websocket.py
    └── mapper.py
```

---

#### `api/`

**MAY contain**:
- FastAPI route definitions (routers)
- Request/response handling
- Input validation (delegated to schemas)
- API-level middleware
- API dependency injection

**MUST NOT contain**:
- Business logic (delegate to `engine/`)
- Database queries (delegate to `repositories/`)
- Exchange API calls (delegate to `adapters/`)
- Complex calculations

**Allowed imports from**: `engine/`, `schemas/`, `core/`, `repositories/`

```
api/
├── __init__.py
├── v1/
│   ├── __init__.py
│   ├── router.py          # Main v1 router aggregation
│   ├── auth.py            # /auth endpoints
│   ├── users.py           # /users endpoints
│   ├── exchange_accounts.py
│   ├── trading_processes.py
│   ├── orders.py
│   ├── portfolio.py
│   ├── strategies.py
│   ├── grid_profiles.py
│   ├── notifications.py
│   └── admin.py
├── middleware/
│   ├── __init__.py
│   ├── auth.py            # JWT authentication middleware
│   ├── rate_limit.py      # Rate limiting middleware
│   └── error_handler.py   # Global error handler
└── dependencies.py        # FastAPI dependency providers
```

---

#### `app/`

**MAY contain**:
- FastAPI app instance creation
- App-level configuration
- Router registration
- Middleware registration
- Startup/shutdown event handlers

**MUST NOT contain**:
- Route definitions (those go in `api/`)
- Business logic
- Database queries

**Allowed imports from**: `api/`, `core/`, `kernel/`

```
app/
├── __init__.py
└── main.py            # create_app() function
```

---

#### `core/`

**MAY contain**:
- Configuration management
- Security utilities (JWT, encryption, hashing)
- Exception definitions
- Base classes shared across modules
- Constants and enums
- Logger implementation
- Storage implementation

**MUST NOT contain**:
- Business logic
- Database models
- API routes
- Exchange-specific code

**Allowed imports from**: (none — this is the foundation layer)

```
core/
├── __init__.py
├── config.py          # Settings via pydantic-settings
├── exceptions.py      # Custom exception hierarchy
├── enums.py           # Shared enums
├── constants.py       # Project-wide constants
├── security/
│   ├── __init__.py
│   ├── jwt.py         # JWT token utilities
│   ├── crypto.py      # Encryption/decryption
│   └── hashing.py     # Password hashing
├── logger/
│   ├── __init__.py
│   ├── base.py        # ILogger interface
│   └── implementation.py
└── storage/
    ├── __init__.py
    ├── base.py        # IStorage interface
    ├── local.py       # Local storage
    └── s3.py          # S3 storage
```

---

#### `database/`

**MAY contain**:
- Database engine setup
- Session factory
- Alembic configuration
- Migration scripts
- Seed data scripts

**MUST NOT contain**:
- ORM models (those go in `models/`)
- Repository implementations (those go in `repositories/`)
- Business logic

**Allowed imports from**: `core/`, `models/`

```
database/
├── __init__.py
├── engine.py          # Engine and session factory
├── base.py            # Declarative base
└── seed/
    ├── __init__.py
    ├── dev/
    │   └── seed_all.py
    └── prod/
        └── seed_initial.py
```

---

#### `engine/`

**MAY contain**:
- Trading engine logic
- Grid engine logic
- Execution engine logic
- Portfolio engine logic
- Risk engine logic
- Profit lock engine logic
- Recovery engine logic
- State machine implementations

**MUST NOT contain**:
- API route definitions
- Database models (use `models/`)
- Exchange API calls (use `adapters/` via interface)
- Pydantic schemas
- Celery task definitions

**Allowed imports from**: `adapters/` (via interface), `core/`, `events/`, `models/`, `repositories/`, `market/` (via interface)

```
engine/
├── __init__.py
├── base.py                # ITradingEngine interface
├── trading_engine.py      # TradingEngine implementation
├── grid/
│   ├── __init__.py
│   ├── base.py            # IGridEngine interface
│   ├── engine.py          # GridEngine implementation
│   └── state.py           # Grid state management
├── execution/
│   ├── __init__.py
│   ├── base.py            # IExecutionEngine interface
│   └── engine.py          # ExecutionEngine implementation
├── portfolio/
│   ├── __init__.py
│   ├── base.py            # IPortfolio interface
│   └── engine.py          # PortfolioEngine implementation
├── risk/
│   ├── __init__.py
│   ├── base.py            # IRiskEngine interface
│   └── engine.py          # RiskEngine implementation
├── profit_lock/
│   ├── __init__.py
│   ├── base.py            # IProfitLock interface
│   └── engine.py          # ProfitLockEngine implementation
└── recovery/
    ├── __init__.py
    ├── base.py            # IRecoveryEngine interface
    └── engine.py          # RecoveryEngine implementation
```

---

#### `events/`

**MAY contain**:
- Event bus implementation (Redis pub/sub)
- Event definitions and schemas
- Event handler registration
- Event serialization/deserialization

**MUST NOT contain**:
- Business logic
- Database queries
- API routes

**Allowed imports from**: `core/`

```
events/
├── __init__.py
├── base.py              # IEventBus interface
├── bus.py               # RedisEventBus implementation
├── types.py             # Event type constants
├── serializer.py        # Event serialization
└── handlers.py          # Event handler registry
```

---

#### `kernel/`

**MAY contain**:
- System bootstrap
- Dependency injection container
- Service registry
- Lifecycle management (start/stop/restart)
- Health check aggregation

**MUST NOT contain**:
- Business logic
- API routes
- Database queries

**Allowed imports from**: All folders (this is the composition root)

```
kernel/
├── __init__.py
├── base.py              # IKernel interface
├── kernel.py            # Kernel implementation
├── container.py         # DI container
├── registry.py          # Service registry
└── lifecycle.py         # Lifecycle management
```

---

#### `market/`

**MAY contain**:
- Market data aggregation
- Price normalization
- Multi-exchange data merging
- Market data caching
- WebSocket subscription management

**MUST NOT contain**:
- Business logic (trading decisions)
- Database models
- API routes
- Order placement

**Allowed imports from**: `adapters/` (via interface), `core/`, `events/`

```
market/
├── __init__.py
├── base.py              # IMarketHub interface
├── hub.py               # MarketHub implementation
├── normalizer.py        # Data normalization
└── cache.py             # Market data cache
```

---

#### `models/`

**MAY contain**:
- SQLAlchemy ORM model definitions
- Model relationships
- Model-level validations (not business validations)

**MUST NOT contain**:
- Business logic
- Database queries (those go in `repositories/`)
- API routes
- Pydantic schemas

**Allowed imports from**: `core/` (enums, constants only)

```
models/
├── __init__.py
├── user.py
├── exchange_account.py
├── trading_process.py
├── order.py
├── position.py
├── grid_profile.py
├── strategy.py
├── transaction.py
├── subscription.py
├── affiliate.py
├── notification.py
└── balance.py
```

---

#### `plugins/`

**MAY contain**:
- Plugin system implementation
- Plugin loading and unloading
- Plugin API definitions

**MUST NOT contain**:
- Core business logic
- Database models
- API routes

**Allowed imports from**: `core/`, `engine/` (via interface)

```
plugins/
├── __init__.py
├── base.py              # Plugin base class
├── manager.py           # Plugin manager
└── registry.py          # Plugin registry
```

---

#### `repositories/`

**MAY contain**:
- Repository implementations (data access)
- Query builders
- Data access optimizations (eager loading, etc.)

**MUST NOT contain**:
- Business logic
- API routes
- Pydantic schemas
- Exchange API calls

**Allowed imports from**: `models/`, `core/`, `database/`

```
repositories/
├── __init__.py
├── base.py              # IRepository generic base
├── user_repository.py
├── exchange_account_repository.py
├── trading_process_repository.py
├── order_repository.py
├── position_repository.py
├── grid_profile_repository.py
├── strategy_repository.py
├── transaction_repository.py
├── subscription_repository.py
├── notification_repository.py
└── balance_repository.py
```

---

#### `schemas/`

**MAY contain**:
- Pydantic request models
- Pydantic response models
- Input validation schemas
- API response wrappers

**MUST NOT contain**:
- Business logic
- Database queries
- Exchange API calls
- SQLAlchemy models

**Allowed imports from**: `core/` (enums, constants only)

```
schemas/
├── __init__.py
├── common.py            # Shared schemas (pagination, errors)
├── auth.py              # Auth request/response schemas
├── user.py              # User schemas
├── exchange_account.py
├── trading_process.py
├── order.py
├── portfolio.py
├── strategy.py
├── grid_profile.py
├── notification.py
└── admin.py
```

---

#### `services/`

**MAY contain**:
- External service integrations (email, SMS, payment)
- Third-party API clients
- Service-specific business logic that is NOT trading-related

**MUST NOT contain**:
- Trading logic (goes in `engine/`)
- Database models
- API routes
- Exchange adapters

**Allowed imports from**: `core/`, `events/`, `repositories/`

```
services/
├── __init__.py
├── notification/
│   ├── __init__.py
│   ├── base.py          # INotification interface
│   ├── service.py       # NotificationService implementation
│   ├── email.py         # Email channel
│   ├── sms.py           # SMS channel
│   └── push.py          # Push notification channel
├── subscription/
│   ├── __init__.py
│   └── service.py       # SubscriptionService
├── affiliate/
│   ├── __init__.py
│   └── service.py       # AffiliateService
└── payment/
    ├── __init__.py
    └── service.py       # PaymentService
```

---

#### `strategies/`

**MAY contain**:
- Trading strategy implementations
- Strategy parameter validation
- Strategy-specific calculations

**MUST NOT contain**:
- API routes
- Database queries
- Exchange API calls (use `adapters/` via interface)
- Order execution (use `engine/execution/`)

**Allowed imports from**: `core/`, `engine/` (via interface), `events/`

```
strategies/
├── __init__.py
├── base.py              # IStrategy interface
├── smart_grid.py        # SmartGridStrategy
├── adaptive_grid.py     # AdaptiveGridStrategy
├── infinity_grid.py     # InfinityGridStrategy
└── dca.py               # DCAStrategy
```

---

#### `tasks/`

**MAY contain**:
- Celery task definitions
- Task scheduling configuration
- Task routing

**MUST NOT contain**:
- Business logic (delegate to `engine/` or `services/`)
- API routes
- Database models

**Allowed imports from**: `engine/` (via interface), `services/` (via interface), `core/`

```
tasks/
├── __init__.py
├── celery_app.py        # Celery app configuration
├── trading_tasks.py     # Trading-related tasks
├── notification_tasks.py
├── sync_tasks.py        # Data sync tasks
└── cleanup_tasks.py     # Cleanup tasks
```

---

#### `utils/`

**MAY contain**:
- Pure utility functions (no side effects)
- Math helpers
- Date/time helpers
- String helpers
- Formatting helpers

**MUST NOT contain**:
- Business logic
- Database queries
- API calls
- State management
- Anything with side effects

**Allowed imports from**: (none — pure functions only)

```
utils/
├── __init__.py
├── math.py              # Math utilities
├── datetime.py          # Date/time utilities
├── string.py            # String utilities
├── decimal.py           # Decimal utilities
└── formatting.py        # Formatting utilities
```

---

#### `workers/`

**MAY contain**:
- Background worker implementations
- Worker lifecycle management
- Worker health monitoring
- Task queue consumers

**MUST NOT contain**:
- Business logic (delegate to `engine/` or `services/`)
- API routes
- Database models

**Allowed imports from**: `engine/` (via interface), `services/` (via interface), `core/`, `events/`

```
workers/
├── __init__.py
├── base.py              # IWorker interface
├── order_worker.py      # Order monitoring worker
├── price_worker.py      # Price update worker
├── grid_worker.py       # Grid management worker
├── notification_worker.py
└── health_worker.py     # Health check worker
```

---

## 4. FRONTEND FOLDER RULES

### 4.1 Structure

```
frontend/
├── public/             # Static assets ONLY
├── src/
│   ├── app/            # Next.js app router pages ONLY
│   ├── components/     # React components ONLY
│   ├── hooks/          # Custom React hooks ONLY
│   ├── stores/         # Zustand stores ONLY
│   ├── services/       # API client functions ONLY
│   ├── types/          # TypeScript type definitions ONLY
│   ├── utils/          # Pure utility functions ONLY
│   ├── constants/      # Constants and enums ONLY
│   └── styles/         # Global styles ONLY
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.js
```

### 4.2 Rules

| Folder | MAY Contain | MUST NOT Contain |
|--------|-------------|------------------|
| `app/` | Page components, layouts, loading/error states | Business logic, API calls (use `services/`) |
| `components/` | Reusable UI components | Page-level logic, API calls |
| `hooks/` | Custom React hooks | UI components, API routes |
| `stores/` | Zustand store definitions | UI components, API calls |
| `services/` | API client functions, WebSocket clients | UI components, state management |
| `types/` | TypeScript interfaces and types | Runtime logic |
| `utils/` | Pure functions | Side effects, API calls |
| `constants/` | Constants, enums, config | Logic, functions |
| `styles/` | Global CSS, Tailwind config | Component-specific styles (use inline) |

---

## 5. IMPORT RULES

### 5.1 Backend Import Rules

```
ALLOWED IMPORT DIRECTION (top = may import from bottom)

api/ ──────────────────────────────────────
engine/ ───────────────────────────────────
strategies/ ──────────────────────────────
services/ ─────────────────────────────────
market/ ───────────────────────────────────
adapters/ ─────────────────────────────────
workers/ ──────────────────────────────────
events/ ───────────────────────────────────
repositories/ ─────────────────────────────
models/ ───────────────────────────────────
database/ ─────────────────────────────────
core/ ─────────────────────────────────────
utils/ ──────────────────────────────────── (no imports allowed)

kernel/ ── may import from ALL (composition root)
```

### 5.2 Forbidden Imports

| Folder | MUST NOT Import From |
|--------|---------------------|
| `core/` | Anything (it's the foundation) |
| `utils/` | Anything (pure functions) |
| `models/` | `engine/`, `api/`, `adapters/` |
| `adapters/` | `engine/`, `api/`, `strategies/` |
| `repositories/` | `engine/`, `api/`, `adapters/` |
| `schemas/` | `engine/`, `models/`, `adapters/` |
| `events/` | `engine/`, `api/`, `models/` |
| `api/` | `adapters/` (use `engine/` which uses `adapters/`) |

### 5.3 Frontend Import Rules

```
app/ ──────────────────────────────────────
components/ ────────────────────────────────
hooks/ ─────────────────────────────────────
stores/ ────────────────────────────────────
services/ ──────────────────────────────────
types/ ─────────────────────────────────────
utils/ ───────────────────────────────────── (no imports allowed)
constants/ ───────────────────────────────── (no imports allowed)
```

---

## 6. ENFORCEMENT

### 6.1 Linting Configuration

**Backend** (`.ruff.toml` or `pyproject.toml`):
```toml
[tool.ruff]
select = ["TID252"]  # Ban relative imports across folders

[tool.ruff.lint.flake8-tidy-imports]
banned-api = {
  "adapters.binance.adapter.BinanceExchangeAdapter": {msg = "Import via IExchangeAdapter interface"}
}
```

**Frontend** (`eslint.config.js`):
```js
{
  rules: {
    "no-restricted-imports": ["error", {
      patterns: [
        { group: ["../services/*"], message: "Services should be imported from services/ root" }
      ]
    }]
  }
}
```

### 6.2 CI Pipeline Check

A script `scripts/check_folder_structure.py` runs in CI to validate:
- No file exists in a folder that violates the rules
- No import crosses forbidden boundaries
- All files in a folder match the allowed file types

---

## 7. CHANGE LOG

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-09 | 1.0.0 | Initial folder responsibility specification |
