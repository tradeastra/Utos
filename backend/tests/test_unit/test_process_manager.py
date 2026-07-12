"""Unit tests for TradingProcess, ProcessStateMachine, and TradingProcessManager."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.context import ProcessMemory
from core.exceptions import AuthenticationError, InvalidStateTransition
from core.types import ExchangeInfo, TradingInstanceStatus
from engine.trading.process import TradingProcess
from engine.trading.process_manager import TradingProcessManager
from engine.trading.state_machine import ProcessStateMachine


class FakeAdapter:
    """Minimal fake exchange adapter for process manager tests."""

    name = "binance"

    def __init__(self) -> None:
        self.config = None

    async def initialize(self, config: Any) -> bool:
        self.config = config
        return True

    async def authenticate(self, credentials: Any) -> bool:
        return True

    async def get_exchange_info(self) -> ExchangeInfo:
        return ExchangeInfo(
            name="binance",
            supported_symbols=["BTCUSDT"],
            rate_limits={},
            fee_structure={},
            server_time=datetime.now(tz=timezone.utc),
        )

    async def disconnect(self) -> bool:
        return True


class FakeCredentialManager:
    def decrypt(self, ciphertext: str) -> str:
        return ciphertext

    def encrypt(self, plaintext: str) -> str:
        return plaintext


@pytest.fixture
def fake_adapter() -> FakeAdapter:
    return FakeAdapter()


@pytest.fixture
def fake_credentials() -> FakeCredentialManager:
    return FakeCredentialManager()


@pytest.fixture
def manager(db_session: AsyncSession, fake_adapter: FakeAdapter, fake_credentials: FakeCredentialManager, monkeypatch: pytest.MonkeyPatch) -> TradingProcessManager:
    monkeypatch.setattr("exchanges.factory.ExchangeFactory.is_registered", lambda name: True)
    monkeypatch.setattr("exchanges.factory.ExchangeFactory.create", lambda name: fake_adapter)
    m = TradingProcessManager(
        db_session,
        credential_manager=fake_credentials,
    )
    return m


@pytest.mark.asyncio
async def test_state_machine_validates_allowed_transitions() -> None:
    ProcessStateMachine.validate_transition(TradingInstanceStatus.CREATED, TradingInstanceStatus.READY)
    ProcessStateMachine.validate_transition(TradingInstanceStatus.READY, TradingInstanceStatus.RUNNING)
    ProcessStateMachine.validate_transition(TradingInstanceStatus.RUNNING, TradingInstanceStatus.PAUSED)
    ProcessStateMachine.validate_transition(TradingInstanceStatus.PAUSED, TradingInstanceStatus.RUNNING)


@pytest.mark.asyncio
async def test_state_machine_rejects_invalid_transition() -> None:
    with pytest.raises(InvalidStateTransition):
        ProcessStateMachine.validate_transition(TradingInstanceStatus.CREATED, TradingInstanceStatus.RUNNING)


@pytest.mark.asyncio
async def test_state_machine_rejects_same_state_transition() -> None:
    with pytest.raises(InvalidStateTransition):
        ProcessStateMachine.validate_transition(TradingInstanceStatus.RUNNING, TradingInstanceStatus.RUNNING)


@pytest.mark.asyncio
async def test_trading_process_snapshot_and_restore(fake_adapter: FakeAdapter) -> None:
    memory = ProcessMemory(instance_id=str(uuid.uuid4()), status="running")
    process = TradingProcess(
        instance_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        exchange_account_id=uuid.uuid4(),
        strategy_id=uuid.uuid4(),
        symbol="BTCUSDT",
        exchange_name="binance",
        status=TradingInstanceStatus.RUNNING,
        adapter=fake_adapter,
        memory=memory,
        worker_id="worker1",
        lock_value="lock1",
        redis=None,
    )
    snapshot = process.snapshot()
    assert snapshot["symbol"] == "BTCUSDT"
    assert snapshot["status"] == "running"

    restored = TradingProcess.from_snapshot(snapshot, fake_adapter, redis=None)
    assert restored.symbol == "BTCUSDT"
    assert restored.status == TradingInstanceStatus.RUNNING


@pytest.mark.asyncio
async def test_create_process(manager: TradingProcessManager, create_trading_instance) -> None:
    instance = await create_trading_instance(manager.session)
    instance2 = await manager.create_process(
        user_id=instance.user_id,
        exchange_account_id=instance.exchange_account_id,
        strategy_id=instance.strategy_id,
        grid_profile_id=instance.grid_profile_id,
        symbol="ETHUSDT",
        start_price=100.0,
        total_investment=500.0,
        base_currency="ETH",
        quote_currency="USDT",
    )
    assert instance2.status == TradingInstanceStatus.CREATED
    assert instance2.symbol == "ETHUSDT"


@pytest.mark.asyncio
async def test_prepare_process(manager: TradingProcessManager, create_trading_instance) -> None:
    instance = await create_trading_instance(manager.session)
    prepared = await manager.prepare(instance.id, instance.user_id)
    assert prepared.status == TradingInstanceStatus.READY


@pytest.mark.asyncio
async def test_start_stop_process(manager: TradingProcessManager, create_trading_instance) -> None:
    instance = await create_trading_instance(manager.session)
    await manager.prepare(instance.id, instance.user_id)
    started = await manager.start(instance.id, instance.user_id)
    assert started.status == TradingInstanceStatus.RUNNING

    stopped = await manager.stop(instance.id, instance.user_id)
    assert stopped.status == TradingInstanceStatus.STOPPED


@pytest.mark.asyncio
async def test_pause_resume_process(manager: TradingProcessManager, create_trading_instance) -> None:
    instance = await create_trading_instance(manager.session)
    await manager.prepare(instance.id, instance.user_id)
    await manager.start(instance.id, instance.user_id)
    paused = await manager.pause(instance.id, instance.user_id)
    assert paused.status == TradingInstanceStatus.PAUSED

    resumed = await manager.resume(instance.id, instance.user_id)
    assert resumed.status == TradingInstanceStatus.RUNNING


@pytest.mark.asyncio
async def test_prepare_fails_for_wrong_user(manager: TradingProcessManager, create_trading_instance) -> None:
    instance = await create_trading_instance(manager.session)
    with pytest.raises(AuthenticationError):
        await manager.prepare(instance.id, uuid.uuid4())


@pytest.mark.asyncio
async def test_invalid_state_transition_is_rejected(manager: TradingProcessManager, create_trading_instance) -> None:
    instance = await create_trading_instance(manager.session)
    with pytest.raises(InvalidStateTransition):
        await manager.start(instance.id, instance.user_id)
