"""
Generic Market Data Hub.

Aggregates market data from multiple exchange adapters, normalizes it, caches it
in memory, and distributes it to consumers. The hub is the single source of truth
for market data; no engine above should talk directly to an exchange adapter.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from adapters.base import IExchangeAdapter
from core.domain_types import Candle, OrderBook, TickerData
from core.exceptions import SymbolNotSupported
from core.logging import get_logger

from market.base import IMarketHub, MarketMetrics, MarketStatus
from market.cache.market_cache import MarketCache
from market.connector.exchange_connector import ExchangeConnector
from market.subscription_manager import SubscriptionManager
from market.symbol_registry import SymbolRegistry

logger = get_logger(__name__)


class MarketHub(IMarketHub):
    """Exchange-agnostic market data hub."""

    def __init__(
        self,
        cache: MarketCache | None = None,
        symbol_registry: SymbolRegistry | None = None,
        stale_threshold_seconds: float = 30.0,
    ) -> None:
        self.cache = cache or MarketCache(
            stale_threshold_seconds=stale_threshold_seconds
        )
        self.symbols = symbol_registry or SymbolRegistry()
        self._connectors: dict[str, ExchangeConnector] = {}
        self._subscription_manager: SubscriptionManager | None = None
        self._running = False
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def register_adapter(self, exchange: str, adapter: IExchangeAdapter) -> None:
        """Register an exchange adapter and initialize its connector."""
        exchange = exchange.lower()
        if exchange in self._connectors:
            return
        connector = ExchangeConnector(
            exchange=exchange,
            adapter=adapter,
            data_callback=self._on_market_data,
        )
        self._connectors[exchange] = connector
        logger.info(f"Registered {exchange} adapter with MarketHub")

    async def start(self) -> None:
        """Start all registered connectors and the subscription manager."""
        async with self._lock:
            self._subscription_manager = SubscriptionManager(
                subscribe_fn=self._subscribe_logical,
                unsubscribe_fn=self._unsubscribe_logical,
            )
            self._running = True
            await asyncio.gather(
                *[connector.start() for connector in self._connectors.values()],
                return_exceptions=True,
            )
        logger.info("MarketHub started")

    async def stop(self) -> None:
        """Stop all connectors and release subscriptions."""
        async with self._lock:
            self._running = False
            if self._subscription_manager is not None:
                self._subscription_manager.clear()
                self._subscription_manager = None
            await asyncio.gather(
                *[connector.stop() for connector in self._connectors.values()],
                return_exceptions=True,
            )
            self.cache.clear()
        logger.info("MarketHub stopped")

    # ------------------------------------------------------------------
    # Consumer API
    # ------------------------------------------------------------------

    async def subscribe(
        self,
        exchange: str,
        symbol: str,
        channel: str,
        callback: Callable[..., Any],
    ) -> str:
        """Subscribe a consumer to a market stream. Deduplicated internally."""
        if self._subscription_manager is None:
            raise RuntimeError("MarketHub has not been started")
        self.symbols.validate(exchange, symbol)
        return await self._subscription_manager.subscribe(
            exchange, symbol, channel, callback
        )

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe a single consumer."""
        if self._subscription_manager is None:
            return
        await self._subscription_manager.unsubscribe(subscription_id)

    async def get_price(self, exchange: str, symbol: str) -> Decimal:
        price = self.cache.get_price(exchange, symbol)
        if price is None:
            await self._fetch_and_cache_ticker(exchange, symbol)
            price = self.cache.get_price(exchange, symbol)
        if price is None:
            raise SymbolNotSupported(symbol, exchange)
        return price

    async def get_ticker(self, exchange: str, symbol: str) -> TickerData:
        ticker = self.cache.get_ticker(exchange, symbol)
        if ticker is None:
            await self._fetch_and_cache_ticker(exchange, symbol)
            ticker = self.cache.get_ticker(exchange, symbol)
        if ticker is None:
            raise SymbolNotSupported(symbol, exchange)
        return ticker

    async def get_tickers(self, exchange: str) -> list[TickerData]:
        """Get all tickers for an exchange, sorted by volume descending."""
        connector = self._connectors.get(exchange.lower())
        if connector is None:
            raise SymbolNotSupported("ALL", exchange)
        return await connector.adapter.get_tickers()

    async def get_orderbook(self, exchange: str, symbol: str) -> OrderBook:
        orderbook = self.cache.get_orderbook(exchange, symbol)
        if orderbook is None:
            await self._fetch_and_cache_orderbook(exchange, symbol)
            orderbook = self.cache.get_orderbook(exchange, symbol)
        if orderbook is None:
            raise SymbolNotSupported(symbol, exchange)
        return orderbook

    async def get_candles(
        self, exchange: str, symbol: str, interval: str
    ) -> list[Candle]:
        candles = self.cache.get_candles(exchange, symbol, interval)
        if candles is None:
            await self._fetch_and_cache_candles(exchange, symbol, interval)
            candles = self.cache.get_candles(exchange, symbol, interval)
        if candles is None:
            raise SymbolNotSupported(symbol, exchange)
        return candles

    async def is_alive(self, exchange: str, symbol: str) -> bool:
        connector = self._connectors.get(exchange.lower())
        if connector is None:
            return self.cache.is_fresh(exchange, symbol)
        return connector.is_alive(symbol) and self.cache.is_fresh(exchange, symbol)

    async def get_status(self, exchange: str, symbol: str) -> MarketStatus:
        connector = self._connectors.get(exchange.lower())
        if connector is None:
            return MarketStatus.DISCONNECTED
        return connector.get_status(symbol)

    async def get_metrics(self, exchange: str, symbol: str) -> MarketMetrics:
        connector = self._connectors.get(exchange.lower())
        if connector is None:
            return MarketMetrics(exchange=exchange.lower(), symbol=symbol.upper())
        return connector.get_metrics(symbol)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _subscribe_logical(
        self, exchange: str, symbol: str, channel: str, callback: Callable[..., Any]
    ) -> str:
        connector = self._connectors.get(exchange.lower())
        if connector is None:
            raise SymbolNotSupported(symbol, exchange)
        return await connector.subscribe(symbol, channel)

    async def _unsubscribe_logical(self, subscription_id: str) -> None:
        for connector in self._connectors.values():
            if subscription_id in connector._sub_map:
                await connector.unsubscribe(subscription_id)
                return

    async def _on_market_data(
        self, exchange: str, symbol: str, channel: str, data: Any
    ) -> None:
        try:
            if channel == "ticker" and isinstance(data, TickerData):
                self.cache.update_ticker(exchange, symbol, data)
            elif channel == "orderbook" and isinstance(data, OrderBook):
                self.cache.update_orderbook(exchange, symbol, data)
            elif channel == "candle" and isinstance(data, list):
                self.cache.update_candles(exchange, symbol, "1m", data)
            elif channel == "candle" and isinstance(data, Candle):
                self.cache.update_candles(exchange, symbol, data.interval, [data])
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to process {exchange}/{symbol}/{channel}: {exc}")

        if self._subscription_manager is not None:
            await self._subscription_manager.fan_out(exchange, symbol, channel, data)

    async def _fetch_and_cache_ticker(self, exchange: str, symbol: str) -> None:
        connector = self._connectors.get(exchange.lower())
        if connector is None:
            return
        ticker = await connector.adapter.get_ticker(symbol.upper())
        self.cache.update_ticker(exchange, symbol, ticker)

    async def _fetch_and_cache_orderbook(self, exchange: str, symbol: str) -> None:
        connector = self._connectors.get(exchange.lower())
        if connector is None:
            return
        orderbook = await connector.adapter.get_order_book(symbol.upper())
        self.cache.update_orderbook(exchange, symbol, orderbook)

    async def _fetch_and_cache_candles(
        self, exchange: str, symbol: str, interval: str
    ) -> None:
        connector = self._connectors.get(exchange.lower())
        if connector is None:
            return
        candles = await connector.adapter.get_candles(symbol.upper(), interval)
        self.cache.update_candles(exchange, symbol, interval, candles)

    # ------------------------------------------------------------------
    # Operational introspection
    # ------------------------------------------------------------------

    def active_subscriptions(self, exchange: str | None = None) -> int:
        if self._subscription_manager is None:
            return 0
        return self._subscription_manager.active_count(exchange)

    def active_websocket_subscriptions(self) -> int:
        """Return total active adapter/WebSocket subscriptions."""
        return sum(len(c._sub_map) for c in self._connectors.values())

    def consumer_count(self) -> int:
        if self._subscription_manager is None:
            return 0
        return self._subscription_manager.consumer_count()

    def cache_entries(self) -> int:
        return self.cache.entry_count()

    def average_update_latency_ms(self, exchange: str | None = None) -> float:
        """Return average latency_ms across all symbols or one exchange."""
        values = []
        for ex, connector in self._connectors.items():
            if exchange is not None and ex != exchange.lower():
                continue
            for _symbol, metrics in connector._metrics.items():
                if metrics.latency_ms > 0:
                    values.append(metrics.latency_ms)
        return sum(values) / len(values) if values else 0.0

    def exchanges(self) -> list[str]:
        return sorted(self._connectors.keys())

    def snapshot(self) -> dict[str, Any]:
        """Operational snapshot for monitoring/tests."""
        datetime.now(UTC)
        return {
            "running": self._running,
            "active_logical_subscriptions": self.active_subscriptions(),
            "active_websocket_subscriptions": self.active_websocket_subscriptions(),
            "consumer_subscriptions": self.consumer_count(),
            "cache_entries": self.cache_entries(),
            "exchanges": self.exchanges(),
            "avg_latency_ms": round(self.average_update_latency_ms(), 3),
        }
