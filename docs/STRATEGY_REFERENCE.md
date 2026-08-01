# Strategy Reference (Internal)

> **Internal — NOT served to frontend.** Kept here so the app owner can read the exact mechanics behind each strategy option. The frontend shows only labels (Fearless/Balanced/Protective, TA Confirm/Widen Step/Trailing Buy, Hyper/Aggressive/Balanced) without the verbose descriptions.

Source of truth (Python): [`backend/internal/strategy_reference.py`](../backend/internal/strategy_reference.py)
Strategy modes A/B/C source: [`backend/services/strategy_mode_store.py`](../backend/services/strategy_mode_store.py) (`DEFAULT_STRATEGY_MODES`) + DB table `strategy_modes`

---

## Circuit Breaker — Continuation Rate (Sensitivity Tier)

The breaker decides when to stop buying based on how often a drop historically continued to fall.

| Rate  | Label       | Full Description                                                                                                                                                |
| ----- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0.90  | Fearless    | Bot tetap averaging selama mungkin. Baru berhenti beli kalau 90% data historis mengatakan harga akan terus jatuh. Paling berani, paling sedikit false alarm.    |
| 0.80  | Balanced    | Butuh 80% keyakinan dari data historis sebelum bot berhenti beli. Seimbang antara aman dan tetap averaging.                                                     |
| 0.70  | Protective  | Cukup 70% yakin harga akan jatuh, bot sudah berhenti beli. Paling cepat keluar dari pasar — aman dari kerugian besar, tapi sering berhenti padahal harga cuma turun sebentar. |

---

## Resume Behavior (After Breaker Triggers)

Controls when buying resumes after the circuit breaker fires.

| Value          | Label                                 | Full Description                                                                                                                       |
| -------------- | ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `ta_confirm`   | TA Confirm — wait for reversal        | Stop buying. Resume only when 15m TA (RSI < 30 + MACD bullish cross) confirms a reversal. Most conservative.                          |
| `widen_step`   | Widen Step — keep buying, slower      | Keep averaging but with 2× wider grid spacing (buy at every 2nd level). Slower accumulation into the drop.                            |
| `trailing_buy` | Trailing Buy — resume on recovery     | Stop buying. Resume when price recovers 5% from the intraday low. Conservative re-entry after a bounce.                               |

### Conditional Parameters

- **Recovery %** (trailing_buy): Resume buying when price recovers this percentage from the intraday low. Lower = resume sooner (more aggressive). Higher = wait for a stronger bounce.
- **Widen Multiplier** (widen_step): Multiply the grid spacing by this factor while the breaker is active. 2 = buy at every 2nd level (2× wider). 3 = every 3rd level. Higher = slower accumulation.

---

## Strategy Modes (A / B / C)

Source: `backend/services/strategy_mode_store.py` → `DEFAULT_STRATEGY_MODES` + DB table `strategy_modes`.

| Mode | Label       | TP Range   | Risk Level        | Full Description                                                                                                                       |
| ---- | ----------- | ---------- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| A    | Hyper       | 0.0–0.3%   | Very Aggressive   | Tightest grid (0.3% spacing). Maximum trade frequency — many small profits, fast capital rotation. Best for ranging markets. TP 0.75% per level.   |
| B    | Aggressive  | 0.0–0.6%   | Aggressive        | Tight grid (0.6% spacing). High trade frequency with moderate profit per level. Good for normal volatility. TP 1.5% per level.                     |
| C    | Balanced    | 0.0–0.9%   | Balanced          | Moderate grid (0.9% spacing). Balanced trade frequency and profit. General-purpose mode. TP 2.25% per level.                                        |

---

## Notes

- Frontend labels are preserved so users still understand the risk context (e.g. "Fearless" implies higher risk) without seeing the underlying mechanics.
- API `listStrategyModes` still serves the `description` field from the DB; the frontend simply does not render it. For full protection, strip `description` in the endpoint (follow-up, out of current scope).
- Source-level comments in frontend code still describe the logic — this obfuscation is for the UI only, not source-level protection.
