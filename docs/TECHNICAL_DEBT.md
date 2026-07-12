# Technical Debt Register

**Version:** v0.4.0  
**Last Updated:** 2026-07-12  
**Baseline:** Sprint 4 merged into `main`  

This document tracks pragmatic decisions, incomplete implementations, and known risks that are intentionally deferred. It is not a backlog to be cleared immediately; it is a map so that today's shortcuts do not become tomorrow's surprises as the codebase grows.

---

## 1. TODO Stubs in API Endpoints

These endpoints were scaffolded during earlier sprints but still contain placeholder logic. They return static or hardcoded responses instead of calling the service/repository layer.

| File | Line(s) | Item |
|------|---------|------|
| `backend/api/v1/endpoints/trading_instances.py` | 87 | Authentication not wired into instance endpoints. |
| `backend/api/v1/endpoints/trading_instances.py` | 100 | `POST /trading-instances` creation logic is a stub. |
| `backend/api/v1/endpoints/trading_instances.py` | 151 | `GET /trading-instances` listing logic is a stub. |
| `backend/api/v1/endpoints/trading_instances.py` | 175 | `GET /trading-instances/{id}` retrieval logic is a stub. |
| `backend/api/v1/endpoints/trading_instances.py` | 200 | Prepare-instance logic is a stub. |
| `backend/api/v1/endpoints/trading_instances.py` | 233 | Start-instance logic is a stub. |
| `backend/api/v1/endpoints/trading_instances.py` | 261 | Stop-instance logic is a stub. |
| `backend/api/v1/endpoints/trading_instances.py` | 290 | Pause-instance logic is a stub. |
| `backend/api/v1/endpoints/trading_instances.py` | 318 | Resume-instance logic is a stub. |
| `backend/api/v1/endpoints/trading_instances.py` | 346 | Delete-instance logic is a stub. |
| `backend/api/v1/endpoints/exchange_accounts.py` | 99 | Actual exchange account retrieval is a stub. |
| `backend/api/v1/endpoints/exchange_accounts.py` | 124 | Actual exchange account deletion is a stub. |
| `backend/api/v1/endpoints/orders.py` | 48 | Order listing is a stub. |
| `backend/api/v1/endpoints/orders.py` | 70 | Order retrieval is a stub. |
| `backend/api/v1/endpoints/orders.py` | 95 | Order cancellation is a stub. |
| `backend/api/v1/endpoints/portfolio.py` | 54 | Portfolio retrieval is a stub. |
| `backend/api/v1/endpoints/portfolio.py` | 85 | Positions retrieval is a stub. |
| `backend/api/v1/endpoints/health.py` | 31, 62, 74 | Health/readiness checks are static placeholders. |
| `backend/api/dependencies.py` | 68, 96, 116 | `get_current_user` and permission checks use hardcoded users and bypass DB lookup. |

**Why it is acceptable now:** Sprint 5 will introduce the Trading Process Manager and state machine; most of these endpoints will be implemented or rewritten as part of that work.

---

## 2. Shortcuts / Pragmatic Decisions

| Shortcut | Location | Rationale | When to Revisit |
|----------|----------|-----------|-----------------|
| All exchange tests use `AsyncMock` | `backend/tests/test_unit/test_binance_adapter.py` | No live network dependency; fast and deterministic. | Before staging on Binance Testnet. |
| Quote asset heuristic | `backend/exchanges/adapters/binance.py` (`_quote_asset`) | Avoids caching full `exchangeInfo` just to resolve `quoteAsset`. | As soon as multi-quote-asset trading is needed (e.g., BTCBRL, USDC pairs). |
| Generic token-bucket rate limiter | `backend/exchanges/rate_limiter.py` | Simple and exchange-agnostic. | Before running multiple instances or polling many symbols. |
| Single-retry auto-resync for `-1021` | `backend/exchanges/adapters/binance.py` (`_signed_request`) | Covers typical clock drift; avoids infinite retry loops. | If production shows repeated drift, increase monitoring or NTP enforcement. |
| Average fill price ignores fees | `backend/exchanges/adapters/binance.py` (`place_order`) | Good enough for PnL approximation. | Before fee-sensitive strategy reporting. |
| Listen key kept alive by periodic PUT only | `backend/exchanges/adapters/binance.py` | No explicit detection of expired key on WebSocket receive. | When user stream becomes critical for production. |

---

## 3. Areas That Need Refactoring

1. **Quote asset resolver**  
   Replace `_quote_asset()` heuristic with a lookup against cached `exchangeInfo.symbols.quoteAsset`. This removes ambiguity for non-USDT and non-standard symbol lengths.

2. **Weight-aware rate limiting**  
   Change `RateLimiter.acquire()` to accept a `weight` parameter and/or parse `X-MBX-USED-WEIGHT-1M` / `Retry-After` headers from Binance responses.

3. **Service layer for API endpoints**  
   Move business logic out of FastAPI endpoints into a dedicated service layer (`backend/services/`) that coordinates repositories, adapters, and the trading engine.

4. **Trading instance state machine**  
   Centralize state transitions (`created` -> `ready` -> `running` -> `paused` -> `stopped`) in a single class/module instead of spreading validation across endpoint handlers.

5. **Config-driven error mapping**  
   Move the Binance error-code-to-exception table from code into a JSON/YAML configuration so other exchanges can reuse `ErrorMapper` without code changes.

6. **WebSocket lifecycle tracking**  
   Track `_receive_task` cancellation and ensure no dangling tasks leak on repeated reconnect.

---

## 4. Performance Risks

| Risk | Impact | Mitigation Today | Target Fix |
|------|--------|------------------|------------|
| Polling `get_open_orders()` per symbol | Hits Binance weight limits quickly. | Conservative polling not yet implemented. | Weight-aware rate limiter + event-driven updates via user stream. |
| SQLite in tests / default | Fine for unit tests; not suitable for production concurrency. | Tests use async SQLite with rollback. | Production config switches to PostgreSQL with connection pooling. |
| WebSocket reconnect creates new receive task | Minor memory churn; can accumulate tasks during flappy networks. | Tasks are created but not explicitly awaited on disconnect. | Track and cancel receive tasks cleanly. |
| No queue for outbound orders | Burst of orders may exceed Binance order rate limits. | Not applicable until order engine exists. | Add outbound order queue in Trading Process Manager. |

---

## 5. Security Risks

| Risk | Severity | Detail | Target Fix |
|------|----------|--------|------------|
| API endpoints are unauthenticated | **High** | `dependencies.py` returns hardcoded users; JWT/session validation not implemented. | Sprint 5+ when auth layer is in scope. |
| Exchange secrets in memory as plain strings | **Medium** | `ExchangeCredentials` stores `api_secret` as a plain string. | Introduce secret encryption at rest (KMS/vault) before production. |
| No rate limiting on public HTTP endpoints | **Medium** | FastAPI routes have no throttling. | Add middleware rate limiter before exposing to internet. |
| Input validation relies on Pydantic only | **Low** | No additional sanitization for dynamic queries. | Add SQL injection and strict validation tests when filters become complex. |
| No audit logging for exchange operations | **Low** | Order/cancel/balance calls are not persisted. | Add audit log table and middleware. |

---

## 6. Scalability Risks

1. **In-memory rate limiter**  
   `RateLimiter` uses an in-process token bucket. Multiple worker instances will not coordinate. Remedy: Redis-backed rate limiter for multi-instance deployments.

2. **Per-instance WebSocket managers**  
   WebSocket subscriptions are local to each running adapter. Horizontal scaling will require either sticky sessions or a shared pub/sub layer for market/user events.

3. **No queue for market data fan-out**  
   Currently the engine would receive market data directly via callback. With many instances, this does not scale. A message broker (Redis/RabbitMQ) should be introduced.

4. **Monolithic adapter design**  
   `BinanceSpotAdapter` mixes REST, WebSocket, authentication, and order mapping. As more exchanges are added, consider splitting into smaller classes (`RestClient`, `StreamClient`, `OrderMapper`).

---

## 7. Recommended Remediation Timeline

| Item | Priority | Effort | Target Sprint |
|------|----------|--------|---------------|
| Implement Trading Instance lifecycle endpoints | **High** | Medium | Sprint 5 |
| Wire up authentication dependencies | **High** | Medium | Sprint 5 / 6 |
| Add service layer for API endpoints | **High** | Medium | Sprint 5 |
| Centralize Trading Instance state machine | **Medium** | Medium | Sprint 5 |
| Quote asset resolver from `exchangeInfo` | **Medium** | Small | Sprint 5 |
| Weight-aware rate limiter | **Medium** | Medium | Sprint 6 |
| Listen key expiration detection | **Medium** | Small | Sprint 6 |
| Redis-backed rate limiter | **Low** | Large | Sprint 7+ |
| Exchange credential encryption | **Low** | Medium | Before production |
| Message broker for market data fan-out | **Low** | Large | Sprint 8+ |

---

## 8. How to Maintain This Document

- Update this file at the end of every sprint audit.
- When a debt item is resolved, move it to a "Resolved" section with the sprint/version in which it was cleared.
- When a new shortcut is taken, add it here immediately rather than relying on memory.
- Before starting a new sprint, review this document in planning to decide which debts to pay down.

---

*Generated as part of the Sprint 4 close-out. This is a living document, not a judgment.*
