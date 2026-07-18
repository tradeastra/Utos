# UTOS — Railway Deployment Guide

Railway deployment guide untuk UTOS Trading Engine (backend + frontend + PostgreSQL + Redis).

## Prerequisites

1. Install Railway CLI: `npm install -g @railway/cli`
2. Login: `railway login`
3. Pastikan repo sudah di-push ke GitHub/GitLab

## Quick Start

```bash
# 1. Buat project baru di Railway
railway init

# 2. Tambahkan PostgreSQL (Railway provision otomatis)
railway add --plugin postgresql

# 3. Tambahkan Redis
railway add --plugin redis

# 4. Deploy backend (service utama)
railway up

# 5. Deploy frontend (service terpisah)
railway up --service frontend
```

## Step-by-Step via Dashboard

### 1. Buat Project & Database

1. Buka [railway.app](https://railway.app) → **New Project**
2. Pilih **Empty Project**
3. Klik **+ Add** → pilih **PostgreSQL** → Railway provision otomatis
4. Klik **+ Add** → pilih **Redis** → Railway provision otomatis
5. Catat nama service PostgreSQL dan Redis (misal: `PostgreSQL`, `Redis`)

### 2. Deploy Backend

1. Klik **+ Add** → **GitHub Repo** → pilih repo UTOS
2. Railway akan detect `railway.toml` dan menggunakan `docker/backend.Dockerfile`
3. **Set environment variables** (di tab Variables):

| Variable | Value | Source |
|---|---|---|
| `DATABASE_URL` | *(reference dari PostgreSQL service)* | `${{PostgreSQL.DATABASE_URL}}` |
| `REDIS_URL` | *(reference dari Redis service)* | `${{Redis.REDIS_URL}}` |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` | Generate sendiri |
| `APP_ENV` | `staging` | Manual |
| `DEBUG` | `false` | Manual |
| `LOG_FORMAT` | `json` | Manual |
| `CORS_ORIGINS` | `https://utos-frontend.up.railway.app` | URL frontend Railway |
| `OTEL_ENABLED` | `false` | Manual |

> **Note:** `DATABASE_URL` dari Railway PostgreSQL formatnya `postgresql://...` — backend auto-convert ke `postgresql+asyncpg://` (sudah ditangani di `config.py`).

4. Railway akan auto-deploy. `preDeployCommand` di `railway.toml` akan run `alembic upgrade head` sebelum app start.
5. Cek **Deployments** tab — health check di `/health` akan dipantau otomatis.

### 3. Deploy Frontend

1. Klik **+ Add** → **GitHub Repo** → pilih repo UTOS yang sama
2. Rename service menjadi `frontend`
3. **Set root directory**: Settings → Build → Root Directory = `/` (root repo)
4. **Set Dockerfile path**: Settings → Build → Dockerfile = `frontend/Dockerfile.prod`
5. **Set environment variables**:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://utos-backend.up.railway.app` (URL backend Railway) |
| `NODE_ENV` | `production` |

6. Deploy — frontend akan build dengan Next.js standalone output.

### 4. Generate Domain

1. Backend service → Settings → **Generate Domain**
2. Frontend service → Settings → **Generate Domain**
3. Update `CORS_ORIGINS` di backend dengan URL frontend Railway
4. Update `NEXT_PUBLIC_API_URL` di frontend dengan URL backend Railway

## Environment Variables Reference

### Backend

```env
DATABASE_URL=${{PostgreSQL.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SECRET_KEY=<generate-with-secrets-token-hex-32>
APP_ENV=staging
DEBUG=false
LOG_FORMAT=json
CORS_ORIGINS=https://utos-frontend.up.railway.app
OTEL_ENABLED=false
```

### Frontend

```env
NEXT_PUBLIC_API_URL=https://utos-backend.up.railway.app
NODE_ENV=production
```

## CLI Commands

```bash
# Install CLI
npm install -g @railway/cli

# Login
railway login

# Link existing project
railway link

# Deploy backend
railway up

# Deploy frontend (if separate service)
railway up --service frontend

# View logs
railway logs

# Open shell
railway shell

# Check status
railway status
```

## Troubleshooting

### Backend tidak bisa connect DB
- Pastikan `DATABASE_URL` di-set sebagai **reference variable** ke PostgreSQL service: `${{PostgreSQL.DATABASE_URL}}`
- Backend auto-convert `postgresql://` → `postgresql+asyncpg://`, tidak perlu manual

### Migration gagal
- Cek logs: `railway logs`
- Run manual: `railway shell` → `cd backend && alembic upgrade head`

### Frontex build error
- Pastikan `frontend/Dockerfile.prod` digunakan (bukan `frontend/Dockerfile` yang masih `npm run dev`)
- Pastikan `NEXT_PUBLIC_API_URL` di-set sebelum build (Next.js bake env var saat build time)

### Health check fail
- Backend: pastikan `/health` return 200 (butuh DB + Redis connected)
- Frontend: pastikan port 3000 exposed dan `node server.js` running

## Cost Estimate (Railway Hobby Plan)

| Service | Resource | Est. Cost |
|---|---|---|
| PostgreSQL | 512MB RAM | ~$5/mo |
| Redis | 256MB RAM | ~$3/mo |
| Backend | 512MB RAM | ~$5/mo |
| Frontend | 256MB RAM | ~$3/mo |
| **Total** | | **~$16/mo** |

> Railway Hobby Plan: $5/mo includes 500 execution hours + 1GB RAM. Additional usage billed per GB-hour.

## File yang Ditambahkan

| File | Fungsi |
|---|---|
| `railway.toml` | Config backend service (Dockerfile path, healthcheck, pre-deploy migration) |
| `railway.frontend.toml` | Config frontend service |
| `frontend/Dockerfile.prod` | Production Dockerfile untuk Next.js (multi-stage, standalone) |
| `backend/core/config.py` (modified) | Auto-convert `postgresql://` → `postgresql+asyncpg://` |
