# Beta Exit Criteria

**Date:** 2026-07-17  
**Phase:** Beta (operational validation)  
**Previous Tag:** v0.17.0-RC2  
**Target:** Go/No-Go review for v1.0.0

---

## Beta Scope

Beta adalah fase validasi operasional pada environment yang menyerupai production. Tidak ada perubahan kode besar. Yang dilakukan:

- Deploy ke staging dengan konfigurasi production-like
- Jalankan 72h soak test
- Jalankan sandbox/paper trading
- Kumpulkan telemetry nyata
- Verifikasi seluruh skenario trading
- Go/No-Go review

---

## Exit Criteria

Semua kriteria berikut harus terpenuhi sebelum Beta dinyatakan selesai:

| # | Criteria | Target | Status | Notes |
|---|----------|--------|--------|-------|
| 1 | Soak test | 72h tanpa memory/resource leak | ⬜ | Monitor: memory, fd, DB pool, WS count |
| 2 | No memory leak | Memory growth < 10% over 72h | ⬜ | `docker stats` trending |
| 3 | No duplicate orders | 0 duplicate across all scenarios | ⬜ | Idempotency via request_id |
| 4 | No orphan orders | 0 orphan after recovery | ⬜ | Reconciler detects none |
| 5 | Recovery after restart | RecoveryCoordinator restores state | ⬜ | Verified via /health and API |
| 6 | Backup & restore | Backup succeeds, restore verified | ⬜ | `pg_dump` + restore to test DB |
| 7 | Blue-green deployment | Switch without downtime | ⬜ | 0 5xx errors during switch |
| 8 | Rollback automatic | Rollback triggers on health failure | ⬜ | Simulate failure, verify rollback |
| 9 | Sandbox trading scenarios | All core scenarios pass | ⬜ | See scenario list below |
| 10 | No blocker bugs | 0 blocker or critical severity | ⬜ | Bug tracker verified |

---

## Sandbox Trading Scenarios

Setiap skenario harus lolos dengan verifikasi state consistency (local == exchange):

| # | Scenario | Status | Verification |
|---|----------|--------|--------------|
| 1 | Create order | ⬜ | Order appears on exchange + local tracker |
| 2 | Cancel order | ⬜ | Status = CANCELLED on both sides |
| 3 | Partial fill | ⬜ | Filled qty matches, remaining qty correct |
| 4 | Full fill | ⬜ | Status = FILLED, position updated |
| 5 | Reconnect after WS drop | ⬜ | Reconnect < 10s, no missed events |
| 6 | Restart server | ⬜ | Recovery restores all state |
| 7 | Recovery after crash | ⬜ | No duplicate/orphan orders |
| 8 | Profit lock (TP/SL) | ⬜ | TP/SL triggers at correct price |
| 9 | Full grid cycle | ⬜ | Buy → fill → sell → fill → profit |
| 10 | Risk rejection | ⬜ | Excessive order blocked by RiskManager |
| 11 | Multiple instances | ⬜ | 3+ instances run independently |
| 12 | Concurrent orders | ⬜ | 10+ concurrent orders, no race condition |

### State Consistency Checks (after each scenario)

| Check | Method | Status |
|-------|--------|--------|
| Orders match | Compare local tracker vs exchange API | ⬜ |
| Positions match | Compare portfolio vs exchange positions | ⬜ |
| PnL consistent | Local PnL vs exchange PnL | ⬜ |
| Exposure within limits | ExposureManager reports within RiskLimits | ⬜ |
| Grid state correct | GridState levels match actual orders | ⬜ |

---

## Monitoring During Beta

| Metric | Target | Alert Threshold | Status |
|--------|--------|-----------------|--------|
| Memory usage | < 1GB per container | > 90% of limit | ⬜ |
| CPU usage | < 70% average | > 90% sustained 5min | ⬜ |
| Response time p99 | < 500ms | > 1000ms | ⬜ |
| Error rate | < 0.1% | > 1% | ⬜ |
| WebSocket connections | Stable | Drop > 50% | ⬜ |
| DB connection pool | < 80% utilized | > 95% | ⬜ |
| Retry queue | Drains to 0 | > 100 stuck | ⬜ |
| Dead letter queue | No growth | Any new entry | ⬜ |
| Recovery events | Expected only | Unexpected recovery | ⬜ |

---

## Go/No-Go Review

Setelah semua exit criteria terpenuhi:

| Question | Answer | Status |
|----------|--------|--------|
| All 10 exit criteria met? | — | ⬜ |
| All 12 sandbox scenarios passed? | — | ⬜ |
| All state consistency checks passed? | — | ⬜ |
| No blocker/critical bugs open? | — | ⬜ |
| Soak test 72h clean? | — | ⬜ |
| Backup & restore verified? | — | ⬜ |
| Blue-green + rollback verified? | — | ⬜ |
| Monitoring & alerting active? | — | ⬜ |
| Team ready for go-live? | — | ⬜ |

**If all answers are YES → proceed to GO_LIVE.md checklist → tag v1.0.0**

**If any answer is NO → fix issues, re-run affected validation, re-review**

---

## Beta Duration

| Phase | Duration | Status | Start | End |
|-------|----------|--------|-------|-----|
| Initial deployment | 1h | ⬜ | — | — |
| Smoke test | 30min | ⬜ | — | — |
| Soak test | 72h | ⬜ | — | — |
| Sandbox trading | 48h (overlapping with soak) | ⬜ | — | — |
| Analysis & review | 4h | ⬜ | — | — |
| **Total** | ~96h | ⬜ | — | — |
