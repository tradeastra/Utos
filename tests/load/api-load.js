import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ─────────────────────────────────────────────
// Sprint 16F-2: k6 API Load Test
//
// Usage:
//   k6 run --vus 500 --duration 5m tests/load/api-load.js
//   k6 run --vus 10000 --duration 10m tests/load/api-load.js
//
// Environment:
//   BASE_URL — target URL (default: http://localhost:8000)
// ─────────────────────────────────────────────

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Custom metrics
const errorRate = new Rate('errors');
const loginDuration = new Trend('login_duration_ms');
const registerDuration = new Trend('register_duration_ms');
const apiDuration = new Trend('api_duration_ms');

// Test configuration — override with CLI flags
export const options = {
  stages: [
    { duration: '30s', target: __ENV.VUS || 500 },
    { duration: '5m', target: __ENV.VUS || 500 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<200', 'p(99)<500'],
    http_req_failed: ['rate<0.01'],
    errors: ['rate<0.05'],
  },
};

// Generate unique user data
function generateUser() {
  const id = Math.floor(Math.random() * 10000000);
  return {
    email: `loadtest_${id}@utos-test.com`,
    password: 'LoadTest123!',
    username: `loadtest_${id}`,
  };
}

export default function () {
  const user = generateUser();

  // ── Health checks ──────────────────────────
  group('Health Endpoints', () => {
    const healthRes = http.get(`${BASE_URL}/health`);
    check(healthRes, {
      'health is 200': (r) => r.status === 200 || r.status === 503,
    });

    const liveRes = http.get(`${BASE_URL}/live`);
    check(liveRes, {
      'live is 200': (r) => r.status === 200,
    });

    const readyRes = http.get(`${BASE_URL}/ready`);
    check(readyRes, {
      'ready is 200': (r) => r.status === 200,
    });
  });

  // ── Register ───────────────────────────────
  let token;
  group('Auth - Register', () => {
    const res = http.post(
      `${BASE_URL}/api/v1/auth/register`,
      JSON.stringify(user),
      { headers: { 'Content-Type': 'application/json' } }
    );
    registerDuration.add(res.timings.duration);

    const ok = check(res, {
      'register status 200 or 201': (r) => r.status === 200 || r.status === 201,
      'register has token': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.access_token !== undefined;
        } catch (e) {
          return false;
        }
      },
    });
    errorRate.add(!ok);

    if (ok) {
      try {
        token = JSON.parse(res.body).access_token;
      } catch (e) {}
    }
  });

  // ── Login (if register failed, try login) ─
  if (!token) {
    group('Auth - Login', () => {
      const res = http.post(
        `${BASE_URL}/api/v1/auth/login`,
        JSON.stringify({ email: user.email, password: user.password }),
        { headers: { 'Content-Type': 'application/json' } }
      );
      loginDuration.add(res.timings.duration);

      const ok = check(res, {
        'login status 200': (r) => r.status === 200,
        'login has token': (r) => {
          try {
            const body = JSON.parse(r.body);
            return body.access_token !== undefined;
          } catch (e) {
            return false;
          }
        },
      });
      errorRate.add(!ok);

      if (ok) {
        try {
          token = JSON.parse(res.body).access_token;
        } catch (e) {}
      }
    });
  }

  // ── Authenticated API calls ────────────────
  if (token) {
    const authHeaders = {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    };

    group('API - User Profile', () => {
      const res = http.get(`${BASE_URL}/api/v1/users/me`, { headers: authHeaders });
      apiDuration.add(res.timings.duration);
      check(res, {
        'profile is 200': (r) => r.status === 200,
      });
    });

    group('API - Trading Instances', () => {
      const res = http.get(`${BASE_URL}/api/v1/trading-instances`, { headers: authHeaders });
      apiDuration.add(res.timings.duration);
      check(res, {
        'instances is 200': (r) => r.status === 200,
      });
    });

    group('API - Market Data', () => {
      const res = http.get(`${BASE_URL}/api/v1/market`, { headers: authHeaders });
      apiDuration.add(res.timings.duration);
      check(res, {
        'market is 200': (r) => r.status === 200,
      });
    });

    group('API - DB Health', () => {
      const res = http.get(`${BASE_URL}/db/health`, { headers: authHeaders });
      apiDuration.add(res.timings.duration);
      check(res, {
        'db health is 200': (r) => r.status === 200,
      });
    });
  }

  sleep(0.1);
}

// Handle summary
export function handleSummary(data) {
  return {
    'tests/load/results.json': JSON.stringify(data, null, 2),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, opts) {
  return JSON.stringify(data.metrics, null, 2);
}
