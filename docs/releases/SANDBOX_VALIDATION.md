# Sandbox Trading Validation Report

**Version:** v0.17.0-RC2-attestation  
**Date:** _(fill on execution)_  
**Environment:** Staging (Exchange Sandbox)  
**Exchange:** _ (e.g. Binance Testnet)  

---

## 1. Test Configuration

| Item | Value |
|------|-------|
| Exchange | _ |
| Testnet/Sandbox | Yes |
| API key | Sandbox key (not production) |
| Trading instances | _ |
| Symbols tested | _ (e.g. BTCUSDT, ETHUSDT) |
| Grid strategy | Smart Grid |
| Test duration | _ hours |

---

## 2. Scenario Results

| # | Scenario | Orders Placed | Expected | Actual | State Consistent | Result | Notes |
|---|----------|---------------|----------|--------|------------------|--------|-------|
| 1 | Market buy | 1 | Order filled, position opened | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |
| 2 | Market sell | 1 | Order filled, position closed | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |
| 3 | Limit buy | 1 | Order placed, waiting for fill | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |
| 4 | Limit sell | 1 | Order placed, waiting for fill | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |
| 5 | Partial fill | 1 | Partial qty filled, remainder open | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |
| 6 | Cancel order | 1 | Status = CANCELLED on both sides | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |
| 7 | Duplicate ACK | 2 (same request_id) | Only 1 order created (idempotency) | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |
| 8 | WebSocket reconnect | 0 | Reconnect < 10s, no missed events | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |
| 9 | Process recovery | 0 | RecoveryCoordinator restores state | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |
| 10 | Profit lock (TP/SL) | 2 | TP triggers at target price | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |
| 11 | Full grid cycle | _ | Buy → fill → sell → fill → profit | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |
| 12 | Grid expansion | _ | New levels created at correct prices | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |
| 13 | Restart during open positions | 0 | All positions restored correctly | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |
| 14 | Risk rejection | 1 (excessive) | Order blocked by RiskManager | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |
| 15 | Multiple concurrent instances | _ | 3+ instances run independently | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |
| 16 | Concurrent orders | 10+ | No race condition, no duplicates | _ | ⬜ | ⬜ PASS / ⬜ FAIL | |

**Summary:** _ / 16 passed

---

## 3. State Consistency Verification

### Per-Scenario Checks

| # | Scenario | Orders Match | Positions Match | PnL Match | Exposure OK | Grid State OK |
|---|----------|-------------|-----------------|-----------|-------------|---------------|
| 1 | Market buy | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 2 | Market sell | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 3 | Limit buy | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 4 | Limit sell | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 5 | Partial fill | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 6 | Cancel order | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 7 | Duplicate ACK | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 8 | WS reconnect | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 9 | Process recovery | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 10 | Profit lock | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 11 | Full grid cycle | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 12 | Grid expansion | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 13 | Restart w/ positions | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 14 | Risk rejection | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 15 | Multiple instances | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 16 | Concurrent orders | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

### Verification Method

| Check | Method |
|-------|--------|
| Orders match | Compare local tracker vs `exchange.fetch_open_orders()` |
| Positions match | Compare portfolio vs `exchange.fetch_positions()` |
| PnL match | Compare local PnL vs exchange PnL |
| Exposure OK | `ExposureManager.get_exposure()` within `RiskLimits` |
| Grid state OK | `GridState.levels` match actual exchange orders |

---

## 4. Idempotency Verification

| Test | Request ID | Orders Created | Expected | Result |
|------|------------|----------------|----------|--------|
| Submit same order twice | _ | _ | 1 | ⬜ PASS / ⬜ FAIL |
| Resubmit after timeout | _ | _ | 1 | ⬜ PASS / ⬜ FAIL |
| Resubmit after reconnect | _ | _ | 1 | ⬜ PASS / ⬜ FAIL |

---

## 5. Recovery Verification

| Test | Trigger | Recovery Time | State After | Result |
|------|---------|---------------|-------------|--------|
| Server restart | `docker restart` | _ s | All state restored | ⬜ PASS / ⬜ FAIL |
| WebSocket drop | Network partition | _ s | Reconnected, no missed events | ⬜ PASS / ⬜ FAIL |
| Database reconnect | `pg_terminate_backend` | _ s | Pool recovered, no data loss | ⬜ PASS / ⬜ FAIL |
| Redis reconnect | `redis-cli flushall` | _ s | Cache rebuilt, no errors | ⬜ PASS / ⬜ FAIL |

---

## 6. Issues Encountered

| # | Issue | Scenario | Severity | Resolution | Status |
|---|-------|----------|----------|------------|--------|
| — | — | — | — | — | — |

---

## 7. Final Verdict

| Question | Answer |
|----------|--------|
| All 16 scenarios passed? | ⬜ Yes / ⬜ No |
| All state consistency checks passed? | ⬜ Yes / ⬜ No |
| Idempotency verified? | ⬜ Yes / ⬜ No |
| Recovery verified? | ⬜ Yes / ⬜ No |
| No duplicate orders? | ⬜ Yes / ⬜ No |
| No orphan orders? | ⬜ Yes / ⬜ No |
| No data loss after recovery? | ⬜ Yes / ⬜ No |

**Sandbox validation verdict:** ⬜ PASS — proceed to Go/No-Go / ⬜ FAIL — investigate and fix

---

## 8. Sign-off

| Role | Name | Decision | Date |
|------|------|----------|------|
| Engineering | _ | ⬜ Pass / ⬜ Fail | _ |
| QA | _ | ⬜ Pass / ⬜ Fail | _ |
| Trading/Strategy | _ | ⬜ Pass / ⬜ Fail | _ |
