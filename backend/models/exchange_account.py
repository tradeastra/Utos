"""
Exchange account model for UTOS Trading Engine.

This module defines the ExchangeAccount model and related database entities.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from database.base import Base


class ExchangeName(str, enum.Enum):
    """Exchange name enum."""
    BINANCE = "binance"
    BYBIT = "bybit"
    OKX = "okx"
    KRAKEN = "kraken"
    HUOBI = "huobi"
    KUCOIN = "kucoin"


class ExchangeAccount(Base):
    """Exchange account model."""
    
    __tablename__ = "exchange_accounts"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Exchange information
    exchange_name = Column(Enum(ExchangeName), nullable=False)
    is_testnet = Column(Boolean, default=False, nullable=False)
    
    # Encrypted credentials
    encrypted_api_key = Column(Text, nullable=False)
    encrypted_api_secret = Column(Text, nullable=False)
    encrypted_passphrase = Column(Text, nullable=True)  # For exchanges that require passphrase
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_connected = Column(Boolean, default=False, nullable=False)
    last_connected_at = Column(DateTime(timezone=True), nullable=True)
    
    # Exchange configuration
    config = Column(JSONB, nullable=True)  # Exchange-specific configuration
    
    # Permissions and limits
    permissions = Column(JSONB, nullable=True)  # API permissions
    rate_limits = Column(JSONB, nullable=True)  # Exchange rate limits
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="exchange_accounts")
    trading_instances = relationship("TradingInstance", back_populates="exchange_account", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ExchangeAccount(id={self.id}, exchange={self.exchange_name}, user_id={self.user_id})>"


class ExchangeBalance(Base):
    """Exchange balance cache model."""
    
    __tablename__ = "exchange_balances"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key
    exchange_account_id = Column(UUID(as_uuid=True), ForeignKey("exchange_accounts.id"), nullable=False, index=True)
    
    # Balance information
    currency = Column(String(10), nullable=False)
    available = Column(String(30), nullable=False)  # Store as string to avoid precision issues
    locked = Column(String(30), nullable=False)
    total = Column(String(30), nullable=False)
    
    # Metadata
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    exchange_account = relationship("ExchangeAccount", back_populates="balances")
    
    # Composite index
    __table_args__ = (
        Index('idx_exchange_account_currency', 'exchange_account_id', 'currency'),
    )
    
    def __repr__(self):
        return f"<ExchangeBalance(account_id={self.exchange_account_id}, currency={self.currency})>"


# Add balances relationship to ExchangeAccount
ExchangeAccount.balances = relationship("ExchangeBalance", back_populates="exchange_account", cascade="all, delete-orphan")
