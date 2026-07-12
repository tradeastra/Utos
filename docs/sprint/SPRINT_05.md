# Sprint 5: Trading Process Manager

## Status

**In Progress — Implementation and tests complete, pending final audit/merge.**

## Vision

Sprint 5 transforms the static `TradingInstance` record into a living, managed process. The goal is a single process that can be created, prepared, started, paused, resumed, stopped, and recovered after an application restart — without placing any order.

This is the boundary between foundation and product. The Binance adapter (Sprint 4) is now used to validate connectivity and identity, but the actual trading brain (grid, strategy, execution) will be added in later sprints.

## Core Architectural Decision

> **One Trading Process = One Symbol + One Strategy + One Exchange Account**

Examples:

- `BTCUSDT + Smart Grid + Binance Account A` = **1 Trading Process**
- `BTCUSDT + Conservative Grid + Binance Account A` = **2nd Trading Process** (different from above)

The persisted entity is the existing `TradingInstance` row. The runtime representation is `TradingProcess` (a Python object held in the process registry). The `TradingProcessManager` owns the registry and lifecycle transitions.

## Scope

### In Scope

1. `TradingProcess` runtime object in `backend/engine/trading/process.py`.
2. `TradingProcessManager` in `backend/engine/trading/process_manager.py`.
3. Process lifecycle state machine:
   - `CREATED` -> `READY`
   - `READY` -> `RUNNING`
   - `RUNNING` -> `PAUSED`
   - `PAUSED` -> `RUNNING`
   - `RUNNING` -> `STOPPING` -> `STOPPED`
   - `ERROR` (from any state on failure)
   - `RECOVERING` -> `RECOVERED` -> `RUNNING` / `PAUSED` / `ERROR`
4. Validation before state transitions:
   - Exchange account exists and belongs to user.
   - Strategy exists and is active.
   - Symbol is supported by the exchange.
   - API key is valid (lightweight health check, no balance required).
   - No duplicate `RUNNING` process for the same `(symbol, strategy_id, exchange_account_id)`.
5. Runtime state storage in Redis:
   - `process:{instance_id}:state` (hash)
   - `process:{instance_id}:lock` (SET NX with TTL)
   - `process:active` (set of running instance IDs)
6. Persistence in PostgreSQL via `TradingInstance` repository:
   - Status updates.
   - `started_at`, `stopped_at`, `error_message`, `worker_id`.
   - `memory_snapshot` / `memory_version` for recovery.
7. Process registry in memory:
   - Maps `instance_id` -> `TradingProcess`.
   - Prevents double start of the same process.
   - Rebuilds from Redis on application startup.
8. Recovery after restart:
   - On startup, scan PostgreSQL for `RUNNING` and `PAUSED` processes.
   - Re-acquire Redis lock.
   - Reconstruct `TradingProcess` objects.
   - Transition to `RECOVERING` then `RUNNING` or `PAUSED` based on saved state.
9. API endpoints:
   - `POST /trading-instances` — create (CREATED)
   - `POST /trading-instances/{id}/prepare` — validate and move to READY
   - `POST /trading-instances/{id}/start` — start (RUNNING)
   - `POST /trading-instances/{id}/pause` — pause (PAUSED)
   - `POST /trading-instances/{id}/resume` — resume (RUNNING)
   - `POST /trading-instances/{id}/stop` — stop (STOPPED)
   - `GET /trading-instances/{id}` — status
   - `GET /trading-instances` — list
10. Unit tests and integration tests for the lifecycle and recovery.

### Out of Scope

- Grid engine / grid calculation
- DCA logic
- Take profit / profit lock
- Order placement / execution engine
- Strategy decision making
- Worker scheduler for periodic tasks
- Market signal processing
- WebSocket market data consumption (only adapter connectivity validation is in scope)
- Frontend changes
- Docker / CI changes

## Data Model

### Existing PostgreSQL

The `trading_instances` table already contains the needed fields. Sprint 5 uses it as-is:

```text
id
user_id
exchange_account_id
strategy_id
grid_profile_id   -- required by schema, not used by process manager
symbol
status
start_price
current_price
total_investment
base_currency
quote_currency
profit_lock_enabled / portfolio_lock_enabled
worker_id
memory_snapshot
memory_version
error_message
started_at / stopped_at / deleted_at
created_at / updated_at
```

### New Redis Keys

```text
process:{instance_id}:state    -> hash {status, worker_id, updated_at, memory_version}
process:{instance_id}:lock     -> "{worker_id} / {timestamp}" (TTL 60s)
process:active                 -> set of instance_id
process:registry               -> hash {instance_id -> serialized process metadata}
```

## State Machine

```
                    +---------+
                    |  ERROR  |<----------------------+
                    +---------+                       |
                         ^                          |
                         |                          |
+--------+    +------+   |   +------+    +--------+  |
| CREATED|--->| READY|--->|->|RUNNING|--->|STOPPING|  |
+--------+    +------+   |   +---+---+    +---+---+
                              |   |            |
                              |   v            v
                              |  PAUSED    STOPPED
                              |
                              +----> RECOVERING -> RECOVERED -> RUNNING/PAUSED
```

Allowed transitions:

| From      | To         | Trigger  |
|-----------|------------|----------|
| CREATED   | READY      | prepare  |
| READY     | RUNNING    | start    |
| RUNNING   | PAUSED     | pause    |
| PAUSED    | RUNNING    | resume   |
| RUNNING   | STOPPING   | stop     |
| STOPPING  | STOPPED    | stopped  |
| *         | ERROR      | failure  |
| RUNNING   | RECOVERING | restart  |
| PAUSED    | RECOVERING | restart  |
| RECOVERING| RECOVERED  | ok       |
| RECOVERED | RUNNING    | resume   |
| RECOVERED | PAUSED     | pause    |

## Process Registry & Locking

### Registry

- `TradingProcessManager` holds `dict[uuid.UUID, TradingProcess]`.
- Methods: `register(process)`, `unregister(instance_id)`, `get(instance_id)`, `list_active()`.
- On startup, `load_from_redis()` or `recover_from_db()` rebuilds the registry.

### Locking

- Before start, `acquire_lock(instance_id, worker_id)` uses Redis `SET key value NX EX 60`.
- Lock TTL is 60 seconds and refreshed every 30 seconds by the process heartbeat.
- If start fails to acquire lock, raise `ProcessAlreadyRunning` / `InvalidStateTransition`.
- On stop, release lock and remove from active set.

## Recovery Flow

1. On application startup, `TradingProcessManager.recover()`:
   - Query `TradingInstance` where `status` in (`RUNNING`, `PAUSED`, `RECOVERING`).
   - For each, check Redis lock:
     - Lock exists and matches this worker: re-acquire.
     - Lock exists and matches another worker: mark `ERROR` (split-brain).
     - No lock: create new lock.
   - Reconstruct `TradingProcess` from `memory_snapshot`.
   - Update status: `RUNNING` -> `RECOVERING` -> `RUNNING`; `PAUSED` -> `RECOVERING` -> `PAUSED`.
   - If recovery fails, move to `ERROR` with `error_message`.

## Implementation Plan

1. Create `sprint-5` branch from `develop`.
2. Create `docs/sprint/SPRINT_05.md`.
3. Implement `TradingProcess` dataclass:
   - `instance_id`, `user_id`, `exchange_account_id`, `strategy_id`, `symbol`, `status`, `adapter`, `memory`.
   - `async start()`, `async pause()`, `async resume()`, `async stop()`, `async recover()`.
4. Implement `TradingProcessManager`:
   - Registry, locking, Redis state, DB persistence.
   - `create_process(...)`, `prepare(...)`, `start(...)`, `pause(...)`, `resume(...)`, `stop(...)`, `recover()`.
5. Implement `ProcessStateMachine` helper (or reuse `InvalidStateTransition` exceptions).
6. Add Redis state helper methods in `TradingProcessManager` or a new `ProcessStateStore`.
7. Implement recovery startup hook in `backend/main.py` lifespan.
8. Implement `POST /trading-instances/{id}/prepare|start|pause|resume|stop` endpoints in `backend/api/v1/endpoints/trading_instances.py`.
9. Implement `GET /trading-instances` and `GET /trading-instances/{id}`.
10. Wire dependencies: `TradingProcessManager` as singleton, `RedisCache`, `ExchangeFactory`, `TradingInstanceRepository`, `ExchangeAccountRepository`.
11. Add unit tests for state machine and manager.
12. Add integration tests for lifecycle + recovery.
13. Run full test suite.
14. Audit against acceptance criteria.
15. Fix issues.
16. Commit and merge to `develop`.

## API Endpoints

| Method | Path | Action |
|--------|------|--------|
| POST | `/trading-instances` | Create process (CREATED) |
| GET | `/trading-instances` | List user processes |
| GET | `/trading-instances/{id}` | Get process status |
| POST | `/trading-instances/{id}/prepare` | Validate and move to READY |
| POST | `/trading-instances/{id}/start` | Start process (RUNNING) |
| POST | `/trading-instances/{id}/pause` | Pause process (PAUSED) |
| POST | `/trading-instances/{id}/resume` | Resume process (RUNNING) |
| POST | `/trading-instances/{id}/stop` | Stop process (STOPPED) |

## Acceptance Criteria

- [ ] Create Trading Process
- [ ] Validate Exchange Account
- [ ] READY state
- [ ] RUNNING state
- [ ] PAUSED state
- [ ] STOPPING state
- [ ] STOPPED state
- [ ] ERROR state
- [ ] Recovery after restart
- [ ] Prevent duplicate running process
- [ ] Process persisted to PostgreSQL
- [ ] Runtime state stored in Redis
- [ ] API Start Process
- [ ] API Stop Process
- [ ] API Pause Process
- [ ] API Resume Process
- [ ] Unit Tests
- [ ] Integration Tests
- [ ] All tests pass
- [ ] Work is committed on `sprint-5` branch and merged into `develop` via PR after audit

## Target Metrics

- Test count: 250+
- All tests pass
- No process can be started twice
- Recovery succeeds within 5 seconds after simulated restart
- State transitions are atomic (DB + Redis updated together, or rolled back on failure)

## Workflow

1. Planning
2. Implement
3. Compile
4. Run Tests
5. Audit
6. Fix
7. Commit (on `sprint-5`)
8. Pull Request `sprint-5` -> `develop`
9. Tag on `main` after merge to `main` at release time

## Risks

1. **Redis unavailable at startup**: Recovery must fall back to DB state and create locks later.
2. **Split-brain between two workers**: Lock must be worker-scoped and TTL-based.
3. **Schema constraint `grid_profile_id`**: `TradingInstance` table requires a `grid_profile_id`; Sprint 5 will create/use a default placeholder profile without invoking grid logic.
4. **Adapter validation failure**: `prepare` relies on `adapter.health_check()` and `authenticate()`; network errors should move process to `ERROR`.
5. **State inconsistency on crash**: DB commit and Redis update must be coordinated; if Redis fails, the DB record remains and recovery will retry.

## Definition of Done

A Trading Process can be created, prepared, started, paused, resumed, stopped, recovered after a server restart, and a second identical process cannot be started while the first is running — all without placing a single order.
