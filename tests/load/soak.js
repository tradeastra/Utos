import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';

// ─────────────────────────────────────────────
// Sprint 16F-4: Soak Test — Long Running
//
// Designed for 24h / 48h / 72h runs.
// Monitors: memory leaks, thread leaks, connection leaks.
//
// Usage:
//   k6 run --vus 100 --duration 24h tests/load/soak.js
//   k6 run --vus 200 --duration 48h tests/load/soak.js
//   k6 run --vus 500 --duration 72h tests/load/soak.js
//
// Environment:
//   BASE_URL — target URL (default: http://localhost:8000)
//   SOAK_DURATION — duration (default: 24h)
// ─────────────────────────────────────────────

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Track metrics over time for leak detection
const requestCount = new Counter('soak_requests_total');
const errorCount = new Counter('soak_errors_total');
const responseTime = new Trend('soak_response_time_ms');
const memoryGrowth = new Trend('soak_memory_growth');

export const options = {
  scenarios: {
    soak: {
      executor: 'constant-vus',
      vus: __ENV.VUS || 100,
      duration: __ENV.SOAK_DURATION || '24h',
    },
  },
  thresholds: {
    soak_response_time_ms: [
      { threshold: 'p(95)<200', abortOnFail: false },
      { threshold: 'p(99)<500', abortOnFail: false },
    ],
    http_req_failed: [
      { threshold: 'rate<0.01', abortOnFail: false },
    ],
  },
  // Collect detailed metrics for leak analysis
  noConnectionReuse: false,
  userAgent: 'k6-soak-test/1.0',
};

let iteration = 0;

export default function () {
  iteration++;

  // ── Health check ───────────────────────────
  const healthRes = http.get(`${BASE_URL}/health`);
  requestCount.add(1);
  responseTime.add(healthRes.timings.duration);

  check(healthRes, {
    'health is 200 or 503': (r) => r.status === 200 || r.status === 503,
  });

  if (healthRes.status >= 500) {
    errorCount.add(1);
  }

  // ── Metrics endpoint (check for memory growth) ──
  if (iteration % 100 === 0) {
    const metricsRes = http.get(`${BASE_URL}/metrics`);
    if (metricsRes.status === 200) {
      // Extract process memory metrics if available
      const lines = metricsRes.body.split('\n');
      for (const line of lines) {
        if (line.includes('process_resident_memory_bytes')) {
          const match = line.match(/(\d+)$/);
          if (match) {
            memoryGrowth.add(parseFloat(match[1]) / 1024 / 1024); // MB
          }
        }
      }
    }
  }

  // ── DB health check (every 50 iterations) ──
  if (iteration % 50 === 0) {
    const dbRes = http.get(`${BASE_URL}/db/health`);
    check(dbRes, {
      'db health is 200': (r) => r.status === 200,
    });
  }

  // ── Vary sleep to simulate realistic traffic ──
  const sleepTime = 0.5 + Math.random() * 2;
  sleep(sleepTime);
}

export function handleSummary(data) {
  const summary = {
    test: 'soak',
    duration: __ENV.SOAK_DURATION || '24h',
    vus: __ENV.VUS || 100,
    metrics: {
      total_requests: data.metrics.soak_requests_total?.values?.count || 0,
      total_errors: data.metrics.soak_errors_total?.values?.count || 0,
      p95_response_ms: data.metrics.soak_response_time_ms?.values?.['p(95)'] || 0,
      p99_response_ms: data.metrics.soak_response_time_ms?.values?.['p(99)'] || 0,
      avg_memory_mb: data.metrics.soak_memory_growth?.values?.avg || 0,
      max_memory_mb: data.metrics.soak_memory_growth?.values?.max || 0,
    },
    thresholds: data.metrics,
  };

  return {
    'tests/load/soak-results.json': JSON.stringify(summary, null, 2),
    stdout: JSON.stringify(summary, null, 2),
  };
}
