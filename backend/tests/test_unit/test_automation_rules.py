"""Unit tests for AutomationRules."""

import pytest
from engine.notification.automation import AutomationRules


class TestAddRemoveRule:

    def test_add_rule(self) -> None:
        rules = AutomationRules()
        rule_id = rules.add_rule(
            "profit_alert",
            "ORDER_FILLED",
            lambda d: True,
            "telegram",
            "order_filled",
        )
        assert isinstance(rule_id, str)
        assert len(rules.get_rules()) == 1
        assert rules.get_metrics()["rules_added"] == 1

    def test_remove_rule(self) -> None:
        rules = AutomationRules()
        rule_id = rules.add_rule(
            "test", "TEST", lambda d: True, "telegram", "order_filled"
        )
        assert rules.remove_rule(rule_id) is True
        assert len(rules.get_rules()) == 0
        assert rules.get_metrics()["rules_removed"] == 1

    def test_remove_nonexistent(self) -> None:
        rules = AutomationRules()
        assert rules.remove_rule("fake") is False

    def test_enable_disable(self) -> None:
        rules = AutomationRules()
        rule_id = rules.add_rule(
            "test", "TEST", lambda d: True, "telegram", "order_filled"
        )
        assert rules.disable_rule(rule_id) is True
        assert rules.get_rule(rule_id).enabled is False
        assert rules.enable_rule(rule_id) is True
        assert rules.get_rule(rule_id).enabled is True


class TestEvaluate:

    @pytest.mark.asyncio
    async def test_evaluate_matching_rule(self) -> None:
        rules = AutomationRules()
        rules.add_rule(
            "profit_alert",
            "ORDER_FILLED",
            lambda d: float(d.get("profit_pct", 0)) > 10,
            "telegram",
            "order_filled",
        )
        actions = await rules.evaluate("ORDER_FILLED", {"profit_pct": 15})
        assert len(actions) == 1
        assert actions[0].channel == "telegram"
        assert actions[0].template == "order_filled"
        assert rules.get_metrics()["rules_triggered"] == 1

    @pytest.mark.asyncio
    async def test_evaluate_condition_false(self) -> None:
        rules = AutomationRules()
        rules.add_rule(
            "profit_alert",
            "ORDER_FILLED",
            lambda d: float(d.get("profit_pct", 0)) > 10,
            "telegram",
            "order_filled",
        )
        actions = await rules.evaluate("ORDER_FILLED", {"profit_pct": 5})
        assert len(actions) == 0
        assert rules.get_metrics()["rules_triggered"] == 0

    @pytest.mark.asyncio
    async def test_evaluate_wrong_event_type(self) -> None:
        rules = AutomationRules()
        rules.add_rule(
            "test", "ORDER_FILLED", lambda d: True, "telegram", "order_filled"
        )
        actions = await rules.evaluate("PRICE_UPDATE", {"v": 1})
        assert len(actions) == 0

    @pytest.mark.asyncio
    async def test_evaluate_disabled_rule(self) -> None:
        rules = AutomationRules()
        rule_id = rules.add_rule(
            "test", "TEST", lambda d: True, "telegram", "order_filled"
        )
        rules.disable_rule(rule_id)
        actions = await rules.evaluate("TEST", {"v": 1})
        assert len(actions) == 0

    @pytest.mark.asyncio
    async def test_evaluate_multiple_rules(self) -> None:
        rules = AutomationRules()
        rules.add_rule("r1", "ORDER_FILLED", lambda d: True, "telegram", "order_filled")
        rules.add_rule("r2", "ORDER_FILLED", lambda d: True, "email", "order_filled")
        actions = await rules.evaluate("ORDER_FILLED", {"v": 1})
        assert len(actions) == 2

    @pytest.mark.asyncio
    async def test_evaluate_condition_exception(self) -> None:
        rules = AutomationRules()

        def bad_condition(d: dict) -> bool:
            raise RuntimeError("eval error")

        rules.add_rule("bad", "TEST", bad_condition, "telegram", "order_filled")
        actions = await rules.evaluate("TEST", {"v": 1})
        assert len(actions) == 0


class TestQueries:

    def test_get_rules_for_event(self) -> None:
        rules = AutomationRules()
        rules.add_rule("r1", "ORDER_FILLED", lambda d: True, "telegram", "order_filled")
        rules.add_rule("r2", "PRICE_UPDATE", lambda d: True, "telegram", "order_filled")
        order_rules = rules.get_rules_for_event("ORDER_FILLED")
        assert len(order_rules) == 1

    @pytest.mark.asyncio
    async def test_trigger_count_incremented(self) -> None:
        rules = AutomationRules()
        rule_id = rules.add_rule(
            "test", "TEST", lambda d: True, "telegram", "order_filled"
        )
        await rules.evaluate("TEST", {"v": 1})
        await rules.evaluate("TEST", {"v": 2})
        rule = rules.get_rule(rule_id)
        assert rule.trigger_count == 2
