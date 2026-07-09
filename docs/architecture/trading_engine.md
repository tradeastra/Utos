# STATE MACHINE SPECIFICATION

**Version:** 1.0.0  
**Last Updated:** 2026-07-09  
**Status:** DRAFT

---

## 1. OVERVIEW

This document defines the state machines for key entities in the UTOS trading system. State machines ensure consistent behavior and prevent invalid state transitions.

### 1.1 State Machine Principles

- **Explicit States**: All states are explicitly defined
- **Valid Transitions**: Only valid transitions are allowed
- **Event-Driven**: State changes are triggered by events
- **Auditable**: All state transitions are logged
- **Recoverable**: System can recover from error states

---

## 2. TRADING PROCESS STATE MACHINE

### 2.1 States

| State | Description |
|-------|-------------|
| `CREATED` | Trading process has been created but not initialized |
| `READY` | Trading process is initialized and ready to start |
| `RUNNING` | Trading process is actively trading |
| `PAUSED` | Trading process is paused by user |
| `STOPPING` | Trading process is in the process of stopping |
| `STOPPED` | Trading process has been stopped |
| `ERROR` | Trading process encountered an error |
| `RECOVERING` | Trading process is recovering from error |

### 2.2 State Transitions

```
┌─────────┐
│ CREATED │
└────┬────┘
     │ initialize()
     ▼
┌─────────┐
│  READY  │
└────┬────┘
     │ start()
     ▼
┌─────────┐
│ RUNNING │◄──────────┐
└────┬────┘           │
     │ pause()        │ resume()
     ▼                │
┌─────────┐           │
│ PAUSED  │───────────┘
└────┬────┘
     │ stop()
     ▼
┌──────────┐
│ STOPPING │
└────┬─────┘
     │ stop_completed()
     ▼
┌─────────┐
│ STOPPED │
└─────────┘

     │ error()
     ▼
┌─────────┐
│  ERROR  │
└────┬────┘
     │ recover()
     ▼
┌───────────┐
│ RECOVERING │
└─────┬─────┘
      │ recovery_completed()
      ▼
┌─────────┐
│ RUNNING │
└─────────┘
```

### 2.3 Transition Rules

| From State | To State | Trigger | Conditions |
|------------|----------|---------|------------|
| `CREATED` | `READY` | `initialize()` | Grid profile valid, balance sufficient |
| `READY` | `RUNNING` | `start()` | User authorization, exchange connected |
| `RUNNING` | `PAUSED` | `pause()` | User request |
| `PAUSED` | `RUNNING` | `resume()` | User request |
| `RUNNING` | `STOPPING` | `stop()` | User request or error |
| `PAUSED` | `STOPPING` | `stop()` | User request |
| `STOPPING` | `STOPPED` | `stop_completed()` | All orders cancelled, positions closed |
| `RUNNING` | `ERROR` | `error()` | Exchange error, system error |
| `PAUSED` | `ERROR` | `error()` | System error |
| `ERROR` | `RECOVERING` | `recover()` | Recovery strategy available |
| `RECOVERING` | `RUNNING` | `recovery_completed()` | State restored successfully |
| `RECOVERING` | `ERROR` | `recovery_failed()` | Recovery failed |
| `ERROR` | `STOPPED` | `stop()` | Manual stop after error |

### 2.4 State-Specific Behaviors

**CREATED**:
- No orders can be placed
- Grid levels are calculated but not activated
- User can modify parameters

**READY**:
- Grid levels are activated
- Orders are placed but not executed
- User can modify parameters

**RUNNING**:
- All orders are active
- Grid trading is executing
- Profit lock is monitoring
- User cannot modify parameters

**PAUSED**:
- No new orders are placed
- Existing orders remain active
- User can modify parameters
- Grid levels are frozen

**STOPPING**:
- All orders are being cancelled
- Positions are being closed
- No new operations allowed

**STOPPED**:
- All orders cancelled
- All positions closed
- Final P&L calculated
- Cannot be restarted

**ERROR**:
- Trading suspended
- Error logged
- User notified
- Recovery attempted

**RECOVERING**:
- State synchronization in progress
- Orders being reconciled
- User notified

---

## 3. ORDER STATE MACHINE

### 3.1 States

| State | Description |
|-------|-------------|
| `PENDING` | Order created, waiting to be placed on exchange |
| `OPEN` | Order placed on exchange, waiting to be filled |
| `PARTIALLY_FILLED` | Order partially filled |
| `FILLED` | Order fully filled |
| `CANCELLED` | Order cancelled by user or system |
| `REJECTED` | Order rejected by exchange |
| `EXPIRED` | Order expired (time-based) |

### 3.2 State Transitions

```
┌─────────┐
│ PENDING │
└────┬────┘
     │ place_order()
     ▼
┌─────────┐
│  OPEN   │◄──────────────┐
└────┬────┘               │
     │ partial_fill()     │
     ▼                    │
┌─────────────────┐       │
│ PARTIALLY_FILLED │───────┘
└────┬────────────┘
     │ fill()
     ▼
┌─────────┐
│ FILLED  │
└─────────┘

     │ cancel()
     ▼
┌───────────┐
│ CANCELLED │
└───────────┘

     │ reject()
     ▼
┌───────────┐
│ REJECTED  │
└───────────┘

     │ expire()
     ▼
┌─────────┐
│ EXPIRED │
└─────────┘
```

### 3.3 Transition Rules

| From State | To State | Trigger | Conditions |
|------------|----------|---------|------------|
| `PENDING` | `OPEN` | `place_order()` | Exchange accepts order |
| `PENDING` | `REJECTED` | `reject()` | Exchange rejects order |
| `OPEN` | `PARTIALLY_FILLED` | `partial_fill()` | Partial fill received |
| `OPEN` | `FILLED` | `fill()` | Full fill received |
| `OPEN` | `CANCELLED` | `cancel()` | User or system cancellation |
| `OPEN` | `EXPIRED` | `expire()` | Time limit reached |
| `PARTIALLY_FILLED` | `FILLED` | `fill()` | Remaining quantity filled |
| `PARTIALLY_FILLED` | `CANCELLED` | `cancel()` | User or system cancellation |
| `PARTIALLY_FILLED` | `EXPIRED` | `expire()` | Time limit reached |

### 3.4 State-Specific Behaviors

**PENDING**:
- Order exists in database only
- Not yet sent to exchange
- Can be cancelled

**OPEN**:
- Order active on exchange
- Monitoring for fills
- Can be cancelled

**PARTIALLY_FILLED**:
- Some quantity filled
- Remaining quantity still active
- Can be cancelled

**FILLED**:
- Order complete
- P&L calculated
- Triggers grid level actions

**CANCELLED**:
- Order cancelled on exchange
- No further action
- May trigger grid rebalancing

**REJECTED**:
- Order rejected by exchange
- Error logged
- User notified

**EXPIRED**:
- Order expired without fill
- No further action
- May trigger grid rebalancing

---

## 4. GRID STATE MACHINE

### 4.1 States

| State | Description |
|-------|-------------|
| `IDLE` | Grid not initialized |
| `INITIALIZED` | Grid levels calculated |
| `ACTIVE` | Grid levels are active and trading |
| `PAUSED` | Grid is paused |
| `COMPLETED` | All grid levels completed |
| `ERROR` | Grid encountered error |

### 4.2 State Transitions

```
┌─────────┐
│  IDLE   │
└────┬────┘
     │ initialize()
     ▼
┌─────────────┐
│ INITIALIZED │
└──────┬──────┘
       │ activate()
       ▼
┌─────────┐
│ ACTIVE  │◄──────────┐
└────┬────┘           │
     │ pause()        │ resume()
     ▼                │
┌─────────┐           │
│ PAUSED  │───────────┘
└────┬────┘
     │ complete()
     ▼
┌───────────┐
│ COMPLETED │
└───────────┘

     │ error()
     ▼
┌─────────┐
│  ERROR  │
└─────────┘
```

### 4.3 Transition Rules

| From State | To State | Trigger | Conditions |
|------------|----------|---------|------------|
| `IDLE` | `INITIALIZED` | `initialize()` | Grid profile valid |
| `INITIALIZED` | `ACTIVE` | `activate()` | Trading process started |
| `ACTIVE` | `PAUSED` | `pause()` | Trading process paused |
| `PAUSED` | `ACTIVE` | `resume()` | Trading process resumed |
| `ACTIVE` | `COMPLETED` | `complete()` | All levels filled |
| `ACTIVE` | `ERROR` | `error()` | Grid calculation error |
| `ERROR` | `ACTIVE` | `recover()` | Error resolved |

### 4.4 State-Specific Behaviors

**IDLE**:
- Grid not created
- No levels calculated
- Can be initialized

**INITIALIZED**:
- Levels calculated
- Orders prepared
- Waiting for activation

**ACTIVE**:
- All levels active
- Orders placed
- Monitoring fills
- Rebalancing as needed

**PAUSED**:
- No new orders
- Existing orders remain
- Levels frozen

**COMPLETED**:
- All levels filled
- Final P&L calculated
- Cannot be reactivated

**ERROR**:
- Grid calculation failed
- Trading suspended
- Recovery attempted

---

## 5. SESSION STATE MACHINE

### 5.1 States

| State | Description |
|-------|-------------|
| `ANONYMOUS` | User not authenticated |
| `AUTHENTICATED` | User logged in |
| `LOCKED` | Account locked (too many failed attempts) |
| `TERMINATED` | Session terminated |

### 5.2 State Transitions

```
┌───────────┐
│ ANONYMOUS │
└─────┬─────┘
      │ login()
      ▼
┌──────────────┐
│ AUTHENTICATED│◄──────────┐
└──────┬───────┘           │
       │ logout()          │ login()
       ▼                    │
┌───────────┐               │
│ TERMINATED│───────────────┘
└───────────┘

      │ failed_login()
      ▼
┌─────────┐
│ LOCKED  │
└────┬────┘
     │ unlock()
     ▼
┌───────────┐
│ ANONYMOUS │
└───────────┘
```

### 5.3 Transition Rules

| From State | To State | Trigger | Conditions |
|------------|----------|---------|------------|
| `ANONYMOUS` | `AUTHENTICATED` | `login()` | Valid credentials |
| `ANONYMOUS` | `LOCKED` | `failed_login()` | Too many failed attempts |
| `AUTHENTICATED` | `TERMINATED` | `logout()` | User logout or timeout |
| `AUTHENTICATED` | `LOCKED` | `failed_login()` | Too many failed attempts (different IP) |
| `LOCKED` | `ANONYMOUS` | `unlock()` | Admin unlock or timeout |

### 5.4 State-Specific Behaviors

**ANONYMOUS**:
- No access to protected resources
- Can attempt login
- Limited API access

**AUTHENTICATED**:
- Full access to user resources
- JWT token valid
- Session timeout monitored

**LOCKED**:
- No login allowed
- Security measure
- Requires admin intervention

**TERMINATED**:
- Session ended
- Token invalidated
- Must re-authenticate

---

## 6. EXCHANGE CONNECTION STATE MACHINE

### 6.1 States

| State | Description |
|-------|-------------|
| `DISCONNECTED` | Not connected to exchange |
| `CONNECTING` | Connection in progress |
| `CONNECTED` | Successfully connected |
| `AUTHENTICATED` | API authentication successful |
| `ERROR` | Connection error |
| `RECONNECTING` | Attempting to reconnect |

### 6.2 State Transitions

```
┌─────────────┐
│ DISCONNECTED│◄─────────────────┐
└──────┬──────┘                  │
       │ connect()               │
       ▼                          │
┌─────────────┐                  │
│ CONNECTING  │                  │
└──────┬──────┘                  │
       │ connected()             │
       ▼                          │
┌─────────────┐                  │
│  CONNECTED  │                  │
└──────┬──────┘                  │
       │ authenticate()          │
       ▼                          │
┌──────────────┐                 │
│ AUTHENTICATED│─────────────────┘
└──────┬───────┘
       │ error()
       ▼
┌─────────┐
│  ERROR  │
└────┬────┘
     │ reconnect()
     ▼
┌──────────────┐
│ RECONNECTING │
└──────┬───────┘
       │ connected()
       ▼
┌─────────────┐
│  CONNECTED  │
└─────────────┘
```

### 6.3 Transition Rules

| From State | To State | Trigger | Conditions |
|------------|----------|---------|------------|
| `DISCONNECTED` | `CONNECTING` | `connect()` | User request or auto-connect |
| `CONNECTING` | `CONNECTED` | `connected()` | Connection successful |
| `CONNECTING` | `ERROR` | `error()` | Connection failed |
| `CONNECTED` | `AUTHENTICATED` | `authenticate()` | API credentials valid |
| `CONNECTED` | `ERROR` | `error()` | Authentication failed |
| `AUTHENTICATED` | `ERROR` | `error()` | Connection lost |
| `ERROR` | `RECONNECTING` | `reconnect()` | Auto-reconnect triggered |
| `RECONNECTING` | `CONNECTED` | `connected()` | Reconnection successful |
| `RECONNECTING` | `ERROR` | `error()` | Reconnection failed |
| `AUTHENTICATED` | `DISCONNECTED` | `disconnect()` | User request |
| `ERROR` | `DISCONNECTED` | `disconnect()` | User request or give up |

### 6.4 State-Specific Behaviors

**DISCONNECTED**:
- No exchange operations
- Can initiate connection
- API keys stored

**CONNECTING**:
- Connection attempt in progress
- No operations allowed
- Timeout monitored

**CONNECTED**:
- Connection established
- Waiting for authentication
- Limited operations

**AUTHENTICATED**:
- Full operations available
- WebSocket subscriptions active
- Rate limiting enforced

**ERROR**:
- Connection failed
- Error logged
- Reconnection attempted

**RECONNECTING**:
- Reconnection in progress
- Exponential backoff
- Max retry limit

---

## 7. IMPLEMENTATION GUIDELINES

### 7.1 State Machine Pattern

Use the State pattern for implementing state machines:

```python
from abc import ABC, abstractmethod
from enum import Enum

class TradingProcessState(ABC):
    """Base class for trading process states."""
    
    @abstractmethod
    def start(self, context: TradingProcessContext) -> TradingProcessState:
        pass
    
    @abstractmethod
    def pause(self, context: TradingProcessContext) -> TradingProcessState:
        pass
    
    @abstractmethod
    def stop(self, context: TradingProcessContext) -> TradingProcessState:
        pass

class CreatedState(TradingProcessState):
    def start(self, context: TradingProcessContext) -> TradingProcessState:
        # Validate and initialize
        return ReadyState()
    
    def pause(self, context: TradingProcessContext) -> TradingProcessState:
        raise InvalidStateTransition("Cannot pause from CREATED")
    
    def stop(self, context: TradingProcessContext) -> TradingProcessState:
        return StoppedState()

class RunningState(TradingProcessState):
    def start(self, context: TradingProcessContext) -> TradingProcessState:
        raise InvalidStateTransition("Already running")
    
    def pause(self, context: TradingProcessContext) -> TradingProcessState:
        # Pause trading
        return PausedState()
    
    def stop(self, context: TradingProcessContext) -> TradingProcessState:
        # Initiate stop
        return StoppingState()
```

### 7.2 State Transition Logging

Log all state transitions for audit:

```python
def transition_to(self, new_state: TradingProcessState, reason: str):
    old_state = self.current_state
    self.current_state = new_state
    
    logger.info(
        "State transition",
        extra={
            "trading_process_id": self.id,
            "old_state": old_state.name,
            "new_state": new_state.name,
            "reason": reason,
            "timestamp": datetime.utcnow()
        }
    )
    
    # Emit event
    event_bus.publish(
        "TRADING_PROCESS_STATE_CHANGED",
        {
            "trading_process_id": self.id,
            "old_state": old_state.name,
            "new_state": new_state.name,
            "reason": reason
        }
    )
```

### 7.3 State Persistence

Persist state to database for recovery:

```python
def save_state(self):
    state_record = TradingProcessStateRecord(
        trading_process_id=self.id,
        state=self.current_state.name,
        transitioned_at=datetime.utcnow()
    )
    db.add(state_record)
    db.commit()
```

---

## 8. ERROR HANDLING

### 8.1 Invalid State Transitions

Throw exception for invalid transitions:

```python
class InvalidStateTransition(Exception):
    def __init__(self, message: str, from_state: str, to_state: str):
        self.message = message
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(message)
```

### 8.2 State Recovery

Implement recovery strategies for error states:

```python
def recover_from_error(self):
    if self.current_state == ERROR:
        # Attempt state synchronization
        success = self.sync_with_exchange()
        
        if success:
            self.transition_to(RUNNING, "Recovery successful")
        else:
            self.transition_to(STOPPED, "Recovery failed")
```

---

## 9. CHANGE LOG

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-09 | 1.0.0 | Initial state machine specification |
