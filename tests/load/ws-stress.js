import ws from 'k6/ws';
import { check } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// ─────────────────────────────────────────────
// Sprint 16F-3: WebSocket Stress Test
//
// Usage:
//   k6 run --vus 1000 --duration 5m tests/load/ws-stress.js
//   k6 run --vus 5000 --duration 10m tests/load/ws-stress.js
//
// Environment:
//   WS_URL — WebSocket URL (default: ws://localhost:8000/ws)
// ─────────────────────────────────────────────

const WS_URL = __ENV.WS_URL || 'ws://localhost:8000/ws';

// Custom metrics
const wsConnections = new Counter('ws_connections_total');
const wsMessages = new Counter('ws_messages_received');
const wsErrors = new Rate('ws_errors');
const wsConnectDuration = new Trend('ws_connect_duration_ms');
const wsMessageDuration = new Trend('ws_message_latency_ms');

export const options = {
  stages: [
    { duration: '1m', target: __ENV.VUS || 1000 },
    { duration: '5m', target: __ENV.VUS || 1000 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    ws_errors: ['rate<0.05'],
    ws_connect_duration_ms: ['p(95)<1000'],
  },
};

export default function () {
  const url = `${WS_URL}?token=loadtest_${__VU}_${__ITER}`;

  const connectStart = Date.now();

  ws.connect(url, {}, function (socket) {
    const connectTime = Date.now() - connectStart;
    wsConnectDuration.add(connectTime);
    wsConnections.add(1);

    socket.on('open', () => {
      // Subscribe to market data
      socket.send(JSON.stringify({
        type: 'subscribe',
        channel: 'ticker',
        exchange: 'binance',
        symbol: 'BTCUSDT',
      }));

      // Heartbeat
      socket.setInterval(() => {
        socket.send(JSON.stringify({ type: 'ping' }));
      }, 20000);
    });

    socket.on('message', (data) => {
      wsMessages.add(1);
      try {
        const msg = JSON.parse(data);
        if (msg.timestamp) {
          const latency = Date.now() - new Date(msg.timestamp).getTime();
          wsMessageDuration.add(latency);
        }
      } catch (e) {
        // Non-JSON message
      }
    });

    socket.on('error', (e) => {
      wsErrors.add(1);
    });

    socket.on('close', () => {
      // Connection closed
    });

    // Keep connection alive for the test duration
    socket.setTimeout(() => {
      socket.close();
    }, 300000); // 5 minutes
  });
}

export function handleSummary(data) {
  return {
    'tests/load/ws-results.json': JSON.stringify(data, null, 2),
  };
}
