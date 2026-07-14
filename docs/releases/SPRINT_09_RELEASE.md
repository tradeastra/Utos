# Sprint 9 Release — Profit Lock Engine

**Version:** v0.9.0
**Date:** 2026-07-14
**Tag:** `v0.9.0`
**Branch:** `sprint-9` → `develop` → `main`

---

## Summary

Sprint 9 delivers the **Profit Lock Engine** — an independent engine that manages trailing profit lock for trading positions. The Profit Lock Engine monitors price movements via events, calculates floating profit, and executes sell orders through the Execution Engine to lock in profit when the price retraces from a peak.

This is the first sprint in the **profit management** layer. Bugs here directly impact money, so the implementation emphasizes correctness, independence, and observability.

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

**Key constraints enforced:**
- Profit Lock Engine does NOT know about exchanges (no Binance, Hyperliquid, etc.)
- Profit Lock Engine does NOT poll prices — event-driven only
- Profit Lock Engine does NOT call Grid Engine — they are siblings, not parent-child
- Profit Lock Engine delegates all order operations to ExecutionEngine
- Profit Lock Engine receives events: `Price Update`, `Position Update`, `Order Filled`, `Order Cancelled`

---

## New Features

### Module 1: ProfitCalculator (`backend/engine/profit_lock/calculator.py`)
- Calculates floating profit for long and short positions
- `ProfitResult` with `floating_profit`, `profit_percentage`, `is_profitable`
- Long: `(current - entry) * qty`; Short: `(entry - current) * qty`
- Validates: positive prices, positive quantity, valid side

### Module 2: ProfitLockPolicy (`backend/engine/profit_lock/policy.py`)
- Determines when lock level should rise and when to execute
- `PolicyDecision` with action: `none`, `trigger_lock`, `update_lock`, `execute_lock`
- Triggers when profit % >= trigger_percentage
- Trails lock_price upward as price makes new highs
- Executes when price drops below lock_price

### Module 3: ProfitLockState + ProfitLockStore (`backend/engine/profit_lock/state.py`)
- **ProfitLockStatus:** `DISABLED → MONITORING → TRIGGERED → EXECUTING → LOCKED → MONITORING` (cycle)
- Validated transitions with `InvalidStateTransition` on invalid attempts
- In-memory `ProfitLockStore` keyed by `instance_id`
- `ProfitLockMetrics` for observability: decisions, errors, events, locks triggered/executed

### Module 4: ProfitLockEngine (`backend/engine/profit_lock/engine.py`)
- Orchestrates the entire profit lock lifecycle
- `enable()` → initialize state, start monitoring
- `on_price_update()` → ProfitCalculator computes → ProfitLockPolicy decides → execute if needed
- `on_position_update()` → update entry_price, quantity
- `on_order_filled()` → transition to LOCKED
- `on_order_cancelled()` → resume trailing
- `disable()` → cancel lock orders, transition to DISABLED
- `execute_lock()` → manual lock execution
- `get_metrics()` → return internal metrics
- Delegates to ExecutionEngine (never touches exchange directly)

### Module 5: ProfitPersistence (`backend/engine/profit_lock/persistence.py`)
- Serialize/deserialize `ProfitLockState` to/from JSON-compatible dict
- `to_json_string()` / `from_json_string()` for database storage
- Roundtrip tested with all fields and None values

---

## Internal Metrics (Observability)

Each instance has a `ProfitLockMetrics` object tracking:
- `decisions_made` — total policy decisions evaluated
- `avg_decision_time_ms` — average time per decision
- `errors_count` — total errors encountered
- `retries_count` — total retries
- `events_processed` — total events received
- `locks_triggered` — total locks triggered
- `locks_executed` — total locks executed (sell order filled)

---

## Test Coverage

| Test File | Tests | Description |
|-----------|-------|-------------|
| `test_profit_calculator.py` | 12 | Long/short profit, percentage, validation |
| `test_profit_lock_state.py` | 26 | State machine transitions, store CRUD, metrics |
| `test_profit_lock_policy.py` | 15 | Trigger, trailing, execution, non-active states |
| `test_profit_lock_engine.py` | 17 | Enable, price update, order events, disable, queries |
| `test_profit_persistence.py` | 5 | Serialize/deserialize roundtrip, JSON string |
| `test_profit_lock_integration.py` | 7 | Full lifecycle, short position, independence, disable |
| **Total Sprint 9** | **82** | |

**Full test suite: 555 tests passing** (473 existing + 82 new)

---

## Acceptance Criteria

- [x] ProfitCalculator correctly computes floating profit for long and short positions
- [x] ProfitLockPolicy triggers lock when profit exceeds trigger_percentage
- [x] ProfitLockPolicy trails lock_price upward as price makes new highs
- [x] ProfitLockPolicy triggers execution when price drops below lock_price
- [x] ProfitLockStateMachine validates all state transitions
- [x] ProfitLockEngine places sell orders via ExecutionEngine (never touches exchange directly)
- [x] ProfitLockEngine reacts to price updates (no polling)
- [x] ProfitLockEngine handles order filled → transition to LOCKED
- [x] ProfitLockEngine handles order cancelled → resume trailing
- [x] ProfitLockEngine is independent from Grid Engine (no imports, no calls)
- [x] ProfitPersistence saves and restores profit lock state
- [x] Internal metrics tracked (decisions, errors, events, etc.)
- [x] All unit tests pass
- [x] All integration tests pass
- [x] No existing tests broken

---

## Files Created

- `backend/engine/profit_lock/__init__.py` — package exports
- `backend/engine/profit_lock/calculator.py` — ProfitCalculator
- `backend/engine/profit_lock/state.py` — ProfitLockState, ProfitLockStateMachine, ProfitLockStore, ProfitLockMetrics
- `backend/engine/profit_lock/policy.py` — ProfitLockPolicy, PolicyDecision
- `backend/engine/profit_lock/engine.py` — ProfitLockEngine
- `backend/engine/profit_lock/persistence.py` — ProfitPersistence
- `backend/tests/test_unit/test_profit_calculator.py` — 12 tests
- `backend/tests/test_unit/test_profit_lock_state.py` — 26 tests
- `backend/tests/test_unit/test_profit_lock_policy.py` — 15 tests
- `backend/tests/test_unit/test_profit_lock_engine.py` — 17 tests
- `backend/tests/test_unit/test_profit_persistence.py` — 5 tests
- `backend/tests/test_unit/test_profit_lock_integration.py` — 7 tests
- `docs/sprint/SPRINT_09.md` — Sprint specification
- `docs/releases/SPRINT_09_RELEASE.md` — This document

## Files Modified

- `backend/core/exceptions.py` — Added `ProfitLockError` exception class
- `docs/ROADMAP.md` — Sprint 9 marked completed, changelog updated

---

## Project Status

| Sprint | Status |
|--------|--------|
| ✅ Sprint 1 | Foundation |
| ✅ Sprint 2 | Database |
| ✅ Sprint 3 | Exchange Infrastructure |
| ✅ Sprint 4 | Binance Adapter |
| ✅ Sprint 5 | Trading Process Manager |
| ✅ Sprint 6 | Market Hub |
| ✅ Sprint 7 | Execution Engine |
| ✅ Sprint 8 | Grid Engine |
| ✅ Sprint 9 | Profit Lock Engine |
