"""
Sprint 16F-1: pytest-benchmark for core engine components.

Benchmarks:
- GridCalculator.calculate_levels (grid generation)
- GridPlanner.plan_initial (action planning)
- ProfitLockPolicy.evaluate (policy decision)
- RiskManager.check_order_risk (risk validation)
- ExecutionEngine order validation + tracking
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.types import GridLevel, GridLevelStatus, GridState, OrderSide, OrderType
from engine.grid.calculator import GridCalculator
from engine.grid.planner import GridPlanner
from engine.grid.state import GridStateStore, GridStateMachine, GridStatus
from engine.profit_lock.calculator import ProfitCalculator, ProfitResult
from engine.profit_lock.policy import ProfitLockPolicy
from engine.profit_lock.state import ProfitLockState, ProfitLockStatus, ProfitLockStore
from engine.risk.manager import RiskManager, RiskLimits
from engine.risk.portfolio import PortfolioManager
from engine.risk.exposure import ExposureManager
from engine.execution.models import OrderRequest
from engine.execution.validator import OrderValidator
from engine.execution.tracker import OrderTracker
from engine.execution.execution_engine import ExecutionEngine


# ── Grid Calculator Benchmark ────────────────

class TestGridCalculatorBenchmark:
    def test_calculate_levels_10(self, benchmark):
        benchmark(
            GridCalculator.calculate_levels,
            upper_price=Decimal("50000"),
            lower_price=Decimal("40000"),
            grid_count=10,
            investment_per_grid=Decimal("100"),
        )

    def test_calculate_levels_50(self, benchmark):
        benchmark(
            GridCalculator.calculate_levels,
            upper_price=Decimal("50000"),
            lower_price=Decimal("40000"),
            grid_count=50,
            investment_per_grid=Decimal("100"),
        )

    def test_calculate_levels_100(self, benchmark):
        benchmark(
            GridCalculator.calculate_levels,
            upper_price=Decimal("50000"),
            lower_price=Decimal("40000"),
            grid_count=100,
            investment_per_grid=Decimal("100"),
        )

    def test_calculate_spacing(self, benchmark):
        benchmark(
            GridCalculator.calculate_spacing,
            upper_price=Decimal("50000"),
            lower_price=Decimal("40000"),
            grid_count=50,
        )

    def test_validate_parameters(self, benchmark):
        benchmark(
            GridCalculator.validate_parameters,
            upper_price=Decimal("50000"),
            lower_price=Decimal("40000"),
            grid_count=10,
            investment_per_grid=Decimal("100"),
        )


# ── Grid Planner Benchmark ───────────────────

class TestGridPlannerBenchmark:
    def test_plan_initial_10_grids(self, benchmark):
        store = GridStateStore()
        levels = GridCalculator.calculate_levels(
            Decimal("50000"), Decimal("40000"), 10, Decimal("100")
        )
        state = GridState(
            instance_id="bench-1",
            status=GridStatus.ACTIVE,
            upper_price=Decimal("50000"),
            lower_price=Decimal("40000"),
            grid_count=10,
            grid_spacing=Decimal("1000"),
            investment_per_grid=Decimal("100"),
            levels=levels,
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
        )
        store.put("bench-1", state)
        planner = GridPlanner(store)

        benchmark(planner.plan_initial, "bench-1", Decimal("45000"))

    def test_plan_initial_50_grids(self, benchmark):
        store = GridStateStore()
        levels = GridCalculator.calculate_levels(
            Decimal("50000"), Decimal("40000"), 50, Decimal("100")
        )
        state = GridState(
            instance_id="bench-2",
            status=GridStatus.ACTIVE,
            upper_price=Decimal("50000"),
            lower_price=Decimal("40000"),
            grid_count=50,
            grid_spacing=Decimal("200"),
            investment_per_grid=Decimal("100"),
            levels=levels,
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
        )
        store.put("bench-2", state)
        planner = GridPlanner(store)

        benchmark(planner.plan_initial, "bench-2", Decimal("45000"))


# ── ProfitLock Policy Benchmark ──────────────

class TestProfitLockPolicyBenchmark:
    def test_evaluate_monitoring(self, benchmark):
        state = ProfitLockState(
            instance_id="bench-pl",
            status=ProfitLockStatus.MONITORING,
            enabled=True,
            trigger_percentage=Decimal("5"),
            trail_percentage=Decimal("2"),
            entry_price=Decimal("50000"),
            quantity=Decimal("0.1"),
            side="long",
            highest_price=Decimal("50000"),
            lock_price=None,
            is_triggered=False,
            is_executed=False,
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
        )
        profit = ProfitResult(
            floating_profit=Decimal("250"),
            profit_percentage=Decimal("5"),
            is_profitable=True,
            entry_price=Decimal("50000"),
            current_price=Decimal("52500"),
            quantity=Decimal("0.1"),
        )
        benchmark(
            ProfitLockPolicy.evaluate,
            Decimal("52500"),
            profit,
            state,
        )

    def test_evaluate_triggered_trailing(self, benchmark):
        state = ProfitLockState(
            instance_id="bench-pl2",
            status=ProfitLockStatus.TRIGGERED,
            enabled=True,
            trigger_percentage=Decimal("5"),
            trail_percentage=Decimal("2"),
            entry_price=Decimal("50000"),
            quantity=Decimal("0.1"),
            side="long",
            highest_price=Decimal("53000"),
            lock_price=Decimal("51940"),
            is_triggered=True,
            is_executed=False,
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
        )
        profit = ProfitResult(
            floating_profit=Decimal("300"),
            profit_percentage=Decimal("6"),
            is_profitable=True,
            entry_price=Decimal("50000"),
            current_price=Decimal("53100"),
            quantity=Decimal("0.1"),
        )
        benchmark(
            ProfitLockPolicy.evaluate,
            Decimal("53100"),
            profit,
            state,
        )

    def test_compute_lock_price(self, benchmark):
        benchmark(
            ProfitLockPolicy.compute_lock_price,
            Decimal("53000"),
            Decimal("2"),
        )


# ── ProfitLock Calculator Benchmark ──────────

class TestProfitCalculatorBenchmark:
    def test_calculate_long(self, benchmark):
        calc = ProfitCalculator()
        benchmark(
            calc.calculate,
            entry_price=Decimal("50000"),
            current_price=Decimal("52500"),
            quantity=Decimal("0.1"),
            side="long",
        )

    def test_calculate_short(self, benchmark):
        calc = ProfitCalculator()
        benchmark(
            calc.calculate,
            entry_price=Decimal("50000"),
            current_price=Decimal("47500"),
            quantity=Decimal("0.1"),
            side="short",
        )


# ── Risk Manager Benchmark ───────────────────

class TestRiskManagerBenchmark:
    def test_check_order_risk_allowed(self, benchmark):
        portfolio = PortfolioManager()
        exposure = ExposureManager()
        rm = RiskManager(portfolio, exposure)
        rm.set_risk_parameters("user1", RiskLimits(
            max_position_size=Decimal("100000"),
            max_capital_per_instance=Decimal("50000"),
            max_exposure_per_symbol=Decimal("200000"),
            max_exposure_per_exchange=Decimal("500000"),
            max_open_positions=10,
        ))
        rm.on_price_update("user1", "BTCUSDT", Decimal("45000"))

        benchmark(
            rm.check_order_risk,
            instance_id="inst-1",
            account_id="acc-1",
            exchange="binance",
            symbol="BTCUSDT",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
            user_id="user1",
        )

    def test_check_order_risk_denied(self, benchmark):
        portfolio = PortfolioManager()
        exposure = ExposureManager()
        rm = RiskManager(portfolio, exposure)
        rm.set_risk_parameters("user1", RiskLimits(
            max_position_size=Decimal("100"),
            max_capital_per_instance=Decimal("50000"),
            max_exposure_per_symbol=Decimal("200000"),
            max_exposure_per_exchange=Decimal("500000"),
            max_open_positions=10,
        ))

        benchmark(
            rm.check_order_risk,
            instance_id="inst-1",
            account_id="acc-1",
            exchange="binance",
            symbol="BTCUSDT",
            side="buy",
            quantity=Decimal("1"),
            price=Decimal("45000"),
            user_id="user1",
        )

    def test_check_portfolio_risk(self, benchmark):
        portfolio = PortfolioManager()
        exposure = ExposureManager()
        rm = RiskManager(portfolio, exposure)
        rm.set_risk_parameters("user1", RiskLimits(
            max_position_size=Decimal("100000"),
            max_capital_per_instance=Decimal("50000"),
            max_exposure_per_symbol=Decimal("200000"),
            max_exposure_per_exchange=Decimal("500000"),
            max_open_positions=10,
        ))

        benchmark(rm.check_portfolio_risk, "user1")


# ── Execution Engine Benchmark ───────────────

class TestExecutionEngineBenchmark:
    def test_order_validation(self, benchmark):
        validator = OrderValidator()
        adapter = MagicMock()
        adapter.exchange_name = "binance"
        adapter.symbol_info = MagicMock()
        adapter.symbol_info.base = "BTC"
        adapter.symbol_info.quote = "USDT"
        adapter.symbol_info.min_qty = Decimal("0.001")
        adapter.symbol_info.max_qty = Decimal("1000")
        adapter.symbol_info.min_notional = Decimal("10")
        adapter.symbol_info.tick_size = Decimal("0.01")

        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )

        benchmark(validator.validate, request, adapter)

    def test_tracker_get_by_request_id(self, benchmark):
        tracker = OrderTracker()
        request_id = uuid.uuid4()
        # Pre-populate
        request = OrderRequest(
            request_id=request_id,
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )

        benchmark(tracker.get_by_request_id, request_id)

    def test_order_request_creation(self, benchmark):
        def create_order():
            return OrderRequest(
                request_id=uuid.uuid4(),
                exchange_account_id=uuid.uuid4(),
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("0.1"),
                price=Decimal("45000"),
            )
        benchmark(create_order)
