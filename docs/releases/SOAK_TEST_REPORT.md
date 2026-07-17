# Soak Test Report

**Version:** v0.17.0-RC2-attestation  
**Start:** _(fill on execution)_  
**End:** _(fill on execution)_  
**Duration:** 72 hours (target)  
**Environment:** Staging  

---

## 1. Test Configuration

| Item | Value |
|------|-------|
| Start time | _ |
| End time | _ |
| Actual duration | _ hours |
| Active slot | _ (blue / green) |
| Trading instances | _ |
| Exchange mode | Sandbox / Paper trading |
| Monitoring interval | 60 seconds |

---

## 2. Summary Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Uptime | 100% | _ % | ⬜ |
| Memory growth | < 10% over 72h | _ % | ⬜ |
| CPU average | < 70% | _ % | ⬜ |
| Response time p99 | < 500ms | _ ms | ⬜ |
| Response time p95 | < 300ms | _ ms | ⬜ |
| Error rate | < 0.1% | _ % | ⬜ |
| WebSocket reconnects | < 5 | _ | ⬜ |
| Unexpected restarts | 0 | _ | ⬜ |
| OOM kills | 0 | _ | ⬜ |
| Duplicate orders | 0 | _ | ⬜ |
| Orphan orders | 0 | _ | ⬜ |
| Recovery events (unexpected) | 0 | _ | ⬜ |

---

## 3. Memory Trend

| Timestamp | Backend RSS | Frontend RSS | Redis | PostgreSQL |
|-----------|-------------|--------------|-------|------------|
| 0h | _ MB | _ MB | _ MB | _ MB |
| 6h | _ MB | _ MB | _ MB | _ MB |
| 12h | _ MB | _ MB | _ MB | _ MB |
| 24h | _ MB | _ MB | _ MB | _ MB |
| 36h | _ MB | _ MB | _ MB | _ MB |
| 48h | _ MB | _ MB | _ MB | _ MB |
| 60h | _ MB | _ MB | _ MB | _ MB |
| 72h | _ MB | _ MB | _ MB | _ MB |

**Growth analysis:**
- Backend: _% over 72h
- Frontend: _% over 72h
- Verdict: ⬜ No leak / ⬜ Leak detected

---

## 4. CPU Trend

| Timestamp | Backend CPU | Frontend CPU | Redis CPU | PostgreSQL CPU |
|-----------|-------------|--------------|-----------|----------------|
| 0h | _ % | _ % | _ % | _ % |
| 24h | _ % | _ % | _ % | _ % |
| 48h | _ % | _ % | _ % | _ % |
| 72h | _ % | _ % | _ % | _ % |

**Verdict:** ⬜ Stable / ⬜ Degradation detected

---

## 5. Latency Trend

| Timestamp | p50 | p95 | p99 | Max |
|-----------|-----|-----|-----|-----|
| 0h | _ ms | _ ms | _ ms | _ ms |
| 24h | _ ms | _ ms | _ ms | _ ms |
| 48h | _ ms | _ ms | _ ms | _ ms |
| 72h | _ ms | _ ms | _ ms | _ ms |

**Verdict:** ⬜ Stable / ⬜ Degradation detected

---

## 6. Connection Stability

| Metric | Target | 0h | 24h | 48h | 72h | Status |
|--------|--------|----|-----|-----|-----|--------|
| WebSocket connections | Stable | _ | _ | _ | _ | ⬜ |
| DB connection pool | < 80% | _ % | _ % | _ % | _ % | ⬜ |
| File descriptors | < 80% of limit | _ | _ | _ | _ | ⬜ |
| Redis connections | Stable | _ | _ | _ | _ | ⬜ |

---

## 7. Queue Health

| Queue | Target | 0h | 24h | 48h | 72h | Status |
|-------|--------|----|-----|-----|-----|--------|
| Retry queue | Drains to 0 | _ | _ | _ | _ | ⬜ |
| Dead letter queue | No growth | _ | _ | _ | _ | ⬜ |
| Notification queue | Drains | _ | _ | _ | _ | ⬜ |
| Celery queue | Drains | _ | _ | _ | _ | ⬜ |

---

## 8. Trading State Integrity

| Check | Target | Actual | Status |
|------|--------|--------|--------|
| Total orders placed | _ | _ | ⬜ |
| Orders matched exchange | 100% | _ % | ⬜ |
| Duplicate orders detected | 0 | _ | ⬜ |
| Orphan orders detected | 0 | _ | ⬜ |
| Positions consistent | Yes | ⬜ | ⬜ |
| PnL consistent | Yes | ⬜ | ⬜ |
| Grid state correct | Yes | ⬜ | ⬜ |
| Exposure within limits | Yes | ⬜ | ⬜ |

---

## 9. Recovery Events

| # | Timestamp | Trigger | Duration | Result | Notes |
|---|-----------|---------|----------|--------|-------|
| — | — | — | — | — | — |

**Verdict:** ⬜ All expected / ⬜ Unexpected events

---

## 10. Error Analysis

| Error type | Count | First seen | Last seen | Impact | Notes |
|------------|-------|------------|-----------|--------|-------|
| HTTP 5xx | _ | _ | _ | _ | |
| HTTP 4xx | _ | _ | _ | _ | |
| WebSocket errors | _ | _ | _ | _ | |
| DB errors | _ | _ | _ | _ | |
| Redis errors | _ | _ | _ | _ | |
| Exchange errors | _ | _ | _ | _ | |

---

## 11. Issues Encountered

| # | Issue | Severity | Detected at | Resolution | Status |
|---|-------|----------|-------------|------------|--------|
| — | — | — | — | — | — |

---

## 12. Final Verdict

| Question | Answer |
|----------|--------|
| Memory leak detected? | ⬜ No / ⬜ Yes |
| CPU degradation? | ⬜ No / ⬜ Yes |
| Latency degradation? | ⬜ No / ⬜ Yes |
| Connection leaks? | ⬜ No / ⬜ Yes |
| Queue backlogs? | ⬜ No / ⬜ Yes |
| Duplicate orders? | ⬜ No / ⬜ Yes |
| Orphan orders? | ⬜ No / ⬜ Yes |
| Unexpected restarts? | ⬜ No / ⬜ Yes |
| Unexpected recovery events? | ⬜ No / ⬜ Yes |
| Error rate within target? | ⬜ Yes / ⬜ No |

**Soak test verdict:** ⬜ PASS — proceed to sandbox validation / ⬜ FAIL — investigate and fix

---

## 13. Sign-off

| Role | Name | Decision | Date |
|------|------|----------|------|
| Engineering | _ | ⬜ Pass / ⬜ Fail | _ |
| DevOps | _ | ⬜ Pass / ⬜ Fail | _ |
| QA | _ | ⬜ Pass / ⬜ Fail | _ |
