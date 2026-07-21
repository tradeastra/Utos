"""
Technical Analysis Configuration model — per-instance TA indicator settings.

Each TradingInstance can have multiple TA configs (1:N).
When enabled, the TA engine evaluates indicators before the GridEngine places buy orders.
Multiple indicators are combined with AND/OR logic.
"""

import uuid

from database.base import GUID, Base, JSONBCompat
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class TechnicalAnalysisConfig(Base):
    """Per-instance technical analysis indicator configuration."""

    __tablename__ = "technical_analysis_configs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    trading_instance_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("trading_instances.id", ondelete="CASCADE"), nullable=False
    )
    indicator: Mapped[str] = mapped_column(String(50), nullable=False)
    time_frame: Mapped[str] = mapped_column(String(10), nullable=False, default="1h")
    operator: Mapped[str] = mapped_column(String(10), nullable=False, default="and")
    params: Mapped[dict | None] = mapped_column(JSONBCompat(), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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
        "TradingInstance", back_populates="ta_configs"
    )

    __table_args__ = (
        Index("idx_ta_configs_instance_id", "trading_instance_id"),
    )

    def __repr__(self) -> str:
        return f"<TAConfig indicator={self.indicator} tf={self.time_frame} enabled={self.enabled}>"
