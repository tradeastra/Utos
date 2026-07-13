"""
Per-exchange symbol registry and normalization.

The registry keeps a list of supported symbols for each registered exchange
and normalizes incoming symbols (e.g. uppercase, base/quote extraction) so
that consumers never deal with exchange-specific formatting.
"""

from __future__ import annotations

from core.exceptions import SymbolNotSupported


class SymbolRegistry:
    """Exchange-agnostic symbol registry."""

    def __init__(self) -> None:
        self._symbols: dict[str, set[str]] = {}

    def normalize(self, symbol: str) -> str:
        """Normalize a symbol to uppercase canonical form."""
        return symbol.strip().upper()

    def normalize_exchange(self, exchange: str) -> str:
        """Normalize exchange name to lowercase canonical form."""
        return exchange.strip().lower()

    def register(self, exchange: str, symbols: list[str]) -> None:
        """Register supported symbols for an exchange."""
        key = self.normalize_exchange(exchange)
        if key not in self._symbols:
            self._symbols[key] = set()
        for symbol in symbols:
            self._symbols[key].add(self.normalize(symbol))

    def is_supported(self, exchange: str, symbol: str) -> bool:
        """Return True if the normalized symbol is supported by the exchange."""
        key = self.normalize_exchange(exchange)
        return key in self._symbols and self.normalize(symbol) in self._symbols[key]

    def validate(self, exchange: str, symbol: str) -> str:
        """Validate and return the normalized symbol, raising if unsupported."""
        normalized = self.normalize(symbol)
        if not self.is_supported(exchange, symbol):
            raise SymbolNotSupported(normalized, self.normalize_exchange(exchange))
        return normalized

    def get_symbols(self, exchange: str) -> list[str]:
        """Return sorted list of supported symbols for an exchange."""
        key = self.normalize_exchange(exchange)
        return sorted(self._symbols.get(key, set()))

    def get_exchanges(self) -> list[str]:
        """Return all registered exchanges."""
        return sorted(self._symbols.keys())

    def unregister(self, exchange: str) -> None:
        """Remove all symbols for an exchange."""
        self._symbols.pop(self.normalize_exchange(exchange), None)
