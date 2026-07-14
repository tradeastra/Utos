# Sprint 10 Release — Portfolio & Risk Engine

**Version:** v0.10.0
**Date:** 2026-07-14
**Tag:** `v0.10.0`
**Branch:** `sprint-10` → `develop` → `main`

---

## Summary

Sprint 10 delivers the **Portfolio & Risk Engine** — a layer that manages all active positions across Trading Processes, calculates exposure, validates orders against risk rules before execution, and produces portfolio-level metrics.

This sprint marks the transition from **building engines** to **controlling engines**. The Risk Manager sits between strategy engines (Grid, DCA, etc.) and the Execution Engine, ensuring all orders operate within defined risk limits.

---

## Architecture

```
Grid Engine ──┐
              │
Profit Lock ──┤
              │
DCA Engine ───┤──→ Risk Manager ──→ Execution Engine
              │
Other Strats ─┘
```

**Key constraints enforced:**
- Execution Engine does NOT know about risk rules — it just executes
- Strategy engines do NOT know about risk implementation — they submit orders and get approved/denied
- Risk Manager is the single gatekeeper for all order execution
- Risk Manager does NOT call Execution Engine (it's a gatekeeper, not executor)
- Portfolio Manager aggregates positions across all Trading Processes
- All modules are independent from Grid Engine, Profit Lock Engine, and Execution Engine

---

## New Features

### Module 1: PortfolioManager (`backend/engine/risk/portfolio.py`)
- Tracks positions per instance, per account, per exchange
- `register_position()` — create new position with validation
- `update_position()` — update on order fills (BUY increases long, SELL decreases long and realizes PnL)
- `close_position()` — force-close and move to closed positions list
- `get_positions()` — query with optional filters (instance, account, exchange, symbol)
- Supports both long and short positions

### Module 2: ExposureManager (`backend/engine/risk/exposure.py`)
- Calculates notional exposure (price × quantity) per dimension
- `get_exposure_by_exchange()`, `get_exposure_by_account()`, `get_exposure_by_symbol()`
- `get_net_exposure()` — long minus short
- `calculate_exposure()` — full `ExposureReport` with all dimensions
- Falls back to entry_price if current price not available

### Module 3: RiskManager (`backend/engine/risk/manager.py`)
- Validates orders before they are sent to Execution Engine
- **Risk rules:**
  - `max_position_size` — max notional per single position
  - `max_exposure_per_symbol` — max notional exposure per asset
  - `max_exposure_per_exchange` — max notional exposure per exchange
  - `max_open_positions` — max number of simultaneous positions
  - `max_capital_per_instance` — max capital allocated per Trading Process
- Returns `RiskCheckResult` with `allowed=True/False` and reason
- `check_portfolio_risk()` — assesses overall portfolio risk level (LOW/MEDIUM/HIGH)
- `on_price_update()` — updates internal price tracking
- Internal metrics: orders checked/allowed/denied, price updates
- Does NOT call ExecutionEngine — it's a gatekeeper, not an executor

### Module 4: PositionAggregator (`backend/engine/risk/aggregator.py`)
- Merges positions from multiple instances for same symbol/exchange/account
- `aggregate_by_symbol()`, `aggregate_by_exchange()`, `aggregate_by_account()`
- `get_net_position()` — net position across all positions
- Computes weighted average entry price, net quantity, position count

### Module 5: PortfolioMetrics (`backend/engine/risk/metrics.py`)
- `calculate_unrealized_pnl()` — across all open positions
- `calculate_realized_pnl()` — from closed positions
- `calculate_total_exposure()` — total notional exposure
- `calculate_drawdown()` — max peak-to-trough decline from PnL history
- `calculate_margin_usage()` — exposure as percentage of account balance
- `generate_report()` — full `PortfolioReport` with all metrics

---

## Test Coverage

| Test File | Tests | Description |
|-----------|-------|-------------|
| `test_portfolio_manager.py` | 20 | Register, update (long/short), close, query, validation |
| `test_exposure_manager.py` | 9 | By exchange/account/symbol, net exposure, full report |
| `test_position_aggregator.py` | 8 | Aggregate by symbol/exchange/account, net position |
| `test_portfolio_metrics.py` | 15 | Unrealized/realized PnL, exposure, drawdown, margin, full report |
| `test_risk_manager.py` | 14 | All risk rules, parameters, portfolio assessment, metrics |
| `test_risk_engine_integration.py` | 8 | Full risk flow, independence verification, metrics tracking |
| **Total Sprint 10** | **74** | |

**Full test suite: 629 tests passing** (555 existing + 74 new)

---

## Acceptance Criteria

- [x] PortfolioManager tracks positions across instances, accounts, exchanges
- [x] ExposureManager calculates exposure per exchange/account/symbol
- [x] RiskManager validates orders against all risk rules
- [x] RiskManager denies orders that exceed limits (returns allowed=False)
- [x] PositionAggregator merges positions correctly
- [x] PortfolioMetrics computes unrealized/realized PnL, exposure, drawdown, margin usage
- [x] Risk Manager does NOT call Execution Engine directly (it's a gatekeeper, not executor)
- [x] All modules are independent from Grid Engine and Profit Lock Engine
- [x] Internal metrics tracked
- [x] All unit tests pass
- [x] All integration tests pass
- [x] No existing tests broken

---

## Files Created

- `backend/engine/risk/__init__.py` — package exports
- `backend/engine/risk/portfolio.py` — PortfolioManager, Position
- `backend/engine/risk/exposure.py` — ExposureManager, ExposureReport
- `backend/engine/risk/aggregator.py` — PositionAggregator, AggregatedPosition
- `backend/engine/risk/metrics.py` — PortfolioMetrics, PortfolioReport
- `backend/engine/risk/manager.py` — RiskManager, RiskLimits
- `backend/tests/test_unit/test_portfolio_manager.py` — 20 tests
- `backend/tests/test_unit/test_exposure_manager.py` — 9 tests
- `backend/tests/test_unit/test_position_aggregator.py` — 8 tests
- `backend/tests/test_unit/test_portfolio_metrics.py` — 15 tests
- `backend/tests/test_unit/test_risk_manager.py` — 14 tests
- `backend/tests/test_unit/test_risk_engine_integration.py` — 8 tests
- `docs/sprint/SPRINT_10.md` — Sprint specification
- `docs/releases/SPRINT_10_RELEASE.md` — This document

## Files Modified

- `backend/core/exceptions.py` — Added `RiskError` exception class
- `docs/ROADMAP.md` — Sprint 10 marked completed, changelog updated

---

## Project Status

| Sprint | Status |
|--------|--------|
| ✅ Sprint 1 | Foundation |
| ✅ Sprint 2 | Database |
| ✅ Sprint 3 | Exchange Infrastructure |
| ✅ Sprint 4 | Binance Adapter |
| ✅ Sprint 5 | Trading Process Manager |
| ✅ Sprint 6 | Market Hub |
| ✅ Sprint 7 | Execution Engine |
| ✅ Sprint 8 | Grid Engine |
| ✅ Sprint 9 | Profit Lock Engine |
| ✅ Sprint 10 | Portfolio & Risk Engine |
