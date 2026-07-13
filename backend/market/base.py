"""
Base interface for the Market Data Hub.

The Market Hub is the single source of truth for real-time market data.
It is intentionally exchange-agnostic: consumers call `get_ticker(exchange, symbol)`,
`is_alive(exchange, symbol)`, etc., without knowing whether the data originates
from Binance, Hyperliquid, Bybit, or any other adapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Callable

from core.types import Candle, OrderBook, TickerData


class MarketStatus(str, Enum):
    """Quality-of-service status for a single market stream."""

    CONNECTED = "connected"
    CONNECTING = "connecting"
    STALE = "stale"
    RECONNECTING = "reconnecting"
    DISCONNECTED = "disconnected"


@dataclass
class MarketMetrics:
    """Latency and health metrics for a single market stream."""

    exchange: str
    symbol: str
    last_update: datetime | None = None
    latency_ms: float = 0.0
    reconnect_count: int = 0
    dropped_messages: int = 0
    message_rate: float = 0.0
    status: MarketStatus = MarketStatus.DISCONNECTED

    def to_dict(self) -> dict[str, Any]:
        return {
            "exchange": self.exchange,
            "symbol": self.symbol,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "latency_ms": round(self.latency_ms, 3),
            "reconnect_count": self.reconnect_count,
            "dropped_messages": self.dropped_messages,
            "message_rate": round(self.message_rate, 3),
            "status": self.status.value,
        }


class IMarketHub(ABC):
    """Abstract interface for the generic Market Data Hub."""

    @abstractmethod
    async def subscribe(
        self,
        exchange: str,
        symbol: str,
        channel: str,
        callback: Callable[..., Any],
    ) -> str:
        """Subscribe to market data. Returns a consumer subscription id."""

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe a single consumer."""

    @abstractmethod
    async def get_price(self, exchange: str, symbol: str) -> Decimal:
        """Get current mid/last price for a symbol."""

    @abstractmethod
    async def get_ticker(self, exchange: str, symbol: str) -> TickerData:
        """Get latest cached ticker data."""

    @abstractmethod
    async def get_orderbook(self, exchange: str, symbol: str) -> OrderBook:
        """Get latest cached order book."""

    @abstractmethod
    async def get_candles(
        self, exchange: str, symbol: str, interval: str
    ) -> list[Candle]:
        """Get latest cached candles for interval."""

    @abstractmethod
    async def is_alive(self, exchange: str, symbol: str) -> bool:
        """Return True if market data is connected and not stale."""

    @abstractmethod
    async def get_status(self, exchange: str, symbol: str) -> MarketStatus:
        """Return current market status."""

    @abstractmethod
    async def get_metrics(self, exchange: str, symbol: str) -> MarketMetrics:
        """Return latency/health metrics for the stream."""

    @abstractmethod
    async def start(self) -> None:
        """Start the market hub and all registered connectors."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the market hub and release all resources."""
