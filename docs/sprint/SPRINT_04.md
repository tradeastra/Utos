# Sprint 4: Binance Spot Adapter

## Status

**Authorized to Start** — CTO approval granted.

## Vision

Implement the first concrete exchange adapter — **Binance Spot** — on top of the infrastructure built in Sprint 3. This adapter proves that the `IExchangeAdapter` abstraction, `HttpClient`, `WebSocketManager`, `CredentialManager`, and `ErrorMapper` are sufficient for a real exchange.

No trading engine, grid, strategy, or worker logic is introduced in this sprint.

## Scope

**In scope:**

1. `BinanceSpotAdapter` implementing `IExchangeAdapter` in `backend/exchanges/adapters/binance.py`.
2. Binance Spot REST API integration:
   - `connect()` / `disconnect()`
   - `authenticate()`
   - `get_account()`
   - `get_balance()`
   - `get_symbol_info()`
   - `get_exchange_info()`
   - `get_ticker()`
   - `get_order_book()`
   - `get_candles()`
   - `get_trades()`
   - `place_order()`
   - `get_order()`
   - `cancel_order()`
   - `cancel_all()`
   - `get_open_orders()`
   - `health_check()`
3. Binance Spot WebSocket integration:
   - `subscribe_ticker()`
   - `subscribe_orderbook()`
   - `subscribe_user_data()`
   - `unsubscribe_ticker()`
   - `unsubscribe_orderbook()`
   - `unsubscribe_user_data()`
4. HMAC-SHA256 request signing and timestamp handling.
5. Binance-specific rate-limit configuration.
6. Error mapping for Binance HTTP and WebSocket responses.
7. **Exchange Certification** checklist and tests:
   - REST API berhasil.
   - WebSocket berhasil.
   - Reconnect berhasil.
   - Cancel Order berhasil.
   - Rate Limit ditangani.
   - Error Mapping benar.
   - Network timeout ditangani.
   - API Key invalid ditangani.
   - Timestamp drift ditangani.
   - Signature invalid ditangani.
8. Unit tests for `BinanceSpotAdapter` using mocked HTTP and WebSocket.

**Out of scope:**

- Grid engine
- Trading engine / order execution engine
- Strategy logic
- Worker / background processing
- DCA / profit lock
- Other exchanges (Hyperliquid, Bybit, OKX, MEXC)
- Database schema changes
- Docker / CI / frontend changes

## Acceptance Criteria

- [ ] `BinanceSpotAdapter` implements `IExchangeAdapter`.
- [ ] All public methods listed in scope are implemented and unit-tested.
- [ ] No `Binance`-specific logic leaks into `HttpClient`, `WebSocketManager`, `RateLimiter`, or `RetryPolicy`.
- [ ] `WebSocketManager` remains exchange-agnostic.
- [ ] HMAC-SHA256 signature and timestamp are generated for authenticated endpoints.
- [ ] Error mapping correctly translates Binance errors to domain `ExchangeError` exceptions.
- [ ] Exchange Certification checklist is defined and passes.
- [ ] Every new feature has a unit test.
- [ ] All tests pass.
- [ ] Work is committed on `sprint-4` branch and merged into `develop` via PR after audit.

## New Discipline

From this sprint onward, **every adapter must pass Exchange Certification before it is considered ready for the engine**.

## Workflow

1. Planning
2. Implement
3. Compile
4. Run Tests
5. Audit
6. Fix
7. Commit (on `sprint-4`)
8. Pull Request `sprint-4` → `develop`
9. Tag on `main` after merge to `main` at release time

## Implementation Plan

1. Create `sprint-4` branch from `develop`.
2. Create `docs/sprint/SPRINT_04.md`.
3. Extend `IExchangeAdapter` with `get_account()`, `get_symbol_info()`, and `cancel_all()` if required for the Binance contract.
4. Create `backend/exchanges/adapters/__init__.py`.
5. Implement `BinanceSpotAdapter` in `backend/exchanges/adapters/binance.py`.
6. Implement `BinanceAuthenticator` for HMAC-SHA256 and timestamp handling.
7. Implement `BinanceErrorMapper` or extend `ErrorMapper` with Binance-specific parsing.
8. Register `BinanceSpotAdapter` in `ExchangeFactory`.
9. Write `backend/tests/test_unit/test_binance_adapter.py` with mocks for REST and WebSocket.
10. Write Exchange Certification checklist/tests.
11. Compile and run tests.
12. Audit against acceptance criteria.
13. Fix issues.
14. Commit and open PR to `develop`.

## Target Metrics

- Test count: 100+
- All tests pass
- No exchange-agnostic component contains Binance-specific logic
