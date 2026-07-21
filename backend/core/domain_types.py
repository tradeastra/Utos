"""
Core data types for UTOS Trading Engine.

This module defines the fundamental data types used throughout the system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    LIMIT = "limit"
    MARKET = "market"
    STOP_LIMIT = "stop_limit"


class OrderStatus(StrEnum):
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TradingInstanceStatus(StrEnum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    RECOVERING = "recovering"
    RECOVERED = "recovered"


class GridLevelStatus(StrEnum):
    WAITING = "waiting"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    TP_HIT = "tp_hit"
    # Legacy aliases for backward compatibility
    IDLE = "waiting"
    BUY_PENDING = "open"
    BUY_FILLED = "filled"
    SELL_PENDING = "open"
    SELL_FILLED = "tp_hit"


class StrategyType(StrEnum):
    SMART_GRID = "smart_grid"
    ADAPTIVE_GRID = "adaptive_grid"
    INFINITY_GRID = "infinity_grid"
    DCA = "dca"


class StrategyMode(StrEnum):
    """Moonbot-style strategy modes — daily range & risk level presets."""
    A = "super_bearish"
    B = "conventional"
    C = "aggressive"
    D = "very_aggressive"
    U = "ultimate"


class MoneyManagementPreset(StrEnum):
    """Money Management presets — control buy amount, max coins, and capital allocation."""
    MM30 = "mm30"
    MM50 = "mm50"
    MM70 = "mm70"
    CUSTOM = "custom"


class TAIndicator(StrEnum):
    """Technical Analysis indicators available as order gates."""
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER_BANDS = "bollinger_bands"
    FIBONACCI_RETRACEMENT = "fibonacci_retracement"
    EMA_CROSSOVER = "ema_crossover"
    SMA_CROSSOVER = "sma_crossover"
    STOCHASTIC = "stochastic"
    ATR = "atr"


class TAOperator(StrEnum):
    """Logical operator for combining multiple TA indicators."""
    AND = "and"
    OR = "or"


class TimeFrame(StrEnum):
    """Supported timeframes for technical analysis."""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


class PositionSide(StrEnum):
    LONG = "long"
    SHORT = "short"


class TransactionType(StrEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    FEE = "fee"
    SUBSCRIPTION = "subscription"
    REFUND = "refund"


class NotificationType(StrEnum):
    ORDER_FILLED = "order_filled"
    ORDER_FAILED = "order_failed"
    GRID_COMPLETED = "grid_completed"
    PROFIT_LOCK = "profit_lock"
    ERROR = "error"
    SYSTEM = "system"
    SUBSCRIPTION = "subscription"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Exchange Adapter Types
@dataclass
class ExchangeCredentials:
    exchange_name: str
    api_key: str
    api_secret: str
    passphrase: str | None = None  # Required for some exchanges (OKX, etc.)


@dataclass
class ExchangeAdapterConfig:
    exchange_name: str
    is_testnet: bool = False
    market_stream_url: str | None = None
    account_stream_url: str | None = None
    rest_url: str | None = None
    connection_timeout: float = 10.0
    request_timeout: float = 30.0
    recv_window: int = 5000


@dataclass
class OrderResult:
    order_id: str
    exchange_order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None
    filled_quantity: Decimal
    average_fill_price: Decimal | None
    status: str
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None


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
    leverage: Decimal | None = None


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
    bids: list[tuple[Decimal, Decimal]]  # [(price, quantity), ...]
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
    rate_limits: dict[str, Any]
    fee_structure: dict[str, Any]
    server_time: datetime


# Grid Engine Types
@dataclass
class GridLevel:
    level: int
    buy_price: Decimal
    sell_price: Decimal
    quantity: Decimal
    buy_order_id: str | None = None
    sell_order_id: str | None = None
    status: GridLevelStatus = GridLevelStatus.WAITING


@dataclass
class GridState:
    instance_id: str
    status: str  # "idle", "initialized", "active", "paused", "completed", "error"
    upper_price: Decimal
    lower_price: Decimal
    grid_count: int
    grid_spacing: Decimal
    investment_per_grid: Decimal
    levels: list[GridLevel] = field(default_factory=list)
    total_cycles: int = 0
    total_profit: Decimal = Decimal("0")
    exchange_account_id: Any | None = None
    symbol: str = ""
    current_price: Decimal | None = None


# Portfolio Types
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
class PortfolioSummary:
    total_value: Decimal
    total_investment: Decimal
    total_pnl: Decimal
    pnl_percentage: Decimal
    positions: list[Position]


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
    date: datetime
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal


# Risk Engine Types
@dataclass
class RiskCheckResult:
    allowed: bool
    reason: str | None
    current_exposure: Decimal
    max_exposure: Decimal


@dataclass
class RiskAssessment:
    risk_level: RiskLevel
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


# Event Bus Types
@dataclass
class Event:
    event_type: str
    event_id: str
    timestamp: datetime
    data: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


# Worker Types
@dataclass
class Task:
    id: str
    type: str
    payload: dict[str, Any]
    priority: int  # 1 (high) to 5 (low)
    retry_count: int
    max_retries: int
    created_at: datetime
    scheduled_at: datetime


@dataclass
class TaskResult:
    task_id: str
    status: str  # "success", "failed", "retry"
    result: dict[str, Any] | None
    error: str | None
    completed_at: datetime


@dataclass
class WorkerHealth:
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    uptime_seconds: int


# Trading Instance Types
@dataclass
class TradingInstance:
    id: str
    user_id: str
    exchange_account_id: str
    symbol: str
    strategy_type: str
    strategy_params: dict[str, Any]
    status: TradingInstanceStatus
    total_investment: Decimal
    current_value: Decimal
    total_pnl: Decimal
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    stopped_at: datetime | None = None

    # Grid-specific fields
    grid_upper_price: Decimal | None = None
    grid_lower_price: Decimal | None = None
    grid_count: int | None = None
    investment_per_grid: Decimal | None = None

    # Risk fields
    max_position_size: Decimal | None = None
    stop_loss_percentage: Decimal | None = None
    take_profit_percentage: Decimal | None = None

    # Portfolio lock fields (premium feature)
    portfolio_lock_enabled: bool = False
    portfolio_lock_percentage: Decimal | None = None


# Strategy Types
@dataclass
class FillEvent:
    order_id: str
    exchange_order_id: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    fee: Decimal
    fee_currency: str
    timestamp: datetime


# Notification Types
@dataclass
class NotificationRequest:
    user_id: str
    notification_type: str
    title: str
    message: str
    data: dict[str, Any] | None = None


@dataclass
class Notification:
    id: str
    user_id: str
    type: str
    title: str
    message: str
    data: dict[str, Any] | None
    is_read: bool
    created_at: datetime
    read_at: datetime | None = None
