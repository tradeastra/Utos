"""
PositionAggregator — aggregates positions for reporting and risk control.

Merges positions from multiple instances for same symbol/exchange/account.
Computes net position (long - short).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from engine.risk.portfolio import Position


@dataclass
class AggregatedPosition:
    """Aggregated position across multiple instances."""

    key: str  # symbol, exchange, or account_id depending on aggregation
    total_long_quantity: Decimal
    total_short_quantity: Decimal
    net_quantity: Decimal
    weighted_avg_entry_price: Decimal
    position_count: int


class PositionAggregator:
    """Aggregate positions by symbol, exchange, or account."""

    @staticmethod
    def _aggregate(
        positions: list[Position], key_func: callable
    ) -> dict[str, AggregatedPosition]:
        groups: dict[str, list[Position]] = {}
        for pos in positions:
            if pos.closed:
                continue
            key = key_func(pos)
            groups.setdefault(key, []).append(pos)

        result: dict[str, AggregatedPosition] = {}
        for key, group in groups.items():
            long_qty = Decimal("0")
            short_qty = Decimal("0")
            total_cost = Decimal("0")
            total_qty = Decimal("0")

            for pos in group:
                if pos.side == "long":
                    long_qty += pos.quantity
                else:
                    short_qty += pos.quantity
                total_cost += pos.entry_price * pos.quantity
                total_qty += pos.quantity

            avg_price = total_cost / total_qty if total_qty > 0 else Decimal("0")
            result[key] = AggregatedPosition(
                key=key,
                total_long_quantity=long_qty,
                total_short_quantity=short_qty,
                net_quantity=long_qty - short_qty,
                weighted_avg_entry_price=avg_price,
                position_count=len(group),
            )
        return result

    @classmethod
    def aggregate_by_symbol(
        cls, positions: list[Position]
    ) -> dict[str, AggregatedPosition]:
        return cls._aggregate(positions, lambda p: p.symbol)

    @classmethod
    def aggregate_by_exchange(
        cls, positions: list[Position]
    ) -> dict[str, AggregatedPosition]:
        return cls._aggregate(positions, lambda p: p.exchange)

    @classmethod
    def aggregate_by_account(
        cls, positions: list[Position]
    ) -> dict[str, AggregatedPosition]:
        return cls._aggregate(positions, lambda p: p.account_id)

    @classmethod
    def get_net_position(cls, positions: list[Position]) -> AggregatedPosition:
        """Get net position across all positions."""
        long_qty = Decimal("0")
        short_qty = Decimal("0")
        total_cost = Decimal("0")
        total_qty = Decimal("0")
        count = 0

        for pos in positions:
            if pos.closed:
                continue
            count += 1
            if pos.side == "long":
                long_qty += pos.quantity
            else:
                short_qty += pos.quantity
            total_cost += pos.entry_price * pos.quantity
            total_qty += pos.quantity

        avg_price = total_cost / total_qty if total_qty > 0 else Decimal("0")
        return AggregatedPosition(
            key="net",
            total_long_quantity=long_qty,
            total_short_quantity=short_qty,
            net_quantity=long_qty - short_qty,
            weighted_avg_entry_price=avg_price,
            position_count=count,
        )
