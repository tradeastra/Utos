# Sprint 10 — Portfolio & Risk Engine

**Version:** v0.10.0
**Branch:** `sprint-10`
**Dependencies:** Sprint 5 (Trading Process Manager), Sprint 7 (Execution Engine), Sprint 8 (Grid Engine), Sprint 9 (Profit Lock Engine)

---

## Objective

Build the **Portfolio & Risk Engine** — a layer that manages all active positions across Trading Processes, calculates exposure, validates orders against risk rules before execution, and produces portfolio-level metrics.

This sprint shifts the focus from **building engines** to **controlling engines**. The Risk Manager sits between strategy engines (Grid, DCA, etc.) and the Execution Engine, ensuring all orders operate within defined risk limits.

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

**Key constraints:**
- Execution Engine does NOT know about risk rules — it just executes
- Strategy engines do NOT know about risk implementation — they submit orders and get approved/denied
- Risk Manager is the single gatekeeper for all order execution
- Portfolio Manager aggregates positions across all Trading Processes
- All modules are event-driven (no polling)

---

## Internal Modules

### Module 1: PortfolioManager (`backend/engine/risk/portfolio.py`)

Manages all active positions across Trading Processes.

**Responsibilities:**
- Track positions per instance, per account, per exchange
- Update positions on order fills
- Close positions on order fills (sell side)
- Query positions by various filters

**Key operations:**
- `register_position(instance_id, account_id, exchange, symbol, side, entry_price, quantity)`
- `update_position(instance_id, fill_price, fill_quantity, side)`
- `close_position(instance_id)`
- `get_positions(instance_id=None, account_id=None, exchange=None, symbol=None)`
- `get_position(instance_id)`

### Module 2: ExposureManager (`backend/engine/risk/exposure.py`)

Calculates exposure per exchange, account, asset, and strategy.

**Responsibilities:**
- Compute notional exposure (price × quantity) per dimension
- Track long/short net exposure
- Aggregate across positions

**Key operations:**
- `calculate_exposure(positions, current_prices) -> ExposureReport`
- `get_exposure_by_exchange(positions, prices) -> dict[str, Decimal]`
- `get_exposure_by_account(positions, prices) -> dict[str, Decimal]`
- `get_exposure_by_symbol(positions, prices) -> dict[str, Decimal]`
- `get_net_exposure(positions, prices) -> Decimal`

### Module 3: RiskManager (`backend/engine/risk/manager.py`)

Validates orders before they are sent to Execution Engine.

**Responsibilities:**
- Check max exposure per symbol/exchange/account
- Check max number of open positions
- Check max position size
- Check max capital per Trading Process
- Return RiskCheckResult (allowed/denied + reason)

**Risk rules:**
- `max_exposure_per_symbol` — max notional exposure per asset
- `max_exposure_per_exchange` — max notional exposure per exchange
- `max_open_positions` — max number of simultaneous positions
- `max_position_size` — max notional per single position
- `max_capital_per_instance` — max capital allocated per Trading Process

**Key operations:**
- `set_risk_parameters(user_id, params)`
- `get_risk_parameters(user_id)`
- `check_order_risk(instance_id, account_id, exchange, symbol, side, quantity, price) -> RiskCheckResult`
- `check_portfolio_risk(user_id) -> RiskAssessment`
- `on_price_update(user_id, symbol, price)` — update prices for exposure tracking

### Module 4: PositionAggregator (`backend/engine/risk/aggregator.py`)

Aggregates positions for reporting and risk control.

**Responsibilities:**
- Merge positions from multiple instances for same symbol
- Compute net position (long - short)
- Group by exchange, account, symbol

**Key operations:**
- `aggregate_by_symbol(positions) -> dict[str, AggregatedPosition]`
- `aggregate_by_exchange(positions) -> dict[str, AggregatedPosition]`
- `aggregate_by_account(positions) -> dict[str, AggregatedPosition]`
- `get_net_position(positions) -> AggregatedPosition`

### Module 5: PortfolioMetrics (`backend/engine/risk/metrics.py`)

Generates portfolio-level metrics.

**Responsibilities:**
- Unrealized PnL across all positions
- Realized PnL from closed positions
- Total exposure
- Drawdown (peak-to-trough)
- Margin usage estimate

**Key operations:**
- `calculate_unrealized_pnl(positions, current_prices) -> Decimal`
- `calculate_realized_pnl(closed_positions) -> Decimal`
- `calculate_total_exposure(positions, current_prices) -> Decimal`
- `calculate_drawdown(pnl_history) -> Decimal`
- `calculate_margin_usage(positions, current_prices, account_balance) -> Decimal`
- `generate_report(positions, current_prices, closed_positions, pnl_history, account_balance) -> PortfolioReport`

---

## Data Types

```python
@dataclass
class Position:
    instance_id: str
    account_id: str
    exchange: str
    symbol: str
    side: str  # "long" or "short"
    entry_price: Decimal
    quantity: Decimal
    realized_pnl: Decimal = Decimal("0")
    opened_at: datetime
    closed: bool = False

@dataclass
class AggregatedPosition:
    symbol: str
    total_long_quantity: Decimal
    total_short_quantity: Decimal
    net_quantity: Decimal
    weighted_avg_entry_price: Decimal
    position_count: int

@dataclass
class ExposureReport:
    total_exposure: Decimal
    long_exposure: Decimal
    short_exposure: Decimal
    net_exposure: Decimal
    by_exchange: dict[str, Decimal]
    by_account: dict[str, Decimal]
    by_symbol: dict[str, Decimal]

@dataclass
class PortfolioReport:
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    total_pnl: Decimal
    total_exposure: Decimal
    drawdown: Decimal
    margin_usage: Decimal
    position_count: int
    timestamp: datetime

@dataclass
class RiskLimits:
    max_exposure_per_symbol: Decimal
    max_exposure_per_exchange: Decimal
    max_open_positions: int
    max_position_size: Decimal
    max_capital_per_instance: Decimal
```

---

## API Surface

```python
class RiskManager:
    def __init__(
        self,
        portfolio: PortfolioManager,
        exposure: ExposureManager,
    ): ...

    def set_risk_parameters(self, user_id: str, limits: RiskLimits) -> None: ...
    def get_risk_parameters(self, user_id: str) -> RiskLimits: ...
    def check_order_risk(
        self, instance_id: str, account_id: str, exchange: str,
        symbol: str, side: str, quantity: Decimal, price: Decimal,
    ) -> RiskCheckResult: ...
    def check_portfolio_risk(self, user_id: str) -> RiskAssessment: ...
    def on_price_update(self, user_id: str, symbol: str, price: Decimal) -> None: ...
```

---

## Error Handling

- `RiskError` — raised on invalid risk operations
- `PortfolioError` — raised on invalid portfolio operations
- `ValidationError` — raised on invalid parameters
- `RiskCheckResult` with `allowed=False` and reason — for denied orders (not an exception)

---

## Acceptance Criteria

- [ ] PortfolioManager tracks positions across instances, accounts, exchanges
- [ ] ExposureManager calculates exposure per exchange/account/symbol
- [ ] RiskManager validates orders against all risk rules
- [ ] RiskManager denies orders that exceed limits (returns allowed=False)
- [ ] PositionAggregator merges positions correctly
- [ ] PortfolioMetrics computes unrealized/realized PnL, exposure, drawdown, margin usage
- [ ] Risk Manager does NOT call Execution Engine directly (it's a gatekeeper, not executor)
- [ ] All modules are independent from Grid Engine and Profit Lock Engine
- [ ] Internal metrics tracked
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No existing tests broken
