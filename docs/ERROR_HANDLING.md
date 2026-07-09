# ERROR HANDLING SPECIFICATION

**Version:** 1.0.0  
**Last Updated:** 2026-07-09  
**Status:** DRAFT

---

## 1. OVERVIEW

This document defines the error handling strategy for the UTOS trading system. Every error scenario has a defined response, retry policy, and escalation path.

### 1.1 Principles

- **Fail Fast**: Detect errors early, do not silently swallow
- **Never Crash**: The system must never crash from a recoverable error
- **Categorize**: Every error has a category, severity, and response
- **Retry with Backoff**: Transient errors use exponential backoff
- **Circuit Breaker**: Repeated failures trigger circuit breaker
- **Notify**: Critical errors notify the user and/or admin
- **Log Everything**: All errors are logged with full context

---

## 2. ERROR CATEGORIES

| Category | Description | Example |
|----------|-------------|---------|
| `EXCHANGE_ERROR` | Exchange API errors | Timeout, rate limit, invalid response |
| `NETWORK_ERROR` | Network connectivity errors | DNS failure, connection refused |
| `DATABASE_ERROR` | Database errors | Connection lost, constraint violation |
| `VALIDATION_ERROR` | Input validation errors | Invalid parameters, missing fields |
| `BUSINESS_LOGIC_ERROR` | Business rule violations | Insufficient balance, invalid state |
| `AUTH_ERROR` | Authentication/authorization errors | Invalid token, expired session |
| `CONFIG_ERROR` | Configuration errors | Missing env vars, invalid config |
| `SYSTEM_ERROR` | Internal system errors | Out of memory, disk full |
| `WEBSOCKET_ERROR` | WebSocket connection errors | Disconnection, parse error |
| `REDIS_ERROR` | Redis/event bus errors | Connection lost, publish failed |

---

## 3. ERROR SEVERITY

| Severity | Description | Response |
|----------|-------------|----------|
| `LOW` | Minor issue, no impact on trading | Log only |
| `MEDIUM` | Degraded functionality | Log + retry + notify system |
| `HIGH` | Trading impacted | Log + pause process + notify user |
| `CRITICAL` | System at risk | Log + stop process + notify user + admin alert |

---

## 4. EXCEPTION HIERARCHY

```python
class UTOSError(Exception):
    """Base exception for all UTOS errors."""
    category: str = "SYSTEM_ERROR"
    severity: str = "MEDIUM"
    error_code: str = "UNKNOWN"
    retryable: bool = False

class ExchangeError(UTOSError):
    category = "EXCHANGE_ERROR"
    
class ExchangeTimeoutError(ExchangeError):
    error_code = "EXCHANGE_TIMEOUT"
    retryable = True
    severity = "HIGH"

class ExchangeRateLimitError(ExchangeError):
    error_code = "EXCHANGE_RATE_LIMIT"
    retryable = True
    severity = "MEDIUM"

class ExchangeConnectionError(ExchangeError):
    error_code = "EXCHANGE_CONNECTION_FAILED"
    retryable = True
    severity = "HIGH"

class ExchangeAuthError(ExchangeError):
    error_code = "EXCHANGE_AUTH_FAILED"
    retryable = False
    severity = "HIGH"

class ExchangeInvalidOrderError(ExchangeError):
    error_code = "EXCHANGE_INVALID_ORDER"
    retryable = False
    severity = "MEDIUM"

class ExchangeInsufficientBalanceError(ExchangeError):
    error_code = "EXCHANGE_INSUFFICIENT_BALANCE"
    retryable = False
    severity = "HIGH"

class NetworkError(UTOSError):
    category = "NETWORK_ERROR"
    retryable = True
    severity = "MEDIUM"

class DatabaseError(UTOSError):
    category = "DATABASE_ERROR"
    
class DatabaseConnectionError(DatabaseError):
    error_code = "DB_CONNECTION_FAILED"
    retryable = True
    severity = "HIGH"

class DatabaseConstraintError(DatabaseError):
    error_code = "DB_CONSTRAINT_VIOLATION"
    retryable = False
    severity = "MEDIUM"

class ValidationError(UTOSError):
    category = "VALIDATION_ERROR"
    retryable = False
    severity = "LOW"

class BusinessLogicError(UTOSError):
    category = "BUSINESS_LOGIC_ERROR"
    retryable = False
    severity = "MEDIUM"

class InsufficientBalanceError(BusinessLogicError):
    error_code = "INSUFFICIENT_BALANCE"
    severity = "HIGH"

class InvalidStateTransitionError(BusinessLogicError):
    error_code = "INVALID_STATE_TRANSITION"
    severity = "MEDIUM"

class AuthError(UTOSError):
    category = "AUTH_ERROR"
    retryable = False
    severity = "MEDIUM"

class InvalidTokenError(AuthError):
    error_code = "INVALID_TOKEN"

class ExpiredTokenError(AuthError):
    error_code = "EXPIRED_TOKEN"

class ConfigError(UTOSError):
    category = "CONFIG_ERROR"
    retryable = False
    severity = "CRITICAL"

class WebSocketError(UTOSError):
    category = "WEBSOCKET_ERROR"
    retryable = True
    severity = "MEDIUM"

class RedisError(UTOSError):
    category = "REDIS_ERROR"
    retryable = True
    severity = "HIGH"
```

---

## 5. ERROR RESPONSE FLOWS

### 5.1 Exchange Timeout

```
Exchange API Call
    │
    ▼
Timeout (30s)
    │
    ▼
Retry 1 (wait 1s)
    │
    ├─ Success → Continue
    │
    ▼
Retry 2 (wait 2s)
    │
    ├─ Success → Continue
    │
    ▼
Retry 3 (wait 4s)
    │
    ├─ Success → Continue
    │
    ▼
Max Retries Exceeded
    │
    ▼
Emit TRADING_PROCESS_ERROR event
    │
    ▼
Trading Engine: Transition to ERROR state
    │
    ▼
Recovery Engine: Attempt recovery
    │
    ├─ Recovery Success → Resume trading
    │
    ▼
Recovery Failed
    │
    ▼
Transition to STOPPED state
    │
    ▼
Notify user: "Trading stopped due to exchange connectivity issues"
    │
    ▼
Admin alert: "Exchange timeout for user {user_id}, process {process_id}"
```

### 5.2 Exchange Rate Limit

```
Exchange API Call
    │
    ▼
HTTP 429 (Too Many Requests)
    │
    ▼
Read Retry-After header
    │
    ▼
Wait for specified duration (default: 5s)
    │
    ▼
Retry request
    │
    ├─ Success → Continue
    │
    ▼
If still rate limited after 3 retries:
    │
    ▼
Reduce request frequency (increase interval)
    │
    ▼
Log warning: "Rate limit hit, reducing frequency"
    │
    ▼
Continue with reduced frequency
```

### 5.3 Exchange Connection Lost

```
WebSocket Disconnect
    │
    ▼
Detect disconnection (heartbeat timeout)
    │
    ▼
Emit EXCHANGE_CONNECTION_LOST event
    │
    ▼
Attempt reconnect with exponential backoff:
    │
    ├─ Attempt 1: wait 1s
    │   ├─ Success → Resubscribe → Continue
    │   │
    ├─ Attempt 2: wait 2s
    │   ├─ Success → Resubscribe → Continue
    │   │
    ├─ Attempt 3: wait 4s
    │   ├─ Success → Resubscribe → Continue
    │   │
    ├─ Attempt 4: wait 8s
    │   ├─ Success → Resubscribe → Continue
    │   │
    ├─ Attempt 5: wait 16s
    │   ├─ Success → Resubscribe → Continue
    │   │
    ▼
Max reconnect attempts (5) exceeded
    │
    ▼
Transition trading process to ERROR state
    │
    ▼
Notify user: "Exchange connection lost"
    │
    ▼
Start recovery engine
    │
    ├─ Recovery success → Resume
    │
    ▼
Stop trading process
    │
    ▼
Notify user: "Trading stopped - unable to reconnect to exchange"
```

### 5.4 Database Connection Lost

```
Database Query
    │
    ▼
Connection Error
    │
    ▼
Retry 1 (wait 0.5s)
    │
    ├─ Success → Continue
    │
    ▼
Retry 2 (wait 1s)
    │
    ├─ Success → Continue
    │
    ▼
Retry 3 (wait 2s)
    │
    ├─ Success → Continue
    │
    ▼
Max retries exceeded
    │
    ▼
Switch to backup database (if available)
    │
    ├─ Success → Continue
    │
    ▼
Emit SYSTEM_ERROR event (severity: CRITICAL)
    │
    ▼
Graceful shutdown:
    │
    ├─ Pause all trading processes
    ├─ Cancel all pending orders
    ├─ Save state to Redis (cache)
    │
    ▼
Admin alert: "Database connection lost - system shutting down"
    │
    ▼
Notify all users: "System maintenance - trading paused"
```

### 5.5 Invalid State Transition

```
User requests action (e.g., start already-running process)
    │
    ▼
State machine check: Invalid transition
    │
    ▼
Raise InvalidStateTransitionError
    │
    ▼
API returns 409 Conflict:
    {
        "error": {
            "code": "INVALID_STATUS",
            "message": "Process cannot be started in current state: RUNNING"
        }
    }
    │
    ▼
Log warning with context
    │
    ▼
No state change, no side effects
```

### 5.6 Insufficient Balance

```
Create trading process
    │
    ▼
Check balance via exchange adapter
    │
    ▼
Balance < total_investment
    │
    ▼
Raise InsufficientBalanceError
    │
    ▼
API returns 400 Bad Request:
    {
        "error": {
            "code": "INSUFFICIENT_BALANCE",
            "message": "Insufficient balance. Required: 1000 USDT, Available: 500 USDT"
        }
    }
    │
    ▼
No orders placed, no state change
```

### 5.7 Order Rejected by Exchange

```
Place order on exchange
    │
    ▼
Exchange returns rejection
    │
    ▼
Parse reject reason
    │
    ├─ INSUFFICIENT_BALANCE → Notify user, stop process
    ├─ INVALID_SYMBOL → Log error, stop process
    ├─ PRICE_OUT_OF_RANGE → Adjust price, retry once
    ├─ ORDER_TOO_SMALL → Adjust quantity, retry once
    ├─ RATE_LIMITED → Wait and retry
    │
    ▼
Emit ORDER_REJECTED event
    │
    ▼
Update order status to REJECTED in database
    │
    ▼
Notify user: "Order rejected: {reason}"
    │
    ▼
Grid engine: Rebalance grid if needed
```

### 5.8 Redis Connection Lost

```
Event publish/subscribe
    │
    ▼
Redis connection error
    │
    ▼
Retry 1 (wait 0.5s)
    │
    ├─ Success → Continue
    │
    ▼
Retry 2 (wait 1s)
    │
    ├─ Success → Continue
    │
    ▼
Retry 3 (wait 2s)
    │
    ├─ Success → Continue
    │
    ▼
Max retries exceeded
    │
    ▼
Switch to fallback mode:
    │
    ├─ Stop publishing events
    ├─ Continue trading with local state
    ├─ Queue events for later publishing
    │
    ▼
Emit SYSTEM_ERROR event (severity: HIGH)
    │
    ▼
Admin alert: "Redis connection lost - running in degraded mode"
    │
    ▼
Attempt periodic reconnection
    │
    ├─ Reconnected → Flush queued events → Resume normal
    │
    ▼
If not reconnected within 5 minutes:
    │
    ▼
Pause all trading processes
    │
    ▼
Notify users: "System degraded - trading paused"
```

### 5.9 WebSocket Error (Frontend)

```
WebSocket Connection
    │
    ▼
Connection error / disconnect
    │
    ▼
Frontend: Show "Connection lost" indicator
    │
    ▼
Auto-reconnect with backoff:
    │
    ├─ Attempt 1: wait 1s
    ├─ Attempt 2: wait 2s
    ├─ Attempt 3: wait 4s
    ├─ Attempt 4: wait 8s
    ├─ Attempt 5: wait 16s
    │
    ▼
Max attempts exceeded
    │
    ▼
Show "Reconnect" button to user
    │
    ▼
Fallback to REST API polling (every 5s)
    │
    ▼
Log warning
```

### 5.10 Order Fill Mismatch (Reconciliation)

```
Recovery Engine: Sync with exchange
    │
    ▼
Compare local orders with exchange orders
    │
    ▼
Mismatch detected:
    │
    ├─ Local: OPEN, Exchange: FILLED
    │   │
    │   ▼
    │   Update local order to FILLED
    │   Emit ORDER_FILLED event
    │   Process fill (grid, portfolio, P&L)
    │
    ├─ Local: OPEN, Exchange: CANCELLED
    │   │
    │   ▼
    │   Update local order to CANCELLED
    │   Emit ORDER_CANCELLED event
    │   Grid: Rebalance
    │
    ├─ Local: FILLED, Exchange: not found
    │   │
    │   ▼
    │   Log critical: "Phantom fill detected"
    │   Admin alert
    │   Manual investigation required
    │
    ├─ Local: not found, Exchange: OPEN
    │   │
    │   ▼
    │   Create local order record
    │   Log warning: "Orphan order detected"
    │   Attempt to associate with trading process
    │
    ▼
Emit RECONCILIATION_COMPLETE event
```

---

## 6. RETRY POLICIES

### 6.1 Standard Retry Policy

| Parameter | Value |
|-----------|-------|
| Max retries | 3 |
| Initial delay | 1 second |
| Backoff multiplier | 2 (exponential) |
| Max delay | 30 seconds |
| Jitter | ±20% of delay |

### 6.2 Exchange-Specific Retry Policy

| Parameter | Value |
|-----------|-------|
| Max retries | 5 |
| Initial delay | 1 second |
| Backoff multiplier | 2 (exponential) |
| Max delay | 60 seconds |
| Jitter | ±20% of delay |
| Retry on | Timeout, 5xx, 429, Network error |
| No retry on | 400, 401, 403, 404 |

### 6.3 Database Retry Policy

| Parameter | Value |
|-----------|-------|
| Max retries | 3 |
| Initial delay | 0.5 seconds |
| Backoff multiplier | 2 (exponential) |
| Max delay | 5 seconds |
| Jitter | ±10% of delay |

### 6.4 Implementation

```python
import asyncio
import random
from functools import wraps

def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_multiplier: float = 2.0,
    max_delay: float = 30.0,
    jitter: float = 0.2,
    retryable_exceptions: tuple = (Exception,),
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    
                    jitter_amount = delay * jitter * (random.random() * 2 - 1)
                    actual_delay = min(delay + jitter_amount, max_delay)
                    
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} after {actual_delay:.2f}s",
                        error=str(e),
                        function=func.__name__,
                    )
                    
                    await asyncio.sleep(actual_delay)
                    delay *= backoff_multiplier
            
            raise last_exception
        return wrapper
    return decorator
```

---

## 7. CIRCUIT BREAKER

### 7.1 Configuration

| Parameter | Value |
|-----------|-------|
| Failure threshold | 5 consecutive failures |
| Recovery timeout | 60 seconds |
| Half-open max calls | 3 |

### 7.2 States

```
CLOSED (normal)
    │
    ▼
5 consecutive failures
    │
    ▼
OPEN (rejecting all calls)
    │
    ▼
60 seconds elapsed
    │
    ▼
HALF-OPEN (allowing limited test calls)
    │
    ├─ Test call succeeds → CLOSED
    │
    ▼
Test call fails
    │
    ▼
OPEN (back to rejecting)
```

### 7.3 Implementation

```python
class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self._state = "closed"
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0

    async def call(self, func, *args, **kwargs):
        if self._state == "open":
            if self._should_attempt_reset():
                self._state = "half_open"
                self._half_open_calls = 0
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")
        
        if self._state == "half_open" and self._half_open_calls >= self.half_open_max_calls:
            raise CircuitBreakerOpenError("Circuit breaker is half-open, max calls reached")
        
        try:
            if self._state == "half_open":
                self._half_open_calls += 1
            
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self._failure_count = 0
        self._state = "closed"

    def _on_failure(self):
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()
        
        if self._state == "half_open":
            self._state = "open"
        elif self._failure_count >= self.failure_threshold:
            self._state = "open"

    def _should_attempt_reset(self) -> bool:
        if self._last_failure_time is None:
            return True
        elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
```

---

## 8. DEAD LETTER QUEUE

### 8.1 Purpose

Events that fail to process after max retries are sent to a dead letter queue (DLQ) for manual inspection and replay.

### 8.2 Flow

```
Event Consumer
    │
    ▼
Process event
    │
    ├─ Success → Done
    │
    ▼
Failure
    │
    ▼
Retry (up to 3 times)
    │
    ├─ Success → Done
    │
    ▼
Max retries exceeded
    │
    ▼
Move to DLQ (Redis list: "dlq:{event_type}")
    │
    ▼
Log error with full context
    │
    ▼
Admin alert (if severity >= HIGH)
```

### 8.3 DLQ Entry Format

```json
{
  "original_event": { ... },
  "error": {
    "type": "ExchangeTimeoutError",
    "message": "Exchange API timeout",
    "traceback": "..."
  },
  "retry_count": 3,
  "first_attempt": "2026-07-09T10:00:00Z",
  "last_attempt": "2026-07-09T10:00:15Z",
  "dlq_entry_at": "2026-07-09T10:00:16Z"
}
```

---

## 9. ERROR NOTIFICATION MATRIX

| Error | Notify User | Notify Admin | Alert (PagerDuty) |
|-------|-------------|--------------|-------------------|
| Exchange timeout | Yes (after stop) | Yes | No |
| Exchange rate limit | No | No | No |
| Exchange connection lost | Yes (after stop) | Yes | No |
| Exchange auth failed | Yes | Yes | No |
| Database connection lost | Yes (maintenance) | Yes | Yes |
| Redis connection lost | No | Yes | No |
| Invalid state transition | No (API error) | No | No |
| Insufficient balance | Yes (API error) | No | No |
| Order rejected | Yes | No | No |
| System error (critical) | Yes | Yes | Yes |
| WebSocket disconnect | No (auto-reconnect) | No | No |
| Phantom fill detected | No | Yes | Yes |

---

## 10. ERROR LOGGING FORMAT

```python
logger.error(
    "Exchange timeout",
    extra={
        "error_code": "EXCHANGE_TIMEOUT",
        "error_category": "EXCHANGE_ERROR",
        "severity": "HIGH",
        "exchange": "binance",
        "operation": "place_order",
        "symbol": "BTCUSDT",
        "trading_process_id": "uuid",
        "user_id": "uuid",
        "retry_count": 3,
        "elapsed_seconds": 30.0,
        "traceback": traceback.format_exc(),
    }
)
```

---

## 11. API ERROR RESPONSE FORMAT

### 11.1 Standard Error

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "email",
      "issue": "Invalid email format"
    }
  }
}
```

### 11.2 Multiple Validation Errors

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Multiple validation errors",
    "details": [
      {
        "field": "email",
        "issue": "Invalid email format"
      },
      {
        "field": "password",
        "issue": "Password must be at least 8 characters"
      }
    ]
  }
}
```

### 11.3 Internal Server Error

```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred",
    "request_id": "uuid"
  }
}
```

---

## 12. CHANGE LOG

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-09 | 1.0.0 | Initial error handling specification |
