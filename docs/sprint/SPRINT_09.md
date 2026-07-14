# Sprint 9 — Profit Lock Engine

**Version:** v0.9.0
**Branch:** `sprint-9`
**Dependencies:** Sprint 5 (Trading Process Manager), Sprint 7 (Execution Engine), Sprint 8 (Grid Engine)

---

## Objective

Build the **Profit Lock Engine** — an independent engine that manages trailing profit lock for trading positions. The Profit Lock Engine monitors price movements, calculates floating profit, and executes sell orders to lock in profit when the price retraces from a peak.

**Critical architectural constraint:** Profit Lock Engine is completely independent from Grid Engine. It does NOT call Grid Engine, and it does NOT read from exchanges. It only receives events from lower layers.

---

## Architecture

```
Trading Process
      │
      ├──────────────┐
      │              │
      ▼              ▼
Grid Engine     Profit Lock Engine
      │              │
      └──────┬───────┘
             ▼
     Execution Engine
             ▼
        Market Hub
             ▼
    Exchange Adapter
```

**Key constraints:**
- Profit Lock Engine does NOT know about exchanges (no Binance, Hyperliquid, etc.)
- Profit Lock Engine does NOT poll prices — event-driven only
- Profit Lock Engine does NOT call Grid Engine — they are siblings, not parent-child
- Profit Lock Engine delegates order operations to Execution Engine
- Profit Lock Engine receives events: `Price Update`, `Position Update`, `Order Filled`, `Order Cancelled`

**Supported combinations (without modifying either engine):**
- Grid without Profit Lock
- DCA with Profit Lock
- Trend Following with Profit Lock
- Arbitrage with Profit Lock

---

## Internal Modules

### Module 1: ProfitCalculator (`backend/engine/profit_lock/calculator.py`)

Calculates floating profit from position data and current price.

**Inputs:**
- `entry_price: Decimal` — average entry price of the position
- `current_price: Decimal` — latest market price
- `quantity: Decimal` — position size
- `side: str` — "long" or "short"

**Output:** `ProfitResult` with:
- `floating_profit: Decimal` — unrealized P&L
- `profit_percentage: Decimal` — profit as % of investment
- `is_profitable: bool` — True if floating_profit > 0

**Logic:**
- Long: `(current_price - entry_price) * quantity`
- Short: `(entry_price - current_price) * quantity`
- Profit %: `floating_profit / (entry_price * quantity) * 100`

### Module 2: ProfitLockPolicy (`backend/engine/profit_lock/policy.py`)

Determines when the lock level should rise and when to trigger execution.

**Inputs:**
- `current_price: Decimal`
- `ProfitLockState` — current lock state (highest_price, lock_price, etc.)
- `ProfitResult` — current profit calculation
- `trigger_percentage: Decimal` — profit % threshold to activate lock
- `trail_percentage: Decimal` — how far below peak the lock sits

**Output:** `PolicyDecision` with:
- `action: str` — "none", "update_lock", "trigger_lock", "execute_lock"
- `new_lock_price: Decimal | None`
- `reason: str`

**Logic:**
1. If profit % < trigger_percentage → no action
2. If profit % >= trigger_percentage and not yet triggered → trigger lock, set lock_price = highest_price * (1 - trail_percentage/100)
3. If price makes new high → update lock_price upward (trailing)
4. If price drops below lock_price → execute lock (place sell order)

### Module 3: ProfitLockState + ProfitLockStore (`backend/engine/profit_lock/state.py`)

Stores and manages profit lock state per instance_id.

**ProfitLockStatus states:**
- `DISABLED` — profit lock not enabled
- `MONITORING` — enabled, watching for trigger condition
- `TRIGGERED` — lock activated, trailing the price
- `EXECUTING` — lock order placed, waiting for fill
- `LOCKED` — lock order filled, profit secured
- `CANCELLED` — lock cancelled or disabled

**State transitions:**
```
DISABLED → MONITORING (enable)
MONITORING → TRIGGERED (profit >= trigger %)
TRIGGERED → TRIGGERED (trailing update — lock_price moves up)
TRIGGERED → EXECUTING (price drops below lock_price)
EXECUTING → LOCKED (sell order filled)
EXECUTING → TRIGGERED (order cancelled, resume trailing)
LOCKED → MONITORING (reset for new position)
Any state → DISABLED (disable)
Any state → CANCELLED (cancel)
```

**ProfitLockStore:** In-memory store of `ProfitLockState` per instance_id.

### Module 4: ProfitLockEngine (`backend/engine/profit_lock/engine.py`)

Orchestrates the entire profit lock lifecycle. Implements `IProfitLock`.

**Key flows:**
1. `enable(instance_id, trigger_percentage, trail_percentage)` → initialize state, start monitoring
2. `on_price_update(instance_id, current_price)` → ProfitCalculator computes profit → ProfitLockPolicy decides action → execute if needed
3. `on_position_update(instance_id, position)` → update entry_price, quantity
4. `on_order_filled(instance_id, order_id, fill_price, quantity)` → if lock order filled, transition to LOCKED
5. `on_order_cancelled(instance_id, order_id)` → if lock order cancelled, resume trailing
6. `disable(instance_id)` → cancel any lock orders, transition to DISABLED
7. `get_state(instance_id)` → return current ProfitLockState
8. `execute_lock(instance_id, lock_price)` → place sell order via ExecutionEngine

**Constructor dependencies:**
- `ExecutionEngine` — for placing sell orders
- `ProfitCalculator` — for profit calculation
- `ProfitLockPolicy` — for lock decisions
- `ProfitLockStore` — for state tracking

**Internal Metrics (observability):**
- `decisions_made: int` — total policy decisions evaluated
- `avg_decision_time_ms: float` — average time per decision
- `errors_count: int` — total errors encountered
- `retries_count: int` — total retries
- `events_processed: int` — total events received
- `locks_triggered: int` — total locks triggered
- `locks_executed: int` — total locks executed (sell order filled)

### Module 5: ProfitPersistence (`backend/engine/profit_lock/persistence.py`)

Saves and loads profit lock state to/from database for recovery after restart.

**Operations:**
- `serialize(state: ProfitLockState) -> dict` — convert to JSON-compatible dict
- `deserialize(data: dict) -> ProfitLockState` — restore from dict
- `to_json_string(state) -> str` — for database storage
- `from_json_string(json_str) -> ProfitLockState` — restore from JSON string

Uses `TradingInstance.memory_snapshot` for persistence (same pattern as GridPersistence).

---

## API Surface

```python
class ProfitLockEngine(IProfitLock):
    def __init__(
        self,
        execution_engine: ExecutionEngine,
        calculator: ProfitCalculator,
        policy: ProfitLockPolicy,
        store: ProfitLockStore,
    ): ...

    async def enable(
        self, instance_id: str, exchange_account_id: uuid.UUID,
        symbol: str, entry_price: Decimal, quantity: Decimal,
        side: str, trigger_percentage: Decimal, trail_percentage: Decimal,
    ) -> bool: ...

    async def disable(self, instance_id: str) -> bool: ...
    async def on_price_update(self, instance_id: str, current_price: Decimal) -> None: ...
    async def on_position_update(self, instance_id: str, entry_price: Decimal, quantity: Decimal) -> None: ...
    async def on_order_filled(self, instance_id: str, order_id: str, fill_price: Decimal, quantity: Decimal) -> None: ...
    async def on_order_cancelled(self, instance_id: str, order_id: str) -> None: ...
    async def get_state(self, instance_id: str) -> ProfitLockState: ...
    async def execute_lock(self, instance_id: str, lock_price: Decimal) -> bool: ...
    def get_metrics(self, instance_id: str) -> ProfitLockMetrics: ...
```

---

## Data Types

```python
@dataclass
class ProfitResult:
    floating_profit: Decimal
    profit_percentage: Decimal
    is_profitable: bool
    entry_price: Decimal
    current_price: Decimal
    quantity: Decimal

@dataclass
class ProfitLockState:
    instance_id: str
    status: ProfitLockStatus
    enabled: bool
    trigger_percentage: Decimal
    trail_percentage: Decimal
    entry_price: Decimal
    quantity: Decimal
    side: str  # "long" or "short"
    highest_price: Optional[Decimal]  # peak price since enable
    lock_price: Optional[Decimal]  # current trailing lock level
    is_triggered: bool
    is_executed: bool
    lock_order_id: Optional[str]
    exchange_account_id: Optional[uuid.UUID]
    symbol: str

@dataclass
class PolicyDecision:
    action: str  # "none", "update_lock", "trigger_lock", "execute_lock"
    new_lock_price: Optional[Decimal]
    reason: str

@dataclass
class ProfitLockMetrics:
    decisions_made: int
    avg_decision_time_ms: float
    errors_count: int
    retries_count: int
    events_processed: int
    locks_triggered: int
    locks_executed: int
```

---

## Error Handling

- `ProfitLockError` — raised on invalid profit lock operations
- `InvalidStateTransition` — raised on invalid lock state transitions
- `ValidationError` — raised on invalid parameters (negative percentages, etc.)
- Profit Lock Engine catches ExecutionEngine errors and transitions to ERROR state

---

## Acceptance Criteria

- [ ] ProfitCalculator correctly computes floating profit for long and short positions
- [ ] ProfitLockPolicy triggers lock when profit exceeds trigger_percentage
- [ ] ProfitLockPolicy trails lock_price upward as price makes new highs
- [ ] ProfitLockPolicy triggers execution when price drops below lock_price
- [ ] ProfitLockStateMachine validates all state transitions
- [ ] ProfitLockEngine places sell orders via ExecutionEngine (never touches exchange directly)
- [ ] ProfitLockEngine reacts to price updates (no polling)
- [ ] ProfitLockEngine handles order filled → transition to LOCKED
- [ ] ProfitLockEngine handles order cancelled → resume trailing
- [ ] ProfitLockEngine is independent from Grid Engine (no imports, no calls)
- [ ] ProfitPersistence saves and restores profit lock state
- [ ] Internal metrics tracked (decisions, errors, events, etc.)
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No existing tests broken
