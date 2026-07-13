# Sprint 6 Release — Market Data Hub

**Version:** v0.6.0 (planned)  
**Date:** TBD — after Sprint 6 audit  
**Tag:** `v0.6.0` (planned)  
**Branch:** `sprint-6` → `develop` → `main`

---

## Summary

Sprint 6 will build the generic Market Data Hub — the single source of truth for real-time market data. The hub aggregates feeds from any registered exchange (Binance, Hyperliquid, Bybit, and future adapters), normalizes the data, caches it in memory, and distributes it to consumers without exposing the underlying exchange.

---

## New Features

- **MarketHub** — generic `IMarketHub` interface and implementation (`backend/market/hub/market_hub.py`)
- **MarketCache** — in-memory cache for ticker, order book, price, candles (`backend/market/cache/market_cache.py`)
- **Subscription Manager** — deduplicated subscriptions: 1 WebSocket per `(symbol, exchange, channel)` regardless of consumer count
- **Symbol Registry** — per-exchange supported symbols with normalization (`backend/market/symbol_registry.py`)
- **Market Status** — per-symbol quality states: `CONNECTED`, `CONNECTING`, `STALE`, `RECONNECTING`, `DISCONNECTED`
- **Alive Check** — `MarketHub.is_alive(symbol, exchange)` for Trading Engine safety checks
- **Latency Metrics** — `last_update`, `latency_ms`, `reconnect_count`, `dropped_messages`, `message_rate`
- **REST API endpoints** for price, ticker, order book, candles, symbols, status, metrics
- **Multi-exchange connector pattern** ready for Binance, Hyperliquid, Bybit, and future adapters

---

## Breaking Changes

To be filled after implementation.

---

## Migration

No database migration required. Sprint 6 uses in-memory cache and optional Redis keys.

---

## Known Issues

To be filled after implementation.

---

## Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Total tests | 270+ | TBD |
| Tests passed | 270+ | TBD |
| Tests failed | 0 | TBD |
| Cache hit latency | < 1ms | TBD |
| Cache miss latency | < 100ms | TBD |
| WebSocket deduplication | 1 per (symbol, exchange, channel) | TBD |

---

## Files Changed

To be filled after implementation.

---

## Test Coverage

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_market_hub.py` | TBD | ⏳ |
| `test_market_cache.py` | TBD | ⏳ |
| `test_subscription_manager.py` | TBD | ⏳ |
| `test_exchange_connector.py` | TBD | ⏳ |
| **Total** | **270+** | **⏳** |

---

## Next Sprint

**Sprint 7: Execution Engine** — order placement, cancellation, fill monitoring, and order state machine.
