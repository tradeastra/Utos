# INTERFACE DEFINITIONS

**Version:** 2.0.0  
**Last Updated:** 2026-07-09  
**Status:** DRAFT

---

## 1. OVERVIEW

This document defines all module interfaces for the **UTOS Trading Engine**. Every interface is a contract — once defined and implemented, breaking changes require version bump and migration plan.

The architecture is built around three core context objects:

- **TradingContext**: All trading-specific state for a single Trading Instance (user, exchange, account, strategy, grid, risk, portfolio, runtime config).
- **KernelContext**: Shared system services available to all engines (logger, event bus, cache, storage, configuration, metrics, clock).
- **ProcessMemory**: In-memory snapshot of a Trading Instance's state. Workers read from memory; database is only for persistence.

### 1.1 Design Principles

- **Interface Segregation**: Each interface has a single responsibility
- **Dependency Inversion**: High-level modules depend on interfaces, not concrete classes
- **Context-First**: Every engine receives a context object instead of many individual IDs
- **Kernel-First**: Engines access shared services via `KernelContext`, not individual injections
- **Memory-First**: Runtime state lives in `ProcessMemory`; database is persistence only
- **Explicit Contracts**: All methods, parameters, and return types are explicitly typed
- **Async-First**: All I/O operations are async
- **Error-Aware**: Every interface defines its error contract

### 1.2 Notation

Interfaces are written in Python ABC (Abstract Base Class) style with type hints. TypeScript equivalents are noted where relevant (frontend interfaces).

### 1.3 Core Concepts

| Concept | Description |
|--------|-------------|
| **Trading Instance** | One active trading session (previously called Trading Process). A user can have multiple instances for the same pair and strategy with different capital/grid/risk. |
| **TradingContext** | Immutable-like context object passed to every trading operation. |
| **KernelContext** | System-wide services accessed by all engines. |
| **ProcessMemory** | In-memory snapshot of a Trading Instance. |

---

## 2. EXCHANGE ADAPTER INTERFACE

### 2.1 IExchangeAdapter

**Location**: `backend/adapters/base.py`

**Responsibility**: Abstract exchange API operations. Every exchange (Binance, Bybit, OKX, etc.) implements this interface.

```python
from abc import ABC, abstractmethod
from typing import Optional
from decimal import Decimal
from datetime import datetime

class IExchangeAdapter(ABC):
    """Base interface for all exchange adapters.
    
    Market data stream and trading API are managed as separate connections
    because most exchanges separate them (different endpoints, different rate limits,
    different failure modes).
    """

    @abstractmethod
    async def initialize(self, config: ExchangeAdapterConfig) -> bool:
        """Initialize the adapter with exchange configuration.
        
        This does NOT open network connections. It only loads configuration,
        exchange info, and validates credentials format.
        """
        pass

    @abstractmethod
    async def authenticate(self, credentials: ExchangeCredentials) -> bool:
        """Authenticate with the exchange using decrypted API credentials.
        
        Performs a lightweight auth check (e.g., ping + account query).
        """
        pass

    @abstractmethod
    async def connect_market(self) -> bool:
        """Open market data connection (WebSocket or REST polling)."""
        pass

    @abstractmethod
    async def connect_account(self) -> bool:
        """Open trading/account connection (private API / WebSocket)."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect all exchange connections."""
        pass

    @abstractmethod
    async def is_market_connected(self) -> bool:
        """Check if market data connection is alive."""
        pass

    @abstractmethod
    async def is_account_connected(self) -> bool:
        """Check if trading/account connection is alive."""
        pass

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,          # "buy" | "sell"
        order_type: str,     # "limit" | "market" | "stop_limit"
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        client_order_id: Optional[str] = None,
    ) -> OrderResult:
        """Place an order on the exchange.
        
        Returns:
            OrderResult with exchange order ID and status.
        
        Raises:
            ExchangeError: If order placement fails.
        """
        pass

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an existing order.
        
        Returns:
            True if cancellation successful, False otherwise.
        
        Raises:
            ExchangeError: If cancellation fails.
        """
        pass

    @abstractmethod
    async def modify_order(
        self,
        symbol: str,
        order_id: str,
        new_price: Optional[Decimal] = None,
        new_quantity: Optional[Decimal] = None,
    ) -> OrderResult:
        """Modify an existing order.
        
        Returns:
            OrderResult with updated order details.
        
        Raises:
            ExchangeError: If modification fails.
        """
        pass

    @abstractmethod
    async def get_balance(self) -> list[BalanceEntry]:
        """Get account balances.
        
        Returns:
            List of BalanceEntry for each currency.
        """
        pass

    @abstractmethod
    async def get_positions(self) -> list[PositionEntry]:
        """Get current positions.
        
        Returns:
            List of PositionEntry for each open position.
        """
        pass

    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> OrderResult:
        """Get order details from exchange.
        
        Returns:
            OrderResult with current order state.
        """
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> list[OrderResult]:
        """Get all open orders.
        
        Returns:
            List of OrderResult for open orders.
        """
        pass

    @abstractmethod
    async def get_order_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100,
    ) -> list[OrderResult]:
        """Get order history.
        
        Returns:
            List of OrderResult for historical orders.
        """
        pass

    @abstractmethod
    async def get_trade_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100,
    ) -> list[TradeEntry]:
        """Get trade (fill) history.
        
        Returns:
            List of TradeEntry for historical trades.
        """
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> TickerData:
        """Get current ticker data for a symbol.
        
        Returns:
            TickerData with bid, ask, last price, volume.
        """
        pass

    @abstractmethod
    async def get_order_book(self, symbol: str, depth: int = 20) -> OrderBook:
        """Get order book for a symbol.
        
        Returns:
            OrderBook with bids and asks.
        """
        pass

    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        interval: str,       # "1m", "5m", "15m", "1h", "4h", "1d"
        limit: int = 100,
    ) -> list[Candle]:
        """Get historical candlestick data.
        
        Returns:
            List of Candle with OHLCV data.
        """
        pass

    @abstractmethod
    async def subscribe_market(
        self,
        symbol: str,
        channel: str,        # "ticker" | "orderbook" | "candle" | "trade"
        callback: Callable,
    ) -> str:
        """Subscribe to market data stream.
        
        Returns:
            Subscription ID for unsubscribing.
        """
        pass

    @abstractmethod
    async def unsubscribe_market(self, subscription_id: str) -> None:
        """Unsubscribe from market data stream."""
        pass

    @abstractmethod
    async def get_exchange_info(self) -> ExchangeInfo:
        """Get exchange metadata (symbols, limits, fees).
        
        Returns:
            ExchangeInfo with supported symbols and rate limits.
        """
        pass

```

### 2.2 Data Types for Exchange Adapter

```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Callable

@dataclass
class OrderResult:
    order_id: str
    exchange_order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Optional[Decimal]
    filled_quantity: Decimal
    average_fill_price: Optional[Decimal]
    status: str            # "pending" | "open" | "partially_filled" | "filled" | "cancelled" | "rejected"
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str]

@dataclass
class BalanceEntry:
    currency: str
    available: Decimal
    locked: Decimal
    total: Decimal

@dataclass
class PositionEntry:
    symbol: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    unrealized_pnl: Decimal
    leverage: Optional[Decimal]

@dataclass
class TradeEntry:
    trade_id: str
    order_id: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    fee: Decimal
    fee_currency: str
    timestamp: datetime

@dataclass
class TickerData:
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume: Decimal
    timestamp: datetime

@dataclass
class OrderBook:
    symbol: str
    bids: list[tuple[Decimal, Decimal]]   # [(price, quantity), ...]
    asks: list[tuple[Decimal, Decimal]]
    timestamp: datetime

@dataclass
class Candle:
    symbol: str
    interval: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    timestamp: datetime

@dataclass
class ExchangeInfo:
    name: str
    supported_symbols: list[str]
    rate_limits: dict
    fee_structure: dict
    server_time: datetime

@dataclass
class ExchangeCredentials:
    exchange_name: str
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None  # Required for some exchanges (OKX, etc.)

@dataclass
class ExchangeAdapterConfig:
    exchange_name: str
    is_testnet: bool = False
    market_stream_url: Optional[str] = None
    account_stream_url: Optional[str] = None
    rest_url: Optional[str] = None
    connection_timeout: float = 10.0
    request_timeout: float = 30.0
```

---

## 3. TRADING ENGINE INTERFACE

### 3.1 ITradingEngine

**Location**: `backend/engine/base.py`

**Responsibility**: Orchestrate Trading Instances, manage lifecycle.

```python
class ITradingEngine(ABC):

    @abstractmethod
    async def create_instance(
        self,
        context: TradingContext,
    ) -> TradingInstance:
        """Create a new Trading Instance in CREATED state.
        
        Does NOT allocate worker or subscribe market yet.
        """
        pass

    @abstractmethod
    async def prepare_instance(self, context: TradingContext) -> bool:
        """Transition CREATED -> READY.
        
        Performs:
        - API key validation
        - Balance check
        - Grid calculation
        - Order/position sync
        - Market subscription
        - Worker allocation
        - ProcessMemory initialization
        
        Raises:
            InvalidStateTransition: If instance is not in CREATED.
            InsufficientBalanceError: If balance is insufficient.
        """
        pass

    @abstractmethod
    async def start_instance(self, context: TradingContext) -> bool:
        """Transition READY -> RUNNING."""
        pass

    @abstractmethod
    async def stop_instance(self, context: TradingContext, reason: str = "user_requested") -> bool:
        """Transition RUNNING -> STOPPING -> STOPPED."""
        pass

    @abstractmethod
    async def pause_instance(self, context: TradingContext) -> bool:
        """Transition RUNNING -> PAUSED."""
        pass

    @abstractmethod
    async def resume_instance(self, context: TradingContext) -> bool:
        """Transition PAUSED -> RUNNING."""
        pass

    @abstractmethod
    async def get_instance(self, instance_id: str) -> TradingInstance:
        """Get Trading Instance details."""
        pass

    @abstractmethod
    async def list_instances(
        self,
        user_id: str,
        status: Optional[str] = None,
    ) -> list[TradingInstance]:
        """List Trading Instances for a user."""
        pass

    @abstractmethod
    async def recover_instance(self, context: TradingContext) -> bool:
        """Recover a Trading Instance from ERROR state."""
        pass

    @abstractmethod
    async def sync_instance_state(self, context: TradingContext) -> bool:
        """Synchronize instance state with exchange."""
        pass
```

---

## 4. GRID ENGINE INTERFACE

### 4.1 IGridEngine

**Location**: `backend/engine/grid/base.py`

**Responsibility**: Manage grid levels, calculate prices, handle grid fills.

```python
class IGridEngine(ABC):

    @abstractmethod
    async def initialize_grid(
        self,
        instance_id: str,
        upper_price: Decimal,
        lower_price: Decimal,
        grid_count: int,
        investment_per_grid: Decimal,
    ) -> GridState:
        """Initialize grid levels for a Trading Instance."""
        pass

    @abstractmethod
    async def activate_grid(self, instance_id: str) -> bool:
        """Activate all grid levels (place orders)."""
        pass

    @abstractmethod
    async def pause_grid(self, instance_id: str) -> bool:
        """Pause grid (cancel pending orders)."""
        pass

    @abstractmethod
    async def resume_grid(self, instance_id: str) -> bool:
        """Resume grid (re-place orders)."""
        pass

    @abstractmethod
    async def on_buy_filled(self, instance_id: str, grid_level: int, fill_price: Decimal, quantity: Decimal) -> None:
        """Handle buy order filled event. Place corresponding sell order."""
        pass

    @abstractmethod
    async def on_sell_filled(self, instance_id: str, grid_level: int, fill_price: Decimal, quantity: Decimal) -> None:
        """Handle sell order filled event. Place corresponding buy order."""
        pass

    @abstractmethod
    async def update_grid_parameters(
        self,
        instance_id: str,
        upper_price: Optional[Decimal] = None,
        lower_price: Optional[Decimal] = None,
        grid_count: Optional[int] = None,
    ) -> GridState:
        """Update grid parameters (only when paused)."""
        pass

    @abstractmethod
    async def get_grid_state(self, instance_id: str) -> GridState:
        """Get current grid state."""
        pass

    @abstractmethod
    async def close_all_grid_orders(self, instance_id: str) -> bool:
        """Cancel all grid orders."""
        pass
```

### 4.2 Grid Data Types

```python
@dataclass
class GridLevel:
    level: int
    buy_price: Decimal
    sell_price: Decimal
    quantity: Decimal
    buy_order_id: Optional[str]
    sell_order_id: Optional[str]
    status: str    # "idle" | "buy_pending" | "buy_filled" | "sell_pending" | "sell_filled"

@dataclass
class GridState:
    instance_id: str
    status: str    # "idle" | "initialized" | "active" | "paused" | "completed" | "error"
    upper_price: Decimal
    lower_price: Decimal
    grid_count: int
    grid_spacing: Decimal
    investment_per_grid: Decimal
    levels: list[GridLevel]
    total_cycles: int
    total_profit: Decimal
```

---

## 5. STRATEGY INTERFACE

### 5.1 IStrategy

**Location**: `backend/strategies/base.py`

**Responsibility**: Define trading strategy logic. Each strategy implements this interface.

```python
class IStrategy(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name."""
        pass

    @property
    @abstractmethod
    def type(self) -> str:
        """Strategy type (smart_grid, adaptive_grid, infinity_grid, dca)."""
        pass

    @abstractmethod
    async def on_start(self, context: StrategyContext) -> None:
        """Called when strategy starts."""
        pass

    @abstractmethod
    async def on_stop(self, context: StrategyContext) -> None:
        """Called when strategy stops."""
        pass

    @abstractmethod
    async def on_price_update(self, context: StrategyContext, price: Decimal) -> None:
        """Called on every price update."""
        pass

    @abstractmethod
    async def on_order_filled(self, context: StrategyContext, fill_event: FillEvent) -> None:
        """Called when an order is filled."""
        pass

    @abstractmethod
    async def on_error(self, context: StrategyContext, error: Exception) -> None:
        """Called when an error occurs."""
        pass

    @abstractmethod
    def get_parameters(self) -> dict:
        """Get strategy parameters schema."""
        pass

    @abstractmethod
    def validate_parameters(self, params: dict) -> bool:
        """Validate strategy parameters."""
        pass
```

### 5.2 Strategy Context

```python
@dataclass
class StrategyContext:
    trading_context: TradingContext
    kernel_context: KernelContext
    process_memory: ProcessMemory
    state: dict   # Strategy-specific state
```

---

## 6. EVENT BUS INTERFACE

### 6.1 IEventBus

**Location**: `backend/events/base.py`

**Responsibility**: Publish and subscribe to events via Redis.

```python
class IEventBus(ABC):

    @abstractmethod
    async def publish(self, event_type: str, data: dict, metadata: Optional[dict] = None) -> str:
        """Publish an event.
        
        Returns:
            Event ID.
        """
        pass

    @abstractmethod
    async def subscribe(
        self,
        channel: str,
        handler: Callable[[Event], None],
    ) -> str:
        """Subscribe to a channel.
        
        Returns:
            Subscription ID.
        """
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from a channel."""
        pass

    @abstractmethod
    async def publish_to_user(self, user_id: str, event_type: str, data: dict) -> str:
        """Publish event to a specific user's channel."""
        pass

    @abstractmethod
    async def request(self, channel: str, data: dict, timeout: float = 5.0) -> dict:
        """Request-response pattern.
        
        Returns:
            Response data from responder.
        """
        pass
```

### 6.2 Event Data Type

```python
@dataclass
class Event:
    event_type: str
    event_id: str
    timestamp: datetime
    data: dict
    metadata: dict
```

---

## 7. MARKET HUB INTERFACE

### 7.1 IMarketHub

**Location**: `backend/market/base.py`

**Responsibility**: Aggregate market data from multiple exchanges, normalize, and distribute.

```python
class IMarketHub(ABC):

    @abstractmethod
    async def subscribe(
        self,
        symbol: str,
        exchange: str,
        channel: str,    # "ticker" | "orderbook" | "candle" | "trade"
        callback: Callable,
    ) -> str:
        """Subscribe to market data for a symbol on an exchange."""
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from market data."""
        pass

    @abstractmethod
    async def get_price(self, symbol: str, exchange: str) -> Decimal:
        """Get current price for a symbol."""
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str, exchange: str) -> TickerData:
        """Get ticker data for a symbol."""
        pass

    @abstractmethod
    async def get_order_book(self, symbol: str, exchange: str, depth: int = 20) -> OrderBook:
        """Get order book for a symbol."""
        pass

    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        limit: int = 100,
    ) -> list[Candle]:
        """Get candlestick data for a symbol."""
        pass

    @abstractmethod
    async def get_supported_symbols(self, exchange: str) -> list[str]:
        """Get list of supported symbols for an exchange."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the market hub (connect to all exchange feeds)."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the market hub."""
        pass
```

---

## 8. PORTFOLIO INTERFACE

### 8.1 IPortfolio

**Location**: `backend/engine/portfolio/base.py`

**Responsibility**: Track positions, calculate P&L, manage portfolio state.

```python
class IPortfolio(ABC):

    @abstractmethod
    async def get_portfolio(self, user_id: str) -> PortfolioSummary:
        """Get portfolio summary for a user."""
        pass

    @abstractmethod
    async def get_positions(self, user_id: str, symbol: Optional[str] = None) -> list[Position]:
        """Get all positions for a user."""
        pass

    @abstractmethod
    async def open_position(
        self,
        user_id: str,
        instance_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        entry_price: Decimal,
    ) -> Position:
        """Open a new position."""
        pass

    @abstractmethod
    async def close_position(
        self,
        position_id: str,
        exit_price: Decimal,
    ) -> Position:
        """Close a position."""
        pass

    @abstractmethod
    async def update_position(
        self,
        position_id: str,
        current_price: Decimal,
    ) -> Position:
        """Update position with current price (unrealized P&L)."""
        pass

    @abstractmethod
    async def get_pnl(self, user_id: str) -> PnLSummary:
        """Get P&L summary for a user."""
        pass

    @abstractmethod
    async def get_pnl_history(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
    ) -> list[PnLRecord]:
        """Get P&L history for a date range."""
        pass
```

### 8.2 Portfolio Data Types

```python
@dataclass
class PortfolioSummary:
    total_value: Decimal
    total_investment: Decimal
    total_pnl: Decimal
    pnl_percentage: Decimal
    positions: list[Position]

@dataclass
class Position:
    id: str
    user_id: str
    instance_id: str
    symbol: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    created_at: datetime
    updated_at: datetime

@dataclass
class PnLSummary:
    total_realized_pnl: Decimal
    total_unrealized_pnl: Decimal
    total_pnl: Decimal
    pnl_percentage: Decimal
    today_pnl: Decimal
    today_pnl_percentage: Decimal

@dataclass
class PnLRecord:
    date: date
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
```

---

## 9. RISK ENGINE INTERFACE

### 9.1 IRiskEngine

**Location**: `backend/engine/risk/base.py`

**Responsibility**: Monitor risk, enforce limits, trigger stop-loss.

```python
class IRiskEngine(ABC):

    @abstractmethod
    async def check_order_risk(
        self,
        user_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
    ) -> RiskCheckResult:
        """Check if an order is within risk limits."""
        pass

    @abstractmethod
    async def check_portfolio_risk(self, user_id: str) -> RiskAssessment:
        """Assess overall portfolio risk."""
        pass

    @abstractmethod
    async def set_risk_parameters(
        self,
        user_id: str,
        max_position_size: Optional[Decimal] = None,
        max_daily_loss: Optional[Decimal] = None,
        max_open_orders: Optional[int] = None,
    ) -> None:
        """Set risk parameters for a user."""
        pass

    @abstractmethod
    async def get_risk_parameters(self, user_id: str) -> RiskParameters:
        """Get current risk parameters for a user."""
        pass

    @abstractmethod
    async def on_price_update(self, user_id: str, symbol: str, price: Decimal) -> None:
        """Monitor price updates for risk triggers."""
        pass

    @abstractmethod
    async def trigger_stop_loss(self, instance_id: str, current_price: Decimal) -> bool:
        """Trigger stop-loss for a Trading Instance."""
        pass
```

### 9.2 Risk Data Types

```python
@dataclass
class RiskCheckResult:
    allowed: bool
    reason: Optional[str]
    current_exposure: Decimal
    max_exposure: Decimal

@dataclass
class RiskAssessment:
    risk_level: str    # "low" | "medium" | "high" | "critical"
    total_exposure: Decimal
    max_drawdown: Decimal
    recommendations: list[str]

@dataclass
class RiskParameters:
    max_position_size: Decimal
    max_daily_loss: Decimal
    max_open_orders: int
    stop_loss_enabled: bool
    stop_loss_percentage: Decimal
```

---

## 10. WORKER INTERFACE

### 10.1 IWorker

**Location**: `backend/workers/base.py`

**Responsibility**: Background job processing.

```python
class IWorker(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """Worker name."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the worker."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the worker."""
        pass

    @abstractmethod
    async def process_task(self, task: Task) -> TaskResult:
        """Process a single task."""
        pass

    @abstractmethod
    async def health_check(self) -> WorkerHealth:
        """Check worker health."""
        pass
```

### 10.2 Worker Data Types

```python
@dataclass
class Task:
    id: str
    type: str
    payload: dict
    priority: int       # 1 (high) to 5 (low)
    retry_count: int
    max_retries: int
    created_at: datetime
    scheduled_at: datetime

@dataclass
class TaskResult:
    task_id: str
    status: str         # "success" | "failed" | "retry"
    result: Optional[dict]
    error: Optional[str]
    completed_at: datetime

@dataclass
class WorkerHealth:
    name: str
    status: str         # "healthy" | "degraded" | "unhealthy"
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    uptime_seconds: int
```

---

## 11. NOTIFICATION INTERFACE

### 11.1 INotification

**Location**: `backend/services/notification/base.py`

**Responsibility**: Send notifications via multiple channels.

```python
class INotification(ABC):

    @abstractmethod
    async def send(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[dict] = None,
    ) -> str:
        """Send a notification to a user.
        
        Returns:
            Notification ID.
        """
        pass

    @abstractmethod
    async def send_batch(
        self,
        notifications: list[NotificationRequest],
    ) -> list[str]:
        """Send batch notifications."""
        pass

    @abstractmethod
    async def get_notifications(
        self,
        user_id: str,
        is_read: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """Get notifications for a user."""
        pass

    @abstractmethod
    async def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        pass

    @abstractmethod
    async def mark_all_as_read(self, user_id: str) -> bool:
        """Mark all notifications as read for a user."""
        pass

    @abstractmethod
    async def delete_notification(self, notification_id: str) -> bool:
        """Delete a notification."""
        pass
```

---

## 12. STORAGE INTERFACE

### 12.1 IStorage

**Location**: `backend/core/storage/base.py`

**Responsibility**: Abstract storage operations (local, S3, etc.).

```python
class IStorage(ABC):

    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload data to storage.
        
        Returns:
            URL or path to the stored data.
        """
        pass

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download data from storage."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete data from storage."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if data exists in storage."""
        pass

    @abstractmethod
    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Get a signed URL for the data."""
        pass
```

---

## 13. LOGGER INTERFACE

### 13.1 ILogger

**Location**: `backend/core/logger/base.py`

**Responsibility**: Structured logging with context.

```python
class ILogger(ABC):

    @abstractmethod
    def debug(self, message: str, **context) -> None:
        """Log debug message."""
        pass

    @abstractmethod
    def info(self, message: str, **context) -> None:
        """Log info message."""
        pass

    @abstractmethod
    def warning(self, message: str, **context) -> None:
        """Log warning message."""
        pass

    @abstractmethod
    def error(self, message: str, exc_info: bool = False, **context) -> None:
        """Log error message."""
        pass

    @abstractmethod
    def critical(self, message: str, exc_info: bool = False, **context) -> None:
        """Log critical message."""
        pass

    @abstractmethod
    def with_context(self, **context) -> "ILogger":
        """Create a child logger with additional context."""
        pass
```

---

## 14. REPOSITORY INTERFACE

### 14.1 IRepository

**Location**: `backend/repositories/base.py`

**Responsibility**: Generic repository pattern for database access.

```python
from typing import Generic, TypeVar

T = TypeVar("T")

class IRepository(Generic[T], ABC):

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def get_all(
        self,
        filters: Optional[dict] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Get all entities with optional filters."""
        pass

    @abstractmethod
    async def create(self, data: dict) -> T:
        """Create a new entity."""
        pass

    @abstractmethod
    async def update(self, id: str, data: dict) -> Optional[T]:
        """Update an entity."""
        pass

    @abstractmethod
    async def delete(self, id: str, soft: bool = True) -> bool:
        """Delete an entity."""
        pass

    @abstractmethod
    async def count(self, filters: Optional[dict] = None) -> int:
        """Count entities with optional filters."""
        pass
```

---

## 15. PROFIT LOCK INTERFACE

### 15.1 IProfitLock

**Location**: `backend/engine/profit_lock/base.py`

**Responsibility**: Manage trailing profit lock for Trading Instances.

```python
class IProfitLock(ABC):

    @abstractmethod
    async def enable(
        self,
        instance_id: str,
        trigger_percentage: Decimal,
        trail_percentage: Decimal,
    ) -> bool:
        """Enable profit lock for a Trading Instance."""
        pass

    @abstractmethod
    async def disable(self, instance_id: str) -> bool:
        """Disable profit lock for a Trading Instance."""
        pass

    @abstractmethod
    async def on_price_update(self, instance_id: str, current_price: Decimal) -> None:
        """Monitor price for profit lock triggers."""
        pass

    @abstractmethod
    async def get_state(self, instance_id: str) -> ProfitLockState:
        """Get current profit lock state."""
        pass

    @abstractmethod
    async def execute_lock(self, instance_id: str, lock_price: Decimal) -> bool:
        """Execute profit lock (place sell order)."""
        pass
```

### 15.2 Profit Lock Data Types

```python
@dataclass
class ProfitLockState:
    instance_id: str
    enabled: bool
    trigger_percentage: Decimal
    trail_percentage: Decimal
    highest_price: Optional[Decimal]
    lock_price: Optional[Decimal]
    is_triggered: bool
    is_executed: bool

@dataclass
class PortfolioLockState:
    instance_id: str
    enabled: bool
    trigger_profit_percentage: Decimal
    trail_profit_percentage: Decimal
    highest_total_profit: Decimal
    lock_profit: Optional[Decimal]
    is_triggered: bool
    is_executed: bool
```

---

## 16. PORTFOLIO LOCK INTERFACE

### 16.1 IPortfolioLock

**Location**: `backend/engine/portfolio_lock/base.py`

**Responsibility**: Manage trailing profit lock for the entire Trading Instance (close all positions when profit drops from peak).

```python
class IPortfolioLock(ABC):

    @abstractmethod
    async def enable(
        self,
        instance_id: str,
        trigger_profit_percentage: Decimal,
        trail_profit_percentage: Decimal,
    ) -> bool:
        """Enable portfolio lock for a Trading Instance."""
        pass

    @abstractmethod
    async def disable(self, instance_id: str) -> bool:
        """Disable portfolio lock."""
        pass

    @abstractmethod
    async def on_profit_update(self, instance_id: str, total_profit: Decimal) -> None:
        """Monitor total profit for portfolio lock triggers."""
        pass

    @abstractmethod
    async def get_state(self, instance_id: str) -> PortfolioLockState:
        """Get current portfolio lock state."""
        pass

    @abstractmethod
    async def execute_lock(self, context: TradingContext) -> bool:
        """Execute portfolio lock (close all positions)."""
        pass
```

---

## 17. EXECUTION ENGINE INTERFACE

### 16.1 IExecutionEngine

**Location**: `backend/engine/execution/base.py`

**Responsibility**: Execute orders on exchanges, manage order lifecycle.

```python
class IExecutionEngine(ABC):

    @abstractmethod
    async def execute_order(
        self,
        instance_id: str,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        grid_level: Optional[int] = None,
        is_profit_lock: bool = False,
    ) -> OrderResult:
        """Execute an order on the exchange."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> OrderResult:
        """Cancel an order. Returns updated order state with status CANCELLED."""
        pass

    @abstractmethod
    async def cancel_all_orders(self, instance_id: str) -> bool:
        """Cancel all orders for a Trading Instance."""
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderResult:
        """Get order status from exchange."""
        pass

    @abstractmethod
    async def sync_orders(self, instance_id: str) -> list[OrderResult]:
        """Synchronize order states with exchange."""
        pass
```

---

## 17. RECOVERY ENGINE INTERFACE

### 17.1 IRecoveryEngine

**Location**: `backend/engine/recovery/base.py`

**Responsibility**: Recover Trading Instances from error states.

```python
class IRecoveryEngine(ABC):

    @abstractmethod
    async def recover_process(self, instance_id: str) -> bool:
        """Recover a Trading Instance from error state.
        
        Steps:
        1. Sync state with exchange
        2. Reconcile orders
        3. Rebuild grid state
        4. Resume trading
        """
        pass

    @abstractmethod
    async def sync_state(self, instance_id: str) -> SyncResult:
        """Synchronize local state with exchange."""
        pass

    @abstractmethod
    async def reconcile_orders(self, instance_id: str) -> ReconciliationResult:
        """Reconcile local orders with exchange orders."""
        pass

    @abstractmethod
    async def rebuild_grid(self, instance_id: str) -> GridState:
        """Rebuild grid state from exchange data."""
        pass
```

### 17.2 Recovery Data Types

```python
@dataclass
class SyncResult:
    instance_id: str
    synced: bool
    discrepancies: list[str]
    corrected: list[str]

@dataclass
class ReconciliationResult:
    instance_id: str
    matched_orders: int
    mismatched_orders: int
    missing_orders: int
    extra_orders: int
    corrections: list[str]
```

---

## 18. KERNEL INTERFACE

### 18.1 IKernel

**Location**: `backend/kernel/base.py`

**Responsibility**: System bootstrap, dependency injection, lifecycle management.

```python
class IKernel(ABC):

    @abstractmethod
    async def initialize(self, config: dict) -> None:
        """Initialize the kernel with configuration."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start all services and workers."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop all services and workers gracefully."""
        pass

    @abstractmethod
    async def restart(self) -> None:
        """Restart the kernel."""
        pass

    @abstractmethod
    @property
    def kernel_context(self) -> KernelContext:
        """Get the shared KernelContext."""
        pass

    @abstractmethod
    def get_service(self, service_name: str) -> Any:
        """Get a service instance by name."""
        pass

    @abstractmethod
    def register_service(self, service_name: str, instance: Any) -> None:
        """Register a service instance."""
        pass

    @abstractmethod
    async def health_check(self) -> KernelHealth:
        """Check kernel health."""
        pass
```

### 18.2 Kernel Health

```python
@dataclass
class KernelHealth:
    status: str    # "healthy" | "degraded" | "unhealthy"
    services: dict[str, str]    # service_name -> status
    uptime_seconds: int
    active_connections: int
    memory_usage: float
    cpu_usage: float
```

---

## 19. CONTEXT & MEMORY OBJECTS

### 19.1 TradingContext

**Responsibility**: Carry all state needed for a single Trading Instance operation. Replaces passing individual IDs (`user_id`, `exchange_account_id`, `strategy_id`, etc.).

```python
@dataclass
class TradingContext:
    instance_id: str
    user: User
    exchange: Exchange
    exchange_account: ExchangeAccount
    trading_instance: TradingInstance
    strategy: Strategy
    grid_profile: GridProfile
    risk_profile: RiskProfile
    portfolio: Portfolio
    worker: Optional[IWorker] = None
    runtime: Optional[InstanceRuntime] = None
    configuration: Optional[InstanceConfiguration] = None
```

### 19.2 KernelContext

**Responsibility**: Provide shared system services to all engines. Every engine receives a `KernelContext` instead of 20 individual dependencies.

```python
@dataclass
class KernelContext:
    logger: ILogger
    events: IEventBus
    cache: ICache
    storage: IStorage
    config: Configuration
    metrics: IMetrics
    clock: IClock
    health: IHealthMonitor

    # Convenience accessors for engines
    @property
    def event_bus(self) -> IEventBus:
        return self.events

    @property
    def log(self) -> ILogger:
        return self.logger
```

### 19.3 ProcessMemory

**Responsibility**: In-memory snapshot of a Trading Instance. Workers read from memory; database is only for persistence and recovery.

```python
@dataclass
class ProcessMemory:
    instance_id: str
    snapshot_version: int
    status: str
    grid_state: GridState
    positions: list[Position]
    open_orders: list[OrderResult]
    balances: list[BalanceEntry]
    profit_lock_state: Optional[ProfitLockState] = None
    portfolio_lock_state: Optional[PortfolioLockState] = None
    market_data: dict[str, TickerData] = field(default_factory=dict)
    last_synced_at: Optional[datetime] = None
```

### 19.4 Additional Context Types

```python
@dataclass
class InstanceRuntime:
    worker_id: str
    allocated_at: datetime
    last_heartbeat_at: Optional[datetime] = None

@dataclass
class InstanceConfiguration:
    max_open_orders: int
    max_position_size: Decimal
    profit_lock_enabled: bool
    portfolio_lock_enabled: bool
    auto_recovery_enabled: bool

@dataclass
class TradingInstance:
    id: str
    user_id: str
    exchange_account_id: str
    strategy_id: str
    grid_profile_id: str
    symbol: str
    status: str  # "created" | "ready" | "running" | "paused" | "stopping" | "stopped" | "error" | "recovering"
    total_investment: Decimal
    base_currency: str
    quote_currency: str
    start_price: Decimal
    current_price: Optional[Decimal]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    stopped_at: Optional[datetime]
    error_message: Optional[str] = None

### 19.5 Kernel Service Interfaces

```python
class ICache(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]: pass
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool: pass
    @abstractmethod
    async def delete(self, key: str) -> bool: pass

class IMetrics(ABC):
    @abstractmethod
    def increment(self, name: str, value: int = 1, labels: Optional[dict] = None) -> None: pass
    @abstractmethod
    def gauge(self, name: str, value: float, labels: Optional[dict] = None) -> None: pass
    @abstractmethod
    def histogram(self, name: str, value: float, labels: Optional[dict] = None) -> None: pass

class IClock(ABC):
    @abstractmethod
    def now(self) -> datetime: pass
    @abstractmethod
    def timestamp(self) -> float: pass

class IHealthMonitor(ABC):
    @abstractmethod
    async def check(self) -> dict: pass
    @abstractmethod
    def register_check(self, name: str, check: Callable) -> None: pass
```

---

## 20. INTERFACE DEPENDENCY GRAPH

```
IKernel (holds KernelContext)
├── ITradingEngine
│   ├── IGridEngine
│   │   └── ProcessMemory
│   ├── IExecutionEngine
│   │   └── IExchangeAdapter
│   ├── IProfitLock
│   ├── IPortfolioLock
│   ├── IPortfolio
│   ├── IRiskEngine
│   └── IRecoveryEngine
│       └── IExchangeAdapter
├── IMarketHub
│   └── IExchangeAdapter
├── IEventBus
├── INotification
├── IStorage
├── ILogger
├── ICache
├── IMetrics
├── IClock
├── IHealthMonitor
└── IWorker(s)
    └── (depends on task type)

TradingContext (cross-cutting)
├── User
├── Exchange
├── ExchangeAccount
├── TradingInstance
├── Strategy
├── GridProfile
├── RiskProfile
└── Portfolio
```

---

## 21. CHANGE LOG

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-09 | 1.0.0 | Initial interface definitions |
| 2026-07-09 | 2.0.0 | Architecture revision: Trading Instance, TradingContext, KernelContext, ProcessMemory, separate market/account connections, TP/ProfitLock/PortfolioLock separation |
