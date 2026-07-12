# Sprint 6: Market Data Hub

## Status

**Planning — not yet started.**

## Vision

Sprint 6 builds the Market Data Hub — the central nervous system for real-time market data. The Market Hub aggregates data from multiple exchange adapters, normalizes it, caches it, and distributes it to consumers (Trading Engine, Grid Engine, Portfolio Engine, Risk Engine).

This is the first sprint that touches the `backend/market/` package, which already has placeholder directories for `hub/`, `cache/`, `connector/`, and `replay/`.

## Core Architectural Decision

> **The Market Hub is the single source of truth for market data.**

No engine or service should call `adapter.get_ticker()` directly. Instead:

```text
Exchange Adapter → Market Hub → Consumers
```

The Market Hub:
- Subscribes to exchange WebSocket streams
- Polls REST endpoints as fallback
- Normalizes data across exchanges
- Caches latest data in memory + Redis
- Distributes updates via callbacks (and later, Event Bus)

## Scope

### In Scope

1. `IMarketHub` interface in `backend/market/base.py`.
2. `MarketHub` implementation in `backend/market/hub/market_hub.py`.
3. Subscription management:
   - `subscribe(symbol, exchange, channel, callback) -> subscription_id`
   - `unsubscribe(subscription_id)`
   - Channel types: `"ticker"`, `"orderbook"`, `"candle"`, `"trade"`
4. Data query API:
   - `get_price(symbol, exchange) -> Decimal`
   - `get_ticker(symbol, exchange) -> TickerData`
   - `get_order_book(symbol, exchange, depth) -> OrderBook`
   - `get_candles(symbol, exchange, interval, limit) -> list[Candle]`
   - `get_supported_symbols(exchange) -> list[str]`
5. Market data caching in `backend/market/cache/`:
   - In-memory cache for latest ticker, order book, price per `(symbol, exchange)`.
   - Redis cache for persistence across restarts (optional fallback).
   - Cache TTL and invalidation strategy.
6. Exchange connector in `backend/market/connector/`:
   - Wraps `IExchangeAdapter` market data methods.
   - Manages WebSocket lifecycle (connect, reconnect, heartbeat).
   - Routes WebSocket callbacks to the Market Hub.
7. Multi-exchange support:
   - Register multiple exchange adapters with the Market Hub.
   - Route queries by `exchange` parameter.
   - Aggregate same-symbol data from different exchanges.
8. Market data normalization:
   - Symbol normalization (uppercase, suffix handling).
   - Price precision normalization.
   - Timestamp normalization to UTC.
9. Lifecycle management:
   - `start()` — connect to all registered exchange feeds.
   - `stop()` — disconnect all feeds, clear cache.
   - Health check — verify all exchange market connections are alive.
10. API endpoints:
    - `GET /market/price/{exchange}/{symbol}` — get current price.
    - `GET /market/ticker/{exchange}/{symbol}` — get ticker data.
    - `GET /market/orderbook/{exchange}/{symbol}` — get order book.
    - `GET /market/candles/{exchange}/{symbol}` — get candles (query params: `interval`, `limit`).
    - `GET /market/symbols/{exchange}` — get supported symbols.
11. Unit tests for Market Hub, cache, connector, and normalization.
12. Integration tests with mock exchange adapter.

### Out of Scope

- Event Bus integration (events like `PRICE_UPDATE`, `TICKER_UPDATE` — deferred to Event Bus sprint)
- Market data replay (`backend/market/replay/` — deferred)
- Historical data storage in database (deferred)
- Frontend WebSocket streaming (deferred)
- Bybit adapter market data (Binance only for now, Bybit already has adapter)
- Grid Engine, Execution Engine, or any trading logic
- Portfolio or risk calculations

## Data Model

### No New Database Tables

Sprint 6 does not add new database tables. Market data is ephemeral (in-memory + Redis cache).

### Redis Keys

```text
market:{exchange}:{symbol}:ticker    -> hash {bid, ask, last, volume, updated_at}
market:{exchange}:{symbol}:price     -> string (latest price)
market:{exchange}:{symbol}:orderbook -> hash {bids, asks, updated_at}
market:active_subscriptions          -> set of subscription_ids
```

### In-Memory Cache

```python
# Per (exchange, symbol)
{
    "ticker": TickerData,
    "orderbook": OrderBook,
    "price": Decimal,
    "candles": dict[str, list[Candle]],  # keyed by interval
    "last_updated": datetime,
}
```

## Architecture

```text
                    ┌─────────────────────────────┐
                    │        MarketHub             │
                    │                              │
                    │  ┌─────────┐  ┌───────────┐  │
                    │  │  Cache  │  │ Connector  │  │
                    │  │ Manager │  │  Manager   │  │
                    │  └────┬────┘  └─────┬─────┘  │
                    │       │             │        │
                    │  ┌────┴─────────────┴─────┐  │
                    │  │   Subscription Manager  │  │
                    │  └────────────────────────┘  │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
              ┌─────┴──────┐       ┌──────┴──────┐
              │  Binance   │       │   Bybit     │
              │  Connector │       │  Connector  │
              └─────┬──────┘       └──────┬──────┘
                    │                     │
              ┌─────┴──────┐       ┌──────┴──────┐
              │  Binance   │       │   Bybit     │
              │  Adapter   │       │   Adapter   │
              └────────────┘       └─────────────┘
```

## Interface (from INTERFACE_DEFINITIONS.md)

```python
class IMarketHub(ABC):

    @abstractmethod
    async def subscribe(
        self,
        symbol: str,
        exchange: str,
        channel: str,    # "ticker" | "orderbook" | "candle" | "trade"
        callback: Callable,
    ) -> str:
        """Subscribe to market data for a symbol on an exchange."""

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from market data."""

    @abstractmethod
    async def get_price(self, symbol: str, exchange: str) -> Decimal:
        """Get current price for a symbol."""

    @abstractmethod
    async def get_ticker(self, symbol: str, exchange: str) -> TickerData:
        """Get ticker data for a symbol."""

    @abstractmethod
    async def get_order_book(self, symbol: str, exchange: str, depth: int = 20) -> OrderBook:
        """Get order book for a symbol."""

    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        limit: int = 100,
    ) -> list[Candle]:
        """Get candlestick data for a symbol."""

    @abstractmethod
    async def get_supported_symbols(self, exchange: str) -> list[str]:
        """Get list of supported symbols for an exchange."""

    @abstractmethod
    async def start(self) -> None:
        """Start the market hub (connect to all exchange feeds)."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the market hub."""
```

## Implementation Plan

1. Create `sprint-6` branch from `develop`.
2. Create `docs/sprint/SPRINT_06.md` (this document).
3. Implement `IMarketHub` in `backend/market/base.py`.
4. Implement `MarketHub` in `backend/market/hub/market_hub.py`:
   - Registry of exchange connectors.
   - Subscription manager (symbol, exchange, channel → callbacks).
   - Query routing (get_price, get_ticker, etc.).
5. Implement `MarketCache` in `backend/market/cache/market_cache.py`:
   - In-memory dict for latest data.
   - Redis fallback for persistence.
   - TTL-based invalidation.
6. Implement `ExchangeConnector` in `backend/market/connector/exchange_connector.py`:
   - Wraps `IExchangeAdapter` for market data.
   - Manages WebSocket connection lifecycle.
   - Routes callbacks to `MarketHub`.
7. Implement normalization helpers:
   - Symbol normalization.
   - Price/quantity precision.
   - Timestamp to UTC.
8. Implement API endpoints in `backend/api/v1/endpoints/market.py`:
   - `GET /market/price/{exchange}/{symbol}`
   - `GET /market/ticker/{exchange}/{symbol}`
   - `GET /market/orderbook/{exchange}/{symbol}`
   - `GET /market/candles/{exchange}/{symbol}`
   - `GET /market/symbols/{exchange}`
9. Wire `MarketHub` as singleton in `backend/main.py` lifespan.
10. Write unit tests:
    - `test_market_hub.py` — subscription, query routing, multi-exchange.
    - `test_market_cache.py` — cache hit/miss, TTL, Redis fallback.
    - `test_exchange_connector.py` — WebSocket lifecycle, callback routing.
11. Write integration tests with mock exchange adapter.
12. Run full test suite.
13. Audit against acceptance criteria.
14. Fix issues.
15. Commit and merge to `develop`.

## API Endpoints

| Method | Path | Action |
|--------|------|--------|
| GET | `/market/price/{exchange}/{symbol}` | Get current price |
| GET | `/market/ticker/{exchange}/{symbol}` | Get ticker data |
| GET | `/market/orderbook/{exchange}/{symbol}` | Get order book (query: `depth`) |
| GET | `/market/candles/{exchange}/{symbol}` | Get candles (query: `interval`, `limit`) |
| GET | `/market/symbols/{exchange}` | Get supported symbols |

## Acceptance Criteria

- [ ] IMarketHub interface defined
- [ ] MarketHub implementation with subscription management
- [ ] MarketCache with in-memory + Redis fallback
- [ ] ExchangeConnector wrapping adapter market data
- [ ] Multi-exchange support (Binance + Bybit adapters)
- [ ] Data normalization (symbol, price, timestamp)
- [ ] Market Hub start/stop lifecycle
- [ ] API endpoints for price, ticker, orderbook, candles, symbols
- [ ] Unit tests for hub, cache, connector
- [ ] Integration tests with mock adapter
- [ ] All tests pass
- [ ] Work is committed on `sprint-6` branch and merged into `develop` after audit

## Target Metrics

- Test count: 260+ (230 existing + 30+ new)
- All tests pass
- Market data query latency: < 10ms (cache hit), < 100ms (cache miss)
- WebSocket reconnection within 5 seconds
- No duplicate subscriptions for same (symbol, exchange, channel)

## Workflow

1. Planning
2. Implement
3. Compile
4. Run Tests
5. Audit
6. Fix
7. Commit (on `sprint-6`)
8. Merge `sprint-6` → `develop`
9. Merge `develop` → `main` → tag `v0.6.0`
10. Create `docs/releases/SPRINT_06_RELEASE.md`

## Risks

1. **WebSocket stability**: Binance WebSocket may disconnect; connector must auto-reconnect with backoff.
2. **Rate limiting**: REST fallback for market data must respect exchange rate limits.
3. **Memory growth**: In-memory cache must have bounded size (TTL eviction or LRU).
4. **Multi-exchange normalization**: Different exchanges have different symbol formats and precision.
5. **Redis unavailability**: Cache must fall back to in-memory only if Redis is down.

## Definition of Done

A user can query the current price, ticker, order book, and candles for any supported symbol on any registered exchange via the Market Hub — all through a single unified API, with data cached for sub-10ms response times.
