# Sprint 16F: Performance & Load Testing

## Overview

This document describes the performance testing strategy for the UTOS Trading Engine,
including benchmarks, load tests, WebSocket stress tests, soak tests, and profiling.

## 16F-1: pytest-benchmark

**Location:** `backend/tests/test_benchmark/test_engine_benchmarks.py`

Benchmarks for core engine components:

| Component | Benchmark | Target |
|-----------|-----------|--------|
| GridCalculator | `calculate_levels` (10/50/100 grids) | < 1ms for 100 grids |
| GridPlanner | `plan_initial` (10/50 grids) | < 5ms for 50 grids |
| ProfitLockPolicy | `evaluate` (monitoring/triggered) | < 0.1ms |
| ProfitCalculator | `calculate` (long/short) | < 0.1ms |
| RiskManager | `check_order_risk` (allowed/denied) | < 1ms |
| RiskManager | `check_portfolio_risk` | < 1ms |
| OrderValidator | `validate` | < 0.5ms |
| OrderTracker | `get_by_request_id` | < 0.1ms |

**Run benchmarks:**
```bash
cd backend
pip install pytest-benchmark
pytest tests/test_benchmark/ --benchmark-only -v
```

**View benchmark history:**
```bash
pytest tests/test_benchmark/ --benchmark-only --benchmark-compare
```

## 16F-2: k6 API Load Test

**Location:** `tests/load/api-load.js`

Tests API endpoints under load with increasing virtual users:

| Level | VUs | Duration | Purpose |
|-------|-----|----------|---------|
| Light | 500 | 5m | Baseline |
| Medium | 1,000 | 5m | Normal load |
| High | 2,500 | 5m | Peak traffic |
| Extreme | 5,000 | 10m | Stress |
| Maximum | 10,000 | 10m | Breaking point |

**Endpoints tested:**
- `GET /health`, `/live`, `/ready`
- `POST /api/v1/auth/register`, `/api/v1/auth/login`
- `GET /api/v1/users/me`, `/api/v1/trading-instances`, `/api/v1/market`
- `GET /db/health`

**Run:**
```bash
# Install k6
# https://k6.io/docs/getting-started/installation/

# Run load tests
k6 run --vus 1000 --duration 5m tests/load/api-load.js

# With custom URL
BASE_URL=https://staging.utos.local k6 run --vus 5000 --duration 10m tests/load/api-load.js
```

## 16F-3: WebSocket Stress Test

**Location:** `tests/load/ws-stress.js`

Tests WebSocket connection handling under concurrent load:

| Level | Clients | Duration | Purpose |
|-------|---------|----------|---------|
| Light | 1,000 | 5m | Baseline |
| High | 2,500 | 5m | Peak |
| Maximum | 5,000 | 10m | Stress |

**Metrics tracked:**
- Connection success rate
- Message receive rate
- Connection latency
- Message latency

**Run:**
```bash
k6 run --vus 1000 --duration 5m tests/load/ws-stress.js
```

## 16F-4: Soak Test

**Location:** `tests/load/soak.js`

Long-running tests to detect resource leaks:

| Duration | VUs | Purpose |
|----------|-----|---------|
| 24 hours | 100 | Daily stability |
| 48 hours | 200 | Extended stability |
| 72 hours | 500 | Weekend stability |

**Leak detection:**
- Memory growth (via `process_resident_memory_bytes` metric)
- Response time degradation over time
- Error rate increase over time
- Connection pool exhaustion

**Run:**
```bash
k6 run --vus 100 --duration 24h tests/load/soak.js
```

## 16F-5: Profiling

**Location:** `scripts/profile.sh`

Three profiling tools:

| Tool | Type | Overhead | Output |
|------|------|----------|--------|
| py-spy | Sampling CPU | Very low | Flamegraph SVG |
| scalene | CPU + Memory | Medium | HTML report |
| memray | Memory allocation | Medium | Flamegraph + stats |

**Run:**
```bash
# py-spy (recommended for production)
bash scripts/profile.sh pyspy 60

# scalene (CPU + memory)
bash scripts/profile.sh scalene 60

# memray (memory allocation tracking)
bash scripts/profile.sh memray 60
```

## Acceptance Criteria

| Metric | Target | How to Measure |
|--------|--------|----------------|
| API p95 | < 200 ms | k6 `http_req_duration` p(95) |
| API p99 | < 500 ms | k6 `http_req_duration` p(99) |
| Recovery | < 30 s | Integration test timing |
| Dashboard load | < 2 s | Frontend Lighthouse audit |
| Trading latency | < 10 ms | pytest-benchmark on engine |
| Order throughput | ≥ 1,000 orders/s | k6 + benchmark |
| Concurrent WS | ≥ 5,000 | k6 WebSocket stress test |
| Concurrent instances | ≥ 10,000 | Load test with mock instances |
| CPU | < 70% | Docker stats during load test |
| Memory | Stable | Soak test — no growth over 24h |

## CI Integration

Benchmarks run on every PR:
```yaml
# In .github/workflows/test.yml
- name: Run benchmarks
  run: |
    cd backend
    poetry run pytest tests/test_benchmark/ --benchmark-only --benchmark-json=benchmark.json
```

Load tests run on merge to main (nightly):
```yaml
# Nightly schedule
on:
  schedule:
    - cron: "0 2 * * *"
```
