"""
Exchange-specific connector for the Market Data Hub.

Each connector wraps one IExchangeAdapter instance and is responsible for:
- opening/closing the market data connection
- subscribing/unsubscribing to market streams via the adapter
- normalizing adapter data and routing it into the Market Hub
- tracking connection status and reconnect metrics
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from adapters.base import IExchangeAdapter
from core.exceptions import ExchangeConnectionError, SymbolNotSupported
from core.logging import get_logger

from market.base import MarketMetrics, MarketStatus

logger = get_logger(__name__)


@dataclass
class ConnectorMetrics:
    """Mutable metrics for a single connector."""

    status: MarketStatus = MarketStatus.DISCONNECTED
    last_update: datetime | None = None
    latency_ms: float = 0.0
    reconnect_count: int = 0
    dropped_messages: int = 0
    message_rate: float = 0.0
    message_times: list[float] = field(default_factory=lambda: [])
    _max_rate_window: int = 100

    def record_message(self, received_at: float | None = None) -> None:
        now = received_at or time.time()
        self.message_times.append(now)
        if len(self.message_times) > self._max_rate_window:
            self.message_times = self.message_times[-self._max_rate_window :]

        if len(self.message_times) >= 2:
            span = self.message_times[-1] - self.message_times[0]
            self.message_rate = len(self.message_times) / span if span > 0 else 0.0

    def record_latency(self, start: float, end: float | None = None) -> None:
        self.latency_ms = ((end or time.time()) - start) * 1000

    def record_reconnect(self) -> None:
        self.reconnect_count += 1

    def record_dropped(self) -> None:
        self.dropped_messages += 1

    def to_market_metrics(self, exchange: str, symbol: str) -> MarketMetrics:
        return MarketMetrics(
            exchange=exchange,
            symbol=symbol,
            last_update=self.last_update,
            latency_ms=self.latency_ms,
            reconnect_count=self.reconnect_count,
            dropped_messages=self.dropped_messages,
            message_rate=self.message_rate,
            status=self.status,
        )


class ExchangeConnector:
    """Wraps one IExchangeAdapter and manages its market data subscriptions."""

    def __init__(
        self,
        exchange: str,
        adapter: IExchangeAdapter,
        data_callback: Callable[[str, str, str, Any], Any],
        reconnect_backoff_seconds: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0),
        stale_threshold_seconds: float = 30.0,
    ) -> None:
        self.exchange = exchange.lower()
        self.adapter = adapter
        self.data_callback = data_callback
        self._reconnect_backoff = reconnect_backoff_seconds
        self._stale_threshold = stale_threshold_seconds
        self._running = False
        self._tasks: set[asyncio.Task[Any]] = set()

        # symbol -> metrics
        self._metrics: dict[str, ConnectorMetrics] = {}

        # adapter subscription id -> symbol, channel
        self._sub_map: dict[str, tuple[str, str]] = {}

    def _metrics_for(self, symbol: str, create: bool = True) -> ConnectorMetrics | None:
        key = symbol.upper()
        if create and key not in self._metrics:
            self._metrics[key] = ConnectorMetrics()
        return self._metrics.get(key)

    async def start(self) -> None:
        """Open the market data connection."""
        if self._running:
            return
        self._running = True
        for metrics in self._metrics.values():
            if metrics.status == MarketStatus.DISCONNECTED:
                metrics.status = MarketStatus.CONNECTING
        try:
            ok = await self.adapter.connect_market()
            if ok:
                for metrics in self._metrics.values():
                    metrics.status = MarketStatus.CONNECTED
                logger.info(f"{self.exchange} market connector started")
            else:
                for metrics in self._metrics.values():
                    metrics.status = MarketStatus.DISCONNECTED
                raise ExchangeConnectionError(
                    f"Failed to connect {self.exchange} market stream", self.exchange
                )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"{self.exchange} market connector start failed: {exc}")
            for metrics in self._metrics.values():
                metrics.status = MarketStatus.DISCONNECTED
            raise

    async def stop(self) -> None:
        """Close the market data connection and cancel tasks."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        for task in list(self._tasks):
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()
        try:
            await self.adapter.disconnect()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"{self.exchange} disconnect error: {exc}")
        for metrics in self._metrics.values():
            metrics.status = MarketStatus.DISCONNECTED

    async def subscribe(self, symbol: str, channel: str) -> str:
        """Subscribe to a market stream. Returns adapter subscription id."""
        metrics = self._metrics_for(symbol)
        if metrics is None:
            raise RuntimeError("Metrics missing")

        if metrics.status == MarketStatus.DISCONNECTED:
            metrics.status = MarketStatus.CONNECTING

        start = time.time()
        try:
            sub_id = await self.adapter.subscribe_market(
                symbol.upper(), channel.lower(), self._make_callback(symbol, channel)
            )
            self._sub_map[sub_id] = (symbol.upper(), channel.lower())
            metrics.status = MarketStatus.CONNECTED
            metrics.record_latency(start, time.time())
            metrics.last_update = datetime.now(UTC)
            return sub_id
        except SymbolNotSupported:
            metrics.status = MarketStatus.DISCONNECTED
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error(f"{self.exchange} subscribe {symbol}/{channel} failed: {exc}")
            metrics.status = MarketStatus.DISCONNECTED
            raise ExchangeConnectionError(
                f"Subscribe failed for {symbol} {channel}", self.exchange
            ) from exc

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from a market stream."""
        try:
            await self.adapter.unsubscribe_market(subscription_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"{self.exchange} unsubscribe error: {exc}")
        finally:
            self._sub_map.pop(subscription_id, None)

    def _make_callback(self, symbol: str, channel: str) -> Callable[..., Any]:
        async def _callback(data: Any) -> None:
            await self._on_market_data(symbol.upper(), channel.lower(), data)

        return _callback

    async def _on_market_data(self, symbol: str, channel: str, data: Any) -> None:
        metrics = self._metrics_for(symbol)
        if metrics is not None:
            metrics.record_message()
            metrics.last_update = datetime.now(UTC)
            if metrics.status != MarketStatus.CONNECTED:
                metrics.status = MarketStatus.CONNECTED
        await self.data_callback(self.exchange, symbol, channel, data)

    def is_alive(self, symbol: str) -> bool:
        metrics = self._metrics_for(symbol, create=False)
        if metrics is None or metrics.status != MarketStatus.CONNECTED:
            return False
        if metrics.last_update is None:
            return False
        elapsed = (datetime.now(UTC) - metrics.last_update).total_seconds()
        if elapsed > self._stale_threshold:
            metrics.status = MarketStatus.STALE
            return False
        return True

    def get_status(self, symbol: str) -> MarketStatus:
        metrics = self._metrics_for(symbol, create=False)
        if metrics is None:
            return MarketStatus.DISCONNECTED
        if metrics.status == MarketStatus.CONNECTED and metrics.last_update is not None:
            elapsed = (datetime.now(UTC) - metrics.last_update).total_seconds()
            if elapsed > self._stale_threshold:
                metrics.status = MarketStatus.STALE
        return metrics.status

    def get_metrics(self, symbol: str) -> MarketMetrics:
        metrics = self._metrics_for(symbol)
        if metrics is None:
            return MarketMetrics(exchange=self.exchange, symbol=symbol.upper())
        return metrics.to_market_metrics(self.exchange, symbol.upper())

    def mark_reconnecting(self, symbol: str) -> None:
        metrics = self._metrics_for(symbol)
        if metrics is not None:
            metrics.status = MarketStatus.RECONNECTING
            metrics.record_reconnect()

    def record_dropped(self, symbol: str) -> None:
        metrics = self._metrics_for(symbol)
        if metrics is not None:
            metrics.record_dropped()

    async def reconnect(self) -> None:
        """Reconnect the market stream with exponential backoff."""
        for _symbol, metrics in self._metrics.items():
            metrics.status = MarketStatus.RECONNECTING
            metrics.record_reconnect()

        for delay in self._reconnect_backoff:
            try:
                await self.adapter.connect_market()
                for _symbol, metrics in self._metrics.items():
                    metrics.status = MarketStatus.CONNECTED
                    metrics.last_update = datetime.now(UTC)
                logger.info(f"{self.exchange} market connector reconnected")
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    f"{self.exchange} reconnect failed: {exc}, retrying in {delay}s"
                )
                await asyncio.sleep(delay)

        for _symbol, metrics in self._metrics.items():
            metrics.status = MarketStatus.DISCONNECTED
        raise ExchangeConnectionError(
            f"{self.exchange} reconnect exhausted", self.exchange
        )

    @property
    def running(self) -> bool:
        return self._running
