"""Internal reference — full descriptions of strategy options.

NOT served to the frontend. Kept here so the app owner can read the
exact mechanics behind each option. The frontend shows only labels
(Fearless/Balanced/Protective, TA Confirm/Widen Step/Trailing Buy, etc.)
without the verbose descriptions that explain the underlying logic.

Human-readable version (tables + formatting):
    docs/STRATEGY_REFERENCE.md

Strategy modes A/B/C full descriptions live in:
    backend/services/strategy_mode_store.py  (DEFAULT_STRATEGY_MODES)
"""

from __future__ import annotations

# ─── Circuit breaker: continuation rate (sensitivity tier) ──────────────
# Maps the continuation rate to the full Indonesian description that
# explains how the breaker decides when to stop buying.
CONTINUATION_RATES_FULL: dict[float, str] = {
    0.90: (
        "Bot tetap averaging selama mungkin. Baru berhenti beli kalau "
        "90% data historis mengatakan harga akan terus jatuh. Paling "
        "berani, paling sedikit false alarm."
    ),
    0.80: (
        "Butuh 80% keyakinan dari data historis sebelum bot berhenti "
        "beli. Seimbang antara aman dan tetap averaging."
    ),
    0.70: (
        "Cukup 70% yakin harga akan jatuh, bot sudah berhenti beli. "
        "Paling cepat keluar dari pasar — aman dari kerugian besar, "
        "tapi sering berhenti padahal harga cuma turun sebentar."
    ),
}

# ─── Resume behavior after the breaker triggers ─────────────────────────
# Maps the resume mode to the full description that explains what the
# bot does after the circuit breaker fires.
BREAKER_RESUME_MODES_FULL: dict[str, str] = {
    "ta_confirm": (
        "Stop buying. Resume only when 15m TA (RSI < 30 + MACD bullish "
        "cross) confirms a reversal. Most conservative."
    ),
    "widen_step": (
        "Keep averaging but with 2× wider grid spacing (buy at every "
        "2nd level). Slower accumulation into the drop."
    ),
    "trailing_buy": (
        "Stop buying. Resume when price recovers 5% from the intraday "
        "low. Conservative re-entry after a bounce."
    ),
}
