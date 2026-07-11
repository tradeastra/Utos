# Sprint 3: Infrastructure Exchange Layer

## Status

**Authorized to Start** — CTO approval granted.

## Vision

Build the **infrastructure abstraction layer** for exchange integrations so that concrete adapters (Binance, Hyperliquid, Bybit, OKX, MEXC, etc.) can be implemented in later sprints without duplicating networking, authentication, retry, rate-limit, or WebSocket management logic.

This sprint intentionally does **not** contain any Binance-specific (or exchange-specific) code.

## Scope

**In scope:**

1. `IExchangeAdapter` abstract interface
2. `ExchangeFactory` for adapter registration / resolution
3. `CredentialManager` for secure API key encryption / decryption
4. `HttpClient` with timeout, retry, and circuit-breaker policy
5. `WebSocketManager` for connection lifecycle and message dispatch
6. `RateLimiter` (token-bucket / in-memory)
7. `RetryPolicy` configuration
8. `ExchangeError` hierarchy and `ErrorMapper`
9. Unit tests for every component

**Out of scope:**

- Any concrete exchange adapter (Binance, Hyperliquid, Bybit, OKX, MEXC, etc.)
- Trading logic, order execution, or strategy code
- Database schema changes
- Docker / CI / frontend changes

## Acceptance Criteria

- [ ] `IExchangeAdapter` declares all common operations (balance, order, cancel, positions, market stream, health, etc.) with abstract async methods.
- [ ] `ExchangeFactory` can register an adapter by `ExchangeName` and create instances by name.
- [ ] `CredentialManager` encrypts and decrypts API keys using a secret derived from `settings.SECRET_KEY`.
- [ ] `HttpClient` supports configurable timeout, retry count, retry backoff, and per-request retry logic.
- [ ] `WebSocketManager` can connect, send, receive, reconnect, and dispatch callbacks.
- [ ] `RateLimiter` supports token-bucket rate limiting for REST and WebSocket endpoints.
- [ ] `ErrorMapper` maps external HTTP / WebSocket errors into domain `ExchangeError` exceptions.
- [ ] 100% unit test coverage for all infrastructure components; every test passes.
- [ ] No Binance-specific code exists in this sprint.
- [ ] All work is committed on `sprint-3` branch and merged into `develop` via PR after audit.

## New Discipline

From this sprint onward, **every new feature must be accompanied by a unit test**. A sprint without tests for its features is considered a failed sprint.

## Workflow

1. Planning
2. Implement
3. Compile
4. Run Tests
5. Audit
6. Fix
7. Commit (on `sprint-3`)
8. Pull Request `sprint-3` → `develop`
9. Tag on `main` after merge to `main` at release time

## Implementation Plan

1. Create `sprint-3` branch from `develop`.
2. Define `IExchangeAdapter` in `backend/exchanges/adapter.py`.
3. Define `ExchangeError` and `ErrorMapper` in `backend/exchanges/errors.py`.
4. Define `ExchangeFactory` in `backend/exchanges/factory.py`.
5. Implement `CredentialManager` in `backend/exchanges/credential_manager.py`.
6. Implement `RateLimiter` in `backend/exchanges/rate_limiter.py`.
7. Implement `RetryPolicy` in `backend/exchanges/retry.py`.
8. Implement `HttpClient` in `backend/exchanges/http_client.py`.
9. Implement `WebSocketManager` in `backend/exchanges/websocket_manager.py`.
10. Write `__init__.py` exports.
11. Write comprehensive unit tests in `backend/tests/test_unit/test_exchanges.py`.
12. Compile and run tests.
13. Audit against acceptance criteria.
14. Fix issues.
15. Commit and open PR to `develop`.

## Target Metrics

- Test count: 70+
- All tests pass
- No exchange-specific code committed
