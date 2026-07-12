# Sprint 5 Release — Trading Process Manager

**Version:** v0.5.0  
**Date:** 2026-07-12  
**Tag:** `v0.5.0`  
**Branch:** `sprint-5` → `develop` → `main`

---

## Summary

Sprint 5 transforms the static `TradingInstance` database record into a living, managed process with full lifecycle management: create, prepare, start, pause, resume, stop, and recover after server restart — all without placing a single order.

This is the boundary between infrastructure and product. The Binance adapter (Sprint 4) is now used to validate connectivity and identity during `prepare()` and `recover()`.

---

## New Features

- **TradingProcess** — runtime object representing a single trading process (`backend/engine/trading/process.py`)
- **TradingProcessManager** — manages the full lifecycle of trading processes (`backend/engine/trading/process_manager.py`)
  - In-process registry with asyncio lock
  - Redis-backed state store with atomic locking (`SET NX EX`)
  - Duplicate running process prevention
  - Recovery after restart: DB → Redis → Exchange → Recover
- **ProcessStateMachine** — validates all state transitions (`backend/engine/trading/state_machine.py`)
  - States: CREATED, READY, RUNNING, PAUSED, STOPPING, STOPPED, ERROR, RECOVERING, RECOVERED
  - 12 valid transitions, rejects same-state and invalid transitions
- **REST API endpoints** (`backend/api/v1/endpoints/trading_instances.py`)
  - `POST /trading-instances` — create (CREATED)
  - `POST /trading-instances/{id}/prepare` — validate and move to READY
  - `POST /trading-instances/{id}/start` — start (RUNNING)
  - `POST /trading-instances/{id}/pause` — pause (PAUSED)
  - `POST /trading-instances/{id}/resume` — resume (RUNNING)
  - `POST /trading-instances/{id}/stop` — stop (STOPPED)
  - `GET /trading-instances/{id}` — get status
  - `GET /trading-instances` — list user processes
  - `DELETE /trading-instances/{id}` — soft-delete

---

## Bug Fixes

- **Recovery flow enhanced**: Added `health_check()` and `_validate_symbol()` to `_recover_instance` so recovery follows the full validation chain: Database → Redis → Exchange → Recover. Previously, recovery only read from DB and rebuilt the process without verifying exchange reachability or symbol support.

---

## Breaking Changes

- **`trading_instances.py` endpoint file rewritten**: The old CRUD-only endpoints were replaced with lifecycle-aware endpoints. The response model changed from inline dicts to `TradingInstanceResponse` with explicit fields.
- **`conftest.py` updated**: New fixtures `create_trading_instance`, `create_exchange_account`, `create_strategy`, `create_grid_profile` added. Existing tests may need fixture updates if they manually created these entities.

---

## Migration

No database migration required. Sprint 5 uses the existing `trading_instances` table schema from Sprint 2. No new columns or tables.

---

## Known Issues

1. **Event publishing not implemented**: State transitions do not yet emit events (e.g., `INSTANCE_RUNNING`, `INSTANCE_PAUSED`). This will be added in the Event Bus sprint.
2. **No heartbeat/lock refresh loop**: The Redis lock has a 60s TTL but there is no background task refreshing it. A heartbeat worker will be added in the Workers sprint. For now, long-running processes may lose their lock if no action is taken within 60s.
3. **No `PAUSED → STOPPING` transition**: The state machine allows `RUNNING → STOPPING` but not `PAUSED → STOPPING`. To stop a paused process, resume first then stop. This will be addressed if needed.
4. **Recovery does not reconnect WebSocket**: Recovery rebuilds the process and validates exchange connectivity, but does not re-subscribe to WebSocket market data streams. This will be handled when Market Hub (Sprint 6) is integrated.

---

## Metrics

| Metric | Value |
|--------|-------|
| Total tests | 230 |
| Tests passed | 230 |
| Tests failed | 0 |
| Process manager tests | 12 |
| Trading instance API tests | 8 |
| New files | 4 |
| Modified files | 7 |
| Lines added | ~1,630 |
| Lines removed | ~314 |

---

## Files Changed

### New Files

- `backend/engine/trading/__init__.py`
- `backend/engine/trading/process.py`
- `backend/engine/trading/process_manager.py`
- `backend/engine/trading/state_machine.py`
- `backend/tests/test_unit/test_process_manager.py`
- `backend/tests/test_unit/test_trading_instances.py`
- `docs/sprint/SPRINT_05.md`

### Modified Files

- `backend/api/v1/endpoints/trading_instances.py` (rewritten)
- `backend/api/v1/__init__.py`
- `backend/main.py`
- `backend/tests/conftest.py`
- `docs/sprint/SPRINT_05.md`

---

## Test Coverage

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_process_manager.py` | 12 | ✅ All pass |
| `test_trading_instances.py` | 8 | ✅ All pass |
| `test_api.py` | 13 | ✅ All pass |
| `test_binance_adapter.py` | 81 | ✅ All pass |
| `test_core.py` | 10 | ✅ All pass |
| `test_exchanges.py` | 86 | ✅ All pass |
| `test_repositories.py` | 20 | ✅ All pass |
| **Total** | **230** | **✅ All pass** |

---

## Next Sprint

**Sprint 6: Market Data Hub** — builds the central market data aggregation layer that will feed real-time prices, tickers, order books, and candles to the trading engines.
