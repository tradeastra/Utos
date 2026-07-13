# Sprint 6: Market Data Hub

## Status

**Planning — requirements finalized, ready to implement.**

## Vision

Sprint 6 builds the Market Data Hub — the central nervous system for real-time market data. The Market Hub aggregates data from multiple exchange adapters, normalizes it, caches it, and distributes it to consumers (Trading Engine, Grid Engine, Portfolio Engine, Risk Engine).

**Critical constraint: the Market Hub must be generic. It must never become a Binance Hub.**

Trading Engine must not know whether market data comes from Binance, Hyperliquid, or Bybit. All data is normalized into a single format.

```text
                Market Hub
                      │
      ┌───────────────┼───────────────┐
      │               │               │
 Binance        Hyperliquid        Bybit
      │               │               │
      └───────────────┼───────────────┘
              Normalized Market Data
```

This is the first sprint that touches the `backend/market/` package, which already has placeholder directories for `hub/`, `cache/`, `connector/`, and `replay/`.

## Scope

### In Scope

1. **Market Hub** — generic `IMarketHub` interface and `MarketHub` implementation.
2. **Market Cache** — in-memory cache for ticker, order book, price, candles.
3. **Subscription Manager** — deduplicated subscriptions so 1 WebSocket feeds N consumers.
4. **Symbol Registry** — per-exchange supported symbol registry with normalization.
5. **Market Status** — per-symbol quality status: `CONNECTED`, `CONNECTING`, `STALE`, `RECONNECTING`, `DISCONNECTED`.
6. **Ticker Cache** — latest normalized `TickerData` per `(exchange, symbol)`.
7. **OrderBook Cache** — latest normalized `OrderBook` per `(exchange, symbol)`.
8. **Candle Cache** — latest normalized `Candle` list per `(exchange, symbol, interval)`.
9. **Latency Metrics** — `last_update`, `latency_ms`, `reconnect_count`, `dropped_messages`, `message_rate`.
10. **Alive Check** — `MarketHub.is_alive(symbol, exchange)` for consumers.
11. **API endpoints** for querying cached market data and status.
12. **Unit tests** for all of the above.

### Out of Scope

- Grid Engine
- Trading logic
- Order placement / Execution Engine
- Take Profit (TP)
- Profit Lock Engine
- Strategy Engine
- Event Bus integration (events like `PRICE_UPDATE`, `TICKER_UPDATE` — deferred to Event Bus sprint)
- Market data replay (`backend/market/replay/` — deferred)
- Historical data storage in database (deferred)
- Frontend WebSocket streaming (deferred)
- Portfolio or risk calculations

## Data Model

### No New Database Tables

Sprint 6 does not add new database tables. Market data is ephemeral (in-memory + Redis cache).

### Redis Keys

```text
market:{exchange}:{symbol}:ticker    -> hash {bid, ask, last, volume, updated_at}
market:{exchange}:{symbol}:price     -> string (latest price)
market:{exchange}:{symbol}:orderbook -> hash {bids, asks, updated_at}
market:{exchange}:{symbol}:status    -> hash {status, last_update, latency_ms, reconnect_count, dropped_messages, message_rate}
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

### Market Status

```python
class MarketStatus(str, Enum):
    CONNECTED = "connected"
    CONNECTING = "connecting"
    STALE = "stale"
    RECONNECTING = "reconnecting"
    DISCONNECTED = "disconnected"
```

### Subscription Manager

```python
# Logical subscription: (symbol, exchange, channel) -> websocket_subscription_id
# Consumer map: subscription_id -> (symbol, exchange, channel, callback)
# Deduplication: if 10 processes subscribe to BTCUSDT ticker on Binance,
# only ONE WebSocket subscription is opened.
```

## Architecture

```text
                    ┌─────────────────────────────────┐
                    │          MarketHub               │
                    │                                  │
                    │  ┌─────────┐  ┌───────────────┐  │
                    │  │  Cache  │  │  Subscription │  │
                    │  │ Manager │  │    Manager    │  │
                    │  └────┬────┘  └───────┬───────┘  │
                    │       │                │          │
                    │  ┌────┴────────────────┴─────┐    │
                    │  │     Exchange Connectors    │    │
                    │  └─────────────┬──────────────┘    │
                    └────────────────┼───────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
        ┌─────┴──────┐        ┌──────┴──────┐        ┌──────┴──────┐
        │  Binance   │        │ Hyperliquid  │        │   Bybit      │
        │  Connector │        │  Connector   │        │  Connector   │
        └─────┬──────┘        └──────┬──────┘        └──────┬──────┘
              │                      │                      │
        ┌─────┴──────┐        ┌──────┴──────┐        ┌──────┴──────┐
        │  Binance   │        │ Hyperliquid  │        │   Bybit      │
        │  Adapter   │        │   Adapter    │        │   Adapter    │
        └────────────┘        └──────────────┘        └──────────────┘
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

    @abstractmethod
    async def is_alive(self, symbol: str, exchange: str) -> bool:
        """Return True if market data for (symbol, exchange) is fresh and connected."""

    @abstractmethod
    async def get_status(self, symbol: str, exchange: str) -> MarketStatus:
        """Get current market status for (symbol, exchange)."""

    @abstractmethod
    async def get_metrics(self, symbol: str, exchange: str) -> dict[str, Any]:
        """Get latency metrics for (symbol, exchange)."""
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
8. Implement `SymbolRegistry` in `backend/market/symbol_registry.py`:
   - Per-exchange supported symbol list.
   - Symbol normalization (uppercase, suffix mapping).
9. Implement API endpoints in `backend/api/v1/endpoints/market.py`:
   - `GET /market/price/{exchange}/{symbol}`
   - `GET /market/ticker/{exchange}/{symbol}`
   - `GET /market/orderbook/{exchange}/{symbol}`
   - `GET /market/candles/{exchange}/{symbol}`
   - `GET /market/symbols/{exchange}`
   - `GET /market/status/{exchange}/{symbol}`
   - `GET /market/metrics/{exchange}/{symbol}`
10. Wire `MarketHub` as singleton in `backend/main.py` lifespan.
11. Write unit tests:
    - `test_market_hub.py` — subscription, query routing, multi-exchange, status, metrics.
    - `test_market_cache.py` — cache hit/miss, TTL, Redis fallback.
    - `test_subscription_manager.py` — deduplication, refcount, unsubscribe.
    - `test_exchange_connector.py` — WebSocket lifecycle, callback routing.
12. Write integration tests with mock exchange adapter.
13. Run full test suite.
14. Audit against acceptance criteria.
15. Fix issues.
16. Commit and merge to `develop`.

## API Endpoints

| Method | Path | Action |
|--------|------|--------|
| GET | `/market/price/{exchange}/{symbol}` | Get current price |
| GET | `/market/ticker/{exchange}/{symbol}` | Get ticker data |
| GET | `/market/orderbook/{exchange}/{symbol}` | Get order book (query: `depth`) |
| GET | `/market/candles/{exchange}/{symbol}` | Get candles (query: `interval`, `limit`) |
| GET | `/market/symbols/{exchange}` | Get supported symbols |
| GET | `/market/status/{exchange}/{symbol}` | Get market status |
| GET | `/market/metrics/{exchange}/{symbol}` | Get latency metrics |

## Acceptance Criteria

- [ ] IMarketHub interface defined (generic, multi-exchange)
- [ ] MarketHub implementation with subscription management
- [ ] SubscriptionManager deduplicates WebSocket subscriptions
- [ ] MarketCache with in-memory storage for ticker, orderbook, price, candles
- [ ] SymbolRegistry with per-exchange supported symbols
- [ ] MarketStatus enum and per-symbol status tracking
- [ ] `is_alive(symbol, exchange)` for consumers
- [ ] Latency metrics: `last_update`, `latency_ms`, `reconnect_count`, `dropped_messages`, `message_rate`
- [ ] ExchangeConnector wrapping adapter market data
- [ ] Multi-exchange support (Binance + Hyperliquid + Bybit patterns)
- [ ] Data normalization (symbol, price, timestamp)
- [ ] Market Hub start/stop lifecycle
- [ ] API endpoints for price, ticker, orderbook, candles, symbols, status, metrics
- [ ] Unit tests for hub, cache, subscription manager, connector
- [ ] Integration tests with mock adapter
- [ ] All tests pass
- [ ] Work is committed on `sprint-6` branch and merged into `develop` after audit

## Target Metrics

- Test count: 270+ (230 existing + 40+ new)
- All tests pass
- Market data query latency: < 1ms (cache hit), < 100ms (cache miss)
- One WebSocket subscription per `(symbol, exchange, channel)` regardless of consumer count
- WebSocket reconnection within 5 seconds
- Status transitions correctly tracked: `CONNECTING` → `CONNECTED` → `STALE` / `RECONNECTING` → `CONNECTED` / `DISCONNECTED`
- Dropped message counter increments only on actual sequence gaps

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

A user can query the current price, ticker, order book, candles, status, and metrics for any supported symbol on any registered exchange via the Market Hub — all through a single unified API. Ten trading processes reading BTCUSDT result in exactly one WebSocket subscription, served from in-memory cache with sub-millisecond response times.
