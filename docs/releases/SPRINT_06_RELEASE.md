# Sprint 6 Release — Market Data Hub

**Version:** v0.6.0  
**Date:** 2026-07-13  
**Tag:** `v0.6.0`  
**Branch:** `sprint-6` → `develop` → `main`

---

## Summary

Sprint 6 delivers the generic Market Data Hub — the single source of truth for real-time market data. The hub aggregates feeds from any registered exchange (Binance, Hyperliquid, Bybit, and future adapters), normalizes the data, caches it in memory, and distributes it to consumers without exposing the underlying exchange.

---

## New Features

- **MarketHub** — generic `IMarketHub` interface and implementation (`backend/market/hub/market_hub.py`)
  - `subscribe(exchange, symbol, channel, callback)` — consumer subscription with deduplication
  - `unsubscribe(subscription_id)` — per-consumer unsubscribe
  - `get_price(exchange, symbol)` — current price from cache or adapter fallback
  - `get_ticker(exchange, symbol)` — full ticker data
  - `get_orderbook(exchange, symbol)` — order book snapshot
  - `get_candles(exchange, symbol, interval)` — historical candles
  - `is_alive(exchange, symbol)` — health check for Trading Engine safety
  - `get_status(exchange, symbol)` — returns `MarketStatus` enum
  - `get_metrics(exchange, symbol)` — latency, reconnect, dropped messages, message rate
  - `snapshot()` — operational overview for monitoring

- **MarketCache** — in-memory cache for ticker, order book, price, candles (`backend/market/cache/market_cache.py`)
  - Per `(exchange, symbol)` storage with staleness tracking
  - Message count and rate calculation
  - Case-insensitive exchange/symbol normalization

- **SubscriptionManager** — deduplicated subscriptions (`backend/market/subscription_manager.py`)
  - 1 WebSocket per `(exchange, symbol, channel)` regardless of consumer count
  - Reference counting: stream closes only when last consumer leaves
  - Fan-out: delivers data to all registered consumer callbacks

- **SymbolRegistry** — per-exchange supported symbols with normalization (`backend/market/symbol_registry.py`)
  - Case-insensitive symbol and exchange normalization
  - Validation with `SymbolNotSupported` exception

- **ExchangeConnector** — wraps `IExchangeAdapter` for market data (`backend/market/connector/exchange_connector.py`)
  - Connection lifecycle management
  - Automatic reconnect with exponential backoff
  - Per-symbol metrics tracking (latency, message rate, dropped messages)
  - Status transitions: `DISCONNECTED → CONNECTING → CONNECTED → STALE → RECONNECTING`

- **MarketStatus** enum — `CONNECTED | CONNECTING | STALE | RECONNECTING | DISCONNECTED`
- **MarketMetrics** dataclass — `last_update`, `latency_ms`, `reconnect_count`, `dropped_messages`, `message_rate`, `status`

- **REST API endpoints** (`backend/api/v1/endpoints/market.py`):
  - `GET /api/v1/market/price/{exchange}/{symbol}`
  - `GET /api/v1/market/ticker/{exchange}/{symbol}`
  - `GET /api/v1/market/orderbook/{exchange}/{symbol}`
  - `GET /api/v1/market/candles/{exchange}/{symbol}?interval=1m&limit=100`
  - `GET /api/v1/market/symbols/{exchange}`
  - `GET /api/v1/market/status/{exchange}/{symbol}`
  - `GET /api/v1/market/metrics/{exchange}/{symbol}`
  - `GET /api/v1/market/snapshot`

- **MarketHub lifecycle** integrated into FastAPI `lifespan` in `main.py`

---

## Breaking Changes

- `main.py` now initializes `market_hub` singleton during app startup. Existing endpoints are unaffected.
- New `/api/v1/market` router added to API v1.

---

## Migration

No database migration required. Sprint 6 uses in-memory cache and optional Redis keys.

---

## Known Issues

- Candle channel does not extract interval from raw WebSocket data; defaults to `1m` for list payloads. Future adapters should emit `Candle` objects with interval metadata.
- No Redis persistence for cache state (planned for future sprint).
- No Event Bus integration (deferred to future Event Bus sprint).

---

## Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Total tests | 270+ | 309 |
| Tests passed | 270+ | 309 |
| Tests failed | 0 | 0 |
| Cache read latency | < 1ms | < 0.1ms per call (10k iterations) |
| Fan-out to 50 consumers | < 1s | < 600ms |
| WebSocket deduplication | 1 per (exchange, symbol, channel) | ✅ Verified (100 consumers = 1 WS) |
| Subscription dedup at scale | 100 consumers = 1 WS | ✅ Verified |
| Concurrent cache writes | 1000 without errors | ✅ Verified |

---

## Files Changed

### New Files

| File | Purpose |
|------|---------|
| `backend/market/__init__.py` | Market package exports |
| `backend/market/base.py` | `IMarketHub` interface, `MarketStatus`, `MarketMetrics` |
| `backend/market/cache/__init__.py` | Cache package exports |
| `backend/market/cache/market_cache.py` | In-memory `MarketCache` |
| `backend/market/connector/__init__.py` | Connector package exports |
| `backend/market/connector/exchange_connector.py` | `ExchangeConnector` |
| `backend/market/hub/__init__.py` | Hub package exports |
| `backend/market/hub/market_hub.py` | `MarketHub` implementation |
| `backend/market/subscription_manager.py` | `SubscriptionManager` |
| `backend/market/symbol_registry.py` | `SymbolRegistry` |
| `backend/api/v1/endpoints/market.py` | REST API endpoints |
| `backend/tests/test_unit/test_market_cache.py` | 18 unit tests |
| `backend/tests/test_unit/test_symbol_registry.py` | 12 unit tests |
| `backend/tests/test_unit/test_subscription_manager.py` | 12 unit tests |
| `backend/tests/test_unit/test_exchange_connector.py` | 11 unit tests |
| `backend/tests/test_unit/test_market_hub.py` | 18 unit tests |
| `backend/tests/test_unit/test_market_integration.py` | 6 integration tests |
| `backend/tests/test_unit/test_market_performance.py` | 5 performance tests |

### Modified Files

| File | Change |
|------|--------|
| `backend/main.py` | Added `MarketHub` singleton and lifecycle management |
| `backend/api/v1/__init__.py` | Added market router registration |
| `backend/api/v1/endpoints/__init__.py` | Added market module import |

---

## Test Coverage

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_market_cache.py` | 18 | ✅ |
| `test_symbol_registry.py` | 12 | ✅ |
| `test_subscription_manager.py` | 12 | ✅ |
| `test_exchange_connector.py` | 11 | ✅ |
| `test_market_hub.py` | 18 | ✅ |
| `test_market_integration.py` | 6 | ✅ |
| `test_market_performance.py` | 5 | ✅ |
| **Sprint 6 Total** | **82** | **✅** |
| **Full Suite Total** | **309** | **✅** |

---

## Acceptance Criteria

- [x] One WebSocket subscription per `(exchange, symbol, channel)`
- [x] Multiple Trading Processes share the same market stream
- [x] In-memory cache updates in real time
- [x] Market status transitions correctly
- [x] Automatic reconnect works
- [x] No duplicate subscriptions
- [x] Cache survives reconnect
- [x] All tests pass (309/309)
- [x] Performance metrics reported

---

## Next Sprint

**Sprint 7: Execution Engine** — order placement, cancellation, fill monitoring, and order state machine.
