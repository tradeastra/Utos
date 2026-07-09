"""
Core context objects for UTOS Trading Engine.

This module defines the three core context objects:
- TradingContext: Trading-specific state for a single Trading Instance
- KernelContext: Shared system services available to all engines
- ProcessMemory: In-memory snapshot of a Trading Instance's state
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class TradingContext:
    """Immutable-like context object for trading operations.
    
    Contains all trading-specific state for a single Trading Instance.
    Passed to every trading operation instead of many individual IDs.
    """
    # Instance identification
    instance_id: str
    user_id: str
    
    # Exchange and account
    exchange_name: str
    exchange_account_id: str
    
    # Trading configuration
    symbol: str
    strategy_type: str
    strategy_params: Dict[str, Any]
    
    # Grid configuration (if applicable)
    grid_upper_price: Optional[Decimal] = None
    grid_lower_price: Optional[Decimal] = None
    grid_count: Optional[int] = None
    investment_per_grid: Optional[Decimal] = None
    
    # Risk configuration
    max_position_size: Optional[Decimal] = None
    stop_loss_percentage: Optional[Decimal] = None
    take_profit_percentage: Optional[Decimal] = None
    
    # Portfolio lock configuration (premium feature)
    portfolio_lock_enabled: bool = False
    portfolio_lock_percentage: Optional[Decimal] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class KernelContext:
    """System-wide services accessed by all engines.
    
    Provides access to shared system services like logging, event bus,
    cache, storage, configuration, metrics, and clock.
    """
    # Core services
    logger: Any  # ILogger interface
    event_bus: Any  # IEventBus interface
    cache: Any  # Redis client
    storage: Any  # IStorage interface
    
    # Configuration
    config: Dict[str, Any]
    
    # Metrics and monitoring
    metrics: Any  # Metrics collector
    
    # Clock (for testing)
    clock: Any = field(default_factory=lambda: datetime.utcnow)
    
    # Application state
    is_shutting_down: bool = False


@dataclass
class ProcessMemory:
    """In-memory snapshot of a Trading Instance's state.
    
    Runtime state lives in ProcessMemory; database is only for persistence.
    Workers read from memory; database is for recovery only.
    """
    # Instance identification
    instance_id: str
    
    # State machine
    status: str  # "created", "ready", "running", "paused", "stopped", "error"
    
    # Market data
    current_price: Optional[Decimal] = None
    last_price_update: Optional[datetime] = None
    
    # Grid state (if applicable)
    grid_state: Optional[Dict[str, Any]] = None
    
    # Position tracking
    current_position: Optional[Dict[str, Any]] = None
    unrealized_pnl: Decimal = Decimal("0")
    
    # Order tracking
    active_orders: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    order_history: list[Dict[str, Any]] = field(default_factory=list)
    
    # Performance metrics
    total_cycles: int = 0
    total_profit: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")
    
    # Risk monitoring
    risk_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Strategy-specific state
    strategy_state: Dict[str, Any] = field(default_factory=dict)
    
    # Exchange connection state
    market_connected: bool = False
    account_connected: bool = False
    
    # Error tracking
    last_error: Optional[str] = None
    error_count: int = 0
    
    # Metadata
    last_updated: datetime = field(default_factory=datetime.utcnow)
    version: int = 1  # For optimistic locking
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ProcessMemory to dictionary for persistence."""
        return {
            "instance_id": self.instance_id,
            "status": self.status,
            "current_price": float(self.current_price) if self.current_price else None,
            "last_price_update": self.last_price_update.isoformat() if self.last_price_update else None,
            "grid_state": self.grid_state,
            "current_position": self.current_position,
            "unrealized_pnl": float(self.unrealized_pnl),
            "active_orders": self.active_orders,
            "order_history": self.order_history,
            "total_cycles": self.total_cycles,
            "total_profit": float(self.total_profit),
            "total_fees": float(self.total_fees),
            "risk_metrics": self.risk_metrics,
            "strategy_state": self.strategy_state,
            "market_connected": self.market_connected,
            "account_connected": self.account_connected,
            "last_error": self.last_error,
            "error_count": self.error_count,
            "last_updated": self.last_updated.isoformat(),
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessMemory":
        """Create ProcessMemory from dictionary."""
        # Convert Decimal fields back
        if data.get("current_price") is not None:
            data["current_price"] = Decimal(str(data["current_price"]))
        if data.get("unrealized_pnl") is not None:
            data["unrealized_pnl"] = Decimal(str(data["unrealized_pnl"]))
        if data.get("total_profit") is not None:
            data["total_profit"] = Decimal(str(data["total_profit"]))
        if data.get("total_fees") is not None:
            data["total_fees"] = Decimal(str(data["total_fees"]))
        
        # Convert datetime fields back
        if data.get("last_price_update") is not None:
            data["last_price_update"] = datetime.fromisoformat(data["last_price_update"])
        if data.get("last_updated") is not None:
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        
        return cls(**data)


@dataclass
class StrategyContext:
    """Context object for strategy implementations.
    
    Provides strategies with access to trading context, kernel services,
    and process memory while maintaining isolation.
    """
    trading_context: TradingContext
    kernel_context: KernelContext
    process_memory: ProcessMemory
    state: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def instance_id(self) -> str:
        """Get instance ID for convenience."""
        return self.trading_context.instance_id
    
    @property
    def symbol(self) -> str:
        """Get symbol for convenience."""
        return self.trading_context.symbol
    
    @property
    def current_price(self) -> Optional[Decimal]:
        """Get current price for convenience."""
        return self.process_memory.current_price
