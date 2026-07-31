"""
BreakerThreshold model — pre-computed daily drop circuit breaker thresholds
per symbol, stored as the app's "source of truth".

The BreakerScreeningStore runs the CircuitBreakerScreener periodically (or on
startup) for all supported symbols and upserts the results into this table.
When a user applies a strategy / starts a trading instance, the grid engine
reads the threshold from here instead of re-fetching and re-analyzing
historical candles each time.

Schema:
  - exchange + symbol + continuation_rate form a unique key (one threshold
    per symbol per continuation-rate setting).
  - threshold_pct is the positive drop % that triggers the breaker.
  - used_fallback indicates whether the value came from historical data or
    the conservative fallback (no candles / insufficient samples).
"""

import uuid
from datetime import datetime

from database.base import GUID, Base
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func


class BreakerThreshold(Base):
    """Pre-computed circuit breaker threshold for a single symbol."""

    __tablename__ = "breaker_thresholds"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    exchange: Mapped[str] = mapped_column(String(30), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    # Continuation rate used to derive the threshold (e.g. 0.70, 0.80, 0.90).
    # Part of the unique key — different rates yield different thresholds.
    min_continuation_rate: Mapped[float] = mapped_column(
        Numeric(precision=3, scale=2), nullable=False
    )
    # The critical drop threshold as a positive percentage (e.g. 4.0 = 4%).
    threshold_pct: Mapped[float] = mapped_column(
        Numeric(precision=5, scale=2), nullable=False
    )
    # Screening parameters used (for audit / reproducibility).
    continuation_window: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    min_future_drop_pct: Mapped[float] = mapped_column(
        Numeric(precision=5, scale=2), nullable=False, default=9.0
    )
    lookback_days: Mapped[int] = mapped_column(Integer, nullable=False, default=365)
    candle_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    used_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Resume behavior after the breaker triggers (tier default).
    # "ta_confirm" = wait for 15m TA reversal (default/legacy).
    # "widen_step" = keep buying with grid step × widen_multiplier.
    # "trailing_buy" = stop, resume after price recovers recovery_pct from low.
    resume_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ta_confirm"
    )
    recovery_pct: Mapped[float] = mapped_column(
        Numeric(precision=4, scale=2), nullable=False, default=5.0
    )
    widen_multiplier: Mapped[float] = mapped_column(
        Numeric(precision=3, scale=1), nullable=False, default=2.0
    )
    # Optional human-readable note (e.g. "screened on startup", "manual override").
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    screened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # One row per (exchange, symbol, continuation_rate).
        Index(
            "ux_breaker_thresholds_key",
            "exchange",
            "symbol",
            "min_continuation_rate",
            unique=True,
        ),
        Index("idx_breaker_thresholds_symbol", "symbol"),
    )

    def __repr__(self) -> str:
        return (
            f"<BreakerThreshold {self.exchange}:{self.symbol} "
            f"rate={self.min_continuation_rate} threshold={self.threshold_pct}%>"
        )
