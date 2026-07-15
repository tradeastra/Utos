"""
AutomationRules — condition-based notification triggers.

Rules evaluate events and return actions for NotificationService to execute.
Does NOT send notifications directly.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AutomationRule:
    id: str
    name: str
    event_type: str
    condition: Callable[[dict[str, Any]], bool]
    action_channel: str
    action_template: str
    action_user_id: str = "system"
    enabled: bool = True
    trigger_count: int = 0


@dataclass
class AutomationAction:
    rule_id: str
    user_id: str
    channel: str
    template: str
    context: dict[str, Any]


class AutomationRules:
    """Evaluates events against rules and returns actions."""

    def __init__(self) -> None:
        self._rules: dict[str, AutomationRule] = {}
        self._metrics: dict[str, int] = {
            "rules_added": 0,
            "rules_removed": 0,
            "rules_triggered": 0,
            "rules_evaluated": 0,
        }

    def add_rule(
        self,
        name: str,
        event_type: str,
        condition: Callable[[dict[str, Any]], bool],
        action_channel: str,
        action_template: str,
        action_user_id: str = "system",
        enabled: bool = True,
    ) -> str:
        rule_id = str(uuid.uuid4())
        rule = AutomationRule(
            id=rule_id,
            name=name,
            event_type=event_type,
            condition=condition,
            action_channel=action_channel,
            action_template=action_template,
            action_user_id=action_user_id,
            enabled=enabled,
        )
        self._rules[rule_id] = rule
        self._metrics["rules_added"] += 1
        logger.info(
            "Automation rule added",
            extra={"rule_id": rule_id, "rule_name": name, "event_type": event_type},
        )
        return rule_id

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id not in self._rules:
            return False
        del self._rules[rule_id]
        self._metrics["rules_removed"] += 1
        return True

    def enable_rule(self, rule_id: str) -> bool:
        if rule_id not in self._rules:
            return False
        self._rules[rule_id].enabled = True
        return True

    def disable_rule(self, rule_id: str) -> bool:
        if rule_id not in self._rules:
            return False
        self._rules[rule_id].enabled = False
        return True

    async def evaluate(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> list[AutomationAction]:
        actions: list[AutomationAction] = []

        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if rule.event_type != event_type:
                continue

            self._metrics["rules_evaluated"] += 1

            try:
                if rule.condition(data):
                    rule.trigger_count += 1
                    self._metrics["rules_triggered"] += 1
                    actions.append(AutomationAction(
                        rule_id=rule.id,
                        user_id=rule.action_user_id,
                        channel=rule.action_channel,
                        template=rule.action_template,
                        context=data,
                    ))
                    logger.info(
                        "Automation rule triggered",
                        extra={"rule_id": rule.id, "rule_name": rule.name},
                    )
            except Exception as exc:
                logger.error(
                    f"Rule evaluation error: {exc}",
                    extra={"rule_id": rule.id, "rule_name": rule.name},
                )

        return actions

    def get_rules(self) -> list[AutomationRule]:
        return list(self._rules.values())

    def get_rule(self, rule_id: str) -> AutomationRule | None:
        return self._rules.get(rule_id)

    def get_rules_for_event(self, event_type: str) -> list[AutomationRule]:
        return [r for r in self._rules.values() if r.event_type == event_type and r.enabled]

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)
