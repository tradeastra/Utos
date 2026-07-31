"""
Unit tests for BreakerScreeningStore and BreakerThresholdRepository.

Verifies the "source of truth" flow:
  1. rescreen_all() screens symbols and persists thresholds to the DB.
  2. get_threshold() reads them back.
  3. rescreen_all() again upserts (updates, not duplicates).
  4. get_threshold() for an unscreened symbol returns fallback.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from core.domain_types import Candle
from market.base import IMarketHub, MarketMetrics, MarketStatus
from repositories.breaker_threshold_repository import BreakerThresholdRepository
from services.breaker_screening_store import BreakerScreeningStore
from services.circuit_breaker_screener import ScreenerConfig
from sqlalchemy.ext.asyncio import AsyncSession


def _candle(close: Decimal, days_ago: int = 0) -> Candle:
    ts = datetime.now(UTC) - timedelta(days=days_ago)
    return Candle(
        symbol="X", interval="1d", open=close, high=close, low=close,
        close=close, volume=Decimal("1000"), timestamp=ts,
    )


def _candles_from_closes(closes: list[Decimal]) -> list[Candle]:
    n = len(closes)
    return [_candle(c, days_ago=n - i - 1) for i, c in enumerate(closes)]


def _killer(drop_pct: Decimal, window: int = 5) -> list[Decimal]:
    """A drop that recovers — future close goes back to 100."""
    drop_price = Decimal("100") * (Decimal("1") - drop_pct / Decimal("100"))
    padding = [Decimal("100")] * window
    return [Decimal("100"), drop_price] + padding


def _continue(drop_pct: Decimal, window: int = 5, future_drop: Decimal = Decimal("9.0")) -> list[Decimal]:
    """A drop that continues — future decline >= future_drop within window."""
    drop_price = Decimal("100") * (Decimal("1") - drop_pct / Decimal("100"))
    future_close = drop_price * (Decimal("1") - future_drop / Decimal("100"))
    closes: list[Decimal] = []
    for i in range(1, window + 1):
        frac = Decimal(i) / Decimal(window)
        c = drop_price + (future_close - drop_price) * frac
        closes.append(c)
    return [Decimal("100"), drop_price] + closes


class FakeMarketHub(IMarketHub):
    def __init__(self, candle_map: dict[str, list[Candle]] | None = None) -> None:
        self._candle_map = candle_map or {}

    def set_candles(self, symbol: str, candles: list[Candle]) -> None:
        self._candle_map[symbol.upper()] = candles

    async def get_candles(self, exchange: str, symbol: str, interval: str) -> list[Candle]:
        candles = self._candle_map.get(symbol.upper())
        if candles is None:
            raise RuntimeError(f"no candles for {symbol}")
        return candles

    async def subscribe(self, *a, **kw): ...
    async def unsubscribe(self, *a, **kw): ...
    async def get_price(self, *a, **kw): return Decimal("0")
    async def get_ticker(self, *a, **kw): ...
    async def get_orderbook(self, *a, **kw): ...
    async def is_alive(self, *a, **kw): return True
    async def get_status(self, *a, **kw): return MarketStatus.CONNECTED
    async def get_metrics(self, *a, **kw): return MarketMetrics(exchange="x", symbol="y")
    async def start(self): ...
    async def stop(self): ...


def _btc_candles() -> list[Candle]:
    """365 candles where 4% drops continue (future decline >= 12%)."""
    w = 5
    closes: list[Decimal] = [Decimal("100")] * 20
    for _ in range(3):
        closes += _killer(Decimal("1"), w)
    for _ in range(3):
        closes += _killer(Decimal("2"), w)
    for _ in range(3):
        closes += _killer(Decimal("3"), w)
    for _ in range(3):
        closes += _killer(Decimal("3.5"), w)
    for _ in range(3):
        closes += _continue(Decimal("4"), w)
    closes += [Decimal("100")] * (365 - len(closes))
    return _candles_from_closes(closes)


def _doge_candles() -> list[Candle]:
    """365 candles where 8% drops continue (future decline >= 24%)."""
    w = 5
    closes: list[Decimal] = [Decimal("100")] * 20
    for _ in range(3):
        closes += _killer(Decimal("4"), w)
    for _ in range(3):
        closes += _killer(Decimal("5"), w)
    for _ in range(3):
        closes += _killer(Decimal("6"), w)
    for _ in range(3):
        closes += _killer(Decimal("7"), w)
    for _ in range(3):
        closes += _killer(Decimal("7.5"), w)
    for _ in range(3):
        closes += _continue(Decimal("8"), w)
    closes += [Decimal("100")] * (365 - len(closes))
    return _candles_from_closes(closes)


@pytest.fixture
def fake_hub() -> FakeMarketHub:
    hub = FakeMarketHub()
    hub.set_candles("BTCUSDT", _btc_candles())
    hub.set_candles("DOGEUSDT", _doge_candles())
    return hub


@pytest.fixture
def store(fake_hub: FakeMarketHub) -> BreakerScreeningStore:
    return BreakerScreeningStore(fake_hub)


class TestBreakerScreeningStore:
    @pytest.mark.asyncio
    async def test_rescreen_all_persists_thresholds(
        self, store: BreakerScreeningStore, db_session: AsyncSession
    ) -> None:
        await store.rescreen_all(
            db_session,
            ["BTCUSDT", "DOGEUSDT"],
            config=ScreenerConfig(
                min_continuation_rate=Decimal("0.90"),
                continuation_window=5,
                min_samples=3,
            ),
        )
        # Read back from DB
        repo = BreakerThresholdRepository(db_session)
        btc = await repo.get_threshold("binance", "BTCUSDT", Decimal("0.90"))
        doge = await repo.get_threshold("binance", "DOGEUSDT", Decimal("0.90"))
        assert btc is not None
        assert doge is not None
        assert Decimal(str(btc.threshold_pct)) == Decimal("4.0")
        assert doge.threshold_pct > btc.threshold_pct

    @pytest.mark.asyncio
    async def test_get_threshold_returns_persisted_value(
        self, store: BreakerScreeningStore, db_session: AsyncSession
    ) -> None:
        await store.rescreen_all(
            db_session,
            ["BTCUSDT"],
            config=ScreenerConfig(
                min_continuation_rate=Decimal("0.90"),
                continuation_window=5,
                min_samples=3,
            ),
        )
        threshold = await store.get_threshold(
            db_session, "BTCUSDT", Decimal("0.90")
        )
        assert threshold == Decimal("4.0")

    @pytest.mark.asyncio
    async def test_get_threshold_returns_fallback_for_unscreened(
        self, store: BreakerScreeningStore, db_session: AsyncSession
    ) -> None:
        # ETHUSDT was never screened — should return fallback, not crash.
        threshold = await store.get_threshold(
            db_session, "ETHUSDT", Decimal("0.90")
        )
        assert threshold == Decimal("5.0")  # fallback for 0.90

    @pytest.mark.asyncio
    async def test_rescreen_all_upserts_not_duplicates(
        self, store: BreakerScreeningStore, db_session: AsyncSession
    ) -> None:
        cfg = ScreenerConfig(
            min_continuation_rate=Decimal("0.90"),
            continuation_window=5,
            min_samples=3,
        )
        # Screen once
        await store.rescreen_all(db_session, ["BTCUSDT"], config=cfg)
        # Screen again
        await store.rescreen_all(db_session, ["BTCUSDT"], config=cfg)
        # Should still be exactly 1 row
        repo = BreakerThresholdRepository(db_session)
        all_rows = await repo.get_all_for_rate(Decimal("0.90"))
        btc_rows = [r for r in all_rows if r.symbol == "BTCUSDT"]
        assert len(btc_rows) == 1

    @pytest.mark.asyncio
    async def test_rescreen_for_multiple_rates(
        self, store: BreakerScreeningStore, db_session: AsyncSession
    ) -> None:
        await store.rescreen_for_rates(
            db_session,
            ["BTCUSDT"],
            rates=[Decimal("0.70"), Decimal("0.80"), Decimal("0.90")],
            base_config=ScreenerConfig(
                continuation_window=5, min_samples=3,
            ),
        )
        repo = BreakerThresholdRepository(db_session)
        for rate in [Decimal("0.70"), Decimal("0.80"), Decimal("0.90")]:
            row = await repo.get_threshold("binance", "BTCUSDT", rate)
            assert row is not None
            assert abs(float(row.min_continuation_rate) - float(rate)) < 0.001

    @pytest.mark.asyncio
    async def test_get_all_thresholds_returns_map(
        self, store: BreakerScreeningStore, db_session: AsyncSession
    ) -> None:
        await store.rescreen_all(
            db_session,
            ["BTCUSDT", "DOGEUSDT"],
            config=ScreenerConfig(
                min_continuation_rate=Decimal("0.90"),
                continuation_window=5,
                min_samples=3,
            ),
        )
        all_thresholds = await store.get_all_thresholds(
            db_session, Decimal("0.90")
        )
        assert "BTCUSDT" in all_thresholds
        assert "DOGEUSDT" in all_thresholds
        assert all_thresholds["BTCUSDT"] == Decimal("4.0")

    @pytest.mark.asyncio
    async def test_threshold_differs_by_continuation_rate(
        self, store: BreakerScreeningStore, db_session: AsyncSession
    ) -> None:
        # Screen BTC for 0.70 and 0.90 — thresholds may differ.
        await store.rescreen_for_rates(
            db_session,
            ["BTCUSDT"],
            rates=[Decimal("0.70"), Decimal("0.90")],
            base_config=ScreenerConfig(
                continuation_window=5, min_samples=3,
            ),
        )
        t70 = await store.get_threshold(db_session, "BTCUSDT", Decimal("0.70"))
        t90 = await store.get_threshold(db_session, "BTCUSDT", Decimal("0.90"))
        # Both should be valid thresholds
        assert t70 > 0
        assert t90 > 0
        # 0.90 should be >= 0.70 (more conservative or equal)
        assert t90 >= t70


class TestBreakerResumeConfig:
    """Tests for get_breaker_config() and update_resume_config() — the resume
    behavior fields (resume_mode, recovery_pct, widen_multiplier) that control
    what the bot does AFTER the breaker triggers.
    """

    @pytest.mark.asyncio
    async def test_get_breaker_config_returns_full_config(
        self, store: BreakerScreeningStore, db_session: AsyncSession
    ) -> None:
        # Screen BTC at 0.90 first so a row exists.
        await store.rescreen_all(
            db_session,
            ["BTCUSDT"],
            config=ScreenerConfig(
                min_continuation_rate=Decimal("0.90"),
                continuation_window=5,
                min_samples=3,
            ),
        )
        cfg = await store.get_breaker_config(
            db_session, "BTCUSDT", Decimal("0.90")
        )
        # Threshold matches what screening found.
        assert cfg["critical_threshold"] == Decimal("4.0")
        # Resume fields present with tier-default values.
        from engine.grid.circuit_breaker import BreakerResumeMode
        assert cfg["resume_mode"] == BreakerResumeMode.WIDEN_STEP  # tier 90% default
        assert cfg["recovery_pct"] == Decimal("5.0")
        assert cfg["widen_multiplier"] == Decimal("2.0")
        assert cfg["min_continuation_rate"] == Decimal("0.90")
        assert cfg["used_fallback"] is False

    @pytest.mark.asyncio
    async def test_get_breaker_config_fallback_for_unscreened(
        self, store: BreakerScreeningStore, db_session: AsyncSession
    ) -> None:
        # ETHUSDT never screened → fallback threshold + legacy defaults.
        cfg = await store.get_breaker_config(
            db_session, "ETHUSDT", Decimal("0.90")
        )
        from engine.grid.circuit_breaker import BreakerResumeMode
        assert cfg["critical_threshold"] == Decimal("5.0")  # fallback for 0.90
        assert cfg["resume_mode"] == BreakerResumeMode.TA_CONFIRM
        assert cfg["recovery_pct"] == Decimal("5.0")
        assert cfg["widen_multiplier"] == Decimal("2.0")
        assert cfg["used_fallback"] is True

    @pytest.mark.asyncio
    async def test_get_breaker_config_tier_defaults_differ_by_rate(
        self, store: BreakerScreeningStore, db_session: AsyncSession
    ) -> None:
        # Screen BTC at all 3 rates.
        await store.rescreen_for_rates(
            db_session,
            ["BTCUSDT"],
            rates=[Decimal("0.70"), Decimal("0.80"), Decimal("0.90")],
            base_config=ScreenerConfig(continuation_window=5, min_samples=3),
        )
        from engine.grid.circuit_breaker import BreakerResumeMode
        # 70% → trailing_buy (recover quickly, conservative re-entry)
        cfg70 = await store.get_breaker_config(db_session, "BTCUSDT", Decimal("0.70"))
        assert cfg70["resume_mode"] == BreakerResumeMode.TRAILING_BUY
        # 80% → ta_confirm (middle ground)
        cfg80 = await store.get_breaker_config(db_session, "BTCUSDT", Decimal("0.80"))
        assert cfg80["resume_mode"] == BreakerResumeMode.TA_CONFIRM
        # 90% → widen_step (keep averaging, slower)
        cfg90 = await store.get_breaker_config(db_session, "BTCUSDT", Decimal("0.90"))
        assert cfg90["resume_mode"] == BreakerResumeMode.WIDEN_STEP

    @pytest.mark.asyncio
    async def test_update_resume_config_overrides_tier_default(
        self, store: BreakerScreeningStore, db_session: AsyncSession
    ) -> None:
        # Screen BTC at 0.90 → default resume_mode = widen_step.
        await store.rescreen_all(
            db_session,
            ["BTCUSDT"],
            config=ScreenerConfig(
                min_continuation_rate=Decimal("0.90"),
                continuation_window=5,
                min_samples=3,
            ),
        )
        # Admin overrides to trailing_buy with 10% recovery.
        repo = BreakerThresholdRepository(db_session)
        updated = await repo.update_resume_config(
            "binance", "BTCUSDT", Decimal("0.90"),
            resume_mode="trailing_buy",
            recovery_pct=Decimal("10.0"),
        )
        assert updated is not None
        assert updated.resume_mode == "trailing_buy"
        assert float(updated.recovery_pct) == 10.0

        # get_breaker_config should reflect the override, not tier default.
        cfg = await store.get_breaker_config(
            db_session, "BTCUSDT", Decimal("0.90")
        )
        from engine.grid.circuit_breaker import BreakerResumeMode
        assert cfg["resume_mode"] == BreakerResumeMode.TRAILING_BUY
        assert cfg["recovery_pct"] == Decimal("10.0")

    @pytest.mark.asyncio
    async def test_update_resume_config_returns_none_for_missing_row(
        self, db_session: AsyncSession
    ) -> None:
        repo = BreakerThresholdRepository(db_session)
        result = await repo.update_resume_config(
            "binance", "NONEXISTENT", Decimal("0.90"),
            resume_mode="trailing_buy",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_update_resume_config_partial_update(
        self, store: BreakerScreeningStore, db_session: AsyncSession
    ) -> None:
        # Screen BTC at 0.80 → default resume_mode = ta_confirm, recovery 5%.
        await store.rescreen_all(
            db_session,
            ["BTCUSDT"],
            config=ScreenerConfig(
                min_continuation_rate=Decimal("0.80"),
                continuation_window=5,
                min_samples=3,
            ),
        )
        # Only update widen_multiplier, leave others alone.
        repo = BreakerThresholdRepository(db_session)
        updated = await repo.update_resume_config(
            "binance", "BTCUSDT", Decimal("0.80"),
            widen_multiplier=Decimal("3.0"),
        )
        assert updated is not None
        assert float(updated.widen_multiplier) == 3.0
        # resume_mode unchanged (still ta_confirm from tier default).
        assert updated.resume_mode == "ta_confirm"
        assert float(updated.recovery_pct) == 5.0


class TestSetupBreakerForInstance:
    """Tests for setup_breaker_for_instance() — the convenience wrapper that
    reads the full breaker config from DB and installs it on the grid engine
    in one call. This is the production wiring point: call this when activating
    a trading instance so the breaker has the correct threshold + resume mode.
    """

    @pytest.mark.asyncio
    async def test_setup_installs_breaker_with_full_config(
        self, store: BreakerScreeningStore, db_session: AsyncSession
    ) -> None:
        # Screen BTC at 0.90 first so a row exists with tier defaults.
        await store.rescreen_all(
            db_session,
            ["BTCUSDT"],
            config=ScreenerConfig(
                min_continuation_rate=Decimal("0.90"),
                continuation_window=5,
                min_samples=3,
            ),
        )
        # Use a fake grid engine to capture the configure call.
        from engine.grid.circuit_breaker import BreakerResumeMode
        from unittest.mock import MagicMock

        fake_engine = MagicMock()
        cfg = await store.setup_breaker_for_instance(
            db=db_session,
            grid_engine=fake_engine,
            instance_id="inst-btc-1",
            symbol="BTCUSDT",
            min_continuation_rate=Decimal("0.90"),
        )
        # Config returned matches what was stored.
        assert cfg["critical_threshold"] == Decimal("4.0")
        assert cfg["resume_mode"] == BreakerResumeMode.WIDEN_STEP
        # configure_circuit_breaker was called with the full config.
        fake_engine.configure_circuit_breaker.assert_called_once()
        call_kwargs = fake_engine.configure_circuit_breaker.call_args.kwargs
        assert call_kwargs["instance_id"] == "inst-btc-1"
        assert call_kwargs["critical_threshold"] == Decimal("4.0")
        assert call_kwargs["resume_mode"] == BreakerResumeMode.WIDEN_STEP
        assert call_kwargs["recovery_pct"] == Decimal("5.0")
        assert call_kwargs["widen_multiplier"] == Decimal("2.0")

    @pytest.mark.asyncio
    async def test_setup_uses_fallback_for_unscreened_symbol(
        self, store: BreakerScreeningStore, db_session: AsyncSession
    ) -> None:
        # ETHUSDT never screened → fallback threshold + legacy defaults.
        from engine.grid.circuit_breaker import BreakerResumeMode
        from unittest.mock import MagicMock

        fake_engine = MagicMock()
        cfg = await store.setup_breaker_for_instance(
            db=db_session,
            grid_engine=fake_engine,
            instance_id="inst-eth-1",
            symbol="ETHUSDT",
            min_continuation_rate=Decimal("0.90"),
        )
        assert cfg["critical_threshold"] == Decimal("5.0")  # fallback for 0.90
        assert cfg["used_fallback"] is True
        # Even with fallback, breaker is still configured (never leave bot
        # unprotected).
        fake_engine.configure_circuit_breaker.assert_called_once()
        call_kwargs = fake_engine.configure_circuit_breaker.call_args.kwargs
        assert call_kwargs["critical_threshold"] == Decimal("5.0")
        assert call_kwargs["resume_mode"] == BreakerResumeMode.TA_CONFIRM

    @pytest.mark.asyncio
    async def test_setup_passes_day_open_price(
        self, store: BreakerScreeningStore, db_session: AsyncSession
    ) -> None:
        await store.rescreen_all(
            db_session,
            ["BTCUSDT"],
            config=ScreenerConfig(
                min_continuation_rate=Decimal("0.80"),
                continuation_window=5,
                min_samples=3,
            ),
        )
        from unittest.mock import MagicMock

        fake_engine = MagicMock()
        await store.setup_breaker_for_instance(
            db=db_session,
            grid_engine=fake_engine,
            instance_id="inst-btc-2",
            symbol="BTCUSDT",
            min_continuation_rate=Decimal("0.80"),
            day_open_price=Decimal("50000"),
        )
        call_kwargs = fake_engine.configure_circuit_breaker.call_args.kwargs
        assert call_kwargs["day_open_price"] == Decimal("50000")
