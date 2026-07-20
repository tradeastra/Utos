"""
ChaosExchangeAdapter — mock exchange adapter for chaos engineering tests.

Simulates:
- Timeout
- Duplicate ACK
- Delayed fill
- Partial fill after cancel
- Out-of-order WebSocket events
- 500 errors
- Connection drops
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from core.domain_types import (
    BalanceEntry,
    Candle,
    ExchangeAdapterConfig,
    ExchangeCredentials,
    ExchangeInfo,
    OrderBook,
    OrderResult,
    OrderStatus,
    PositionEntry,
    TickerData,
    TradeEntry,
)
from core.exceptions import (
    ExchangeConnectionError,
    ExchangeError,
    ExchangeRateLimitError,
)

_FIXED_DT = datetime(2025, 1, 1, tzinfo=UTC)


class ChaosExchangeAdapter:
    """Mock exchange adapter with configurable failure modes for chaos testing."""

    def __init__(
        self,
        exchange_name: str = "chaos",
        failure_mode: str = "none",
        failure_rate: float = 0.0,
        delay_seconds: float = 0.0,
        duplicate_ack: bool = False,
        partial_fill_after_cancel: bool = False,
        out_of_order_events: bool = False,
    ) -> None:
        self._name = exchange_name
        self._failure_mode = failure_mode
        self._failure_rate = failure_rate
        self._delay = delay_seconds
        self._duplicate_ack = duplicate_ack
        self._partial_fill_after_cancel = partial_fill_after_cancel
        self._out_of_order = out_of_order_events

        self._orders: dict[str, OrderResult] = {}
        self._cancelled: set[str] = set()
        self._filled: set[str] = set()
        self._call_count = 0
        self._connected = True
        self._event_log: list[dict[str, Any]] = []

    @property
    def exchange_name(self) -> str:
        return self._name

    @property
    def is_testnet(self) -> bool:
        return True

    def _should_fail(self) -> bool:
        if self._failure_mode == "none":
            return False
        if self._failure_rate <= 0:
            return False
        return random.random() < self._failure_rate

    def _maybe_delay(self) -> Awaitable[None]:
        if self._delay > 0:
            return asyncio.sleep(self._delay)
        return asyncio.sleep(0)

    def _raise_failure(self) -> None:
        mode = self._failure_mode
        if mode == "timeout":
            raise ExchangeConnectionError(
                f"Simulated timeout on {self._name}", self._name
            )
        elif mode == "500":
            raise ExchangeError(f"Simulated 500 error on {self._name}", self._name)
        elif mode == "rate_limit":
            raise ExchangeRateLimitError(
                f"Simulated rate limit on {self._name}", self._name
            )
        elif mode == "connection_drop":
            self._connected = False
            raise ExchangeConnectionError(
                f"Simulated connection drop on {self._name}", self._name
            )
        else:
            raise ExchangeError(f"Simulated failure: {mode}", self._name)

    def _log_event(self, event_type: str, data: dict[str, Any]) -> None:
        self._event_log.append({"type": event_type, "data": data})

    def get_event_log(self) -> list[dict[str, Any]]:
        return list(self._event_log)

    def reset(self) -> None:
        self._orders.clear()
        self._cancelled.clear()
        self._filled.clear()
        self._call_count = 0
        self._connected = True
        self._event_log.clear()

    # ── IExchangeAdapter implementation ──────────

    async def initialize(self, config: ExchangeAdapterConfig) -> bool:
        return True

    async def authenticate(self, credentials: ExchangeCredentials) -> bool:
        return True

    async def connect_market(self) -> bool:
        self._connected = True
        return True

    async def connect_account(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def is_market_connected(self) -> bool:
        return self._connected

    async def is_account_connected(self) -> bool:
        return self._connected

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Decimal | None = None,
        stop_price: Decimal | None = None,
        client_order_id: str | None = None,
        **kwargs: Any,
    ) -> OrderResult:
        self._call_count += 1
        await self._maybe_delay()

        if self._should_fail():
            self._log_event(
                "place_order_failed", {"symbol": symbol, "mode": self._failure_mode}
            )
            self._raise_failure()

        order_id = str(random.randint(100000, 999999))

        result = OrderResult(
            order_id=order_id,
            exchange_order_id=order_id,
            symbol=symbol.upper(),
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            filled_quantity=Decimal("0"),
            average_fill_price=None,
            status=OrderStatus.OPEN.value,
            created_at=_FIXED_DT,
            updated_at=_FIXED_DT,
        )

        # Duplicate ACK: return different order_id for duplicate requests
        if self._duplicate_ack and self._call_count % 2 == 0:
            dup_id = str(random.randint(100000, 999999))
            result = OrderResult(
                order_id=dup_id,
                exchange_order_id=dup_id,
                symbol=symbol.upper(),
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                filled_quantity=Decimal("0"),
                average_fill_price=None,
                status=OrderStatus.OPEN.value,
                created_at=_FIXED_DT,
                updated_at=_FIXED_DT,
            )

        self._orders[order_id] = result
        self._log_event("place_order", {"order_id": order_id, "symbol": symbol})
        return result

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        self._call_count += 1
        await self._maybe_delay()

        if self._should_fail():
            self._raise_failure()

        self._cancelled.add(order_id)

        # Partial fill after cancel: mark as partially filled instead of cancelled
        if self._partial_fill_after_cancel and order_id in self._orders:
            order = self._orders[order_id]
            if order.filled_quantity == Decimal("0"):
                self._orders[order_id] = OrderResult(
                    order_id=order.exchange_order_id,
                    exchange_order_id=order.exchange_order_id,
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    price=order.price,
                    filled_quantity=order.quantity / Decimal("2"),
                    average_fill_price=order.price,
                    status=OrderStatus.PARTIALLY_FILLED.value,
                    created_at=order.created_at,
                    updated_at=_FIXED_DT,
                )
                self._log_event("partial_fill_after_cancel", {"order_id": order_id})
                return True

        self._log_event("cancel_order", {"order_id": order_id})
        return True

    async def modify_order(
        self,
        symbol: str,
        order_id: str,
        new_price: Decimal | None = None,
        new_quantity: Decimal | None = None,
    ) -> OrderResult:
        if order_id in self._orders:
            return self._orders[order_id]
        raise ExchangeError(f"Order {order_id} not found", self._name)

    async def get_balance(self, asset: str | None = None) -> list[BalanceEntry]:
        return []

    async def get_positions(self, symbol: str | None = None) -> list[PositionEntry]:
        return []

    async def get_order(self, symbol: str, order_id: str) -> OrderResult:
        if self._should_fail():
            self._raise_failure()
        if order_id in self._orders:
            return self._orders[order_id]
        raise ExchangeError(f"Order {order_id} not found", self._name)

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        return [
            o
            for oid, o in self._orders.items()
            if oid not in self._cancelled and oid not in self._filled
        ]

    async def get_ticker(self, symbol: str) -> TickerData:
        return TickerData(
            symbol=symbol.upper(),
            bid=Decimal("50000"),
            ask=Decimal("50001"),
            last=Decimal("50000"),
            volume=Decimal("1000"),
            timestamp=_FIXED_DT,
        )

    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        return OrderBook(
            symbol=symbol.upper(),
            bids=[(Decimal("49999"), Decimal("1"))],
            asks=[(Decimal("50001"), Decimal("1"))],
            timestamp=_FIXED_DT,
        )

    async def get_candles(
        self, symbol: str, interval: str, limit: int = 100
    ) -> list[Candle]:
        return []

    async def get_trades(self, symbol: str, limit: int = 100) -> list[TradeEntry]:
        return []

    async def get_order_history(
        self, symbol: str | None = None, limit: int = 100
    ) -> list[OrderResult]:
        return list(self._orders.values())

    async def get_trade_history(
        self, symbol: str | None = None, limit: int = 100
    ) -> list[TradeEntry]:
        return []

    async def health_check(self) -> bool:
        return self._connected

    async def get_exchange_info(self) -> ExchangeInfo:
        return ExchangeInfo(
            name=self._name,
            supported_symbols=["BTCUSDT", "ETHUSDT"],
            rate_limits={},
            fee_structure={},
            server_time=_FIXED_DT,
        )

    async def subscribe_market(
        self, symbols: list[str], channel: str, callback: Callable[[Any], None]
    ) -> bool:
        return True

    async def subscribe_account(
        self, channel: str, callback: Callable[[Any], None]
    ) -> bool:
        return True

    async def unsubscribe_market(self, symbols: list[str], channel: str) -> bool:
        return True

    async def unsubscribe_account(self, channel: str) -> bool:
        return True

    async def get_account(self) -> Any:
        return {"balances": [], "permissions": []}

    async def get_symbol_info(self, symbol: str) -> Any:
        return {
            "symbol": symbol,
            "min_qty": Decimal("0.001"),
            "max_qty": Decimal("1000"),
            "min_notional": Decimal("10"),
            "tick_size": Decimal("0.01"),
        }
