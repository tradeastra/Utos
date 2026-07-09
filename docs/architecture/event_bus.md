# EVENT BUS SPECIFICATION

**Version:** 1.0.0  
**Last Updated:** 2026-07-09  
**Status:** DRAFT

---

## 1. OVERVIEW

The UTOS system uses an event-driven architecture with Redis as the event bus. Events are immutable messages that are published by producers and consumed by subscribers.

### 1.1 Event Flow

```
Event Producer → Redis Pub/Sub → Event Consumers
```

### 1.2 Event Naming Convention

- Use **past tense** for events (e.g., `ORDER_FILLED`, `PRICE_UPDATED`)
- Use **uppercase with underscores**
- Be **descriptive but concise**

### 1.3 Event Structure

All events follow this structure:

```json
{
  "event_type": "EVENT_NAME",
  "event_id": "uuid",
  "timestamp": "2026-07-09T10:00:00Z",
  "data": { ... },
  "metadata": {
    "source": "service_name",
    "correlation_id": "uuid"
  }
}
```

---

## 2. MARKET EVENTS

### 2.1 PRICE_UPDATE

**Description**: Emitted when market price changes for a symbol.

**Event Type**: `PRICE_UPDATE`

**Data Schema**:
```json
{
  "symbol": "BTCUSDT",
  "exchange": "binance",
  "price": 50000.0,
  "price_change": 100.0,
  "price_change_percentage": 0.2,
  "volume_24h": 1000000.0,
  "timestamp": "2026-07-09T10:00:00Z"
}
```

**Producers**: Market Hub, Exchange Adapters

**Consumers**: Trading Engine, Portfolio Engine, Risk Engine

---

### 2.2 TICKER_UPDATE

**Description**: Emitted when ticker data is updated.

**Event Type**: `TICKER_UPDATE`

**Data Schema**:
```json
{
  "symbol": "BTCUSDT",
  "exchange": "binance",
  "bid": 49999.0,
  "ask": 50001.0,
  "last": 50000.0,
  "volume": 1000.0,
  "timestamp": "2026-07-09T10:00:00Z"
}
```

**Producers**: Market Hub, Exchange Adapters

**Consumers**: Trading Engine, Analytics Engine

---

### 2.3 ORDER_BOOK_UPDATE

**Description**: Emitted when order book changes.

**Event Type**: `ORDER_BOOK_UPDATE`

**Data Schema**:
```json
{
  "symbol": "BTCUSDT",
  "exchange": "binance",
  "bids": [
    [49999.0, 1.0],
    [49998.0, 2.0]
  ],
  "asks": [
    [50001.0, 1.0],
    [50002.0, 2.0]
  ],
  "timestamp": "2026-07-09T10:00:00Z"
}
```

**Producers**: Market Hub, Exchange Adapters

**Consumers**: Trading Engine, Analytics Engine

---

### 2.4 CANDLE_UPDATE

**Description**: Emitted when a new candle is formed or updated.

**Event Type**: `CANDLE_UPDATE`

**Data Schema**:
```json
{
  "symbol": "BTCUSDT",
  "exchange": "binance",
  "interval": "1m",
  "open": 49900.0,
  "high": 50100.0,
  "low": 49800.0,
  "close": 50000.0,
  "volume": 1000.0,
  "timestamp": "2026-07-09T10:00:00Z"
}
```

**Producers**: Market Hub, Exchange Adapters

**Consumers**: Trading Engine, Analytics Engine, AI Engine

---

## 3. TRADING EVENTS

### 3.1 ORDER_PLACED

**Description**: Emitted when an order is placed on an exchange.

**Event Type**: `ORDER_PLACED`

**Data Schema**:
```json
{
  "order_id": "uuid",
  "exchange_order_id": "123456789",
  "user_id": "uuid",
  "trading_process_id": "uuid",
  "symbol": "BTCUSDT",
  "side": "buy",
  "order_type": "limit",
  "quantity": 0.1,
  "price": 50000.0,
  "exchange": "binance",
  "grid_level": 1,
  "is_profit_lock": false
}
```

**Producers**: Execution Engine, Exchange Adapters

**Consumers**: Order Manager, Trading Engine, Notification Engine

---

### 3.2 ORDER_FILLED

**Description**: Emitted when an order is fully or partially filled.

**Event Type**: `ORDER_FILLED`

**Data Schema**:
```json
{
  "order_id": "uuid",
  "exchange_order_id": "123456789",
  "user_id": "uuid",
  "trading_process_id": "uuid",
  "symbol": "BTCUSDT",
  "side": "buy",
  "filled_quantity": 0.1,
  "average_fill_price": 50000.0,
  "exchange": "binance",
  "fee": 0.001,
  "fee_currency": "USDT",
  "grid_level": 1,
  "is_profit_lock": false
}
```

**Producers**: Exchange Adapters, Order Manager

**Consumers**: Trading Engine, Portfolio Engine, Grid Engine, Notification Engine

---

### 3.3 ORDER_CANCELLED

**Description**: Emitted when an order is cancelled.

**Event Type**: `ORDER_CANCELLED`

**Data Schema**:
```json
{
  "order_id": "uuid",
  "exchange_order_id": "123456789",
  "user_id": "uuid",
  "trading_process_id": "uuid",
  "symbol": "BTCUSDT",
  "cancelled_quantity": 0.1,
  "exchange": "binance",
  "reason": "user_requested"
}
```

**Producers**: Execution Engine, Exchange Adapters

**Consumers**: Order Manager, Trading Engine, Notification Engine

---

### 3.4 ORDER_REJECTED

**Description**: Emitted when an order is rejected by the exchange.

**Event Type**: `ORDER_REJECTED`

**Data Schema**:
```json
{
  "order_id": "uuid",
  "user_id": "uuid",
  "trading_process_id": "uuid",
  "symbol": "BTCUSDT",
  "side": "buy",
  "order_type": "limit",
  "quantity": 0.1,
  "price": 50000.0,
  "exchange": "binance",
  "reject_reason": "insufficient_balance",
  "error_code": "INSUFFICIENT_BALANCE"
}
```

**Producers**: Exchange Adapters

**Consumers**: Trading Engine, Risk Engine, Notification Engine

---

### 3.5 BUY_FILLED

**Description**: Emitted when a buy order is filled (convenience event).

**Event Type**: `BUY_FILLED`

**Data Schema**:
```json
{
  "order_id": "uuid",
  "exchange_order_id": "123456789",
  "user_id": "uuid",
  "trading_process_id": "uuid",
  "symbol": "BTCUSDT",
  "filled_quantity": 0.1,
  "average_fill_price": 50000.0,
  "exchange": "binance",
  "grid_level": 1
}
```

**Producers**: Order Manager

**Consumers**: Grid Engine, Portfolio Engine

---

### 3.6 SELL_FILLED

**Description**: Emitted when a sell order is filled (convenience event).

**Event Type**: `SELL_FILLED`

**Data Schema**:
```json
{
  "order_id": "uuid",
  "exchange_order_id": "123456789",
  "user_id": "uuid",
  "trading_process_id": "uuid",
  "symbol": "BTCUSDT",
  "filled_quantity": 0.1,
  "average_fill_price": 51000.0,
  "exchange": "binance",
  "grid_level": 1,
  "is_profit_lock": false
}
```

**Producers**: Order Manager

**Consumers**: Grid Engine, Portfolio Engine, Profit Lock Engine

---

### 3.7 TP_FILLED

**Description**: Emitted when a take-profit order is filled.

**Event Type**: `TP_FILLED`

**Data Schema**:
```json
{
  "order_id": "uuid",
  "exchange_order_id": "123456789",
  "user_id": "uuid",
  "trading_process_id": "uuid",
  "symbol": "BTCUSDT",
  "filled_quantity": 0.1,
  "average_fill_price": 55000.0,
  "exchange": "binance",
  "profit_percentage": 10.0
}
```

**Producers**: Order Manager

**Consumers**: Trading Engine, Portfolio Engine, Notification Engine

---

### 3.8 SL_FILLED

**Description**: Emitted when a stop-loss order is filled.

**Event Type**: `SL_FILLED`

**Data Schema**:
```json
{
  "order_id": "uuid",
  "exchange_order_id": "123456789",
  "user_id": "uuid",
  "trading_process_id": "uuid",
  "symbol": "BTCUSDT",
  "filled_quantity": 0.1,
  "average_fill_price": 45000.0,
  "exchange": "binance",
  "loss_percentage": 10.0
}
```

**Producers**: Order Manager

**Consumers**: Trading Engine, Portfolio Engine, Notification Engine

---

## 4. GRID EVENTS

### 4.1 GRID_CREATED

**Description**: Emitted when a new grid is created.

**Event Type**: `GRID_CREATED`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "grid_profile_id": "uuid",
  "upper_price": 60000.0,
  "lower_price": 40000.0,
  "grid_count": 10,
  "grid_spacing": 2000.0,
  "investment_per_grid": 100.0
}
```

**Producers**: Grid Engine

**Consumers**: Trading Engine, Analytics Engine

---

### 4.2 GRID_UPDATED

**Description**: Emitted when grid parameters are updated.

**Event Type**: `GRID_UPDATED`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "updated_fields": {
    "upper_price": 65000.0,
    "lower_price": 35000.0
  },
  "previous_values": {
    "upper_price": 60000.0,
    "lower_price": 40000.0
  }
}
```

**Producers**: Grid Engine

**Consumers**: Trading Engine, Analytics Engine

---

### 4.3 GRID_LEVEL_ACTIVATED

**Description**: Emitted when a grid level is activated.

**Event Type**: `GRID_LEVEL_ACTIVATED`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "grid_level": 5,
  "price": 50000.0,
  "order_id": "uuid",
  "side": "buy"
}
```

**Producers**: Grid Engine

**Consumers**: Trading Engine, Execution Engine

---

### 4.4 GRID_LEVEL_FILLED

**Description**: Emitted when a grid level order is filled.

**Event Type**: `GRID_LEVEL_FILLED`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "grid_level": 5,
  "price": 50000.0,
  "order_id": "uuid",
  "side": "buy",
  "filled_quantity": 0.1
}
```

**Producers**: Grid Engine

**Consumers**: Trading Engine, Portfolio Engine, Analytics Engine

---

### 4.5 GRID_COMPLETED

**Description**: Emitted when all grid levels are completed.

**Event Type**: `GRID_COMPLETED`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "total_cycles": 5,
  "total_profit": 500.0,
  "total_profit_percentage": 5.0,
  "duration_seconds": 86400
}
```

**Producers**: Grid Engine

**Consumers**: Trading Engine, Notification Engine, Analytics Engine

---

## 5. PROFIT LOCK EVENTS

### 5.1 PROFIT_LOCK_TRIGGERED

**Description**: Emitted when profit lock is triggered.

**Event Type**: `PROFIT_LOCK_TRIGGERED`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "current_price": 55000.0,
  "trigger_price": 54000.0,
  "profit_percentage": 10.0,
  "lock_percentage": 5.0
}
```

**Producers**: Profit Lock Engine

**Consumers**: Trading Engine, Execution Engine

---

### 5.2 PROFIT_LOCK_UPDATED

**Description**: Emitted when profit lock level is updated.

**Event Type**: `PROFIT_LOCK_UPDATED`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "old_lock_price": 54000.0,
  "new_lock_price": 54500.0,
  "trail_percentage": 1.0
}
```

**Producers**: Profit Lock Engine

**Consumers**: Trading Engine, Execution Engine

---

### 5.3 PROFIT_LOCK_EXECUTED

**Description**: Emitted when profit lock order is executed.

**Event Type**: `PROFIT_LOCK_EXECUTED`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "lock_price": 54000.0,
  "executed_price": 53900.0,
  "locked_profit": 400.0,
  "order_id": "uuid"
}
```

**Producers**: Profit Lock Engine

**Consumers**: Trading Engine, Portfolio Engine, Notification Engine

---

## 6. TRADING PROCESS EVENTS

### 6.1 TRADING_PROCESS_CREATED

**Description**: Emitted when a trading process is created.

**Event Type**: `TRADING_PROCESS_CREATED`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "strategy_id": "uuid",
  "grid_profile_id": "uuid",
  "exchange_account_id": "uuid",
  "total_investment": 1000.0,
  "start_price": 50000.0
}
```

**Producers**: Trading Engine

**Consumers**: Analytics Engine, Notification Engine

---

### 6.2 TRADING_PROCESS_STARTED

**Description**: Emitted when a trading process is started.

**Event Type**: `TRADING_PROCESS_STARTED`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "start_price": 50000.0,
  "started_at": "2026-07-09T10:00:00Z"
}
```

**Producers**: Trading Engine

**Consumers**: Analytics Engine, Notification Engine

---

### 6.3 TRADING_PROCESS_PAUSED

**Description**: Emitted when a trading process is paused.

**Event Type**: `TRADING_PROCESS_PAUSED`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "paused_at": "2026-07-09T10:00:00Z",
  "reason": "user_requested"
}
```

**Producers**: Trading Engine

**Consumers**: Analytics Engine, Notification Engine

---

### 6.4 TRADING_PROCESS_RESUMED

**Description**: Emitted when a trading process is resumed.

**Event Type**: `TRADING_PROCESS_RESUMED`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "resumed_at": "2026-07-09T10:00:00Z"
}
```

**Producers**: Trading Engine

**Consumers**: Analytics Engine, Notification Engine

---

### 6.5 TRADING_PROCESS_STOPPING

**Description**: Emitted when a trading process is stopping.

**Event Type**: `TRADING_PROCESS_STOPPING`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "stopping_at": "2026-07-09T10:00:00Z",
  "reason": "user_requested"
}
```

**Producers**: Trading Engine

**Consumers**: Execution Engine, Analytics Engine

---

### 6.6 TRADING_PROCESS_STOPPED

**Description**: Emitted when a trading process is stopped.

**Event Type**: `TRADING_PROCESS_STOPPED`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "stopped_at": "2026-07-09T10:00:00Z",
  "final_price": 51000.0,
  "total_profit": 100.0,
  "total_profit_percentage": 1.0
}
```

**Producers**: Trading Engine

**Consumers**: Analytics Engine, Notification Engine

---

### 6.7 TRADING_PROCESS_ERROR

**Description**: Emitted when a trading process encounters an error.

**Event Type**: `TRADING_PROCESS_ERROR`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "error_code": "EXCHANGE_CONNECTION_ERROR",
  "error_message": "Failed to connect to exchange",
  "error_timestamp": "2026-07-09T10:00:00Z"
}
```

**Producers**: Trading Engine

**Consumers**: Analytics Engine, Notification Engine, Recovery Engine

---

### 6.8 TRADING_PROCESS_RECOVERING

**Description**: Emitted when a trading process is recovering from error.

**Event Type**: `TRADING_PROCESS_RECOVERING`

**Data Schema**:
```json
{
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "recovery_started_at": "2026-07-09T10:00:00Z",
  "recovery_strategy": "state_sync"
}
```

**Producers**: Recovery Engine

**Consumers**: Analytics Engine, Notification Engine

---

## 7. PORTFOLIO EVENTS

### 7.1 PORTFOLIO_UPDATED

**Description**: Emitted when portfolio is updated.

**Event Type**: `PORTFOLIO_UPDATED`

**Data Schema**:
```json
{
  "user_id": "uuid",
  "total_value": 5100.0,
  "total_investment": 5000.0,
  "total_pnl": 100.0,
  "pnl_percentage": 2.0,
  "updated_at": "2026-07-09T10:00:00Z"
}
```

**Producers**: Portfolio Engine

**Consumers**: Analytics Engine, Notification Engine

---

### 7.2 POSITION_OPENED

**Description**: Emitted when a new position is opened.

**Event Type**: `POSITION_OPENED`

**Data Schema**:
```json
{
  "position_id": "uuid",
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "side": "long",
  "quantity": 0.1,
  "entry_price": 50000.0,
  "value": 5000.0
}
```

**Producers**: Portfolio Engine

**Consumers**: Analytics Engine, Risk Engine

---

### 7.3 POSITION_CLOSED

**Description**: Emitted when a position is closed.

**Event Type**: `POSITION_CLOSED`

**Data Schema**:
```json
{
  "position_id": "uuid",
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "side": "long",
  "quantity": 0.1,
  "entry_price": 50000.0,
  "exit_price": 51000.0,
  "realized_pnl": 100.0,
  "pnl_percentage": 2.0
}
```

**Producers**: Portfolio Engine

**Consumers**: Analytics Engine, Risk Engine, Notification Engine

---

### 7.4 POSITION_UPDATED

**Description**: Emitted when position is updated.

**Event Type**: `POSITION_UPDATED`

**Data Schema**:
```json
{
  "position_id": "uuid",
  "trading_process_id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "current_price": 51000.0,
  "unrealized_pnl": 100.0,
  "pnl_percentage": 2.0
}
```

**Producers**: Portfolio Engine

**Consumers**: Analytics Engine, Risk Engine

---

## 8. USER EVENTS

### 8.1 USER_REGISTERED

**Description**: Emitted when a new user registers.

**Event Type**: `USER_REGISTERED`

**Data Schema**:
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "referral_code": "ABC123",
  "referred_by": "uuid",
  "registered_at": "2026-07-09T10:00:00Z"
}
```

**Producers**: Auth Service

**Consumers**: Analytics Engine, Notification Engine

---

### 8.2 USER_VERIFIED

**Description**: Emitted when a user verifies their email.

**Event Type**: `USER_VERIFIED`

**Data Schema**:
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "verified_at": "2026-07-09T10:00:00Z"
}
```

**Producers**: Auth Service

**Consumers**: Analytics Engine

---

### 8.3 USER_LOGIN

**Description**: Emitted when a user logs in.

**Event Type**: `USER_LOGIN`

**Data Schema**:
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "login_at": "2026-07-09T10:00:00Z"
}
```

**Producers**: Auth Service

**Consumers**: Analytics Engine

---

### 8.4 USER_LOGOUT

**Description**: Emitted when a user logs out.

**Event Type**: `USER_LOGOUT`

**Data Schema**:
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "logout_at": "2026-07-09T10:00:00Z"
}
```

**Producers**: Auth Service

**Consumers**: Analytics Engine

---

### 8.5 SUBSCRIPTION_CHANGED

**Description**: Emitted when user subscription changes.

**Event Type**: `SUBSCRIPTION_CHANGED`

**Data Schema**:
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "old_tier": "free",
  "new_tier": "pro",
  "changed_at": "2026-07-09T10:00:00Z"
}
```

**Producers**: Subscription Service

**Consumers**: Analytics Engine, Notification Engine

---

## 9. SYSTEM EVENTS

### 9.1 SYSTEM_STARTED

**Description**: Emitted when the system starts.

**Event Type**: `SYSTEM_STARTED`

**Data Schema**:
```json
{
  "version": "1.0.0",
  "environment": "production",
  "started_at": "2026-07-09T10:00:00Z"
}
```

**Producers**: System Bootstrap

**Consumers**: Monitoring System

---

### 9.2 SYSTEM_SHUTDOWN

**Description**: Emitted when the system shuts down.

**Event Type**: `SYSTEM_SHUTDOWN`

**Data Schema**:
```json
{
  "version": "1.0.0",
  "environment": "production",
  "shutdown_at": "2026-07-09T10:00:00Z",
  "reason": "maintenance"
}
```

**Producers**: System Bootstrap

**Consumers**: Monitoring System

---

### 9.3 SYSTEM_ERROR

**Description**: Emitted when a system-level error occurs.

**Event Type**: `SYSTEM_ERROR`

**Data Schema**:
```json
{
  "error_code": "DATABASE_CONNECTION_ERROR",
  "error_message": "Failed to connect to database",
  "service": "trading_engine",
  "severity": "critical",
  "timestamp": "2026-07-09T10:00:00Z"
}
```

**Producers**: All Services

**Consumers**: Monitoring System, Alert System

---

### 9.4 HEALTH_CHECK

**Description**: Emitted periodically for health monitoring.

**Event Type**: `HEALTH_CHECK`

**Data Schema**:
```json
{
  "service": "trading_engine",
  "status": "healthy",
  "metrics": {
    "cpu_usage": 50.0,
    "memory_usage": 60.0,
    "active_connections": 100
  },
  "timestamp": "2026-07-09T10:00:00Z"
}
```

**Producers**: All Services

**Consumers**: Monitoring System

---

## 10. NOTIFICATION EVENTS

### 10.1 NOTIFICATION_CREATED

**Description**: Emitted when a notification is created.

**Event Type**: `NOTIFICATION_CREATED`

**Data Schema**:
```json
{
  "notification_id": "uuid",
  "user_id": "uuid",
  "type": "order_filled",
  "title": "Order Filled",
  "message": "Your order for 0.1 BTC has been filled",
  "data": {
    "order_id": "uuid",
    "symbol": "BTCUSDT"
  },
  "created_at": "2026-07-09T10:00:00Z"
}
```

**Producers**: Notification Service

**Consumers**: WebSocket Service, Email Service

---

### 10.2 NOTIFICATION_SENT

**Description**: Emitted when a notification is sent.

**Event Type**: `NOTIFICATION_SENT`

**Data Schema**:
```json
{
  "notification_id": "uuid",
  "user_id": "uuid",
  "channel": "email",
  "sent_at": "2026-07-09T10:00:00Z",
  "status": "delivered"
}
```

**Producers**: Notification Service

**Consumers**: Analytics Engine

---

## 11. EVENT CHANNELS

Events are published to Redis channels based on their category:

| Category | Channel Pattern | Example |
|----------|----------------|---------|
| Market | `market:{symbol}` | `market:BTCUSDT` |
| Trading | `trading:{user_id}` | `trading:uuid` |
| Trading Process | `trading_process:{process_id}` | `trading_process:uuid` |
| Portfolio | `portfolio:{user_id}` | `portfolio:uuid` |
| User | `user:{user_id}` | `user:uuid` |
| System | `system:{event_type}` | `system:SYSTEM_ERROR` |
| Notification | `notification:{user_id}` | `notification:uuid` |

---

## 12. EVENT CONSUMER GUIDELINES

### 12.1 Idempotency

All event consumers must be idempotent. Processing the same event multiple times should not cause side effects.

**Example**:
```python
def handle_order_filled(event: Event):
    order_id = event.data["order_id"]
    
    # Check if already processed
    if order_repository.is_processed(order_id):
        return
    
    # Process event
    order_repository.mark_as_processed(order_id)
    # ... rest of processing
```

### 12.2 Error Handling

Consumers should handle errors gracefully and not crash the entire system.

**Example**:
```python
def handle_event(event: Event):
    try:
        process_event(event)
    except Exception as e:
        logger.error(f"Failed to process event: {e}", exc_info=True)
        # Send to dead letter queue for retry
        dead_letter_queue.publish(event)
```

### 12.3 Event Ordering

For events that require ordering (e.g., order lifecycle), use sequence numbers or timestamps.

**Example**:
```json
{
  "event_type": "ORDER_FILLED",
  "sequence": 123,
  "timestamp": "2026-07-09T10:00:00Z",
  "data": { ... }
}
```

---

## 13. CHANGE LOG

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-09 | 1.0.0 | Initial event specification |
