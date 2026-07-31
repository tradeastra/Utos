"""
Trading instance model — matches DATABASE.md §2.3.
"""

import uuid

from core.domain_types import StrategyMode, TradingInstanceStatus
from database.base import GUID, Base, JSONBCompat
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class TradingInstance(Base):
    """Trading instances table."""

    __tablename__ = "trading_instances"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False
    )
    exchange_account_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("exchange_accounts.id"), nullable=False
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("strategies.id"), nullable=False
    )
    grid_profile_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("grid_profiles.id"), nullable=False
    )

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[TradingInstanceStatus] = mapped_column(
        Enum(TradingInstanceStatus, name="trading_instance_status", values_callable=lambda x: [e.value for e in x]),
        default=TradingInstanceStatus.CREATED,
        nullable=False,
    )

    start_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    current_price: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    total_investment: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(10), nullable=False)

    strategy_mode: Mapped[StrategyMode | None] = mapped_column(
        Enum(StrategyMode, name="strategy_mode_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    selected_coins: Mapped[list[str] | None] = mapped_column(JSONBCompat(), nullable=True)

    # Circuit breaker config (chosen by user in setup wizard).
    # continuation_rate: 0.70 / 0.80 / 0.90 — selects which breaker threshold tier to use.
    # breaker_enabled: master toggle.
    continuation_rate: Mapped[float | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    breaker_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    mm_preset_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("mm_presets.id"), nullable=True
    )
    capital: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)

    profit_lock_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    profit_lock_trigger_percentage: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    profit_lock_trail_percentage: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    portfolio_lock_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    portfolio_lock_trigger_percentage: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    portfolio_lock_trail_percentage: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )

    avg_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    non_stop: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    partial_sell: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    formula_mode: Mapped[str] = mapped_column(
        String(50), default="default", nullable=False
    )

    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    memory_snapshot: Mapped[dict | None] = mapped_column(JSONBCompat(), nullable=True)
    memory_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stopped_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="trading_instances")
    exchange_account: Mapped["ExchangeAccount"] = relationship(
        back_populates="trading_instances"
    )
    strategy: Mapped["Strategy"] = relationship(back_populates="trading_instances")
    grid_profile: Mapped["GridProfile"] = relationship(
        back_populates="trading_instances"
    )
    mm_preset: Mapped["MMPreset | None"] = relationship("MMPreset")
    orders: Mapped[list["Order"]] = relationship(
        back_populates="trading_instance", cascade="all, delete-orphan"
    )
    positions: Mapped[list["Position"]] = relationship(
        back_populates="trading_instance", cascade="all, delete-orphan"
    )
    averaging_configs: Mapped[list["AveragingConfig"]] = relationship(
        back_populates="trading_instance", cascade="all, delete-orphan",
        order_by="AveragingConfig.step_number",
    )
    ta_configs: Mapped[list["TechnicalAnalysisConfig"]] = relationship(
        back_populates="trading_instance", cascade="all, delete-orphan",
        order_by="TechnicalAnalysisConfig.priority",
    )

    __table_args__ = (
        Index("idx_trading_instances_user_id", "user_id"),
        Index("idx_trading_instances_exchange_account_id", "exchange_account_id"),
        Index("idx_trading_instances_strategy_id", "strategy_id"),
        Index("idx_trading_instances_status", "status"),
        Index("idx_trading_instances_symbol", "symbol"),
    )

    def __repr__(self) -> str:
        return (
            f"<TradingInstance id={self.id} symbol={self.symbol} status={self.status}>"
        )
