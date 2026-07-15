# Sprint 12 Release — Worker Scheduler & Event Bus

**Version:** v0.12.0
**Date:** 2026-07-15
**Tag:** `v0.12.0`

---

## Summary

Sprint 12 delivers the **Worker Scheduler & Event Bus** — the operational infrastructure that transforms UTOS from a collection of engines into a coordinated, event-driven system. All engines now communicate via events, background tasks are scheduled and retried automatically, and system health is continuously monitored.

This sprint also introduces **Architecture Decision Records (ADR)** documenting all key architectural choices.

---

## 6-Module Architecture

```
engine/scheduler/
    ├── __init__.py          — package exports
    ├── bus.py               — EventBus (in-memory pub/sub)
    ├── manager.py           — WorkerManager (lifecycle)
    ├── scheduler.py         — JobScheduler (periodic tasks)
    ├── retry.py             — RetryWorker (exponential backoff)
    ├── dlq.py               — DeadLetterQueue (failed events)
    └── heartbeat.py         — HeartbeatMonitor (health checks)
```

**Event flow:**
```
ExecutionEngine → emit ORDER_FILLED
    ↓
EventBus → route to all subscribers
    ↓
    GridEngine, ProfitLockEngine, PortfolioManager,
    RiskManager, NotificationService, AuditLogger
```

---

## Modules

### Module 1: EventBus (`scheduler.bus`)
- In-memory pub/sub for event-driven communication
- `publish()` — emit events to all subscribers
- `subscribe()` / `unsubscribe()` — manage subscriptions
- Supports both sync and async handlers
- Metrics: events_published, events_delivered, subscribers_count

### Module 2: WorkerManager (`scheduler.manager`)
- Manages worker lifecycle: register, start, stop, pause, resume
- Error tracking with `mark_error()`
- `get_all_workers()` / `get_running_workers()` — query worker states
- Does NOT execute coroutines — only manages lifecycle

### Module 3: JobScheduler (`scheduler.scheduler`)
- Schedules periodic tasks: cleanup, checkpoint, heartbeat, sync, retry
- `add_task()` / `remove_task()` / `enable_task()` / `disable_task()`
- `run_task()` / `run_all()` — execute due tasks
- `get_pending_tasks()` — find tasks ready to run
- Supports both sync and async task coroutines

### Module 4: RetryWorker (`scheduler.retry`)
- Retries failed jobs with exponential backoff (1s, 2s, 4s)
- Configurable max_retries (default: 3) and backoff_base
- After max retries → moves to DeadLetterQueue via callback
- `submit()` / `process_queue()` — manage retry queue

### Module 5: DeadLetterQueue (`scheduler.dlq`)
- Stores failed events/tasks for analysis and replay
- `add()` / `get_all()` / `get_by_event_type()` — manage entries
- `replay()` — attempt to replay failed event via handler
- `clear()` — purge all entries
- Metrics: entries_added, entries_replayed, entries_cleared

### Module 6: HeartbeatMonitor (`scheduler.heartbeat`)
- Monitors health of all system components
- `register()` — register health check function per component
- `check()` / `check_all()` — run health checks
- `get_unhealthy()` / `get_healthy()` — query results
- Does NOT recover — reports only (RecoveryCoordinator handles recovery)

---

## Architecture Decision Records (ADR)

Created `docs/ARCHITECTURE_DECISIONS.md` with 10 ADRs:

| ADR | Title |
|-----|-------|
| ADR-001 | Event-Driven Architecture |
| ADR-002 | RecoveryCoordinator Over RecoveryManager |
| ADR-003 | Generic MarketHub (Multi-Exchange) |
| ADR-004 | RiskManager as Gatekeeper |
| ADR-005 | Only ExecutionEngine Accesses Exchange Adapter |
| ADR-006 | No Polling — Event-Driven Price Updates |
| ADR-007 | Recovery & Resilience as a 4-Layer System |
| ADR-008 | Callback-Based Engine Design |
| ADR-009 | Idempotency in All Operations |
| ADR-010 | Enums and Dataclasses for All Type Definitions |

---

## Test Coverage

| Test File | Tests | Description |
|-----------|-------|-------------|
| `test_event_bus.py` | 8 | Publish/subscribe, multiple subscribers, async handlers, unsubscribe |
| `test_worker_manager.py` | 10 | Lifecycle, pause/resume, error tracking, queries |
| `test_job_scheduler.py` | 10 | Add/remove, sync/async tasks, run_all, pending tasks |
| `test_retry_worker.py` | 10 | Success, retry, max retries, backoff, DLQ callback |
| `test_dead_letter_queue.py` | 8 | Add/get, replay success/failure, clear |
| `test_heartbeat_monitor.py` | 10 | Register, check healthy/unhealthy, async, tuple results |
| `test_scheduler_integration.py` | 7 | Event flow, worker+scheduler, retry→DLQ, heartbeat, full flow |
| **Total Sprint 12** | **75** | |

**Full test suite: 779 tests passing** (704 existing + 75 new)

---

## Key Constraints Enforced

- Engines must NOT call each other directly — all communication via EventBus
- EventBus is lightweight (in-memory) — production uses RedisEventBus
- WorkerManager does NOT execute tasks — it manages lifecycle only
- JobScheduler does NOT retry — failed tasks go to RetryWorker
- RetryWorker does NOT analyze — max retries → DeadLetterQueue
- HeartbeatMonitor does NOT recover — it reports, RecoveryCoordinator recovers
- All modules are independent — failure in one does not block others

---

## Files Created

- `docs/ARCHITECTURE_DECISIONS.md` — 10 ADRs
- `docs/sprint/SPRINT_12.md` — Sprint 12 spec
- `backend/engine/scheduler/__init__.py` — package exports
- `backend/engine/scheduler/bus.py` — EventBus
- `backend/engine/scheduler/manager.py` — WorkerManager, WorkerStatus
- `backend/engine/scheduler/scheduler.py` — JobScheduler, ScheduledTask
- `backend/engine/scheduler/retry.py` — RetryWorker
- `backend/engine/scheduler/dlq.py` — DeadLetterQueue, DeadLetterEntry
- `backend/engine/scheduler/heartbeat.py` — HeartbeatMonitor, HealthCheckResult
- `backend/tests/test_unit/test_event_bus.py` — 8 tests
- `backend/tests/test_unit/test_worker_manager.py` — 10 tests
- `backend/tests/test_unit/test_job_scheduler.py` — 10 tests
- `backend/tests/test_unit/test_retry_worker.py` — 10 tests
- `backend/tests/test_unit/test_dead_letter_queue.py` — 8 tests
- `backend/tests/test_unit/test_heartbeat_monitor.py` — 10 tests
- `backend/tests/test_unit/test_scheduler_integration.py` — 7 tests

## Files Modified

- `docs/ROADMAP.md` — Sprint 12 completed, milestone M6, changelog v5.2.0

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
| ✅ Sprint 10 | Portfolio & Risk Engine |
| ✅ Sprint 11 | Recovery & Resilience |
| ✅ Sprint 12 | Worker Scheduler & Event Bus |
