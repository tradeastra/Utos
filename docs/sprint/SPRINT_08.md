# Sprint 8 — Grid Engine

**Version:** v0.8.0
**Branch:** `sprint-8`
**Dependencies:** Sprint 5 (Trading Process Manager), Sprint 6 (Market Hub), Sprint 7 (Execution Engine)

---

## Objective

Build the Grid Engine — the first trading strategy layer. The Grid Engine manages grid levels, places buy/sell orders through the Execution Engine, and reacts to price updates from the Market Hub — all without directly touching exchange adapters or polling prices.

---

## Architecture

```
MarketHub → Price Update Event → GridEngine → ExecutionEngine → ExchangeAdapter
```

**Key constraints:**
- Grid Engine does NOT know about exchanges (no Binance, Hyperliquid, etc.)
- Grid Engine does NOT poll prices — event-driven via Market Hub `subscribe()`
- Grid Engine delegates all order operations to Execution Engine
- Execution Engine remains stateless regarding strategies

---

## Internal Modules

### Module 1: GridCalculator (`backend/engine/grid/calculator.py`)

Generates grid levels from configuration parameters.

**Inputs:**
- `upper_price: Decimal`
- `lower_price: Decimal`
- `grid_count: int`
- `investment_per_grid: Decimal`

**Output:** `list[GridLevel]` with calculated buy/sell prices and quantities.

**Logic:**
- Evenly spaced grid levels between upper and lower price
- Each level has a buy price (below mid) and sell price (above mid)
- Quantity = `investment_per_grid / price`
- Validates: upper > lower, grid_count > 0, investment > 0

### Module 2: GridPlanner (`backend/engine/grid/planner.py`)

Determines which grid levels should have active orders based on current price.

**Inputs:**
- `levels: list[GridLevel]`
- `current_price: Decimal`

**Output:** `GridPlan` — which levels need buy orders, which need sell orders, which should be cancelled.

**Logic:**
- Levels below current price → place buy orders
- Levels above current price → place sell orders (if buy was filled)
- Levels far from current price → no action (waiting)
- Respects existing order state from GridStateStore

### Module 3: GridStateMachine + GridStateStore (`backend/engine/grid/state.py`)

Per-level status tracking with validated state transitions.

**GridLevelStatus states:**
- `WAITING` — level calculated, no order placed
- `OPEN` — order placed on exchange, waiting to fill
- `FILLED` — order filled, ready for opposite side
- `CANCELLED` — order cancelled
- `TP_HIT` — take profit (opposite side) filled, cycle complete

**GridStatus (overall grid):**
- `IDLE` → `INITIALIZED` → `ACTIVE` ↔ `PAUSED` → `COMPLETED` / `ERROR`

**GridStateStore:** In-memory store of `GridState` per instance_id.

### Module 4: GridEngine (`backend/engine/grid/engine.py`)

Orchestrates the entire grid cycle. Implements `IGridEngine`.

**Key flows:**
1. `initialize_grid()` → GridCalculator generates levels → store in GridStateStore
2. `activate_grid()` → GridPlanner decides initial orders → place via ExecutionEngine
3. `on_price_update(price)` → GridPlanner re-evaluates → place/cancel orders
4. `on_buy_filled(level, price, qty)` → place sell order at sell price
5. `on_sell_filled(level, price, qty)` → place buy order at buy price, increment cycle count
6. `pause_grid()` → cancel all open orders
7. `resume_grid()` → re-place orders based on current price

**Constructor dependencies:**
- `ExecutionEngine` — for placing/cancelling orders
- `GridCalculator` — for level calculation
- `GridPlanner` — for order planning
- `GridStateStore` — for state tracking

### Module 5: GridPersistence (`backend/engine/grid/persistence.py`)

Saves and loads grid state to/from database.

**Operations:**
- `save_grid_state(instance_id, state)` — persist to DB
- `load_grid_state(instance_id)` — restore from DB
- `delete_grid_state(instance_id)` — remove from DB

Uses `GridProfile` model and `TradingInstance.memory_snapshot` for persistence.

---

## API Surface

```python
class GridEngine(IGridEngine):
    def __init__(
        self,
        execution_engine: ExecutionEngine,
        calculator: GridCalculator,
        planner: GridPlanner,
        store: GridStateStore,
        persistence: GridPersistence | None = None,
    ): ...

    async def initialize_grid(
        self, instance_id: str, exchange_account_id: uuid.UUID,
        symbol: str, upper_price: Decimal, lower_price: Decimal,
        grid_count: int, investment_per_grid: Decimal,
    ) -> GridState: ...

    async def activate_grid(self, instance_id: str) -> bool: ...
    async def pause_grid(self, instance_id: str) -> bool: ...
    async def resume_grid(self, instance_id: str) -> bool: ...
    async def on_price_update(self, instance_id: str, price: Decimal) -> None: ...
    async def on_buy_filled(self, instance_id: str, grid_level: int, fill_price: Decimal, quantity: Decimal) -> None: ...
    async def on_sell_filled(self, instance_id: str, grid_level: int, fill_price: Decimal, quantity: Decimal) -> None: ...
    async def get_grid_state(self, instance_id: str) -> GridState: ...
    async def close_all_grid_orders(self, instance_id: str) -> bool: ...
```

---

## Error Handling

- `GridError` — raised on invalid grid operations
- `InvalidStateTransition` — raised on invalid grid/level state transitions
- `ValidationError` — raised on invalid grid parameters
- Grid Engine catches ExecutionEngine errors and transitions grid to ERROR state

---

## Acceptance Criteria

- [ ] GridCalculator generates correct evenly-spaced grid levels
- [ ] GridPlanner correctly determines which orders to place/cancel based on price
- [ ] GridStateMachine validates all level transitions
- [ ] GridEngine places orders via ExecutionEngine (never touches exchange directly)
- [ ] GridEngine reacts to price updates from Market Hub (no polling)
- [ ] Buy fill → sell order placed at sell price
- [ ] Sell fill → buy order placed at buy price, cycle count incremented
- [ ] Pause cancels all open orders, resume re-places them
- [ ] GridPersistence saves and restores grid state
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No existing tests broken
