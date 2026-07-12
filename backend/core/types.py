"""
Core data types for UTOS Trading Engine.

This module defines the fundamental data types used throughout the system.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from decimal import Decimal
from datetime import datetime
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    LIMIT = "limit"
    MARKET = "market"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TradingInstanceStatus(str, Enum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    RECOVERING = "recovering"
    RECOVERED = "recovered"


class GridLevelStatus(str, Enum):
    IDLE = "idle"
    BUY_PENDING = "buy_pending"
    BUY_FILLED = "buy_filled"
    SELL_PENDING = "sell_pending"
    SELL_FILLED = "sell_filled"


class StrategyType(str, Enum):
    SMART_GRID = "smart_grid"
    ADAPTIVE_GRID = "adaptive_grid"
    INFINITY_GRID = "infinity_grid"
    DCA = "dca"


class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"


class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    FEE = "fee"
    SUBSCRIPTION = "subscription"
    REFUND = "refund"


class NotificationType(str, Enum):
    ORDER_FILLED = "order_filled"
    ORDER_FAILED = "order_failed"
    GRID_COMPLETED = "grid_completed"
    PROFIT_LOCK = "profit_lock"
    ERROR = "error"
    SYSTEM = "system"
    SUBSCRIPTION = "subscription"


class RiskLevel(str, Enum):
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
    recv_window: int = 5000


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
    status: str
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None


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
    leverage: Optional[Decimal] = None


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
    bids: List[tuple[Decimal, Decimal]]  # [(price, quantity), ...]
    asks: List[tuple[Decimal, Decimal]]
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
    supported_symbols: List[str]
    rate_limits: Dict[str, Any]
    fee_structure: Dict[str, Any]
    server_time: datetime


# Grid Engine Types
@dataclass
class GridLevel:
    level: int
    buy_price: Decimal
    sell_price: Decimal
    quantity: Decimal
    buy_order_id: Optional[str] = None
    sell_order_id: Optional[str] = None
    status: GridLevelStatus = GridLevelStatus.IDLE


@dataclass
class GridState:
    instance_id: str
    status: str  # "idle", "initialized", "active", "paused", "completed", "error"
    upper_price: Decimal
    lower_price: Decimal
    grid_count: int
    grid_spacing: Decimal
    investment_per_grid: Decimal
    levels: List[GridLevel] = field(default_factory=list)
    total_cycles: int = 0
    total_profit: Decimal = Decimal("0")


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
    positions: List[Position]


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
    reason: Optional[str]
    current_exposure: Decimal
    max_exposure: Decimal


@dataclass
class RiskAssessment:
    risk_level: RiskLevel
    total_exposure: Decimal
    max_drawdown: Decimal
    recommendations: List[str]


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
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


# Worker Types
@dataclass
class Task:
    id: str
    type: str
    payload: Dict[str, Any]
    priority: int  # 1 (high) to 5 (low)
    retry_count: int
    max_retries: int
    created_at: datetime
    scheduled_at: datetime


@dataclass
class TaskResult:
    task_id: str
    status: str  # "success", "failed", "retry"
    result: Optional[Dict[str, Any]]
    error: Optional[str]
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
    strategy_params: Dict[str, Any]
    status: TradingInstanceStatus
    total_investment: Decimal
    current_value: Decimal
    total_pnl: Decimal
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    
    # Grid-specific fields
    grid_upper_price: Optional[Decimal] = None
    grid_lower_price: Optional[Decimal] = None
    grid_count: Optional[int] = None
    investment_per_grid: Optional[Decimal] = None
    
    # Risk fields
    max_position_size: Optional[Decimal] = None
    stop_loss_percentage: Optional[Decimal] = None
    take_profit_percentage: Optional[Decimal] = None
    
    # Portfolio lock fields (premium feature)
    portfolio_lock_enabled: bool = False
    portfolio_lock_percentage: Optional[Decimal] = None


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
    data: Optional[Dict[str, Any]] = None


@dataclass
class Notification:
    id: str
    user_id: str
    type: str
    title: str
    message: str
    data: Optional[Dict[str, Any]]
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None
