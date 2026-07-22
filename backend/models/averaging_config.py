"""
Averaging Configuration model — per-step drop rate, buy amount multiplier, and take profit.

Each TradingInstance can have multiple AveragingConfig rows (1:N).
Step 0 is the initial buy; subsequent steps define averaging-down behavior.

Default template: 35 steps with standard pattern:
  Step 1: 0.6%, Step 2: 1.2%, Step 3: 1.1%, Step 4: 1.0%, Step 5: 2.0%, ...
"""

import uuid

from database.base import GUID, Base
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class AveragingConfig(Base):
    """Per-step averaging configuration for a trading instance."""

    __tablename__ = "averaging_configs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    trading_instance_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("trading_instances.id", ondelete="CASCADE"), nullable=False
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    drop_rate: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    multiple_buy_amount: Mapped[float] = mapped_column(
        Numeric(10, 4), nullable=False, default=1.0
    )
    take_profit: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    trading_instance: Mapped["TradingInstance"] = relationship(
        "TradingInstance", back_populates="averaging_configs"
    )

    __table_args__ = (
        UniqueConstraint("trading_instance_id", "step_number", name="uq_avg_config_instance_step"),
        Index("idx_averaging_configs_instance_id", "trading_instance_id"),
    )

    def __repr__(self) -> str:
        return f"<AveragingConfig step={self.step_number} drop={self.drop_rate}% tp={self.take_profit}%>"
