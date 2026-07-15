# Sprint 12: Worker Scheduler & Event Bus

**Version Target:** v0.12.0  
**Status:** In Progress  
**Dependencies:** Sprint 05–11

---

## Objective

Implement event-driven orchestration, background job scheduling, and observability infrastructure. This sprint transforms UTOS from a collection of engines into a **coordinated system** where all components communicate via events, not direct calls.

---

## 6-Module Architecture

```
engine/scheduler/
    ├── __init__.py          — package exports
    ├── bus.py               — Simple in-memory EventBus (pub/sub)
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

## Module Breakdown

### Module 1: EventBus (`scheduler.bus`)
**Purpose:** In-memory pub/sub event bus for testing and worker orchestration. Production uses RedisEventBus.

```python
class EventBus:
    async def publish(event_type: str, data: dict, metadata: dict = None) -> str
    async def subscribe(event_type: str, handler: Callable) -> str
    async def unsubscribe(subscription_id: str) -> None
    def get_subscribers(event_type: str) -> list[Callable]
    def get_metrics() -> dict[str, int]
```

Key constraints:
- Does NOT replace RedisEventBus — it's for testing and lightweight use
- Async by default (supports sync handlers via wrapper)
- Metrics tracked: events_published, events_delivered, subscribers_count

### Module 2: WorkerManager (`scheduler.manager`)
**Purpose:** Manages worker lifecycle: start, stop, pause, resume, health.

```python
class WorkerManager:
    async def start_worker(name: str, coroutine: Callable) -> str
    async def stop_worker(name: str) -> bool
    async def pause_worker(name: str) -> bool
    async def resume_worker(name: str) -> bool
    def get_worker_status(name: str) -> WorkerStatus
    def get_all_workers() -> list[WorkerStatus]
    def get_metrics() -> dict[str, int]
```

### Module 3: JobScheduler (`scheduler.scheduler`)
**Purpose:** Schedules periodic tasks with configurable intervals.

```python
class JobScheduler:
    async def add_task(task: ScheduledTask) -> str
    async def remove_task(task_id: str) -> bool
    async def run_all() -> list[TaskResult]
    def get_pending_tasks() -> list[ScheduledTask]
    def get_task_count() -> int
```

Task types: `cleanup`, `checkpoint`, `heartbeat`, `sync`, `retry`

### Module 4: RetryWorker (`scheduler.retry`)
**Purpose:** Handles failed job retries with exponential backoff.

```python
class RetryWorker:
    async def submit(task: Task) -> str
    async def process_queue() -> list[TaskResult]
    def get_queue_size() -> int
    def get_max_retries() -> int
    def get_backoff_seconds(retry_count: int) -> int
```

Rules:
- Max 3 retries with exponential backoff: 1s, 2s, 4s
- After max retries → move to DeadLetterQueue
- Backoff is configurable (default: 1, 2, 4 seconds)

### Module 5: DeadLetterQueue (`scheduler.dlq`)
**Purpose:** Stores failed events/tasks for analysis and replay.

```python
class DeadLetterQueue:
    async def add(event: Event, reason: str) -> None
    def get_all() -> list[DeadLetterEntry]
    def get_by_event_type(event_type: str) -> list[DeadLetterEntry]
    def replay(entry: DeadLetterEntry) -> bool
    def clear() -> None
    def get_metrics() -> dict[str, int]
```

### Module 6: HeartbeatMonitor (`scheduler.heartbeat`)
**Purpose:** Monitors health of all system components.

```python
class HeartbeatMonitor:
    async def register(component: str, check_fn: Callable) -> None
    async def check_all() -> list[HealthCheckResult]
    async def check(component: str) -> HealthCheckResult
    def get_unhealthy() -> list[HealthCheckResult]
    def get_metrics() -> dict[str, int]
```

Monitors: Trading Process, Worker, Exchange Connector, Market Hub, EventBus

---

## Data Types

```python
@dataclass
class WorkerStatus:
    name: str
    state: str  # "idle" | "running" | "paused" | "stopped" | "error"
    started_at: datetime | None
    stopped_at: datetime | None
    error_count: int

@dataclass
class ScheduledTask:
    id: str
    name: str
    task_type: str  # "cleanup" | "checkpoint" | "heartbeat" | "sync" | "retry"
    interval_seconds: int
    coroutine: Callable
    last_run: datetime | None
    next_run: datetime | None
    enabled: bool

@dataclass
class HealthCheckResult:
    component: str
    healthy: bool
    last_check: datetime
    response_time_ms: float
    error: str | None
```

---

## Key Constraints

- Engines must NOT call each other directly — all communication via EventBus
- EventBus is lightweight (in-memory) — production uses RedisEventBus
- WorkerManager does NOT execute tasks — it manages lifecycle
- JobScheduler does NOT retry — failed tasks go to RetryWorker
- RetryWorker does NOT analyze — max retries → DeadLetterQueue
- HeartbeatMonitor does NOT recover — it reports, RecoveryCoordinator recovers
- All modules are independent — failure in one does not block others

---

## Acceptance Criteria

- [ ] EventBus routes events to all subscribers
- [ ] WorkerManager manages start/stop/pause/resume lifecycle
- [ ] JobScheduler runs periodic tasks (cleanup, checkpoint, heartbeat, sync)
- [ ] RetryWorker retries failed jobs with exponential backoff (1s, 2s, 4s)
- [ ] DeadLetterQueue stores failed events after max retries
- [ ] HeartbeatMonitor monitors all 4 component types
- [ ] Adding a new engine requires only subscribing to EventBus
- [ ] Unit tests for all 6 modules
- [ ] Integration tests for event flow across engines
- [ ] No regressions in existing 704 tests
