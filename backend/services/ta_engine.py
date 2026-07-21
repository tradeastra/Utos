"""
TAEngine — Technical Analysis evaluation service.

Evaluates configured indicators (RSI, MACD, Bollinger Bands, etc.) and returns
a gate decision: should the GridEngine place a buy order or not?

The TA engine is purely computational. It receives candle/OHLCV data and
indicator configs, then returns pass/fail per indicator and a combined result
based on the AND/OR operator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from core.domain_types import TAOperator
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class IndicatorResult:
    """Result of a single indicator evaluation."""
    indicator: str
    passed: bool
    value: float | None = None
    detail: str = ""


@dataclass
class TAGateResult:
    """Combined result of all TA indicators for a gate decision."""
    passed: bool
    operator: str
    results: list[IndicatorResult] = field(default_factory=list)

    @property
    def summary(self) -> str:
        parts = [f"{r.indicator}={'PASS' if r.passed else 'FAIL'}" for r in self.results]
        return f"TA Gate ({self.operator.upper()}): {' | '.join(parts)} → {'PASS' if self.passed else 'FAIL'}"


class TAEngine:
    """Evaluate technical analysis indicators as a gate before order placement."""

    def evaluate(
        self,
        configs: list[dict[str, Any]],
        candle_data: list[dict[str, Any]],
        current_price: Decimal,
    ) -> TAGateResult:
        """Evaluate all configured TA indicators against candle data.

        Args:
            configs: List of TA config dicts with keys: indicator, time_frame,
                     operator, params, enabled
            candle_data: List of OHLCV candles (newest first or oldest first,
                         individual indicators handle ordering)
            current_price: Current market price

        Returns:
            TAGateResult with combined pass/fail decision
        """
        enabled_configs = [c for c in configs if c.get("enabled", True)]
        if not enabled_configs:
            return TAGateResult(passed=True, operator="none", results=[])

        # Determine the combining operator from the first config
        operator = enabled_configs[0].get("operator", TAOperator.AND.value)

        results: list[IndicatorResult] = []
        for config in enabled_configs:
            indicator = config["indicator"]
            params = config.get("params", {})
            try:
                result = self._evaluate_indicator(indicator, params, candle_data, current_price)
                results.append(result)
            except Exception as exc:
                logger.warning(
                    f"TA indicator {indicator} evaluation failed: {exc}",
                    extra={"indicator": indicator, "error": str(exc)},
                )
                results.append(IndicatorResult(
                    indicator=indicator,
                    passed=False,
                    detail=f"Evaluation error: {exc}",
                ))

        # Combine results
        if operator == TAOperator.AND.value:
            passed = all(r.passed for r in results)
        else:  # OR
            passed = any(r.passed for r in results)

        logger.info(
            "TA gate evaluated",
            extra={
                "operator": operator,
                "passed": passed,
                "indicators": [r.indicator for r in results],
            },
        )

        return TAGateResult(passed=passed, operator=operator, results=results)

    def _evaluate_indicator(
        self,
        indicator: str,
        params: dict[str, Any],
        candles: list[dict[str, Any]],
        current_price: Decimal,
    ) -> IndicatorResult:
        """Dispatch to the correct indicator evaluator."""
        if indicator == "rsi":
            return self._eval_rsi(params, candles)
        elif indicator == "macd":
            return self._eval_macd(params, candles)
        elif indicator == "bollinger_bands":
            return self._eval_bollinger(params, candles, current_price)
        elif indicator == "fibonacci_retracement":
            return self._eval_fibonacci(params, candles, current_price)
        elif indicator == "ema_crossover":
            return self._eval_ema_crossover(params, candles)
        elif indicator == "sma_crossover":
            return self._eval_sma_crossover(params, candles)
        elif indicator == "stochastic":
            return self._eval_stochastic(params, candles)
        elif indicator == "atr":
            return self._eval_atr(params, candles)
        else:
            return IndicatorResult(
                indicator=indicator,
                passed=True,
                detail=f"Unknown indicator {indicator}, defaulting to pass",
            )

    # ─── Individual indicator implementations ──────────────────────

    def _eval_rsi(self, params: dict, candles: list[dict]) -> IndicatorResult:
        """RSI: pass if RSI is below oversold threshold (buy signal)."""
        period = params.get("period", 14)
        oversold = params.get("oversold", 30)
        overbought = params.get("overbought", 70)

        closes = [float(c["close"]) for c in candles if "close" in c]
        if len(closes) < period + 1:
            return IndicatorResult("rsi", False, detail=f"Insufficient data ({len(closes)} < {period + 1})")

        rsi = self._calculate_rsi(closes, period)
        passed = rsi < oversold

        return IndicatorResult(
            "rsi", passed, value=round(rsi, 2),
            detail=f"RSI={rsi:.2f} {'< oversold' if passed else '>= oversold'} ({oversold})",
        )

    def _calculate_rsi(self, closes: list[float], period: int) -> float:
        """Calculate RSI from closing prices."""
        if len(closes) < period + 1:
            return 50.0

        gains = []
        losses = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _eval_macd(self, params: dict, candles: list[dict]) -> IndicatorResult:
        """MACD: pass if MACD line crosses above signal line (bullish)."""
        fast = params.get("fast_period", 12)
        slow = params.get("slow_period", 26)
        signal = params.get("signal_period", 9)

        closes = [float(c["close"]) for c in candles if "close" in c]
        if len(closes) < slow + signal:
            return IndicatorResult("macd", False, detail=f"Insufficient data ({len(closes)} < {slow + signal})")

        macd_line, signal_line = self._calculate_macd(closes, fast, slow, signal)
        passed = macd_line > signal_line

        return IndicatorResult(
            "macd", passed, value=round(macd_line, 6),
            detail=f"MACD={macd_line:.6f} Signal={signal_line:.6f} {'bullish' if passed else 'bearish'}",
        )

    def _calculate_macd(self, closes: list[float], fast: int, slow: int, signal: int) -> tuple[float, float]:
        """Calculate MACD line and signal line."""
        ema_fast = self._calculate_ema(closes, fast)
        ema_slow = self._calculate_ema(closes, slow)
        macd_values = [f - s for f, s in zip(ema_fast, ema_slow)]
        signal_values = self._calculate_ema(macd_values, signal)

        return macd_values[-1], signal_values[-1]

    def _calculate_ema(self, values: list[float], period: int) -> list[float]:
        """Calculate EMA for a series of values."""
        if len(values) < period:
            return [values[-1]] if values else [0.0]

        multiplier = 2.0 / (period + 1)
        ema = [sum(values[:period]) / period]
        for i in range(period, len(values)):
            ema.append((values[i] - ema[-1]) * multiplier + ema[-1])
        return ema

    def _eval_bollinger(self, params: dict, candles: list[dict], current_price: Decimal) -> IndicatorResult:
        """Bollinger Bands: pass if price is below lower band (oversold)."""
        period = params.get("period", 20)
        std_dev = params.get("std_dev", 2)

        closes = [float(c["close"]) for c in candles if "close" in c]
        if len(closes) < period:
            return IndicatorResult("bollinger_bands", False, detail=f"Insufficient data ({len(closes)} < {period})")

        sma = sum(closes[-period:]) / period
        variance = sum((c - sma) ** 2 for c in closes[-period:]) / period
        stddev = variance ** 0.5
        lower_band = sma - std_dev * stddev
        upper_band = sma + std_dev * stddev

        price = float(current_price)
        passed = price < lower_band

        return IndicatorResult(
            "bollinger_bands", passed, value=round(price, 6),
            detail=f"Price={price:.6f} Lower={lower_band:.6f} Upper={upper_band:.6f} "
                   f"{'below lower' if passed else 'within/above bands'}",
        )

    def _eval_fibonacci(self, params: dict, candles: list[dict], current_price: Decimal) -> IndicatorResult:
        """Fibonacci Retracement: pass if price is near a key retracement level."""
        lookback = params.get("lookback", 100)
        tolerance = params.get("tolerance", 0.02)  # 2% tolerance

        closes = [float(c["close"]) for c in candles if "close" in c]
        if len(closes) < 10:
            return IndicatorResult("fibonacci_retracement", False, detail="Insufficient data")

        recent = closes[-lookback:] if len(closes) >= lookback else closes
        high = max(recent)
        low = min(recent)
        diff = high - low
        if diff == 0:
            return IndicatorResult("fibonacci_retracement", False, detail="Zero range")

        # Key Fibonacci levels
        fib_levels = {
            "0.236": low + diff * 0.236,
            "0.382": low + diff * 0.382,
            "0.500": low + diff * 0.500,
            "0.618": low + diff * 0.618,
            "0.786": low + diff * 0.786,
        }

        price = float(current_price)
        nearest_level = min(fib_levels.items(), key=lambda x: abs(x[1] - price))
        distance_pct = abs(nearest_level[1] - price) / price
        passed = distance_pct <= tolerance

        return IndicatorResult(
            "fibonacci_retracement", passed, value=round(price, 6),
            detail=f"Price={price:.6f} near Fib {nearest_level[0]}={nearest_level[1]:.6f} "
                   f"dist={distance_pct:.4f} {'within tolerance' if passed else 'outside tolerance'}",
        )

    def _eval_ema_crossover(self, params: dict, candles: list[dict]) -> IndicatorResult:
        """EMA Crossover: pass if fast EMA is above slow EMA (bullish)."""
        fast_period = params.get("fast_period", 9)
        slow_period = params.get("slow_period", 21)

        closes = [float(c["close"]) for c in candles if "close" in c]
        if len(closes) < slow_period:
            return IndicatorResult("ema_crossover", False, detail=f"Insufficient data ({len(closes)} < {slow_period})")

        ema_fast = self._calculate_ema(closes, fast_period)
        ema_slow = self._calculate_ema(closes, slow_period)

        passed = ema_fast[-1] > ema_slow[-1]

        return IndicatorResult(
            "ema_crossover", passed, value=round(ema_fast[-1], 6),
            detail=f"EMA{fast_period}={ema_fast[-1]:.6f} EMA{slow_period}={ema_slow[-1]:.6f} "
                   f"{'bullish cross' if passed else 'bearish cross'}",
        )

    def _eval_sma_crossover(self, params: dict, candles: list[dict]) -> IndicatorResult:
        """SMA Crossover: pass if fast SMA is above slow SMA (bullish)."""
        fast_period = params.get("fast_period", 9)
        slow_period = params.get("slow_period", 21)

        closes = [float(c["close"]) for c in candles if "close" in c]
        if len(closes) < slow_period:
            return IndicatorResult("sma_crossover", False, detail=f"Insufficient data ({len(closes)} < {slow_period})")

        sma_fast = sum(closes[-fast_period:]) / fast_period
        sma_slow = sum(closes[-slow_period:]) / slow_period

        passed = sma_fast > sma_slow

        return IndicatorResult(
            "sma_crossover", passed, value=round(sma_fast, 6),
            detail=f"SMA{fast_period}={sma_fast:.6f} SMA{slow_period}={sma_slow:.6f} "
                   f"{'bullish cross' if passed else 'bearish cross'}",
        )

    def _eval_stochastic(self, params: dict, candles: list[dict]) -> IndicatorResult:
        """Stochastic Oscillator: pass if %K is below oversold threshold."""
        k_period = params.get("k_period", 14)
        d_period = params.get("d_period", 3)
        oversold = params.get("oversold", 20)

        highs = [float(c["high"]) for c in candles if "high" in c]
        lows = [float(c["low"]) for c in candles if "low" in c]
        closes = [float(c["close"]) for c in candles if "close" in c]

        if len(closes) < k_period:
            return IndicatorResult("stochastic", False, detail=f"Insufficient data ({len(closes)} < {k_period})")

        recent_high = max(highs[-k_period:])
        recent_low = min(lows[-k_period:])
        if recent_high == recent_low:
            return IndicatorResult("stochastic", False, detail="Zero range")

        k_value = ((closes[-1] - recent_low) / (recent_high - recent_low)) * 100
        # Simple %D as SMA of %K
        k_values = []
        for i in range(max(k_period, len(closes) - d_period * k_period), len(closes)):
            if i >= k_period:
                h = max(highs[i - k_period:i])
                l = min(lows[i - k_period:i])
                if h != l:
                    k_values.append(((closes[i] - l) / (h - l)) * 100)

        d_value = sum(k_values[-d_period:]) / d_period if len(k_values) >= d_period else k_value
        passed = k_value < oversold

        return IndicatorResult(
            "stochastic", passed, value=round(k_value, 2),
            detail=f"%K={k_value:.2f} %D={d_value:.2f} {'< oversold' if passed else '>= oversold'} ({oversold})",
        )

    def _eval_atr(self, params: dict, candles: list[dict]) -> IndicatorResult:
        """ATR: pass if current volatility is within acceptable range."""
        period = params.get("period", 14)
        max_multiplier = params.get("max_multiplier", 3.0)  # Max ATR as multiple of average

        highs = [float(c["high"]) for c in candles if "high" in c]
        lows = [float(c["low"]) for c in candles if "low" in c]
        closes = [float(c["close"]) for c in candles if "close" in c]

        if len(closes) < period + 1:
            return IndicatorResult("atr", False, detail=f"Insufficient data ({len(closes)} < {period + 1})")

        true_ranges = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            true_ranges.append(tr)

        atr = sum(true_ranges[-period:]) / period
        avg_atr = sum(true_ranges) / len(true_ranges) if true_ranges else atr
        passed = atr <= avg_atr * max_multiplier

        return IndicatorResult(
            "atr", passed, value=round(atr, 6),
            detail=f"ATR={atr:.6f} AvgATR={avg_atr:.6f} {'within range' if passed else 'excessive volatility'}",
        )


# Default indicator parameter templates
DEFAULT_INDICATOR_PARAMS = {
    "rsi": {"period": 14, "oversold": 30, "overbought": 70},
    "macd": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
    "bollinger_bands": {"period": 20, "std_dev": 2},
    "fibonacci_retracement": {"lookback": 100, "tolerance": 0.02},
    "ema_crossover": {"fast_period": 9, "slow_period": 21},
    "sma_crossover": {"fast_period": 9, "slow_period": 21},
    "stochastic": {"k_period": 14, "d_period": 3, "oversold": 20},
    "atr": {"period": 14, "max_multiplier": 3.0},
}


def get_indicator_descriptions() -> list[dict]:
    """Return descriptions of all available indicators."""
    return [
        {"indicator": "rsi", "label": "RSI", "description": "Relative Strength Index — oversold/bought momentum", "default_params": DEFAULT_INDICATOR_PARAMS["rsi"]},
        {"indicator": "macd", "label": "MACD", "description": "Moving Average Convergence Divergence — trend momentum", "default_params": DEFAULT_INDICATOR_PARAMS["macd"]},
        {"indicator": "bollinger_bands", "label": "Bollinger Bands", "description": "Volatility bands — price below lower band = oversold", "default_params": DEFAULT_INDICATOR_PARAMS["bollinger_bands"]},
        {"indicator": "fibonacci_retracement", "label": "Fibonacci Retracement", "description": "Key retracement levels — price near support levels", "default_params": DEFAULT_INDICATOR_PARAMS["fibonacci_retracement"]},
        {"indicator": "ema_crossover", "label": "EMA Crossover", "description": "Exponential MA crossover — fast above slow = bullish", "default_params": DEFAULT_INDICATOR_PARAMS["ema_crossover"]},
        {"indicator": "sma_crossover", "label": "SMA Crossover", "description": "Simple MA crossover — fast above slow = bullish", "default_params": DEFAULT_INDICATOR_PARAMS["sma_crossover"]},
        {"indicator": "stochastic", "label": "Stochastic", "description": "Stochastic Oscillator — %K below oversold threshold", "default_params": DEFAULT_INDICATOR_PARAMS["stochastic"]},
        {"indicator": "atr", "label": "ATR", "description": "Average True Range — volatility filter", "default_params": DEFAULT_INDICATOR_PARAMS["atr"]},
    ]
