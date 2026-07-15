# Sprint 11: Recovery & Resilience

**Version Target:** v0.11.0  
**Status:** In Progress  
**Dependencies:** Sprint 05, Sprint 07, Sprint 08, Sprint 09, Sprint 10

---

## Objective

Make the UTOS system resilient against all real-world failure scenarios.

The system must be able to **automatically recover** its full operational state
after any combination of the following failures:

1. Server restart / process crash
2. Redis restart (in-memory state lost)
3. PostgreSQL restart (DB connection lost)
4. Exchange disconnection (WebSocket dropped)
5. WebSocket reconnect (re-subscribe, re-sync prices)
6. Order queue backlog (orders placed but not yet confirmed)
7. Grid State inconsistency (local vs exchange live orders diverge)
8. Portfolio position divergence (local vs exchange actual positions)

---

## 4-Layer Architecture

```
RecoveryCoordinator (orchestrator, NOT a God Object)
    │
    ├── Layer 1: ConnectionRecovery
    │       ├── Redis reconnect + queue replay
    │       ├── PostgreSQL reconnect + retry
    │       ├── Exchange disconnect handling
    │       └── WebSocket reconnect + re-subscribe
    │
    ├── Layer 2: StateRecovery
    │       ├── Trading Process state (from DB)
    │       ├── Grid State (from persistence + reconcile)
    │       ├── Profit Lock State (from persistence)
    │       └── Portfolio (from exchange positions)
    │
    ├── Layer 3: RuntimeReconciler
    │       ├── Grid: local levels vs exchange live orders
    │       ├── Portfolio: local positions vs exchange positions
    │       ├── Detect orphan orders (on exchange, not in local state)
    │       └── Detect missing orders (in local state, not on exchange)
    │
    └── Layer 4: Chaos Tests
            ├── Server restart → 100 instances recovered
            ├── Redis death → state rebuilt from PostgreSQL
            ├── WebSocket drop → reconnect + re-subscribe
            ├── Exchange timeout → queue + replay
            └── Order filled during restart → detected on reconcile
```

**Key constraints:**
- RecoveryCoordinator orchestrates but does NOT implement recovery logic itself
- Each layer is independent — failure in one does NOT block others
- Recovery is triggered by events (not polling)
- All recovery operations are idempotent — safe to run multiple times
- RecoveryCoordinator does NOT know exchange internals — uses ExecutionEngine and PortfolioManager
- Events emitted: `RECOVERY_STARTED`, `RECOVERY_COMPLETED`, `RECOVERY_FAILED`, `RECONCILIATION_NEEDED`

---

## Module Breakdown

### Module 1: RecoveryCoordinator
**File:** `backend/engine/recovery/coordinator.py`

Orchestrates recovery across all 4 layers. NOT a God Object — delegates to specialized modules.

```python
class RecoveryCoordinator:
    async def recover_all(self, instance_id: str) -> RecoveryReport
    async def recover_instance(self, instance_id: str) -> RecoveryReport
    async def get_recovery_status(self, instance_id: str) -> RecoveryStatus
    def register_instance(self, instance_id: str, context: InstanceContext) -> None
```

### Module 2: ConnectionRecovery (Layer 1)
**File:** `backend/engine/recovery/connection.py`

Handles all connection-level recovery.

```python
class ConnectionRecovery:
    async def recover_redis(self) -> bool
    async def recover_postgres(self) -> bool
    async def on_exchange_disconnect(self, exchange: str, account_id: str) -> None
    async def on_exchange_reconnect(self, exchange: str, account_id: str) -> bool
    async def resubscribe_all(self, account_id: str, symbols: list[str]) -> bool
    async def resync_prices(self, symbols: list[str]) -> dict[str, Decimal]
    def queue_order(self, order: QueuedOrder) -> None
    async def replay_queued_orders(self) -> list[OrderResult]
```

### Module 3: StateRecovery (Layer 2)
**File:** `backend/engine/recovery/state.py`

Rebuilds in-memory state from persistent storage.

```python
class StateRecovery:
    async def recover_trading_process(self, instance_id: str) -> bool
    async def recover_grid(self, instance_id: str) -> GridState | None
    async def recover_profit_lock(self, instance_id: str) -> ProfitLockState | None
    async def recover_portfolio(self, instance_id: str) -> list[Position]
```

### Module 4: RuntimeReconciler (Layer 3)
**File:** `backend/engine/recovery/reconciler.py`

Reconciles local state against exchange live state at runtime.

```python
class RuntimeReconciler:
    async def reconcile_grid(self, instance_id: str, grid_state: GridState, live_orders: list[OrderResult]) -> ReconciliationResult
    async def reconcile_portfolio(self, instance_id: str, local_positions: list[Position], exchange_positions: list[PositionEntry]) -> ReconciliationResult
    def find_missing_orders(self, grid_state: GridState, live_orders: list[OrderResult]) -> list[GridLevel]
    def find_orphan_orders(self, grid_state: GridState, live_orders: list[OrderResult]) -> list[OrderResult]
```

### Module 5: RecoveryPersistence
**File:** `backend/engine/recovery/persistence.py`

Checkpoints recovery state for auditability.

```python
class RecoveryPersistence:
    def save_checkpoint(self, instance_id: str, checkpoint: RecoveryCheckpoint) -> None
    def load_checkpoint(self, instance_id: str) -> RecoveryCheckpoint | None
    def clear_checkpoint(self, instance_id: str) -> None
    def list_checkpoints(self) -> list[str]
```

---

## Data Types

```python
@dataclass
class RecoveryReport:
    instance_id: str
    started_at: datetime
    completed_at: datetime | None
    connection_ok: bool
    state_ok: bool
    reconciliation_ok: bool
    errors: list[str]
    reconciliation_results: list[ReconciliationResult]

@dataclass
class ReconciliationResult:
    component: str  # "grid" | "portfolio" | "profit_lock"
    action: str     # "restored" | "cancelled" | "skipped" | "failed"
    count: int
    details: list[str]

@dataclass
class RecoveryStatus:
    instance_id: str
    state: str  # "idle" | "recovering" | "completed" | "failed"
    started_at: datetime | None
    completed_at: datetime | None
    last_error: str | None

@dataclass
class RecoveryCheckpoint:
    instance_id: str
    created_at: datetime
    phase: str  # "connection" | "state" | "reconciliation"
    data: dict

@dataclass
class QueuedOrder:
    instance_id: str
    account_id: str
    exchange: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    queued_at: datetime

@dataclass
class InstanceContext:
    instance_id: str
    account_id: str
    exchange: str
    symbol: str
    has_grid: bool
    has_profit_lock: bool
```

---

## Recovery Scenarios

### Scenario 1: Server Restart
1. Load all active Trading Instances from PostgreSQL
2. For each instance, call `recover_trading_process()`
3. If Grid Engine was active → call `recover_grid()`
4. If Profit Lock was active → call `recover_profit_lock()`
5. Rebuild portfolio from open positions
6. Emit `RECOVERY_COMPLETED` event

### Scenario 2: Redis Restart
1. Detect Redis unavailable (connection error)
2. Queue all writes
3. On Redis reconnect, replay queue
4. Reload any in-memory state from PostgreSQL

### Scenario 3: Exchange Disconnect
1. WebSocket disconnect triggers `on_disconnect()`
2. Queue pending order placements
3. Start reconnect loop with exponential backoff
4. On reconnect: `resubscribe_all()` → `resync_prices()` → replay queued orders

### Scenario 4: Grid Reconciliation
1. Fetch live orders from exchange via ExecutionEngine
2. Compare with local GridState
3. Mark filled levels as filled, cancelled levels as cancelled
4. Re-place missing orders if grid still active
5. Record orphan orders (on exchange but not in local state) for manual review

### Scenario 5: Portfolio Reconciliation
1. Fetch open positions from exchange
2. Compare with PortfolioManager state
3. Add missing positions (positions on exchange but not locally)
4. Close positions locally that are no longer open on exchange

---

## Error Handling

| Exception | When |
|-----------|------|
| `RecoveryError` | General recovery failure |
| `ReconciliationError` | State divergence that cannot be auto-resolved |
| `CheckpointError` | Checkpoint save/load failure |

---

## Events Emitted

| Event | When |
|-------|------|
| `RECOVERY_STARTED` | Recovery begins for an instance |
| `RECOVERY_COMPLETED` | All recovery steps succeeded |
| `RECOVERY_FAILED` | Recovery could not complete |
| `RECONCILIATION_NEEDED` | Divergence detected, manual review required |

---

## Chaos Test Plan

Each of the following failure modes will be tested with automated chaos tests:

| Failure | Test |
|---------|------|
| Server restart | Kill process → restart → verify state rebuilt |
| Redis restart | Flush Redis → verify recovery from PostgreSQL |
| PostgreSQL restart | Disconnect DB → reconnect → verify retry |
| Exchange disconnect | Simulate WebSocket drop → verify reconnect + re-subscribe |
| Grid divergence | Inject orphan orders → verify reconciliation |
| Portfolio divergence | Inject missing positions → verify rebuild |
| Partial order fill on disconnect | Fill during disconnect → verify fill detected on reconnect |

---

## Acceptance Criteria

- [ ] RecoveryCoordinator orchestrates 4 layers without being a God Object
- [ ] System can recover 100 Trading Processes after server restart
- [ ] No duplicate orders after recovery
- [ ] No corrupt state after recovery
- [ ] No missing positions after recovery
- [ ] Grid State reconciled with exchange after any disconnect
- [ ] Profit Lock State restored from persistent store
- [ ] Portfolio positions rebuilt from exchange
- [ ] WebSocket reconnects with re-subscription
- [ ] All recovery operations are idempotent
- [ ] Chaos tests pass for all 5 failure scenarios
- [ ] RecoveryCoordinator does NOT know exchange API directly
- [ ] Each layer fails independently without blocking others
- [ ] Events emitted for all recovery lifecycle transitions
- [ ] Unit tests for each module
- [ ] Integration tests for full recovery flow
