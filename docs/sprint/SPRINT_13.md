# Sprint 13: Notification & Automation

**Version Target:** v0.13.0
**Status:** In Progress
**Dependencies:** Sprint 05–12

---

## Objective

Implement a multi-channel notification system with template-based messaging, async queue processing, and automation rules. Notifications are decoupled from trading — a Telegram failure must NOT block trading.

---

## 5-Module Architecture

```
engine/notification/
    ├── __init__.py          — package exports
    ├── channels.py          — Notification channels (Email, Telegram, Discord, Webhook)
    ├── template.py          — TemplateEngine (render notifications from templates)
    ├── queue.py             — NotificationQueue (async queue + worker)
    ├── service.py           — NotificationService (orchestrator)
    └── automation.py        — AutomationRules (condition-based triggers)
```

**Notification flow:**
```
Engine → EventBus → NotificationQueue → Worker → TemplateEngine → Channel
```

---

## Module Breakdown

### Module 1: NotificationChannels (`notification.channels`)
**Purpose:** Send notifications via different channels.

```python
class NotificationChannel(ABC):
    async def send(recipient: str, title: str, message: str, data: dict) -> bool

class EmailChannel(NotificationChannel): ...
class TelegramChannel(NotificationChannel): ...
class DiscordChannel(NotificationChannel): ...
class WebhookChannel(NotificationChannel): ...
```

Key constraints:
- Each channel is independent — failure in one does not affect others
- Channels use callback-based sending (no direct SMTP/HTTP in tests)
- Each channel tracks its own metrics

### Module 2: TemplateEngine (`notification.template`)
**Purpose:** Render notification messages from templates.

```python
class TemplateEngine:
    def register_template(name: str, template: NotificationTemplate) -> None
    def render(template_name: str, context: dict) -> NotificationMessage
    def list_templates() -> list[str]
```

Templates support:
- Title and message with `{variable}` placeholders
- Channel-specific formatting (e.g., Telegram markdown vs plain email)
- Default templates: order_filled, order_failed, grid_completed, profit_lock_triggered, recovery_failed, risk_rejected

### Module 3: NotificationQueue (`notification.queue`)
**Purpose:** Async queue with worker pattern.

```python
class NotificationQueue:
    async def enqueue(notification: QueuedNotification) -> str
    async def process() -> list[NotificationResult]
    def get_pending_count() -> int
    def get_metrics() -> dict
```

Key constraints:
- Queue is in-memory (production uses Redis)
- Worker processes queue items sequentially
- Failed notifications are retried (max 3) then moved to DLQ
- Queue does NOT send directly — delegates to NotificationService

### Module 4: NotificationService (`notification.service`)
**Purpose:** Orchestrates channels, templates, and queue.

```python
class NotificationService:
    def register_channel(name: str, channel: NotificationChannel) -> None
    def register_template(name: str, template: NotificationTemplate) -> None
    async def notify(user_id: str, template_name: str, channel: str, context: dict) -> str
    async def notify_multi(user_id: str, template_name: str, channels: list[str], context: dict) -> list[str]
    def get_metrics() -> dict
```

### Module 5: AutomationRules (`notification.automation`)
**Purpose:** Condition-based notification triggers.

```python
class AutomationRules:
    def add_rule(rule: AutomationRule) -> str
    def remove_rule(rule_id: str) -> bool
    async def evaluate(event_type: str, data: dict) -> list[AutomationAction]
    def get_rules() -> list[AutomationRule]
```

Rule examples:
- `profit > 10%` → send Telegram
- `recovery_failed` → email admin
- `risk_rejected` → webhook

---

## Data Types

```python
@dataclass
class NotificationTemplate:
    name: str
    title_template: str
    message_template: str
    channel_format: dict[str, str]  # channel-specific overrides

@dataclass
class NotificationMessage:
    title: str
    message: str
    channel: str

@dataclass
class QueuedNotification:
    id: str
    user_id: str
    channel: str
    title: str
    message: str
    data: dict
    retry_count: int
    max_retries: int
    created_at: datetime

@dataclass
class NotificationResult:
    notification_id: str
    channel: str
    status: str  # success | failed | retry
    error: str | None
    sent_at: datetime

@dataclass
class AutomationRule:
    id: str
    name: str
    event_type: str
    condition: Callable[[dict], bool]
    action_channel: str
    action_template: str
    enabled: bool

@dataclass
class AutomationAction:
    rule_id: str
    channel: str
    template: str
    context: dict
```

---

## Key Constraints

- NotificationService does NOT send directly — uses queue
- Queue does NOT send directly — uses channels via service
- Channels do NOT know about templates — they receive final title + message
- TemplateEngine does NOT know about channels — it renders messages
- AutomationRules do NOT send — they return actions for the service to execute
- All modules are independent — failure in one does not block others
- No channel failure may block trading

---

## Acceptance Criteria

- [ ] 4 notification channels: Email, Telegram, Discord, Webhook
- [ ] TemplateEngine renders messages with variable substitution
- [ ] NotificationQueue processes items with retry (max 3) → DLQ
- [ ] NotificationService orchestrates channels + templates + queue
- [ ] AutomationRules evaluate events and trigger notifications
- [ ] Channel failure does NOT block other channels
- [ ] Notification failure does NOT block trading
- [ ] Unit tests for all 5 modules
- [ ] Integration tests for full flow: event → queue → template → channel
- [ ] No regressions in existing 779 tests
