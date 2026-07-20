"""
Unit tests for MarketCache.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from core.domain_types import Candle, OrderBook, TickerData
from market.cache.market_cache import MarketCache


@pytest.fixture
def cache() -> MarketCache:
    return MarketCache(stale_threshold_seconds=30.0)


@pytest.fixture
def ticker() -> TickerData:
    return TickerData(
        symbol="BTCUSDT",
        bid=Decimal("50000.00"),
        ask=Decimal("50001.00"),
        last=Decimal("50000.50"),
        volume=Decimal("1000.5"),
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def orderbook() -> OrderBook:
    return OrderBook(
        symbol="BTCUSDT",
        bids=[(Decimal("50000"), Decimal("1.5")), (Decimal("49999"), Decimal("2.0"))],
        asks=[(Decimal("50001"), Decimal("1.0")), (Decimal("50002"), Decimal("0.5"))],
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def candles() -> list[Candle]:
    return [
        Candle(
            symbol="BTCUSDT",
            interval="1m",
            open=Decimal("50000"),
            high=Decimal("50100"),
            low=Decimal("49900"),
            close=Decimal("50050"),
            volume=Decimal("100"),
            timestamp=datetime.now(UTC),
        ),
    ]


class TestMarketCache:
    def test_update_and_get_ticker(
        self, cache: MarketCache, ticker: TickerData
    ) -> None:
        cache.update_ticker("binance", "BTCUSDT", ticker)
        result = cache.get_ticker("binance", "BTCUSDT")
        assert result is not None
        assert result.symbol == "BTCUSDT"
        assert result.last == Decimal("50000.50")

    def test_update_ticker_sets_price(
        self, cache: MarketCache, ticker: TickerData
    ) -> None:
        cache.update_ticker("binance", "BTCUSDT", ticker)
        assert cache.get_price("binance", "BTCUSDT") == Decimal("50000.50")

    def test_get_ticker_missing(self, cache: MarketCache) -> None:
        assert cache.get_ticker("binance", "ETHUSDT") is None

    def test_get_price_missing(self, cache: MarketCache) -> None:
        assert cache.get_price("binance", "ETHUSDT") is None

    def test_update_and_get_orderbook(
        self, cache: MarketCache, orderbook: OrderBook
    ) -> None:
        cache.update_orderbook("binance", "BTCUSDT", orderbook)
        result = cache.get_orderbook("binance", "BTCUSDT")
        assert result is not None
        assert len(result.bids) == 2
        assert len(result.asks) == 2

    def test_update_and_get_candles(
        self, cache: MarketCache, candles: list[Candle]
    ) -> None:
        cache.update_candles("binance", "BTCUSDT", "1m", candles)
        result = cache.get_candles("binance", "BTCUSDT", "1m")
        assert result is not None
        assert len(result) == 1
        assert result[0].interval == "1m"

    def test_candles_different_intervals(
        self, cache: MarketCache, candles: list[Candle]
    ) -> None:
        cache.update_candles("binance", "BTCUSDT", "1m", candles)
        candles_5m = [
            Candle(
                symbol="BTCUSDT",
                interval="5m",
                open=Decimal("50000"),
                high=Decimal("50200"),
                low=Decimal("49800"),
                close=Decimal("50100"),
                volume=Decimal("500"),
                timestamp=datetime.now(UTC),
            )
        ]
        cache.update_candles("binance", "BTCUSDT", "5m", candles_5m)
        assert cache.get_candles("binance", "BTCUSDT", "1m") is not None
        assert cache.get_candles("binance", "BTCUSDT", "5m") is not None
        assert len(cache.get_candles("binance", "BTCUSDT", "5m")) == 1

    def test_is_fresh_after_update(
        self, cache: MarketCache, ticker: TickerData
    ) -> None:
        cache.update_ticker("binance", "BTCUSDT", ticker)
        assert cache.is_fresh("binance", "BTCUSDT") is True

    def test_is_fresh_missing(self, cache: MarketCache) -> None:
        assert cache.is_fresh("binance", "BTCUSDT") is False

    def test_is_fresh_stale(self, cache: MarketCache, ticker: TickerData) -> None:
        stale_cache = MarketCache(stale_threshold_seconds=0.01)
        stale_cache.update_ticker("binance", "BTCUSDT", ticker)
        import time

        time.sleep(0.02)
        assert stale_cache.is_fresh("binance", "BTCUSDT") is False

    def test_clear_all(self, cache: MarketCache, ticker: TickerData) -> None:
        cache.update_ticker("binance", "BTCUSDT", ticker)
        cache.clear()
        assert cache.get_ticker("binance", "BTCUSDT") is None
        assert cache.entry_count() == 0

    def test_clear_by_exchange(self, cache: MarketCache, ticker: TickerData) -> None:
        cache.update_ticker("binance", "BTCUSDT", ticker)
        cache.update_ticker("bybit", "BTCUSDT", ticker)
        cache.clear(exchange="binance")
        assert cache.get_ticker("binance", "BTCUSDT") is None
        assert cache.get_ticker("bybit", "BTCUSDT") is not None

    def test_symbols(self, cache: MarketCache, ticker: TickerData) -> None:
        cache.update_ticker("binance", "BTCUSDT", ticker)
        cache.update_ticker("binance", "ETHUSDT", ticker)
        assert cache.symbols("binance") == ["BTCUSDT", "ETHUSDT"]

    def test_exchanges(self, cache: MarketCache, ticker: TickerData) -> None:
        cache.update_ticker("binance", "BTCUSDT", ticker)
        cache.update_ticker("bybit", "BTCUSDT", ticker)
        assert cache.exchanges() == ["binance", "bybit"]

    def test_entry_count(self, cache: MarketCache, ticker: TickerData) -> None:
        assert cache.entry_count() == 0
        cache.update_ticker("binance", "BTCUSDT", ticker)
        assert cache.entry_count() == 1
        cache.update_ticker("bybit", "BTCUSDT", ticker)
        assert cache.entry_count() == 2

    def test_message_count(self, cache: MarketCache, ticker: TickerData) -> None:
        cache.update_ticker("binance", "BTCUSDT", ticker)
        cache.update_ticker("binance", "BTCUSDT", ticker)
        assert cache.get_message_count("binance", "BTCUSDT") == 2

    def test_snapshot(self, cache: MarketCache, ticker: TickerData) -> None:
        cache.update_ticker("binance", "BTCUSDT", ticker)
        snap = cache.snapshot()
        assert ("binance", "BTCUSDT") in snap
        assert snap[("binance", "BTCUSDT")]["has_ticker"] is True

    def test_case_insensitive_exchange(
        self, cache: MarketCache, ticker: TickerData
    ) -> None:
        cache.update_ticker("Binance", "btcusdt", ticker)
        assert cache.get_ticker("BINANCE", "BTCUSDT") is not None
