"""
PortfolioManager — manages all active positions across Trading Processes.

Tracks positions per instance, per account, per exchange.
Updates on order fills, closes on sell-side fills.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from core.exceptions import PortfolioError, ValidationError


@dataclass
class Position:
    """A single trading position tied to a Trading Instance."""

    instance_id: str
    account_id: str
    exchange: str
    symbol: str
    side: str  # "long" or "short"
    entry_price: Decimal
    quantity: Decimal
    realized_pnl: Decimal = Decimal("0")
    opened_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    closed: bool = False
    closed_at: datetime | None = None


class PortfolioManager:
    """In-memory portfolio manager tracking positions across all instances."""

    def __init__(self) -> None:
        self._positions: dict[str, Position] = {}  # keyed by instance_id
        self._closed_positions: list[Position] = []

    def register_position(
        self,
        instance_id: str,
        account_id: str,
        exchange: str,
        symbol: str,
        side: str,
        entry_price: Decimal,
        quantity: Decimal,
    ) -> Position:
        """Register a new position. Raises if one already exists for instance_id."""
        if instance_id in self._positions:
            raise PortfolioError(f"Position already exists for instance {instance_id}")
        if side not in ("long", "short"):
            raise ValidationError(f"side must be 'long' or 'short', got '{side}'")
        if entry_price <= 0:
            raise ValidationError(f"entry_price must be > 0, got {entry_price}")
        if quantity <= 0:
            raise ValidationError(f"quantity must be > 0, got {quantity}")

        position = Position(
            instance_id=instance_id,
            account_id=account_id,
            exchange=exchange,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
        )
        self._positions[instance_id] = position
        return position

    def update_position(
        self,
        instance_id: str,
        fill_price: Decimal,
        fill_quantity: Decimal,
        side: str,
    ) -> Position:
        """Update position on order fill.

        For long position:
          - BUY fill → increase quantity, update avg entry price
          - SELL fill → decrease quantity, realize PnL
        For short position:
          - SELL fill → increase quantity, update avg entry price
          - BUY fill → decrease quantity, realize PnL
        """
        position = self._positions.get(instance_id)
        if position is None:
            raise PortfolioError(f"Position not found for instance {instance_id}")
        if position.closed:
            raise PortfolioError(f"Position already closed for instance {instance_id}")

        is_opening = (position.side == "long" and side == "buy") or (
            position.side == "short" and side == "sell"
        )

        if is_opening:
            total_cost = (
                position.entry_price * position.quantity + fill_price * fill_quantity
            )
            total_qty = position.quantity + fill_quantity
            position.entry_price = total_cost / total_qty
            position.quantity = total_qty
        else:
            if fill_quantity > position.quantity:
                raise PortfolioError(
                    f"Fill quantity {fill_quantity} exceeds position quantity {position.quantity}"
                )
            if position.side == "long":
                pnl = (fill_price - position.entry_price) * fill_quantity
            else:
                pnl = (position.entry_price - fill_price) * fill_quantity
            position.realized_pnl += pnl
            position.quantity -= fill_quantity
            if position.quantity == 0:
                position.closed = True
                position.closed_at = datetime.now(UTC)

        return position

    def close_position(self, instance_id: str) -> Position:
        """Force-close a position (e.g., on disable/cancel)."""
        position = self._positions.get(instance_id)
        if position is None:
            raise PortfolioError(f"Position not found for instance {instance_id}")
        position.closed = True
        position.closed_at = datetime.now(UTC)
        del self._positions[instance_id]
        self._closed_positions.append(position)
        return position

    def get_position(self, instance_id: str) -> Position | None:
        return self._positions.get(instance_id)

    def get_positions(
        self,
        instance_id: str | None = None,
        account_id: str | None = None,
        exchange: str | None = None,
        symbol: str | None = None,
    ) -> list[Position]:
        """Get positions filtered by optional criteria."""
        positions = list(self._positions.values())
        if instance_id:
            positions = [p for p in positions if p.instance_id == instance_id]
        if account_id:
            positions = [p for p in positions if p.account_id == account_id]
        if exchange:
            positions = [p for p in positions if p.exchange == exchange]
        if symbol:
            positions = [p for p in positions if p.symbol == symbol]
        return positions

    def get_closed_positions(self) -> list[Position]:
        return list(self._closed_positions)

    def get_open_position_count(self) -> int:
        return len(self._positions)

    def remove_position(self, instance_id: str) -> Position | None:
        return self._positions.pop(instance_id, None)

    def clear(self) -> None:
        self._positions.clear()
        self._closed_positions.clear()
