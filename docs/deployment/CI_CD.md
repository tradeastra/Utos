# Sprint 16E: CI/CD & Blue-Green Deployment

## Overview

This document describes the CI/CD pipeline, Docker image release process,
blue-green deployment strategy, smoke testing, automatic rollback, and
environment matrix for the UTOS Trading Engine.

## GitHub Actions Workflows

### Pipeline Architecture

```
Push to main/develop
       │
       ├── ci.yml         (lint, type check)
       ├── test.yml        (unit + integration tests)
       ├── security.yml    (pip-audit, npm audit, Trivy, secret scan)
       └── docker.yml      (build + push to GHCR, image scan)
              │
              ▼
         deploy.yml        (blue-green deploy + smoke test)
              │
              ▼
         release.yml       (tag, GHCR, GitHub Release, CHANGELOG)
```

### Workflow Files

| File | Purpose | Trigger |
|------|---------|---------|
| `ci.yml` | Lint (ruff, black, mypy, eslint, tsc) | Push/PR to main, develop |
| `test.yml` | Backend pytest + Frontend vitest | Push/PR to main, develop |
| `security.yml` | pip-audit, npm audit, Trivy, secret scan | Push/PR + weekly schedule |
| `docker.yml` | Build & push images to GHCR + Trivy scan | Push to main, develop, tags |
| `deploy.yml` | Blue-green deploy with smoke test + rollback | Tag push or manual dispatch |
| `release.yml` | Auto version, tag, GitHub Release, CHANGELOG | Push to main or manual |

## Docker Image Tags

Images are published to GitHub Container Registry (GHCR):

```
ghcr.io/andra2112s/utos-backend:{tag}
ghcr.io/andra2112s/utos-frontend:{tag}
```

Tag formats:
- `latest` — latest stable (main branch)
- `v0.16.0` — semantic version
- `v0.16.0-rc1` — release candidate
- `sha-abc12345` — commit SHA (immutable)
- `develop` — development branch

## Blue-Green Deployment

### Architecture

```
         Nginx
           │
     ┌─────┴─────┐
     │           │
   Blue         Green
  (active)    (standby)
     │           │
  backend     backend
  frontend    frontend
     │           │
     └─────┬─────┘
           │
      PostgreSQL
      Redis
```

### Deployment Flow

1. **Deploy Green** — new version deployed to inactive slot
2. **Health Check** — wait for `/health`, `/ready`, `/live` to pass
3. **Smoke Test** — run `scripts/smoke-test.sh` against Green slot
4. **Switch Nginx** — update active slot, reload Nginx
5. **Verify** — smoke test against active endpoint
6. **Stop Blue** — old slot stopped after grace period

### Rollback

If smoke tests fail or post-switch verification fails:
1. Switch active slot back to previous
2. Reload Nginx
3. Stop failed slot
4. Alert via GitHub Actions

### Automatic Rollback Monitor

Run `scripts/auto-rollback.sh` as a sidecar or cron job:

```bash
# Monitor with Prometheus integration
PROMETHEUS_URL=http://prometheus:9090 \
bash scripts/auto-rollback.sh production
```

Triggers rollback when:
- Health check fails for 3 consecutive checks
- 5xx error rate > 5%
- Latency > 2000ms

## Smoke Tests

`scripts/smoke-test.sh` verifies post-deploy health:

| Test | Endpoint | Expected |
|------|----------|----------|
| Liveness | `GET /live` | 200 |
| Readiness | `GET /ready` | 200 |
| Health | `GET /health` | 200 or 503 |
| Metrics | `GET /metrics` | 200 |
| Root | `GET /` | 200 |
| Register | `POST /api/v1/auth/register` | 200 with token |
| Login | `POST /api/v1/auth/login` | 200 with token |
| Profile | `GET /api/v1/users/me` | 200 with user data |
| Instances | `GET /api/v1/trading-instances` | 200 |
| Market | `GET /api/v1/market` | 200 |
| DB Health | `GET /db/health` | 200 |
| Latency | `GET /health` | < 500ms |

## Environment Matrix

| Property | Development | Staging | Production |
|----------|-------------|---------|------------|
| Compose | `docker-compose.yml` | `docker-compose.staging.yml` | `docker-compose.prod.yml` |
| Env file | `.env` | `.env.staging` | `.env.production` |
| APP_ENV | development | staging | production |
| Debug | true | false | false |
| DB | utos_dev | utos_staging | utos |
| Redis | 256MB | 128MB | 256MB |
| Backend CPU | unlimited | 1.0 | 2.0 |
| Backend Memory | unlimited | 512M | 1G |
| TLS | none | self-signed | Let's Encrypt |
| Backup | manual | 3 days / 5 copies | 7 days / 10 copies |
| OTEL | disabled | enabled | enabled |
| Rollback | N/A | manual | automatic |

## Release Process

### Automatic (on merge to main)

1. `release.yml` determines next version
2. Builds and pushes Docker images to GHCR
3. Creates GitHub Release with auto-generated changelog
4. Updates `CHANGELOG.md`
5. Tags the release

### Manual

```bash
# Trigger release workflow
gh workflow run release.yml \
  -f version=v0.16.0 \
  -f prerelease=false
```

### Deploy to staging

```bash
# Trigger deploy workflow
gh workflow run deploy.yml \
  -f environment=staging \
  -f image_tag=v0.16.0
```

### Deploy to production

```bash
gh workflow run deploy.yml \
  -f environment=production \
  -f image_tag=v0.16.0
```

## Required GitHub Secrets

| Secret | Purpose |
|--------|---------|
| `DEPLOY_HOST` | SSH host for deployment |
| `DEPLOY_USER` | SSH username |
| `DEPLOY_SSH_KEY` | SSH private key |
| `GITHUB_TOKEN` | Auto-provided — GHCR push, releases |

## Disaster Recovery Test

```bash
# Run DR test (backup → destroy → restore → verify)
bash scripts/dr-test.sh
```
