"""
ExposureManager — calculates exposure per exchange, account, asset, and strategy.

Pure computation, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from engine.risk.portfolio import Position


@dataclass
class ExposureReport:
    """Full exposure breakdown across dimensions."""

    total_exposure: Decimal
    long_exposure: Decimal
    short_exposure: Decimal
    net_exposure: Decimal
    by_exchange: dict[str, Decimal] = field(default_factory=dict)
    by_account: dict[str, Decimal] = field(default_factory=dict)
    by_symbol: dict[str, Decimal] = field(default_factory=dict)


class ExposureManager:
    """Calculate notional exposure across positions."""

    @staticmethod
    def get_exposure_by_exchange(
        positions: list[Position], prices: dict[str, Decimal]
    ) -> dict[str, Decimal]:
        result: dict[str, Decimal] = {}
        for pos in positions:
            if pos.closed:
                continue
            price = prices.get(pos.symbol, pos.entry_price)
            notional = price * pos.quantity
            result[pos.exchange] = result.get(pos.exchange, Decimal("0")) + notional
        return result

    @staticmethod
    def get_exposure_by_account(
        positions: list[Position], prices: dict[str, Decimal]
    ) -> dict[str, Decimal]:
        result: dict[str, Decimal] = {}
        for pos in positions:
            if pos.closed:
                continue
            price = prices.get(pos.symbol, pos.entry_price)
            notional = price * pos.quantity
            result[pos.account_id] = result.get(pos.account_id, Decimal("0")) + notional
        return result

    @staticmethod
    def get_exposure_by_symbol(
        positions: list[Position], prices: dict[str, Decimal]
    ) -> dict[str, Decimal]:
        result: dict[str, Decimal] = {}
        for pos in positions:
            if pos.closed:
                continue
            price = prices.get(pos.symbol, pos.entry_price)
            notional = price * pos.quantity
            result[pos.symbol] = result.get(pos.symbol, Decimal("0")) + notional
        return result

    @staticmethod
    def get_net_exposure(
        positions: list[Position], prices: dict[str, Decimal]
    ) -> Decimal:
        net = Decimal("0")
        for pos in positions:
            if pos.closed:
                continue
            price = prices.get(pos.symbol, pos.entry_price)
            notional = price * pos.quantity
            if pos.side == "long":
                net += notional
            else:
                net -= notional
        return net

    @classmethod
    def calculate_exposure(
        cls,
        positions: list[Position],
        current_prices: dict[str, Decimal],
    ) -> ExposureReport:
        """Calculate full exposure report."""
        long_exposure = Decimal("0")
        short_exposure = Decimal("0")

        for pos in positions:
            if pos.closed:
                continue
            price = current_prices.get(pos.symbol, pos.entry_price)
            notional = price * pos.quantity
            if pos.side == "long":
                long_exposure += notional
            else:
                short_exposure += notional

        return ExposureReport(
            total_exposure=long_exposure + short_exposure,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            net_exposure=long_exposure - short_exposure,
            by_exchange=cls.get_exposure_by_exchange(positions, current_prices),
            by_account=cls.get_exposure_by_account(positions, current_prices),
            by_symbol=cls.get_exposure_by_symbol(positions, current_prices),
        )
