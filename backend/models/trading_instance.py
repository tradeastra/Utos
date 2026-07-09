"""
Trading instance model for UTOS Trading Engine.

This module defines the TradingInstance model and related database entities.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum, ForeignKey, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from decimal import Decimal

from database.base import Base


class TradingInstanceStatus(str, enum.Enum):
    """Trading instance status enum."""
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    RECOVERING = "recovering"
    RECOVERED = "recovered"


class StrategyType(str, enum.Enum):
    """Strategy type enum."""
    SMART_GRID = "smart_grid"
    ADAPTIVE_GRID = "adaptive_grid"
    INFINITY_GRID = "infinity_grid"
    DCA = "dca"


class TradingInstance(Base):
    """Trading instance model."""
    
    __tablename__ = "trading_instances"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    exchange_account_id = Column(UUID(as_uuid=True), ForeignKey("exchange_accounts.id"), nullable=False, index=True)
    
    # Basic information
    symbol = Column(String(20), nullable=False, index=True)
    strategy_type = Column(Enum(StrategyType), nullable=False)
    strategy_params = Column(JSONB, nullable=False)
    
    # Status
    status = Column(Enum(TradingInstanceStatus), default=TradingInstanceStatus.CREATED, nullable=False, index=True)
    
    # Financial information (stored as strings to avoid precision issues)
    total_investment = Column(Numeric(20, 8), nullable=False)
    current_value = Column(Numeric(20, 8), nullable=False)
    total_pnl = Column(Numeric(20, 8), nullable=False)
    total_fees = Column(Numeric(20, 8), nullable=False)
    
    # Grid configuration
    grid_upper_price = Column(Numeric(20, 8), nullable=True)
    grid_lower_price = Column(Numeric(20, 8), nullable=True)
    grid_count = Column(Integer, nullable=True)
    investment_per_grid = Column(Numeric(20, 8), nullable=True)
    
    # Risk management
    max_position_size = Column(Numeric(20, 8), nullable=True)
    stop_loss_percentage = Column(Numeric(5, 2), nullable=True)
    take_profit_percentage = Column(Numeric(5, 2), nullable=True)
    
    # Portfolio lock (premium feature)
    portfolio_lock_enabled = Column(Boolean, default=False, nullable=False)
    portfolio_lock_percentage = Column(Numeric(5, 2), nullable=True)
    
    # Performance metrics
    total_cycles = Column(Integer, default=0, nullable=False)
    total_trades = Column(Integer, default=0, nullable=False)
    total_wins = Column(Integer, default=0, nullable=False)
    total_losses = Column(Integer, default=0, nullable=False)
    win_rate = Column(Numeric(5, 2), default=0, nullable=False)
    
    # Error tracking
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    
    # Process memory snapshot (JSON)
    process_memory = Column(JSONB, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="trading_instances")
    exchange_account = relationship("ExchangeAccount", back_populates="trading_instances")
    orders = relationship("Order", back_populates="trading_instance", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="trading_instance", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="trading_instance", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TradingInstance(id={self.id}, symbol={self.symbol}, status={self.status})>"


class Order(Base):
    """Order model."""
    
    __tablename__ = "orders"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key
    trading_instance_id = Column(UUID(as_uuid=True), ForeignKey("trading_instances.id"), nullable=False, index=True)
    
    # Exchange information
    exchange_order_id = Column(String(100), nullable=True, index=True)
    
    # Order details
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(OrderSide), nullable=False)  # buy/sell
    order_type = Column(Enum(OrderType), nullable=False)  # limit/market/stop_limit
    quantity = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8), nullable=True)
    stop_price = Column(Numeric(20, 8), nullable=True)
    
    # Order status
    status = Column(Enum(OrderStatus), nullable=False, index=True)
    
    # Fill information
    filled_quantity = Column(Numeric(20, 8), default=0, nullable=False)
    average_fill_price = Column(Numeric(20, 8), nullable=True)
    fill_fee = Column(Numeric(20, 8), nullable=True)
    
    # Grid information
    grid_level = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    filled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    trading_instance = relationship("TradingInstance", back_populates="orders")
    
    def __repr__(self):
        return f"<Order(id={self.id}, symbol={self.symbol}, status={self.status})>"


class Position(Base):
    """Position model."""
    
    __tablename__ = "positions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key
    trading_instance_id = Column(UUID(as_uuid=True), ForeignKey("trading_instances.id"), nullable=False, index=True)
    
    # Position details
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(PositionSide), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    
    # Price information
    entry_price = Column(Numeric(20, 8), nullable=False)
    current_price = Column(Numeric(20, 8), nullable=False)
    exit_price = Column(Numeric(20, 8), nullable=True)
    
    # P&L information
    unrealized_pnl = Column(Numeric(20, 8), default=0, nullable=False)
    realized_pnl = Column(Numeric(20, 8), default=0, nullable=False)
    
    # Status
    is_open = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    trading_instance = relationship("TradingInstance", back_populates="positions")
    
    def __repr__(self):
        return f"<Position(id={self.id}, symbol={self.symbol}, is_open={self.is_open})>"


class Transaction(Base):
    """Transaction model."""
    
    __tablename__ = "transactions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key
    trading_instance_id = Column(UUID(as_uuid=True), ForeignKey("trading_instances.id"), nullable=False, index=True)
    
    # Transaction details
    transaction_type = Column(Enum(TransactionType), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(OrderSide), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    
    # Financial information
    total_amount = Column(Numeric(20, 8), nullable=False)
    fee = Column(Numeric(20, 8), nullable=False)
    fee_currency = Column(String(10), nullable=False)
    
    # Exchange information
    exchange_order_id = Column(String(100), nullable=True)
    exchange_trade_id = Column(String(100), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    trading_instance = relationship("TradingInstance", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, type={self.transaction_type}, symbol={self.symbol})>"


# Import enums from core.types
from core.types import OrderSide, OrderType, OrderStatus, PositionSide, TransactionType
