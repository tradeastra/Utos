"""
Grid profile model — matches DATABASE.md §2.6.
"""

import uuid

from core.domain_types import StrategyType
from database.base import GUID, Base
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class GridProfile(Base):
    """Grid profiles table."""

    __tablename__ = "grid_profiles"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_type: Mapped[StrategyType] = mapped_column(
        Enum(StrategyType, name="grid_strategy_type", values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    upper_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    lower_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    grid_count: Mapped[int] = mapped_column(Integer, nullable=False)
    grid_spacing: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    investment_per_grid: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)

    take_profit_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    take_profit_percentage: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    stop_loss_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    stop_loss_percentage: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )

    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="grid_profiles")
    trading_instances: Mapped[list["TradingInstance"]] = relationship(
        back_populates="grid_profile"
    )

    __table_args__ = (Index("idx_grid_profiles_user_id", "user_id"),)

    def __repr__(self) -> str:
        return f"<GridProfile id={self.id} name={self.name}>"
