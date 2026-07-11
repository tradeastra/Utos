"""
Exchange adapter factory — Sprint 3.

Responsible for registering and resolving concrete exchange adapters
by `ExchangeName` without coupling callers to specific implementations.
"""

from typing import Type

from core.logging import get_logger
from exchanges.adapter import IExchangeAdapter

logger = get_logger(__name__)


class ExchangeFactory:
    """Factory that registers and creates exchange adapters by name."""

    _registry: dict[str, Type[IExchangeAdapter]] = {}

    @classmethod
    def register(
        cls, exchange_name: str, adapter_class: Type[IExchangeAdapter]
    ) -> None:
        """Register an adapter class for the given exchange name."""
        cls._registry[exchange_name.lower()] = adapter_class
        logger.info(f"Registered adapter for {exchange_name}")

    @classmethod
    def create(cls, exchange_name: str) -> IExchangeAdapter:
        """Create an instance of the adapter registered for the exchange."""
        key = exchange_name.lower()
        adapter_class = cls._registry.get(key)
        if adapter_class is None:
            raise ValueError(f"No adapter registered for exchange: {exchange_name}")

        adapter = adapter_class()
        adapter.name = exchange_name
        logger.info(f"Created adapter for {exchange_name}")
        return adapter

    @classmethod
    def is_registered(cls, exchange_name: str) -> bool:
        """Return True if an adapter is registered for the exchange."""
        return exchange_name.lower() in cls._registry

    @classmethod
    def registered_exchanges(cls) -> list[str]:
        """Return a list of registered exchange names."""
        return list(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered adapters (mainly for tests)."""
        cls._registry.clear()
