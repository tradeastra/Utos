"""
Unit tests for GridPersistence.
"""

from decimal import Decimal

from core.types import GridLevel, GridLevelStatus, GridState
from engine.grid.persistence import GridPersistence
from engine.grid.state import GridStatus


def _make_state() -> GridState:
    return GridState(
        instance_id="inst-1",
        status=GridStatus.ACTIVE,
        upper_price=Decimal("100"),
        lower_price=Decimal("50"),
        grid_count=3,
        grid_spacing=Decimal("10"),
        investment_per_grid=Decimal("100"),
        levels=[
            GridLevel(
                level=0,
                buy_price=Decimal("50"),
                sell_price=Decimal("60"),
                quantity=Decimal("2"),
                buy_order_id="order-1",
                status=GridLevelStatus.OPEN,
            ),
            GridLevel(
                level=1,
                buy_price=Decimal("60"),
                sell_price=Decimal("70"),
                quantity=Decimal("1.67"),
                status=GridLevelStatus.WAITING,
            ),
            GridLevel(
                level=2,
                buy_price=Decimal("70"),
                sell_price=Decimal("80"),
                quantity=Decimal("1.43"),
                sell_order_id="order-2",
                status=GridLevelStatus.TP_HIT,
            ),
        ],
        total_cycles=5,
        total_profit=Decimal("42.50"),
        symbol="BTCUSDT",
        current_price=Decimal("65"),
    )


class TestGridPersistenceSerialize:

    def test_serialize_returns_dict(self) -> None:
        state = _make_state()
        data = GridPersistence.serialize(state)
        assert isinstance(data, dict)
        assert data["instance_id"] == "inst-1"
        assert data["status"] == GridStatus.ACTIVE
        assert data["upper_price"] == "100"
        assert data["lower_price"] == "50"
        assert data["grid_count"] == 3
        assert data["symbol"] == "BTCUSDT"
        assert data["total_cycles"] == 5
        assert data["total_profit"] == "42.50"
        assert len(data["levels"]) == 3

    def test_serialize_levels(self) -> None:
        state = _make_state()
        data = GridPersistence.serialize(state)
        lv0 = data["levels"][0]
        assert lv0["level"] == 0
        assert lv0["buy_price"] == "50"
        assert lv0["sell_price"] == "60"
        assert lv0["buy_order_id"] == "order-1"
        assert lv0["status"] == "open"

    def test_serialize_current_price_none(self) -> None:
        state = _make_state()
        state.current_price = None
        data = GridPersistence.serialize(state)
        assert data["current_price"] is None


class TestGridPersistenceDeserialize:

    def test_deserialize_roundtrip(self) -> None:
        state = _make_state()
        data = GridPersistence.serialize(state)
        restored = GridPersistence.deserialize(data)
        assert restored.instance_id == state.instance_id
        assert restored.status == state.status
        assert restored.upper_price == state.upper_price
        assert restored.lower_price == state.lower_price
        assert restored.grid_count == state.grid_count
        assert restored.grid_spacing == state.grid_spacing
        assert restored.investment_per_grid == state.investment_per_grid
        assert restored.total_cycles == state.total_cycles
        assert restored.total_profit == state.total_profit
        assert restored.symbol == state.symbol
        assert restored.current_price == state.current_price
        assert len(restored.levels) == len(state.levels)

    def test_deserialize_levels_roundtrip(self) -> None:
        state = _make_state()
        data = GridPersistence.serialize(state)
        restored = GridPersistence.deserialize(data)
        for orig, rest in zip(state.levels, restored.levels):
            assert rest.level == orig.level
            assert rest.buy_price == orig.buy_price
            assert rest.sell_price == orig.sell_price
            assert rest.quantity == orig.quantity
            assert rest.buy_order_id == orig.buy_order_id
            assert rest.sell_order_id == orig.sell_order_id
            assert rest.status == orig.status

    def test_deserialize_unknown_status_defaults_to_waiting(self) -> None:
        state = _make_state()
        data = GridPersistence.serialize(state)
        data["levels"][0]["status"] = "unknown_status"
        restored = GridPersistence.deserialize(data)
        assert restored.levels[0].status == GridLevelStatus.WAITING


class TestGridPersistenceJsonString:

    def test_to_json_and_from_json_roundtrip(self) -> None:
        state = _make_state()
        json_str = GridPersistence.to_json_string(state)
        restored = GridPersistence.from_json_string(json_str)
        assert restored.instance_id == state.instance_id
        assert restored.status == state.status
        assert len(restored.levels) == len(state.levels)
        assert restored.total_cycles == state.total_cycles
