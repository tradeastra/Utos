# Architecture Decision Records (ADR)

## ADR-001: Event-Driven Architecture

**Date:** 2026-07-15  
**Status:** Accepted

### Context

All engines in UTOS need to communicate without tight coupling. Adding a new engine (e.g., NotificationService, AuditLogger) should not require modifying existing engines.

### Decision

All inter-engine communication goes through the EventBus. No engine may call another engine directly. Engines publish events, and the EventBus routes them to subscribers.

**Example flow:**
```
ExecutionEngine emits ORDER_FILLED
                ↓
EventBus routes to all subscribers
                ↓
    GridEngine, ProfitLockEngine, PortfolioManager, RiskManager, NotificationService, AuditLogger
```

**Consequences:**
- New engines can be added by subscribing to events without touching existing code
- Engine lifecycle is independent (one can crash without affecting others)
- Debugging requires event tracing (logs include event ID)
- Cannot use synchronous return values across engines

---

## ADR-002: RecoveryCoordinator Over RecoveryManager

**Date:** 2026-07-15  
**Status:** Accepted

### Context

Recovery is complex. Multiple components need recovery (Connection, State, Grid, Portfolio, Profit Lock). One class that handles all of them would become a God Object.

### Decision

Use a `RecoveryCoordinator` that orchestrates recovery across independent layers. Each layer has its own specialist class: `ConnectionRecovery`, `StateRecovery`, `RuntimeReconciler`. The coordinator only delegates.

**Consequences:**
- Each layer can be tested independently
- New recovery types can be added without modifying the coordinator
- Failure in one layer does not block recovery in others
- Coordinator adds minimal overhead

---

## ADR-003: Generic MarketHub (Multi-Exchange)

**Date:** 2026-07-15  
**Status:** Accepted

### Context

UTOS may need to support multiple exchanges (Binance, OKX, Hyperliquid, etc.). If the MarketHub is built for one exchange only, adding new exchanges requires rewriting it.

### Decision

`MarketHub` is a generic engine that receives a list of exchange adapter instances. Each adapter implements the same interface (`IExchangeAdapter`). MarketHub maps subscriptions to the appropriate adapter by exchange name. No exchange-specific code exists in the MarketHub.

**Consequences:**
- Adding a new exchange means writing a new adapter, not modifying the MarketHub
- All exchanges share the same event format (price updates, order book, etc.)
- Single exchange-specific bug cannot affect other exchanges
- Adapter contract is strict and must be fully implemented

---

## ADR-004: RiskManager as Gatekeeper

**Date:** 2026-07-15  
**Status:** Accepted

### Context

Risk management must be enforced at the boundary between strategy and execution. If an order is placed that violates risk limits, the system must reject it before it reaches the exchange.

### Decision

`RiskManager` sits between strategy engines and the `ExecutionEngine`. No engine may call `ExecutionEngine` directly — all order submissions must go through `RiskManager.check_order_risk()`. If the check fails, the order is rejected with a `RiskError`.

**Consequences:**
- Risk cannot be bypassed — no direct ExecutionEngine calls allowed
- RiskManager can be tested independently (mock orders, no exchange needed)
- Risk rules are configurable per user
- Adds latency to order path (one function call, minimal)

---

## ADR-005: Only ExecutionEngine Accesses Exchange Adapter

**Date:** 2026-07-15  
**Status:** Accepted

### Context

If multiple engines (Grid, Profit Lock, Portfolio, etc.) each call the exchange adapter directly, bugs, rate limits, and connection issues would be scattered across the codebase. Debugging would be hard.

### Decision

Only the `ExecutionEngine` may call `ExchangeAdapter`. All other engines must submit requests to the ExecutionEngine, which queues and executes them.

**Consequences:**
- Rate limit management is centralized
- Connection health is managed in one place
- Exchange-specific bugs are isolated
- ExecutionEngine must be robust (retry logic, queue management, etc.)

---

## ADR-006: No Polling — Event-Driven Price Updates

**Date:** 2026-07-15  
**Status:** Accepted

### Context

Polling for price data creates unnecessary load and latency. WebSocket streams from exchanges provide real-time price updates.

### Decision

All price-sensitive engines receive price updates via events from `MarketHub`. No engine may poll prices. The `MarketHub` subscribes to WebSocket streams and emits `PriceUpdate` events. Engines react to these events.

**Consequences:**
- Lower CPU and network usage
- Lower latency for price-driven decisions
- No polling logic in any engine
- MarketHub must handle WebSocket reconnects (see ADR-007)

---

## ADR-007: Recovery & Resilience as a 4-Layer System

**Date:** 2026-07-15  
**Status:** Accepted

### Context

Server restarts, Redis crashes, and exchange disconnects are inevitable. The system must recover without manual intervention. A single recovery module would be too complex and error-prone.

### Decision

Recovery is divided into 4 layers:
1. **Connection Recovery** — reconnect Redis, PostgreSQL, Exchange, WebSocket
2. **State Recovery** — rebuild in-memory state from persistent snapshots (DB, snapshots)
3. **Runtime Reconciliation** — sync local state with exchange live state (detect fills, orphans, stale positions)
4. **Chaos Recovery** — automated tests that simulate all failure scenarios

**Consequences:**
- Each layer can be tested and debugged independently
- Recovery is idempotent (safe to run multiple times)
- Failure in one layer does not block others
- Automated testing provides confidence in real-world scenarios

---

## ADR-008: Callback-Based Engine Design

**Date:** 2026-07-15  
**Status:** Accepted

### Context

Engines need to interact with external systems (DB, Redis, exchange) but should not be tightly coupled to them. For example, `StateRecovery` needs to read from DB but should not know SQLAlchemy.

### Decision

Engines receive external dependencies via callback functions in the constructor, not by importing them. This is an inversion of control (IoC) pattern.

**Example:**
```python
class StateRecovery:
    def __init__(self, load_instance_fn: Callable[[str], dict] | None = None):
        self._load_instance_fn = load_instance_fn
```

**Consequences:**
- Engines can be tested with mock callbacks (no DB/Redis needed)
- Production wiring is done at the top level (dependency injection)
- Easier to swap implementations (e.g., switch from Redis to PostgreSQL)
- Engine code is simpler and more focused

---

## ADR-009: Idempotency in All Operations

**Date:** 2026-07-15  
**Status:** Accepted

### Context

Recovery, retry, and reconciliation may run the same operation multiple times. Running the same operation twice should not produce different results.

### Decision

All critical operations (recovery, reconciliation, order placement, checkpoint save) are idempotent. Running them twice is safe.

**Examples:**
- RecoveryCoordinator.recover_instance() can be called twice safely
- Grid level marked as FILLED will remain FILLED if reconciliation runs again
- Portfolio position added once will not be duplicated if reconciliation runs again

**Consequences:**
- Simpler retry logic (no need for "run once" checks)
- Safer recovery (partial recovery can be retried)
- Requires careful state tracking to prevent double counting

---

## ADR-010: Enums and Dataclasses for All Type Definitions

**Date:** 2026-07-15  
**Status:** Accepted

### Context

Using raw strings and dicts for data transfer between engines creates ambiguity and bugs. Type safety reduces runtime errors.

### Decision

All data types (OrderStatus, GridLevelStatus, Position, etc.) are defined as Python `Enum` or `@dataclass`. No raw strings or dicts for inter-engine communication.

**Consequences:**
- Type hints are meaningful and can be checked by mypy
- Auto-completion in IDE improves developer experience
- Less ambiguity (e.g., `OrderStatus.FILLED` vs `"filled"`)
- Slightly more code (but less debugging)

