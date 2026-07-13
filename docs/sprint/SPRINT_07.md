# Sprint 7 — Execution Engine

**Version:** v0.7.0 (planned)  
**Layer:** Order execution  
**Status:** In Progress  
**Branch:** `sprint-7` → `develop` → `main`  
**Dependencies:** Sprint 05 (Trading Process Manager), Sprint 06 (Market Hub)

---

## Objective

Build a narrow, safe, and idempotent **Execution Engine** that is the single entry point for placing, cancelling, and tracking orders. The engine receives `OrderRequest` objects, validates them, delegates exchange execution through `IExchangeAdapter`, tracks order state, and handles transient errors with retry and idempotency.

This sprint does **not** implement Grid, DCA, Strategy, or Profit Lock logic. Those layers will sit on top of the Execution Engine in later sprints.

---

## In Scope

1. **ExecutionEngine** — core facade (`backend/engine/execution/execution_engine.py`)
2. **OrderRequest** — dataclass for order placement requests (`backend/engine/execution/models.py`)
3. **OrderResult** — dataclass for execution results (`backend/engine/execution/models.py`)
4. **OrderState / OrderStatus** — order lifecycle state machine (`backend/engine/execution/order_state.py`)
5. **OrderValidator** — pre-execution validation (`backend/engine/execution/validator.py`)
6. **OrderExecutor** — actual adapter dispatch and retry (`backend/engine/execution/executor.py`)
7. **OrderTracker** — in-memory tracking of active/pending orders (`backend/engine/execution/tracker.py`)
8. **Cancel Order** — cancel a single order by ID
9. **Cancel All Orders** — cancel all orders for a given exchange account + symbol
10. **Retry logic** — exponential backoff retry for transient exchange errors
11. **Idempotency Key** — every order carries `request_id` (UUID); duplicate requests return cached result
12. **Unit Tests** — mock exchange adapter
13. **Integration Tests** — with fake adapter + state transitions

---

## Out of Scope

- Grid Engine (Sprint 8)
- DCA logic
- Strategy Engine (Sprint 10)
- Profit Lock Engine (Sprint 9)
- Portfolio management / position tracking beyond order fills
- Wallet/account balance reconciliation
- Persistence of order history to database (in-memory only for this sprint)

---

## Key Requirements

### Idempotency

Every `OrderRequest` must include:

```python
request_id: uuid.UUID  # idempotency key
```

Execution Engine flow:

```
request_id
    ↓
Check processed cache
    ↓
Yes → return cached OrderResult
No  → validate → execute → store result → return result
```

This prevents double orders on timeout, retry, or duplicate HTTP requests.

### Order State Machine

```
PENDING
  ↓
SUBMITTING
  ↓
OPEN
  ↓ (filled)
FILLED
  ↓ (partial)
PARTIALLY_FILLED
  ↓
CANCELLING → CANCELLED
  ↓ (error)
REJECTED
  ↓ (transient)
FAILED → retry → SUBMITTING
```

States must be validated before transition; invalid transitions raise `InvalidStateTransition`.

### Retry Logic

- Retry only on transient errors (network timeout, rate limit, temporary exchange unavailability).
- Do NOT retry on validation errors, rejected orders, or insufficient balance.
- Exponential backoff with max attempts.
- Each retry uses the same `request_id` and must not create duplicate exchange orders.

### API Surface

```python
class ExecutionEngine:
    async def place_order(self, request: OrderRequest) -> OrderResult
    async def cancel_order(self, exchange_account_id: UUID, order_id: str) -> OrderResult
    async def cancel_all_orders(self, exchange_account_id: UUID, symbol: str | None = None) -> list[OrderResult]
    async def get_order(self, exchange_account_id: UUID, order_id: str) -> OrderResult | None
    async def sync_order(self, exchange_account_id: UUID, order_id: str) -> OrderResult
    def list_active_orders(self, exchange_account_id: UUID | None = None) -> list[OrderResult]
```

### Exchange Adapter Integration

- Execution Engine receives an authenticated `IExchangeAdapter` instance.
- It uses adapter methods:
  - `place_order(...)`
  - `cancel_order(...)`
  - `get_order_status(...)`
  - `get_open_orders(...)` (optional for cancel_all)
- All exchange-specific details are hidden from callers.

### Error Handling

- `OrderValidationError` — request is invalid
- `OrderExecutionError` — exchange returned non-transient error
- `OrderNotFound` — order ID does not exist
- `InvalidStateTransition` — illegal lifecycle move

---

## Acceptance Criteria

- [ ] ExecutionEngine exposes `place_order`, `cancel_order`, `cancel_all_orders`, `get_order`, `sync_order`, `list_active_orders`
- [ ] All orders require `request_id` (UUID) for idempotency
- [ ] Duplicate `request_id` returns cached result without hitting exchange
- [ ] Order state machine transitions are validated
- [ ] Retry only on transient errors with exponential backoff
- [ ] Cancel order and cancel all orders implemented
- [ ] Unit tests with mock adapter pass
- [ ] Integration tests for place → fill → sync pass
- [ ] All existing tests still pass
- [ ] SPRINT_07_RELEASE.md updated
- [ ] Commit, merge to develop, merge to main, tag v0.7.0

---

## Files to Create / Modify

### New Files

- `backend/engine/execution/__init__.py`
- `backend/engine/execution/models.py`
- `backend/engine/execution/order_state.py`
- `backend/engine/execution/validator.py`
- `backend/engine/execution/executor.py`
- `backend/engine/execution/tracker.py`
- `backend/engine/execution/execution_engine.py`
- `backend/engine/execution/exceptions.py` (if needed, or reuse core exceptions)
- `backend/tests/test_unit/test_execution_engine.py`
- `backend/tests/test_unit/test_order_state.py`
- `backend/tests/test_unit/test_order_validator.py`
- `backend/tests/test_unit/test_order_executor.py`
- `backend/tests/test_unit/test_order_tracker.py`
- `backend/tests/test_unit/test_execution_integration.py`
- `docs/releases/SPRINT_07_RELEASE.md`

### Modified Files

- `backend/main.py` — register execution engine lifecycle if needed
- `backend/engine/__init__.py` — export ExecutionEngine

---

## Notes for Future Sprints

Backlog items from Sprint 6 review:

1. **Market sequence/version** — add sequence/version to market updates for lost-update detection.
2. **Timestamp separation** — distinguish `exchange_timestamp`, `receive_timestamp`, `processed_timestamp`.
3. **Observability** — metrics: reconnect success rate, average update latency, cache freshness, dropped message count.

These remain out of scope for Sprint 7.
