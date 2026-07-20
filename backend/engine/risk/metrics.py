"""
PortfolioMetrics — generates portfolio-level metrics.

Computes unrealized PnL, realized PnL, total exposure, drawdown, margin usage.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from engine.risk.portfolio import Position


@dataclass
class PortfolioReport:
    """Full portfolio metrics report."""

    unrealized_pnl: Decimal
    realized_pnl: Decimal
    total_pnl: Decimal
    total_exposure: Decimal
    drawdown: Decimal
    margin_usage: Decimal
    position_count: int
    timestamp: datetime


class PortfolioMetrics:
    """Calculate portfolio-level metrics."""

    @staticmethod
    def calculate_unrealized_pnl(
        positions: list[Position], current_prices: dict[str, Decimal]
    ) -> Decimal:
        total = Decimal("0")
        for pos in positions:
            if pos.closed:
                continue
            price = current_prices.get(pos.symbol)
            if price is None:
                continue
            if pos.side == "long":
                total += (price - pos.entry_price) * pos.quantity
            else:
                total += (pos.entry_price - price) * pos.quantity
        return total

    @staticmethod
    def calculate_realized_pnl(closed_positions: list[Position]) -> Decimal:
        return sum(
            (pos.realized_pnl for pos in closed_positions),
            Decimal("0"),
        )

    @staticmethod
    def calculate_total_exposure(
        positions: list[Position], current_prices: dict[str, Decimal]
    ) -> Decimal:
        total = Decimal("0")
        for pos in positions:
            if pos.closed:
                continue
            price = current_prices.get(pos.symbol, pos.entry_price)
            total += price * pos.quantity
        return total

    @staticmethod
    def calculate_drawdown(pnl_history: list[Decimal]) -> Decimal:
        """Calculate max drawdown from a PnL history series.

        Drawdown = peak-to-trough decline.
        """
        if not pnl_history:
            return Decimal("0")

        peak = pnl_history[0]
        max_dd = Decimal("0")

        for value in pnl_history:
            if value > peak:
                peak = value
            dd = peak - value
            if dd > max_dd:
                max_dd = dd

        return max_dd

    @staticmethod
    def calculate_margin_usage(
        positions: list[Position],
        current_prices: dict[str, Decimal],
        account_balance: Decimal,
    ) -> Decimal:
        """Calculate margin usage as a percentage of account balance."""
        if account_balance <= 0:
            return Decimal("0")

        total_exposure = PortfolioMetrics.calculate_total_exposure(
            positions, current_prices
        )
        return (total_exposure / account_balance) * Decimal("100")

    @classmethod
    def generate_report(
        cls,
        positions: list[Position],
        current_prices: dict[str, Decimal],
        closed_positions: list[Position],
        pnl_history: list[Decimal],
        account_balance: Decimal,
    ) -> PortfolioReport:
        """Generate a full portfolio report."""
        unrealized = cls.calculate_unrealized_pnl(positions, current_prices)
        realized = cls.calculate_realized_pnl(closed_positions)
        exposure = cls.calculate_total_exposure(positions, current_prices)
        drawdown = cls.calculate_drawdown(pnl_history)
        margin = cls.calculate_margin_usage(positions, current_prices, account_balance)
        open_count = sum(1 for p in positions if not p.closed)

        return PortfolioReport(
            unrealized_pnl=unrealized,
            realized_pnl=realized,
            total_pnl=unrealized + realized,
            total_exposure=exposure,
            drawdown=drawdown,
            margin_usage=margin,
            position_count=open_count,
            timestamp=datetime.now(UTC),
        )
