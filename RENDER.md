# UTOS — Render Deployment Guide

Deploy UTOS Trading Engine ke Render (free tier) sebagai alternatif/paralel Fly.io.

## Free Tier Limitations

| Service | Free Tier Limit |
|---|---|
| Web Service | 512MB RAM, 0.1 CPU, **spin-down setelah 15min idle** |
| PostgreSQL | 256MB storage, **expired setelah 30 hari** |
| Redis | 25MB, **no persistence** |

> **Note:** Free tier cocok untuk staging/testing. Untuk production, upgrade ke Starter ($7/bln per service).

## Prerequisites

1. Akun [render.com](https://render.com) (bisa login dengan GitHub)
2. Repo UTOS sudah di-push ke GitHub
3. Tidak perlu install CLI — Render deploy via dashboard atau blueprint

## Quick Deploy via Blueprint

### Step 1: Create Blueprint

1. Buka [dashboard.render.com](https://dashboard.render.com)
2. Klik **New +** → **Blueprint**
3. Pilih repo GitHub: `andra2112s/Utos`
4. Render akan detect `render.yaml` otomatis
5. Review services yang akan dibuat:
   - `utos-postgres` (PostgreSQL free)
   - `utos-redis` (Redis free)
   - `utos-backend` (Web service free)
   - `utos-frontend` (Web service free)

### Step 2: Set Secret Variables

Render akan prompt untuk `sync: false` variables:

**Backend:**
| Variable | Value |
|---|---|
| `SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `CORS_ORIGINS` | (isi setelah frontend URL diketahui, misal: `https://utos-frontend.onrender.com`) |

**Frontend:**
| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://utos-backend.onrender.com` (URL backend Render) |

### Step 3: Deploy

1. Klik **Apply**
2. Render akan provision semua services sekaligus
3. Tunggu build selesai (~5-10 menit untuk first deploy)
4. `preDeployCommand` di backend akan run `alembic upgrade head` otomatis

### Step 4: Get URLs & Update CORS

1. Setelah deploy selesai, catat URLs:
   - Backend: `https://utos-backend.onrender.com`
   - Frontend: `https://utos-frontend.onrender.com`
2. Update `CORS_ORIGINS` di backend service → set ke URL frontend
3. Update `NEXT_PUBLIC_API_URL` di frontend service → set ke URL backend
4. Redeploy both services

## Manual Deploy (tanpa blueprint)

### 1. Create PostgreSQL

1. Dashboard → **New +** → **PostgreSQL**
2. Name: `utos-postgres`
3. Plan: **Free**
4. Database name: `utos`
5. Save → catat **Internal Database URL** (format: `postgres://...`)

### 2. Create Redis

1. Dashboard → **New +** → **Redis**
2. Name: `utos-redis`
3. Plan: **Free**
4. Save → catat **Internal Redis URL**

### 3. Create Backend

1. Dashboard → **New +** → **Web Service**
2. Connect repo: `andra2112s/Utos`
3. Name: `utos-backend`
4. Runtime: **Docker**
5. Dockerfile Path: `docker/backend.Dockerfile`
6. Docker Context: `.`
7. Plan: **Free**
8. Environment Variables:

| Key | Value |
|---|---|
| `DATABASE_URL` | (PostgreSQL internal URL dari step 1) |
| `REDIS_URL` | (Redis internal URL dari step 2) |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `APP_ENV` | `staging` |
| `DEBUG` | `false` |
| `LOG_FORMAT` | `json` |
| `CORS_ORIGINS` | `https://utos-frontend.onrender.com` |
| `OTEL_ENABLED` | `false` |
| `PYTHONPATH` | `/app/backend` |

9. Advanced → **Pre-Deploy Command**: `cd backend && alembic upgrade head`
10. Health Check Path: `/health`
11. Create Web Service

### 4. Create Frontend

1. Dashboard → **New +** → **Web Service**
2. Connect repo: `andra2112s/Utos` (same repo)
3. Name: `utos-frontend`
4. Runtime: **Docker**
5. Dockerfile Path: `frontend/Dockerfile.prod`
6. Docker Context: `.`
7. Plan: **Free**
8. Environment Variables:

| Key | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://utos-backend.onrender.com` |
| `NODE_ENV` | `production` |

9. Health Check Path: `/`
10. Create Web Service

## Environment Variables Reference

### Backend (`utos-backend`)

```env
DATABASE_URL=<from postgres service>
REDIS_URL=<from redis service>
SECRET_KEY=<generate-64-char-hex>
APP_ENV=staging
DEBUG=false
LOG_FORMAT=json
CORS_ORIGINS=https://utos-frontend.onrender.com
OTEL_ENABLED=false
PYTHONPATH=/app/backend
```

> `DATABASE_URL` dari Render formatnya `postgres://...` — backend auto-convert ke `postgresql+asyncpg://` (sudah ditangani di `config.py`).

### Frontend (`utos-frontend`)

```env
NEXT_PUBLIC_API_URL=https://utos-backend.onrender.com
NODE_ENV=production
```

## Verify Deployment

```bash
# Backend health
curl https://utos-backend.onrender.com/health

# Backend liveness
curl https://utos-backend.onrender.com/live

# Backend docs
open https://utos-backend.onrender.com/docs

# Frontend
open https://utos-frontend.onrender.com
```

## Known Limitations (Free Tier)

1. **Spin-down:** Web services sleep setelah 15 menit idle. First request setelah sleep butuh ~30 detik untuk wake up.
2. **PostgreSQL expired 30 hari:** Free Postgres akan dihapus setelah 30 hari. Backup data sebelum expired, atau upgrade ke paid plan.
3. **Redis 25MB:** Cukup untuk staging, tidak ada persistence (data hilang saat restart).
4. **No custom domain di free tier:** URL default `*.onrender.com`.

## Troubleshooting

### Backend tidak bisa connect DB
- Pastikan `DATABASE_URL` menggunakan **Internal Database URL** (bukan External)
- Backend auto-convert `postgres://` → `postgresql+asyncpg://`, tidak perlu manual

### Migration gagal
- Cek logs di dashboard: service → Logs
- Run manual via **Shell** (tab di dashboard): `cd backend && alembic upgrade head`

### Frontend build error
- Pastikan `frontend/Dockerfile.prod` digunakan (bukan `frontend/Dockerfile`)
- `NEXT_PUBLIC_API_URL` harus di-set **sebelum** build (Next.js bake env var saat build time)
- Jika ganti `NEXT_PUBLIC_API_URL`, perlu **manual rebuild** (bukan redeploy)

### Health check fail
- Backend: pastikan `/health` return 200 (butuh DB + Redis connected)
- Frontend: pastikan port 3000 exposed dan `node server.js` running

## Cost: Free → Paid Upgrade Path

| Service | Free | Starter | Standard |
|---|---|---|---|
| Backend | $0 (spin-down) | $7/bln | $25/bln |
| Frontend | $0 (spin-down) | $7/bln | $25/bln |
| PostgreSQL | $0 (30hari) | $7/bln | $20/bln |
| Redis | $0 (25MB) | $10/bln | $30/bln |
| **Total Free** | **$0** | | |
| **Total Starter** | | **$31/bln** | |

## Files yang Ditambahkan

| File | Fungsi |
|---|---|
| `render.yaml` | Blueprint config — 4 services dalam 1 file |
| `frontend/Dockerfile.prod` | Production Dockerfile Next.js (sudah ada dari Railway setup) |
| `backend/core/config.py` (modified) | Auto-convert `postgres://` dan `postgresql://` → `postgresql+asyncpg://` |
