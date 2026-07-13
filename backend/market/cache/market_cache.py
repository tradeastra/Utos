"""
In-memory market data cache.

The cache is the hot path for all market queries. Every read is expected to
complete in sub-millisecond time. Data is stored per (exchange, symbol) and is
updated by the subscription manager / connector as new messages arrive.

Redis persistence is optional and used only for metrics/survivability, not as
a primary lookup path.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from core.types import Candle, OrderBook, TickerData


@dataclass
class _CacheEntry:
    """Single (exchange, symbol) cache entry with metadata."""

    symbol: str
    exchange: str
    ticker: TickerData | None = None
    orderbook: OrderBook | None = None
    candles: dict[str, list[Candle]] = field(default_factory=dict)
    price: Decimal | None = None
    last_update: datetime | None = None
    message_count: int = 0
    message_times: deque[float] = field(default_factory=lambda: deque(maxlen=100))
    last_sequence: int | None = None

    def update_timestamp(self) -> None:
        self.last_update = datetime.now(timezone.utc)
        now = time.time()
        self.message_times.append(now)
        self.message_count += 1

    @property
    def message_rate(self) -> float:
        """Messages per second over the last 100 arrivals."""
        if len(self.message_times) < 2:
            return 0.0
        span = self.message_times[-1] - self.message_times[0]
        return len(self.message_times) / span if span > 0 else 0.0


class MarketCache:
    """Thread-safe-ish async in-memory cache for normalized market data."""

    def __init__(self, stale_threshold_seconds: float = 30.0) -> None:
        self._data: dict[tuple[str, str], _CacheEntry] = {}
        self._stale_threshold = stale_threshold_seconds

    def _key(self, exchange: str, symbol: str) -> tuple[str, str]:
        return exchange.lower(), symbol.upper()

    def _entry(self, exchange: str, symbol: str, create: bool = True) -> _CacheEntry | None:
        key = self._key(exchange, symbol)
        if key not in self._data and create:
            self._data[key] = _CacheEntry(symbol=symbol.upper(), exchange=exchange.lower())
        return self._data.get(key)

    def update_ticker(self, exchange: str, symbol: str, ticker: TickerData) -> None:
        entry = self._entry(exchange, symbol)
        if entry is None:
            return
        entry.ticker = ticker
        entry.price = ticker.last
        entry.update_timestamp()

    def update_orderbook(self, exchange: str, symbol: str, orderbook: OrderBook) -> None:
        entry = self._entry(exchange, symbol)
        if entry is None:
            return
        entry.orderbook = orderbook
        entry.update_timestamp()

    def update_candles(
        self, exchange: str, symbol: str, interval: str, candles: list[Candle]
    ) -> None:
        entry = self._entry(exchange, symbol)
        if entry is None:
            return
        entry.candles[interval] = candles
        entry.update_timestamp()

    def get_price(self, exchange: str, symbol: str) -> Decimal | None:
        entry = self._entry(exchange, symbol, create=False)
        return entry.price if entry else None

    def get_ticker(self, exchange: str, symbol: str) -> TickerData | None:
        entry = self._entry(exchange, symbol, create=False)
        return entry.ticker if entry else None

    def get_orderbook(self, exchange: str, symbol: str) -> OrderBook | None:
        entry = self._entry(exchange, symbol, create=False)
        return entry.orderbook if entry else None

    def get_candles(self, exchange: str, symbol: str, interval: str) -> list[Candle] | None:
        entry = self._entry(exchange, symbol, create=False)
        if entry is None:
            return None
        return entry.candles.get(interval)

    def get_last_update(self, exchange: str, symbol: str) -> datetime | None:
        entry = self._entry(exchange, symbol, create=False)
        return entry.last_update if entry else None

    def get_message_count(self, exchange: str, symbol: str) -> int:
        entry = self._entry(exchange, symbol, create=False)
        return entry.message_count if entry else 0

    def get_message_rate(self, exchange: str, symbol: str) -> float:
        entry = self._entry(exchange, symbol, create=False)
        return entry.message_rate if entry else 0.0

    def is_fresh(self, exchange: str, symbol: str) -> bool:
        """Return True if data exists and is not stale."""
        entry = self._entry(exchange, symbol, create=False)
        if entry is None or entry.last_update is None:
            return False
        elapsed = (datetime.now(timezone.utc) - entry.last_update).total_seconds()
        return elapsed < self._stale_threshold

    def clear(self, exchange: str | None = None, symbol: str | None = None) -> None:
        if exchange is None and symbol is None:
            self._data.clear()
            return
        target = (exchange or "").lower(), (symbol or "").upper()
        keys = [k for k in self._data if (target[0] == "" or k[0] == target[0]) and (target[1] == "" or k[1] == target[1])]
        for key in keys:
            del self._data[key]

    def symbols(self, exchange: str | None = None) -> list[str]:
        if exchange is None:
            return sorted({k[1] for k in self._data})
        return sorted({k[1] for k in self._data if k[0] == exchange.lower()})

    def exchanges(self) -> list[str]:
        return sorted({k[0] for k in self._data})

    def entry_count(self) -> int:
        return len(self._data)

    def snapshot(self) -> dict[tuple[str, str], dict[str, Any]]:
        """Return a serializable snapshot for tests/metrics."""
        return {
            key: {
                "symbol": entry.symbol,
                "exchange": entry.exchange,
                "has_ticker": entry.ticker is not None,
                "has_orderbook": entry.orderbook is not None,
                "candle_intervals": list(entry.candles.keys()),
                "price": str(entry.price) if entry.price else None,
                "last_update": entry.last_update.isoformat() if entry.last_update else None,
                "message_count": entry.message_count,
                "message_rate": round(entry.message_rate, 3),
            }
            for key, entry in self._data.items()
        }
