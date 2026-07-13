"""
Unit tests for SymbolRegistry.
"""

import pytest

from core.exceptions import SymbolNotSupported
from market.symbol_registry import SymbolRegistry


@pytest.fixture
def registry() -> SymbolRegistry:
    r = SymbolRegistry()
    r.register("binance", ["BTCUSDT", "ETHUSDT", "BNBUSDT"])
    r.register("bybit", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    return r


class TestSymbolRegistry:
    def test_normalize_uppercase(self, registry: SymbolRegistry) -> None:
        assert registry.normalize("btcusdt") == "BTCUSDT"
        assert registry.normalize("  ethusdt  ") == "ETHUSDT"

    def test_normalize_exchange_lowercase(self, registry: SymbolRegistry) -> None:
        assert registry.normalize_exchange("Binance") == "binance"
        assert registry.normalize_exchange("  BYBIT  ") == "bybit"

    def test_is_supported_true(self, registry: SymbolRegistry) -> None:
        assert registry.is_supported("binance", "BTCUSDT") is True
        assert registry.is_supported("bybit", "SOLUSDT") is True

    def test_is_supported_false(self, registry: SymbolRegistry) -> None:
        assert registry.is_supported("binance", "SOLUSDT") is False
        assert registry.is_supported("bybit", "BNBUSDT") is False

    def test_is_supported_case_insensitive(self, registry: SymbolRegistry) -> None:
        assert registry.is_supported("Binance", "btcusdt") is True
        assert registry.is_supported("BYBIT", "EthUSDT") is True

    def test_validate_success(self, registry: SymbolRegistry) -> None:
        result = registry.validate("binance", "btcusdt")
        assert result == "BTCUSDT"

    def test_validate_raises(self, registry: SymbolRegistry) -> None:
        with pytest.raises(SymbolNotSupported):
            registry.validate("binance", "DOGEUSDT")

    def test_get_symbols(self, registry: SymbolRegistry) -> None:
        symbols = registry.get_symbols("binance")
        assert symbols == ["BNBUSDT", "BTCUSDT", "ETHUSDT"]

    def test_get_symbols_empty(self, registry: SymbolRegistry) -> None:
        assert registry.get_symbols("hyperliquid") == []

    def test_get_exchanges(self, registry: SymbolRegistry) -> None:
        assert registry.get_exchanges() == ["binance", "bybit"]

    def test_unregister(self, registry: SymbolRegistry) -> None:
        registry.unregister("binance")
        assert registry.is_supported("binance", "BTCUSDT") is False
        assert registry.is_supported("bybit", "BTCUSDT") is True

    def test_register_additional(self, registry: SymbolRegistry) -> None:
        registry.register("binance", ["ADAUSDT"])
        assert registry.is_supported("binance", "ADAUSDT") is True
        assert registry.is_supported("binance", "BTCUSDT") is True
