"""
RiskManager — validates orders before they are sent to Execution Engine.

The Risk Manager is a gatekeeper, NOT an executor. It does NOT call
ExecutionEngine. Strategy engines call RiskManager.check_order_risk()
before submitting to ExecutionEngine.

Risk rules:
- max_exposure_per_symbol — max notional exposure per asset
- max_exposure_per_exchange — max notional exposure per exchange
- max_open_positions — max number of simultaneous open positions
- max_position_size — max notional per single position
- max_capital_per_instance — max capital allocated per Trading Process
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from core.exceptions import RiskError
from core.logging import get_logger
from core.types import RiskAssessment, RiskCheckResult, RiskLevel
from engine.risk.exposure import ExposureManager
from engine.risk.portfolio import PortfolioManager

logger = get_logger(__name__)


@dataclass
class RiskLimits:
    """Risk limits per user."""

    max_exposure_per_symbol: Decimal = Decimal("100000")
    max_exposure_per_exchange: Decimal = Decimal("500000")
    max_open_positions: int = 20
    max_position_size: Decimal = Decimal("50000")
    max_capital_per_instance: Decimal = Decimal("100000")


class RiskManager:
    """Gatekeeper for order execution — validates against risk rules."""

    def __init__(
        self,
        portfolio: PortfolioManager,
        exposure: ExposureManager,
    ) -> None:
        self._portfolio = portfolio
        self._exposure = exposure
        self._limits: dict[str, RiskLimits] = {}
        self._prices: dict[str, Decimal] = {}  # symbol -> latest price
        self._instance_capital: dict[str, Decimal] = {}  # instance_id -> allocated capital
        self._metrics: dict[str, dict[str, int]] = {}

    def set_risk_parameters(self, user_id: str, limits: RiskLimits) -> None:
        self._limits[user_id] = limits
        self._metrics.setdefault(user_id, {
            "orders_checked": 0,
            "orders_allowed": 0,
            "orders_denied": 0,
            "price_updates": 0,
        })
        logger.info("Risk parameters set", extra={"user_id": user_id})

    def get_risk_parameters(self, user_id: str) -> RiskLimits:
        if user_id not in self._limits:
            return RiskLimits()
        return self._limits[user_id]

    def set_instance_capital(self, instance_id: str, capital: Decimal) -> None:
        self._instance_capital[instance_id] = capital

    def get_instance_capital(self, instance_id: str) -> Decimal:
        return self._instance_capital.get(instance_id, Decimal("0"))

    def on_price_update(self, user_id: str, symbol: str, price: Decimal) -> None:
        """Update internal price tracking for exposure calculations."""
        self._prices[symbol] = price
        metrics = self._metrics.get(user_id)
        if metrics is not None:
            metrics["price_updates"] += 1

    def check_order_risk(
        self,
        instance_id: str,
        account_id: str,
        exchange: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        user_id: str = "default",
    ) -> RiskCheckResult:
        """Check if an order is within risk limits.

        Returns RiskCheckResult with allowed=True/False and reason.
        Does NOT raise on denied orders — returns allowed=False instead.
        """
        limits = self.get_risk_parameters(user_id)
        metrics = self._metrics.setdefault(user_id, {
            "orders_checked": 0,
            "orders_allowed": 0,
            "orders_denied": 0,
            "price_updates": 0,
        })
        metrics["orders_checked"] += 1

        order_notional = quantity * price

        # Rule 1: max position size
        if order_notional > limits.max_position_size:
            metrics["orders_denied"] += 1
            return RiskCheckResult(
                allowed=False,
                reason=f"Order notional {order_notional} exceeds max_position_size {limits.max_position_size}",
                current_exposure=order_notional,
                max_exposure=limits.max_position_size,
            )

        # Rule 2: max capital per instance
        instance_capital = self._instance_capital.get(instance_id, Decimal("0"))
        if instance_capital > 0 and instance_capital > limits.max_capital_per_instance:
            metrics["orders_denied"] += 1
            return RiskCheckResult(
                allowed=False,
                reason=f"Instance capital {instance_capital} exceeds max_capital_per_instance {limits.max_capital_per_instance}",
                current_exposure=instance_capital,
                max_exposure=limits.max_capital_per_instance,
            )

        # Get current positions for exposure checks
        all_positions = self._portfolio.get_positions()
        current_prices = {**self._prices, symbol: price}

        # Rule 3: max exposure per symbol
        symbol_exposure = self._exposure.get_exposure_by_symbol(all_positions, current_prices)
        current_symbol_exposure = symbol_exposure.get(symbol, Decimal("0"))
        new_symbol_exposure = current_symbol_exposure + order_notional
        if new_symbol_exposure > limits.max_exposure_per_symbol:
            metrics["orders_denied"] += 1
            return RiskCheckResult(
                allowed=False,
                reason=f"Symbol {symbol} exposure {new_symbol_exposure} exceeds max_exposure_per_symbol {limits.max_exposure_per_symbol}",
                current_exposure=new_symbol_exposure,
                max_exposure=limits.max_exposure_per_symbol,
            )

        # Rule 4: max exposure per exchange
        exchange_exposure = self._exposure.get_exposure_by_exchange(all_positions, current_prices)
        current_exchange_exposure = exchange_exposure.get(exchange, Decimal("0"))
        new_exchange_exposure = current_exchange_exposure + order_notional
        if new_exchange_exposure > limits.max_exposure_per_exchange:
            metrics["orders_denied"] += 1
            return RiskCheckResult(
                allowed=False,
                reason=f"Exchange {exchange} exposure {new_exchange_exposure} exceeds max_exposure_per_exchange {limits.max_exposure_per_exchange}",
                current_exposure=new_exchange_exposure,
                max_exposure=limits.max_exposure_per_exchange,
            )

        # Rule 5: max open positions
        open_count = self._portfolio.get_open_position_count()
        existing = self._portfolio.get_position(instance_id)
        if existing is None and open_count >= limits.max_open_positions:
            metrics["orders_denied"] += 1
            return RiskCheckResult(
                allowed=False,
                reason=f"Open positions {open_count} exceeds max_open_positions {limits.max_open_positions}",
                current_exposure=Decimal(open_count),
                max_exposure=Decimal(limits.max_open_positions),
            )

        metrics["orders_allowed"] += 1
        return RiskCheckResult(
            allowed=True,
            reason=None,
            current_exposure=new_symbol_exposure,
            max_exposure=limits.max_exposure_per_symbol,
        )

    def check_portfolio_risk(self, user_id: str) -> RiskAssessment:
        """Assess overall portfolio risk."""
        limits = self.get_risk_parameters(user_id)
        all_positions = self._portfolio.get_positions()
        report = self._exposure.calculate_exposure(all_positions, self._prices)

        if report.total_exposure > limits.max_exposure_per_exchange:
            level = RiskLevel.HIGH
        elif report.total_exposure > limits.max_exposure_per_exchange * Decimal("0.7"):
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        recommendations: list[str] = []
        if level == RiskLevel.HIGH:
            recommendations.append("Consider reducing position sizes")
        if self._portfolio.get_open_position_count() > limits.max_open_positions * 0.8:
            recommendations.append("Approaching max open positions limit")

        return RiskAssessment(
            risk_level=level,
            total_exposure=report.total_exposure,
            max_drawdown=Decimal("0"),
            recommendations=recommendations,
        )

    def get_metrics(self, user_id: str) -> dict[str, int]:
        return self._metrics.get(user_id, {
            "orders_checked": 0,
            "orders_allowed": 0,
            "orders_denied": 0,
            "price_updates": 0,
        })
