# DEPLOYMENT SPECIFICATION

**Version:** 2.0.0  
**Last Updated:** 2026-07-09  
**Status:** DRAFT

---

## 1. OVERVIEW

This document defines the deployment architecture, processes, and environments for the UTOS Trading Engine.

### 1.1 Environments

| Environment | Purpose | URL |
|-------------|---------|-----|
| `local` | Local development | `http://localhost:3000` |
| `dev` | Development server | `https://dev.utos.com` |
| `staging` | Pre-production testing | `https://staging.utos.com` |
| `production` | Live system | `https://utos.com` |

### 1.2 Deployment Principles

- **Infrastructure as Code**: All infrastructure defined in code
- **Zero Downtime**: Production deployments with no service interruption
- **Rollback Ready**: Every deployment can be rolled back instantly
- **Blue-Green**: Production uses blue-green deployment strategy
- **Automated**: CI/CD pipeline handles all deployments
- **Monitored**: Every deployment triggers health checks

---

## 2. ARCHITECTURE

### 2.1 Production Architecture

```
                    ┌─────────────┐
                    │   CloudFlare │
                    │    (CDN/WAF) │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Nginx     │
                    │  (Load Bal.) │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼─────┐ ┌───▼────┐ ┌────▼─────┐
       │  Frontend   │ │ API 1  │ │  API 2   │
       │  (Next.js)  │ │(FastAPI│ │(FastAPI) │
       │  (SSR/SSG)  │ │  )     │ │          │
       └────────────┘ └───┬────┘ └────┬─────┘
                           │           │
              ┌────────────┼───────────┘
              │            │
       ┌──────▼─────┐ ┌───▼──────┐
       │ PostgreSQL  │ │  Redis   │
       │ (Primary +  │ │ (Cluster)│
       │  Replica)   │ │          │
       └────────────┘ └──────────┘
              │            │
       ┌──────▼─────┐ ┌───▼──────┐
       │  Workers    │ │  Celery  │
       │  (Trading)  │ │  Beat    │
       └────────────┘ └──────────┘
```

### 2.2 Kubernetes Architecture

```
┌─────────────────────────────────────────────────┐
│                  Kubernetes Cluster              │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Namespace:│  │ Namespace:│  │ Namespace:│     │
│  │  utos-prod│  │ utos-stg  │  │  utos-dev │     │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                  │
│  ┌────────────────────────────────────────┐     │
│  │  Ingress Controller (Nginx Ingress)     │     │
│  └────────────────────────────────────────┘     │
│                                                  │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐           │
│  │Front-│ │ API  │ │ API  │ │Worker│           │
│  │end   │ │ Pod 1│ │ Pod 2│ │ Pod 1│           │
│  │ Pod  │ └──────┘ └──────┘ └──────┘           │
│  └──────┘                    ┌──────┐           │
│                              │Worker│           │
│                              │ Pod 2│           │
│                              └──────┘           │
│                                                  │
│  ┌────────────────────────────────────────┐     │
│  │  StatefulSet: PostgreSQL (Primary)      │     │
│  │  StatefulSet: PostgreSQL (Replica)      │     │
│  │  StatefulSet: Redis                     │     │
│  └────────────────────────────────────────┘     │
│                                                  │
│  ┌────────────────────────────────────────┐     │
│  │  Monitoring: Prometheus + Grafana       │     │
│  │  Logging: Fluentd → Elasticsearch       │     │
│  └────────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```

---

## 3. DOCKER CONFIGURATION

### 3.1 Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim AS builder

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry export -f requirements.txt > requirements.txt

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 3.2 Frontend Dockerfile

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine

WORKDIR /app

COPY --from=builder /app ./
RUN npm install --omit=dev

EXPOSE 3000

CMD ["npm", "start"]
```

### 3.3 Docker Compose (Development)

```yaml
# docker-compose.yml
version: "3.9"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://utos:utos@postgres:5432/utos
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=local
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
    volumes:
      - ./frontend:/app
    command: npm run dev

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: utos
      POSTGRES_USER: utos
      POSTGRES_PASSWORD: utos
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  worker:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://utos:utos@postgres:5432/utos
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=local
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app
    command: celery -A tasks.celery_app worker --loglevel=info

volumes:
  postgres_data:
  redis_data:
```

---

## 4. KUBERNETES MANIFESTS

### 4.1 API Deployment

```yaml
# infrastructure/k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: utos-api
  namespace: utos-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: utos-api
  template:
    metadata:
      labels:
        app: utos-api
    spec:
      containers:
        - name: api
          image: registry.utos.com/utos-api:latest
          ports:
            - containerPort: 8000
          envFrom:
            - secretRef:
                name: utos-secrets
            - configMapRef:
                name: utos-config
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "1000m"
              memory: "1Gi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
```

### 4.2 API Service

```yaml
# infrastructure/k8s/api-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: utos-api-service
  namespace: utos-prod
spec:
  selector:
    app: utos-api
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP
```

### 4.3 Worker Deployment

```yaml
# infrastructure/k8s/worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: utos-worker
  namespace: utos-prod
spec:
  replicas: 2
  selector:
    matchLabels:
      app: utos-worker
  template:
    metadata:
      labels:
        app: utos-worker
    spec:
      containers:
        - name: worker
          image: registry.utos.com/utos-api:latest
          command: ["celery", "-A", "tasks.celery_app", "worker", "--loglevel=info"]
          envFrom:
            - secretRef:
                name: utos-secrets
            - configMapRef:
                name: utos-config
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
```

### 4.4 Ingress

```yaml
# infrastructure/k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: utos-ingress
  namespace: utos-prod
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/websocket-services: "utos-api-service"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
    - hosts:
        - api.utos.com
        - utos.com
      secretName: utos-tls
  rules:
    - host: api.utos.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: utos-api-service
                port:
                  number: 80
    - host: utos.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: utos-frontend-service
                port:
                  number: 80
```

### 4.5 HPA (Horizontal Pod Autoscaler)

```yaml
# infrastructure/k8s/api-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: utos-api-hpa
  namespace: utos-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: utos-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

---

## 5. CI/CD PIPELINE

### 5.1 Pipeline Stages

```
Push to branch
    │
    ▼
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│   Lint    │────▶│  Test    │────▶│  Build   │────▶│  Scan    │
│ (ruff,    │     │ (pytest, │     │ (Docker) │     │(Trivy,   │
│  eslint)  │     │  vitest) │     │          │     │ Sonar)   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                          │
                                          ▼
                                   ┌──────────┐
                                   │  Push to │
                                   │ Registry │
                                   └─────┬────┘
                                         │
                              ┌──────────┼──────────┐
                              │          │          │
                              ▼          ▼          ▼
                         ┌────────┐ ┌────────┐ ┌────────┐
                         │  Dev   │ │Staging │ │  Prod  │
                         │Deploy  │ │Deploy  │ │Deploy* │
                         └────────┘ └────────┘ └────────┘
                         
                         * Prod only on main branch + manual approval
```

### 5.2 GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main, develop]
  workflow_dispatch:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install ruff
      - run: ruff check backend/
      - run: ruff format --check backend/
      
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd frontend && npm ci
      - run: cd frontend && npm run lint

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
      redis:
        image: redis:7
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r backend/requirements-dev.txt
      - run: pytest --cov=backend --cov-report=xml
      - uses: codecov/codecov-action@v4
      
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd frontend && npm ci
      - run: cd frontend && npm run test:coverage

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: registry.utos.com
          username: ${{ secrets.REGISTRY_USER }}
          password: ${{ secrets.REGISTRY_PASS }}
      - run: docker build -t registry.utos.com/utos-api:${{ github.sha }} ./backend
      - run: docker push registry.utos.com/utos-api:${{ github.sha }}
      - run: docker build -t registry.utos.com/utos-frontend:${{ github.sha }} ./frontend
      - run: docker push registry.utos.com/utos-frontend:${{ github.sha }}

  deploy-dev:
    needs: build
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to dev
        run: |
          kubectl set image deployment/utos-api api=registry.utos.com/utos-api:${{ github.sha }} -n utos-dev
          kubectl set image deployment/utos-frontend frontend=registry.utos.com/utos-frontend:${{ github.sha }} -n utos-dev
          kubectl rollout status deployment/utos-api -n utos-dev
          kubectl rollout status deployment/utos-frontend -n utos-dev

  deploy-staging:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to staging
        run: |
          kubectl set image deployment/utos-api api=registry.utos.com/utos-api:${{ github.sha }} -n utos-stg
          kubectl rollout status deployment/utos-api -n utos-stg

  deploy-production:
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to production (blue-green)
        run: |
          # Deploy to green
          kubectl set image deployment/utos-api-green api=registry.utos.com/utos-api:${{ github.sha }} -n utos-prod
          kubectl rollout status deployment/utos-api-green -n utos-prod
          
          # Health check
          kubectl exec deployment/utos-api-green -- curl -f http://localhost:8000/health
          
          # Switch traffic
          kubectl patch service utos-api-service -p '{"spec":{"selector":{"version":"green"}}}' -n utos-prod
```

---

## 6. ENVIRONMENT VARIABLES

### 6.1 Backend

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | Yes | - |
| `REDIS_URL` | Redis connection URL | Yes | - |
| `JWT_SECRET` | JWT signing secret | Yes | - |
| `JWT_EXPIRE_MINUTES` | JWT expiration (minutes) | No | 60 |
| `ENCRYPTION_KEY` | AES-256 encryption key | Yes | - |
| `ENVIRONMENT` | Environment name | Yes | local |
| `LOG_LEVEL` | Logging level | No | INFO |
| `CORS_ORIGINS` | Allowed CORS origins | Yes | - |
| `BINANCE_API_KEY` | Binance API key (testnet) | No | - |
| `BINANCE_API_SECRET` | Binance API secret (testnet) | No | - |
| `SENTRY_DSN` | Sentry error tracking DSN | No | - |
| `PROMETHEUS_PORT` | Prometheus metrics port | No | 9090 |

### 6.2 Frontend

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | Yes | - |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL | Yes | - |
| `NEXT_PUBLIC_SENTRY_DSN` | Sentry DSN | No | - |
| `NEXT_PUBLIC_GA_ID` | Google Analytics ID | No | - |

---

## 7. HEALTH CHECKS

### 7.1 Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness probe (is process running?) |
| `GET /ready` | Readiness probe (is service ready?) |
| `GET /metrics` | Prometheus metrics |

### 7.2 Health Response

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "exchange_api": "healthy"
  }
}
```

### 7.3 Readiness Response

```json
{
  "status": "ready",
  "checks": {
    "database": "connected",
    "redis": "connected",
    "migrations": "up_to_date"
  }
}
```

---

## 8. MONITORING

### 8.1 Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `utos_orders_total` | Counter | Total orders placed |
| `utos_orders_filled_total` | Counter | Total orders filled |
| `utos_trading_instances_active` | Gauge | Active trading instances |
| `utos_grid_cycles_total` | Counter | Total grid cycles completed |
| `utos_api_request_duration_seconds` | Histogram | API request latency |
| `utos_websocket_connections` | Gauge | Active WebSocket connections |
| `utos_event_bus_publish_total` | Counter | Events published |
| `utos_event_bus_consume_total` | Counter | Events consumed |
| `utos_exchange_api_latency_seconds` | Histogram | Exchange API latency |
| `utos_database_query_duration_seconds` | Histogram | Database query latency |

### 8.2 Grafana Dashboards

- **System Overview**: CPU, memory, network, disk
- **API Performance**: Request rate, latency, error rate
- **Trading Metrics**: Active processes, orders, fills, P&L
- **Exchange Status**: Connection status, API latency, rate limits
- **Database**: Connection pool, query performance, slow queries
- **Redis**: Memory usage, pub/sub rate, connection count

### 8.3 Alerting Rules

| Alert | Condition | Severity |
|-------|-----------|----------|
| API Down | `up{job="utos-api"} == 0` for 1m | Critical |
| High Error Rate | `rate(utos_api_errors_total[5m]) > 0.05` | High |
| High Latency | `histogram_quantile(0.95, utos_api_request_duration_seconds) > 2` | High |
| DB Connection Pool | `utos_db_pool_usage > 0.8` | High |
| Redis Memory | `redis_memory_used / redis_memory_max > 0.8` | Medium |
| Exchange Disconnected | `utos_exchange_connected == 0` for 5m | Critical |
| Worker Down | `up{job="utos-worker"} == 0` for 2m | High |

---

## 9. ROLLBACK PROCEDURE

### 9.1 Automatic Rollback

```bash
# Rollback to previous deployment
kubectl rollout undo deployment/utos-api -n utos-prod

# Check rollback status
kubectl rollout status deployment/utos-api -n utos-prod
```

### 9.2 Blue-Green Rollback

```bash
# Switch back to blue (previous version)
kubectl patch service utos-api-service -p '{"spec":{"selector":{"version":"blue"}}}' -n utos-prod

# Verify
kubectl get pods -l version=blue -n utos-prod
```

### 9.3 Database Rollback

```bash
# Rollback migration
alembic downgrade -1

# Restore from backup (if needed)
pg_restore -U postgres -d utos -c backup_20260709.sql
```

---

## 10. SCALABILITY FOR 100,000+ TRADING INSTANCES

### 10.1 Horizontal Pod Autoscaling (HPA)

| Service | Min Replicas | Max Replicas | Trigger |
|---------|-------------|--------------|---------|
| API | 3 | 20 | CPU > 70%, memory > 80% |
| Workers | 10 | 200 | Active instances per worker > 1000 |
| Event Bus | 3 | 10 | Message lag > 10,000 |
| Market Hub | 3 | 10 | Active symbol subscriptions > 5,000 |

### 10.2 Worker Pool Architecture

- Workers are **stateful per instance** (one Trading Instance is owned by one worker).
- Worker assignment uses consistent hashing on `instance_id`.
- Workers load `ProcessMemory` snapshot from database on startup and reconcile with exchange.
- Graceful shutdown: persist snapshot, stop accepting new instances, drain existing instances.

### 10.3 Database Scaling

- PostgreSQL primary + 2 read replicas.
- PgBouncer transaction pooling (500-1000 connections).
- Partition `orders` by `created_at` (monthly) and `trading_instance_id` (hash).
- Bulk `memory_snapshot` updates with background task.

### 10.4 Redis Scaling

- Redis Cluster for Pub/Sub and cache.
- Redis Streams (Phase 2) for ordered event processing at scale.
- Separate Redis for sessions, cache, and event bus.

### 10.5 Network & Storage

- WebSocket ingress with sticky sessions for account streams.
- S3 for persistent snapshots and audit logs.
- CDN for static frontend assets.

---

## 11. SECURITY CHECKLIST

- [ ] SSL/TLS certificates valid and auto-renewing
- [ ] Secrets stored in Kubernetes Secrets (not in code)
- [ ] API keys encrypted at rest (AES-256)
- [ ] Database backups encrypted
- [ ] Rate limiting enabled on all endpoints
- [ ] CORS configured correctly
- [ ] WAF (CloudFlare) enabled
- [ ] DDoS protection enabled
- [ ] Container images scanned (Trivy)
- [ ] No secrets in environment variables in code
- [ ] JWT tokens have expiration
- [ ] Password hashing uses bcrypt
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (CSP headers)
- [ ] CSRF protection enabled
- [ ] Audit logging enabled

---

## 12. BACKUP STRATEGY

| Data | Frequency | Retention | Storage |
|------|-----------|-----------|---------|
| PostgreSQL full | Daily at 00:00 | 30 days | S3 (encrypted) |
| PostgreSQL WAL | Continuous | 7 days | S3 (encrypted) |
| Redis snapshot | Every 6 hours | 7 days | S3 (encrypted) |
| Kubernetes etcd | Daily at 01:00 | 14 days | S3 (encrypted) |
| Container images | On build | 90 days | Registry |

---

## 13. CHANGE LOG

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-09 | 1.0.0 | Initial deployment specification |
| 2026-07-09 | 2.0.0 | Architecture revision: project rename, scalability for 100,000+ Trading Instances, ProcessMemory, worker pool |
