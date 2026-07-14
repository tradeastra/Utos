"""
Unit tests for ProfitPersistence.
"""

import uuid
from decimal import Decimal

from engine.profit_lock.persistence import ProfitPersistence
from engine.profit_lock.state import ProfitLockState, ProfitLockStatus


def _make_state() -> ProfitLockState:
    return ProfitLockState(
        instance_id="inst-1",
        status=ProfitLockStatus.TRIGGERED,
        enabled=True,
        trigger_percentage=Decimal("10"),
        trail_percentage=Decimal("5"),
        entry_price=Decimal("100"),
        quantity=Decimal("2"),
        side="long",
        highest_price=Decimal("115"),
        lock_price=Decimal("109.25"),
        is_triggered=True,
        is_executed=False,
        lock_order_id="order-123",
        exchange_account_id=uuid.UUID("12345678-1234-1234-1234-123456789012"),
        symbol="BTCUSDT",
    )


class TestProfitPersistenceSerialize:

    def test_serialize_returns_dict(self) -> None:
        state = _make_state()
        data = ProfitPersistence.serialize(state)
        assert isinstance(data, dict)
        assert data["instance_id"] == "inst-1"
        assert data["status"] == ProfitLockStatus.TRIGGERED
        assert data["enabled"] is True
        assert data["trigger_percentage"] == "10"
        assert data["trail_percentage"] == "5"
        assert data["entry_price"] == "100"
        assert data["quantity"] == "2"
        assert data["side"] == "long"
        assert data["highest_price"] == "115"
        assert data["lock_price"] == "109.25"
        assert data["is_triggered"] is True
        assert data["lock_order_id"] == "order-123"
        assert data["symbol"] == "BTCUSDT"

    def test_serialize_none_fields(self) -> None:
        state = _make_state()
        state.highest_price = None
        state.lock_price = None
        state.lock_order_id = None
        state.exchange_account_id = None
        data = ProfitPersistence.serialize(state)
        assert data["highest_price"] is None
        assert data["lock_price"] is None
        assert data["lock_order_id"] is None
        assert data["exchange_account_id"] is None


class TestProfitPersistenceDeserialize:

    def test_deserialize_roundtrip(self) -> None:
        state = _make_state()
        data = ProfitPersistence.serialize(state)
        restored = ProfitPersistence.deserialize(data)
        assert restored.instance_id == state.instance_id
        assert restored.status == state.status
        assert restored.enabled == state.enabled
        assert restored.trigger_percentage == state.trigger_percentage
        assert restored.trail_percentage == state.trail_percentage
        assert restored.entry_price == state.entry_price
        assert restored.quantity == state.quantity
        assert restored.side == state.side
        assert restored.highest_price == state.highest_price
        assert restored.lock_price == state.lock_price
        assert restored.is_triggered == state.is_triggered
        assert restored.is_executed == state.is_executed
        assert restored.lock_order_id == state.lock_order_id
        assert restored.exchange_account_id == state.exchange_account_id
        assert restored.symbol == state.symbol

    def test_deserialize_none_fields(self) -> None:
        state = _make_state()
        state.highest_price = None
        state.lock_price = None
        state.exchange_account_id = None
        data = ProfitPersistence.serialize(state)
        restored = ProfitPersistence.deserialize(data)
        assert restored.highest_price is None
        assert restored.lock_price is None
        assert restored.exchange_account_id is None


class TestProfitPersistenceJsonString:

    def test_to_json_and_from_json_roundtrip(self) -> None:
        state = _make_state()
        json_str = ProfitPersistence.to_json_string(state)
        restored = ProfitPersistence.from_json_string(json_str)
        assert restored.instance_id == state.instance_id
        assert restored.status == state.status
        assert restored.trigger_percentage == state.trigger_percentage
        assert restored.lock_price == state.lock_price
        assert restored.exchange_account_id == state.exchange_account_id
