# UTOS — Platform Deployment Comparison

> Dokumen perbandingan platform hosting untuk UTOS Project  
> Dibuat: 18 Juli 2026  
> Status: Research/Reference

---

## Table of Contents

1. [Cloud Service Models (IaaS, PaaS, BaaS, SaaS)](#1-cloud-service-models)
2. [Platform Comparison Summary](#2-platform-comparison-summary)
3. [Railway](#3-railway)
4. [Fly.io](#4-flyio)
5. [Render](#5-render)
6. [Supabase](#6-supabase)
7. [Vercel](#7-vercel)
8. [Cost Comparison for UTOS Stack](#8-cost-comparison-for-utos-stack)
9. [Scaling Comparison](#9-scaling-comparison)
10. [Hidden Costs](#10-hidden-costs)
11. [UTOS Frontend Stack](#11-utos-frontend-stack)
12. [UTOS User Management Architecture](#12-utos-user-management-architecture)
13. [Final Recommendation](#13-final-recommendation)
14. [Deployment Strategy: Railway Dulu, Fly.io Nanti](#14-deployment-strategy-railway-dulu-flyio-nanti)
15. [Scaling to 100,000 Users: Long-Term Architecture](#15-scaling-to-100000-users-long-term-architecture)

---

## 1. Cloud Service Models

```
Layer Technology Stack:

On-Premise  → Anda install semua: server, OS, DB, runtime, app
IaaS        → Cloud provider kasih server + OS (AWS EC2, DigitalOcean)
PaaS        → Cloud provider kasih server + OS + runtime + DB (Railway, Fly.io, Render, Heroku)
BaaS        → Cloud provider kasih backend siap pakai: DB + Auth + API (Supabase, Firebase)
SaaS        → Cloud provider kasih aplikasi jadi tinggal pakai (Gmail, Notion, Slack)
```

| Layer | Yang Anda Manage | Yang Provider Manage | Contoh |
|---|---|---|---|
| On-Premise | Semua | Tidak ada | Server di rumah/kantor |
| IaaS | OS, runtime, DB, app | Hardware, network, power | AWS EC2, DigitalOcean Droplet |
| PaaS | App + data | Hardware, OS, runtime, DB | Railway, Fly.io, Render, Heroku |
| BaaS | App logic (sedikit) | Hardware, OS, DB, Auth, API | Supabase, Firebase |
| SaaS | Tidak ada | Semua | Gmail, Notion, Trello |

**UTOS = SaaS yang dibangun di atas PaaS.** User management, subscription, billing di-handle oleh backend UTOS sendiri. PaaS hanya sebagai infra hosting.

---

## 2. Platform Comparison Summary

| Platform | Type | Bisa Host UTOS Lengkap? | Best For |
|---|---|---|---|
| **Railway** | PaaS | ✅ Ya (all-in-one) | Start → mid-scale, simplest |
| **Fly.io** | PaaS | ✅ Ya (all-in-one) | Large-scale, multi-region |
| **Render** | PaaS | ✅ Ya (all-in-one) | Frontend + compliance murah |
| **Supabase** | BaaS | ❌ Tidak (DB + Auth only) | Backend-as-a-Service |
| **Vercel** | Frontend + Serverless | ❌ Tidak (frontend only) | Next.js frontend hosting |

---

## 3. Railway

### Pricing Model
- Subscription + usage-based, billed per second
- Subscription fee = minimum usage commitment

| Plan | Price | Included Usage | Max Services |
|---|---|---|---|
| Free | $0/bln | $1 credit/bln | 5 projects, 5 services/project |
| Hobby | $5/bln | $5 usage credit | Unlimited |
| Pro | $20/bln per seat | $20 usage credit | Unlimited |
| Enterprise | Custom | Custom | Unlimited |

### Resource Rates
| Resource | Rate |
|---|---|
| RAM | $10/GB/bulan |
| CPU | $20/vCPU/bulan |
| Egress | $0.05/GB |
| Volume Storage | $0.15/GB/bulan |

### Plan Resource Limits
| Plan | Max Replicas | Max RAM | Max CPU | Volume Storage |
|---|---|---|---|---|
| Free | 1 | 0.5 GB | 1 vCPU | 0.5 GB |
| Hobby | 6 | 48 GB | 48 vCPU | 5 GB |
| Pro | 42 | 1 TB | 1,000 vCPU | 1 TB |
| Enterprise | 50 | 2.4 TB | 2,400 vCPU | 5 TB |

### Features
- Deploy dari GitHub: auto-deploy on push, PR preview environments
- Deploy dari Docker: auto-detect Dockerfile
- Managed PostgreSQL: 1-click deploy, backup + PITR
- Managed Redis: 1-click deploy
- Visual canvas dashboard, real-time, collaborative
- Infra-as-Code: TOML/JSON config
- Custom domain + auto TLS: unlimited (Hobby+)
- Private networking: Pro+ only ($20)
- Auto-scaling: based on metrics
- Auto-stop idle: serverless mode
- Log retention: 7 days (Free), 30 days (Hobby), 90 days (Pro)
- Image retention: 24h (Free), 72h (Hobby), 120h (Pro), 360h (Enterprise)

### Hobby Plan — Bisa Production?
Ya, tidak ada larangan teknis. Trade-off:
- Tidak ada private networking (traffic antar service = egress charge)
- Log hanya 30 hari
- Tidak ada priority support
- Tidak ada concurrent global regions

### Railway untuk UTOS
```
Railway Project: UTOS
├── Service: PostgreSQL (managed, 1-click)
├── Service: Redis (managed, 1-click)
├── Service: Backend — FastAPI (from GitHub/Docker)
└── Service: Frontend — Next.js (from GitHub/Docker)
```
- Semua dalam 1 project, 1 dashboard, 1 bill
- Service-to-service via internal variables (Hobby) atau private networking (Pro)
- Auto connection string: DATABASE_URL, REDIS_URL
- Managed DB: backup + PITR built-in

---

## 4. Fly.io

### Pricing Model
- Pure pay-as-you-go, per second, per organization
- Tidak ada subscription minimum (kecuali support plan)
- Bisa commit upfront untuk diskon 40%

### Compute Pricing (per machine, always-on)
| Preset | RAM | Price/month |
|---|---|---|
| shared-cpu-1x | 256MB | ~$2 |
| shared-cpu-1x | 512MB | ~$3 |
| shared-cpu-1x | 1GB | ~$6 |
| shared-cpu-1x | 2GB | ~$11 |
| shared-cpu-2x | 1GB | ~$7 |
| performance-1x | 2GB | ~$32 |

### Other Rates
| Resource | Rate |
|---|---|
| Egress (NA/EU) | $0.02/GB |
| Egress (Asia) | >$0.02/GB (lebih mahal) |
| Volume Storage | $0.15/GB/bulan |
| Stopped machine rootfs | $0.15/GB/bulan |
| IPv4 dedicated | $2/bln |
| Support Standard | $29/bln |
| Support Premium | $149/bln |
| Compliance (HIPAA/SOC2) | $99/bln |

### Features
- 30+ region bare metal sendiri
- Anycast IPv6 gratis, edge routing built-in
- Private networking: gratis (WireGuard-based)
- Custom domains + SSL: gratis
- GPU support: A100, L4
- Auto-stop idle machines
- Metrics-based autoscaler (bisa create/destroy machines)
- Unlimited machines per app
- CLI-first workflow (flyctl)
- Fly Postgres (semi-managed)
- Docker-based deployment

### Limitations
- Tidak ada free tier (butuh credit card)
- Tidak ada PR preview environments
- Tidak ada 1-click managed DB (perlu setup manual)
- Tidak ada visual canvas dashboard
- Stopped machine tetap bayar (rootfs + volume)
- Volume orphaned tetap bayar

---

## 5. Render

### Pricing Model
- Workspace plan + compute per service
- Compute prorated per second

| Plan | Price | Max Services | Bandwidth Included |
|---|---|---|---|
| Hobby | $0 + compute | 25 | 5 GB |
| Pro | $25/bln flat | Unlimited | 25 GB |
| Scale | $499/bln flat | Unlimited | 1 TB |
| Enterprise | Custom | Unlimited | Custom |

### Compute Pricing (per service, always-on)
| Instance | RAM | CPU | Price/month |
|---|---|---|---|
| Free | 512MB | 0.1 | $0 (spin-down 15min idle) |
| Starter | 512MB | 0.5 | $7 |
| Standard | 2GB | 1 | $25 |
| Pro | 4GB | 2 | $85 |
| Pro Plus | 8GB | 4 | $175 |
| Pro Max | 16GB | 4 | $225 |
| Pro Ultra | 32GB | 8 | $450 |

### Other Rates
| Resource | Rate |
|---|---|
| Egress | $0.15/GB (paling mahal!) |
| Persistent disk | $0.25/GB/bulan |
| Postgres storage | $0.30/GB/bulan |
| Custom domain (extra) | $0.25/domain/bulan |
| Dedicated IP (Pro+) | $100/bln |
| Build minutes overage | $5/1000 min |

### Features
- Managed PostgreSQL: PITR 3-7 hari, read replicas, HA
- Managed Redis (Render Key Value)
- Free Postgres: 256MB, expired 30 hari
- Free Redis: 25MB, no persistence
- Zero-config CDN: gratis
- DDoS mitigation: gratis
- Private networking: gratis (semua plan)
- Global regions
- PR preview: single (Hobby), full-stack (Pro+)
- Horizontal autoscaling: Pro+ ($25)
- Compliance: SOC 2 + ISO 27001 di Pro ($25)
- HIPAA: Scale ($499)
- SSO/SAML: Scale ($499)

### Limitations
- Egress $0.15/GB — 3x Railway, 7.5x Fly.io
- Free web services spin-down 15 menit idle
- Free Postgres expired 30 hari
- Compute paling mahal dibanding Railway/Fly.io
- Custom domain $0.25/domain/bln (Railway/Fly.io gratis)

---

## 6. Supabase

### Penting: Supabase BUKAN General-Purpose Hosting
Supabase adalah Backend-as-a-Service (BaaS) — bukan platform hosting untuk deploy app arbitrary.

### Supabase Provide vs Tidak Provide
| Provide | Tidak Provide |
|---|---|
| Managed PostgreSQL | Hosting FastAPI/Python |
| Auth (JWT, OAuth, MFA, SAML) | Hosting Next.js |
| Storage (S3-compatible) | Redis |
| Edge Functions (Deno only) | Docker container hosting |
| Realtime subscriptions | WebSocket server custom |
| REST/GraphQL API auto-generated | Background workers (Python) |

### Pricing
| Plan | Price | Database | Egress | MAU | Storage |
|---|---|---|---|---|---|
| Free | $0 | 500MB | 5GB | 50,000 | 1GB |
| Pro | $25/bln | 8GB | 250GB | 100,000 | 100GB |
| Team | $599/bln | 8GB | 250GB | 100,000 | 100GB |
| Enterprise | Custom | Custom | Custom | Custom | Custom |

### Compute (per project, billed hourly)
| Size | $/bln | CPU | RAM |
|---|---|---|---|
| Micro (include Pro) | $10 | 2-core ARM shared | 1GB |
| Small | $15 | 2-core ARM shared | 2GB |
| Medium | $60 | 2-core ARM shared | 4GB |
| Large | $110 | 2-core ARM dedicated | 8GB |
| XL | $210 | 4-core ARM dedicated | 16GB |
| 2XL | $410 | 8-core ARM dedicated | 32GB |

### Add-ons
| Add-on | Price |
|---|---|
| PITR | $100/bln per 7 days retention |
| Custom domain | $10/domain/bln |
| IPv4 | $4/bln |
| Database branching | $0.013/hr per branch |
| Log drains | $60/drain/bln + $0.20/juta events |

### Hidden Costs
- Egress overage: $0.09/GB setelah 250GB (Pro)
- Compute per project: 3 projects = 3x compute
- DB branching: $0.013/hr per branch = ~$10/bln per branch
- PITR: $100/bln (Railway/Fly.io include gratis)
- Custom domain: $10/bln (Railway/Fly.io gratis)
- Free tier pause: 1 minggu inactivity → DB paused

### Supabase untuk UTOS
- TIDAK bisa standalone — butuh platform lain untuk FastAPI + Next.js + Redis
- UTOS sudah punya JWT auth sendiri → Supabase Auth redundant
- UTOS butuh Redis → Supabase tidak provide
- UTOS butuh always-on DB → Free tier pause = problem
- Hybrid (Supabase + Railway + Upstash) = lebih mahal + complex

### Supabase cocok untuk:
- Project baru tanpa backend custom
- Butuh RLS (Row Level Security)
- Butuh realtime subscriptions
- Butuh auto-generated REST/GraphQL API
- App yang fit around BaaS model

---

## 7. Vercel

### Penting: Vercel BUKAN General-Purpose Hosting
Vercel adalah Frontend-as-a-Service + Serverless Functions — bukan platform untuk host backend always-on.

### Vercel Bisa vs Tidak Bisa
| Bisa | Tidak Bisa |
|---|---|
| Next.js / React / Vue / Svelte frontend | Python FastAPI (always-on server) |
| Serverless Functions (cold start, timeout) | Long-running process (trading bot) |
| Static sites + SSR + ISR | Redis |
| Edge Functions (Deno) | WebSocket server persistent |
| CDN global + DDoS protection | Background workers 24/7 |
| Preview deployments per PR | Managed PostgreSQL |

### Pricing
| Plan | Price | Target |
|---|---|---|
| Hobby | $0 | Personal, non-commercial only |
| Pro | $20/seat/bln + $20 usage credit | Team, commercial |
| Enterprise | Custom | SLA, SSO, dedicated support |

### Hobby Limits
| Resource | Limit |
|---|---|
| Bandwidth | 100 GB |
| Edge requests | 1,000,000 |
| Function invocations | 1,000,000 |
| Active CPU | 4 hours/bln |
| Function timeout | 60 seconds |
| Blob storage | 1 GB |
| Projects | 200 |

### Pro Limits
| Resource | Limit |
|---|---|
| Bandwidth | 1 TB (lalu on-demand) |
| Edge requests | 10,000,000 |
| Function timeout | 300 seconds (5 menit) |
| Active CPU | Usage-based ($0.128/hr) |
| Function invocations | $0.60/juta |

### Mengapa Vercel TIDAK Cocok untuk UTOS Backend
- Tidak bisa host FastAPI (always-on) — Vercel = serverless
- Tidak bisa trading bot — butuh 24/7 process
- Tidak bisa WebSocket — UTOS butuh real-time market data
- Tidak ada Redis
- Tidak ada PostgreSQL managed
- Hobby = non-commercial (UTOS = SaaS komersial, harus Pro $20)
- 60 detik timeout (Hobby) — API call ke exchange bisa >60 detik
- Cold start 500ms-3s — problem untuk trading

### Vercel HANYA Cocok untuk Frontend UTOS
- Creator of Next.js → native support
- CDN global: 100+ edge locations, gratis
- ISR / SSR / SSG: native
- Image optimization: built-in
- PR preview: best in class, password-protectable
- DDoS + WAF: built-in
- Analytics: Web Vitals + traffic insights

### Vercel untuk UTOS Frontend (opsional)
Frontend UTOS bisa deploy di Vercel tanpa masalah karena Next.js native. Tapi:
- Hobby dilarang untuk komersial → harus Pro $20
- Pro $20 (frontend) + Railway $5 (backend+DB) = $25/bln total
- Railway saja = $5-8/bln untuk semua

---

## 8. Cost Comparison for UTOS Stack

### UTOS Stack: 4 Services (FastAPI + Next.js + PostgreSQL + Redis, always-on)

| Approach | Cost/bln | Platforms | Complexity |
|---|---|---|---|
| **Railway saja (all-in-one)** | $5-8 | 1 | Rendah |
| **Fly.io saja (all-in-one)** | $14-20 | 1 | Sedang |
| **Render saja (all-in-one)** | $20-35 | 1 | Rendah |
| **Vercel + Railway (hybrid)** | $25-27 | 2 | Sedang |
| **Supabase Free + Railway** | $7-10 | 2 | Tinggi |
| **Supabase Pro + Railway** | $30-35 | 2 | Tinggi |
| **Vercel + Supabase + Railway + Upstash** | $25-62 | 4 | Sangat tinggi |

### Detailed Breakdown

#### Railway Hobby ($5/bln)
| Service | Estimasi |
|---|---|
| Backend (FastAPI) | ~$3/bln |
| Frontend (Next.js) | ~$2/bln |
| PostgreSQL (managed) | include |
| Redis (managed) | include |
| **Total** | **~$5-8/bln** |

#### Fly.io (pay-as-you-go)
| Service | Estimasi |
|---|---|
| Backend (FastAPI) | ~$3-4/bln |
| Frontend (Next.js) | ~$2/bln |
| PostgreSQL (Fly Postgres) | ~$6-7/bln |
| Redis | ~$3/bln |
| **Total** | **~$14-20/bln** |

#### Render
| Service | Estimasi |
|---|---|
| Backend (FastAPI) | $7/bln (Starter) |
| Frontend (Next.js) | Free ($0, tapi spin-down) |
| PostgreSQL | Free (30 hari, lalu upgrade) |
| Redis | Free (25MB, no persistence) |
| **Total realistic** | **~$20-35/bln** |

---

## 9. Scaling Comparison

### Horizontal Scaling (banyak instances)
| Aspek | Railway | Fly.io | Render |
|---|---|---|---|
| Max replicas/machines | 6-50 | Unlimited | Unlimited (Pro+) |
| Auto-scaling | Metrics-based | Metrics-based autoscaler | Pro+ ($25) |
| Multi-region replicas | Pro+ ($20) | Native, gratis | Global regions |
| Speed scale up | Detik | Detik (Firecracker microVM) | Detik |

**Fly.io menang** — unlimited machines, multi-region native.

### Vertical Scaling (resource per instance)
| Aspek | Railway | Fly.io | Render |
|---|---|---|---|
| Max CPU | 2,400 vCPU (Enterprise) | 16 vCPU | 64 vCPU (Custom) |
| Max RAM | 2.4 TB (Enterprise) | 128 GB | 512 GB (Custom) |
| GPU | Tidak ada | A100, L4 | Tidak ada |

**Railway menang** untuk max resource (Enterprise). **Fly.io menang** untuk GPU.

### Multi-Region / Global
| Aspek | Railway | Fly.io | Render |
|---|---|---|---|
| Region choice | Multi-cloud (AWS, GCP, Azure) | 30+ region bare metal | Global regions |
| Latency | Bergantung cloud provider | Lebih rendah (bare metal + Anycast) | Standar |
| Multi-region deploy | Pro+ ($20) | Gratis | Gratis |
| Edge routing | Tidak ada | Anycast IPv6 gratis | Zero-config CDN gratis |
| Data residency | Pilih region, terbatas | 30+ region, granular per machine | Global regions |

**Fly.io menang telak** untuk multi-region.

### Cost saat Scale Up (10 services, 1 vCPU + 1GB RAM each, 24/7)
| | Railway Pro | Fly.io | Render Pro |
|---|---|---|---|
| Base subscription | $20/bln | $0 | $25/bln |
| Compute (10 services) | ~$300/bln | ~$80/bln | ~$250/bln |
| Included credit | -$20 | $0 | $0 |
| Egress (100GB) | $5 | $2 | $15 |
| **Total** | **~$285/bln** | **~$82/bln** | **~$290/bln** |

**Fly.io jauh lebih murah saat scale up** — ~3x lebih murah.

### Database Scaling
| Aspek | Railway | Fly.io | Render |
|---|---|---|---|
| Managed Postgres | 1-click, PITR, backup | Fly Postgres, multi-region | Managed, PITR, read replicas, HA |
| Read replicas | Tidak | Bisa setup | Pro+ |
| Connection pooling | Built-in | PgBouncer manual | Built-in |
| Redis cluster | Single instance | Bisa setup cluster | Render Key Value |

### Networking saat Scale
| Aspek | Railway | Fly.io | Render |
|---|---|---|---|
| Private networking | Pro+ ($20) | Gratis | Gratis |
| Egress rate | $0.05/GB | $0.02/GB | $0.15/GB |
| Load balancing | Built-in per service | Built-in (Anycast) | Built-in |
| CDN | Tidak ada | Tidak ada | Zero-config CDN gratis |
| DDoS protection | Tidak ada | Tidak ada | Gratis |

### Compliance & Enterprise
| Aspek | Railway | Fly.io | Render | Supabase | Vercel |
|---|---|---|---|---|---|
| SOC 2 | Enterprise | $99/bln add-on | Pro ($25) | Team ($599) | Enterprise |
| ISO 27001 | Tidak | Tidak | Pro ($25) | Team ($599) | Enterprise |
| HIPAA | $1000 committed | $99/bln add-on | Scale ($499) | Team ($599) | $350/bln add-on |
| SSO/SAML | $2000 committed | Gratis | Scale ($499) | Team ($599) | $300/bln add-on |
| RBAC | $2000 committed | Gratis (ACLs) | Scale ($499) | Team ($599) | Enterprise |
| Audit logs | $2000 committed | Tidak | Pro ($25) | Team ($599) | Enterprise |

**Render paling accessible untuk compliance** — SOC 2 + ISO 27001 di Pro $25.

---

## 10. Hidden Costs

### Railway
| Hidden Cost | Detail |
|---|---|
| Egress antar service (public URL) | $0.05/GB — Hobby tidak ada private networking |
| Overage charge | Usage > $5 (Hobby) → bayar selisih, per detik |
| Volume storage tetap jalan | $0.15/GB/bln walau service di-pause |
| Multiple replicas = multiply cost | 3 replicas x 1GB RAM = bayar 3GB |

**Hidden cost terbesar: Tidak ada private networking di Hobby.** Semua komunikasi backend ↔ Postgres ↔ Redis = egress charge $0.05/GB.

### Fly.io
| Hidden Cost | Detail |
|---|---|
| Stopped machine tetap bayar | $0.15/GB/bln untuk rootfs storage |
| Volume tetap bayar walau machine stop | $0.15/GB/bln, tidak peduli running atau tidak |
| Volume snapshot billing (Jan 2026) | Incremental snapshot storage charge |
| Additional RAM | ~$5/GB/30hari di atas preset default |
| IPv4 dedicated | $2/bln (shared IPv4 = gratis, IPv6 = gratis) |
| Egress di region non-NA/EU | >$0.02/GB di Asia/Australia |
| Metrics autoscaler create machines | Bisa create machine baru = biaya tak terduga |

**Hidden cost terbesar: Volume + stopped machine tetap bayar.**

### Render
| Hidden Cost | Detail |
|---|---|
| Egress | $0.15/GB (paling mahal!) |
| Custom domain extra | $0.25/domain/bln |
| Persistent disk | $0.25/GB/bln |
| Postgres storage | $0.30/GB/bln |
| Build minutes overage | $5/1000 min |
| Free DB expired | 30 hari lalu harus upgrade |
| Free service spin-down | 15min idle → sleep |
| Dedicated IP | $100/bln (Pro+) |

### Supabase
| Hidden Cost | Detail |
|---|---|
| Egress overage | $0.09/GB setelah 250GB (Pro) |
| Compute per project | 3 projects = 3x compute |
| DB branching | $0.013/hr per branch = ~$10/bln per branch |
| PITR | $100/bln |
| Custom domain | $10/domain/bln |
| IPv4 | $4/bln |
| Log drains | $60/drain/bln + $0.20/juta events |
| Free tier pause | 1 minggu inactivity → DB paused |

### Vercel
| Hidden Cost | Detail |
|---|---|
| Hobby = non-commercial | UTOS = SaaS komersial, harus Pro $20 |
| Active CPU limit | 4 hours/bln (Hobby) — cepat habis untuk serverless |
| Function timeout | 60s (Hobby), 300s (Pro) |
| Cold start | 500ms-3s delay setiap cold invocation |
| Pro seat | $20/seat/bln (deploying member) |
| SSO add-on | $300/bln |
| HIPAA add-on | $350/bln |
| Static IPs | $100/bln per project |

### Tips Hindari Hidden Costs

**Railway:**
- Upgrade ke Pro ($20) untuk private networking → egress DB = $0
- Monitor usage dashboard secara berkala
- Hapus service/volume yang tidak dipakai
- Set usage limits untuk cap spending

**Fly.io:**
- `fly machine destroy` bukan `fly machine stop` kalau tidak dipakai
- Hapus volume yang tidak attached: `fly volumes remove`
- Pakai shared IPv4 (gratis) kecuali exchange butuh dedicated IPv4
- Deploy di region NA/EU untuk egress termurah
- Matikan auto-snapshot kalau tidak perlu

**Render:**
- Hindari untuk bandwidth-heavy app (egress $0.15/GB)
- Upgrade ke Pro ($25) untuk unlimited services + no spin-down
- Hapus free DB sebelum expired 30 hari

---

## 11. UTOS Frontend Stack

### Teknologi Frontend
| Teknologi | Versi | Fungsi |
|---|---|---|
| Next.js | 15.5.20 | Framework utama (App Router) |
| React | 18.3.1 | UI library |
| TypeScript | 5.5.3 | Type safety |
| TailwindCSS | 3.4.6 | Styling |
| Zustand | 4.5.4 | State management |
| Recharts | 2.12.7 | Chart / grafik trading |
| Lucide React | 0.408.0 | Icon library |
| Vitest | 3.2.6 | Testing |

### Konfigurasi Penting
- `output: 'standalone'` — Next.js build menjadi self-contained Docker image, portable ke platform manapun
- API proxy: `/api/:path*` → `NEXT_PUBLIC_API_URL/api/:path*` (proxy ke backend FastAPI)
- Image optimization: AVIF + WebP, cache TTL 3600s
- Compression: enabled
- React strict mode: enabled

### Deploy Frontend
- **Railway**: build dari Dockerfile (standalone), deploy sebagai service
- **Vercel**: native support (creator Next.js), tapi Pro $20 untuk komersial
- **Fly.io**: build dari Dockerfile, deploy sebagai machine
- **Render**: build dari Dockerfile, deploy sebagai web service

**Tidak perlu Vercel** karena `output: 'standalone'` = portable, Railway bisa host frontend tanpa masalah.

---

## 12. UTOS User Management Architecture

### Architecture Flow
```
Frontend (Next.js)
  │ HTTP + JWT
  ▼
API Layer (FastAPI)
  /auth/register  /auth/login  /users/me
  │
  ▼
Service Layer (SaaS)
  AuthService · SubscriptionService
  RBACService · BillingService
  │
  ▼
Repository Layer (CRUD)
  UserRepository · SubscriptionRepository
  │
  ▼
Database (PostgreSQL)
  users · subscriptions · transactions
```

### User Model (users table)
| Field | Type | Keterangan |
|---|---|---|
| id | UUID | Primary key |
| email | String(255) | Unique, untuk login |
| password_hash | String(255) | Bcrypt hash |
| full_name | String(100) | Nama lengkap |
| phone | String(20) | Nomor HP |
| is_active | Boolean | Account aktif/tidak |
| is_verified | Boolean | Email verified/tidak |
| role | Enum | user / admin |
| subscription_tier | Enum | free / basic / pro / enterprise |
| referral_code | String(20) | Kode referral unik |
| referred_by | UUID | FK ke users.id (siapa yang refer) |
| last_login_at | DateTime | Login terakhir |
| deleted_at | DateTime | Soft delete |

### User Relationships
- exchange_accounts — API keys exchange user
- trading_instances — bot trading yang running
- orders — order history
- notifications — notifikasi
- transactions — transaksi billing
- grid_profiles — konfigurasi grid bot
- subscription — 1:1 subscription aktif
- affiliate — 1:1 program affiliate

### Auth Service
- Register: validate email + password strength → hash → save to DB
- Login: verify password → generate JWT (access + refresh token)
- Token verification: decode JWT → find user → check is_active
- MFA: enable/verify/disable multi-factor auth
- Password reset: request reset token → verify → update hash
- Change password: verify old → update new

### RBAC Service — 4 Roles
| Role | Permissions |
|---|---|
| user | trade:read, account:read |
| trader | trade:create, trade:read, trade:delete, grid:manage, account:read |
| admin | All trader + risk:manage, account:manage, user:read, billing:read |
| super_admin | All admin + user:manage, billing:manage, system:manage, affiliate:manage |

### Subscription Service — 4 Tiers
| Tier | Price/bln | Target |
|---|---|---|
| free | $0 | Trial, limited features |
| starter | $29 | Individual trader |
| pro | $99 | Active trader, multi-bot |
| enterprise | $499 | Institution, unlimited |

### Subscription Operations
- create_subscription(user_id, tier, duration_days, auto_renew)
- upgrade(user_id, new_tier) — naik tier
- downgrade(user_id, new_tier) — turun tier
- cancel(user_id) — batalkan
- renew(user_id, duration_days) — perpanjang
- check_active(user_id) — cek masih aktif atau expired

### Billing Service — 4 Payment Providers
| Provider | Status |
|---|---|
| Manual | Working (mark as paid) |
| Stripe | Stub (butuh API key) |
| Midtrans | Stub (butuh server key) |
| Xendit | Stub (butuh API key) |

### Billing Flow
1. User pilih plan → create_invoice(user_id, amount, currency, plan)
2. User bayar → process_payment(invoice_id, provider_name)
3. Provider charge → return PaymentResult (success/failed)
4. Jika success → invoice.status = "paid", subscription di-upgrade

### API Endpoints
| Endpoint | Method | Auth | Function |
|---|---|---|---|
| /auth/register | POST | No | Register user baru |
| /auth/login | POST | No | Login, dapat JWT |
| /auth/refresh | POST | Refresh token | Dapat access token baru |
| /users/me | GET | JWT | Get profile sendiri |

### User Journey
1. REGISTER → POST /auth/register → user dibuat (role=user, tier=free)
2. LOGIN → POST /auth/login → dapat access_token + refresh_token
3. ACCESS → Authorization: Bearer <token> → verify JWT → check RBAC
4. UPGRADE → create_invoice → bayar via Stripe/Midtrans/Xendit → upgrade tier
5. MANAGE TRADING → connect exchange API keys → buat grid profile → start bot
6. BILLING → check_active() setiap login → expired → downgrade ke free

### Implementation Status
| Komponen | Status |
|---|---|
| User model | Complete |
| Subscription model | Complete |
| Auth service (register, login, JWT, MFA) | Complete |
| RBAC service | Complete |
| Subscription service | Complete |
| Billing service (4 provider) | Stub |
| User repository | Complete |
| Subscription repository | Complete |
| Auth endpoints | Complete |
| User endpoint (/me) | Complete |
| Payment provider integration | Stub (perlu real SDK) |
| Email verification | Stub (butuh SMTP) |
| Frontend auth pages | Ada (login, register) |

---

## 13. Final Recommendation

### Ranking untuk UTOS

| Rank | Platform | Role | Cost | Alasan |
|---|---|---|---|---|
| #1 | Railway | All-in-one | $5-8/bln | Cheapest untuk 4 services, 1-click DB, always-on, best UX |
| #2 | Fly.io | All-in-one | $14-20/bln | Private network gratis, egress murah, tapi setup manual |
| #3 | Render | All-in-one | $20-35/bln | Egress mahal, free DB expired, CDN + DDoS gratis |
| — | Supabase | BaaS (DB only) | $0-25/bln | Tidak bisa host backend, UTOS sudah punya auth sendiri |
| — | Vercel | Frontend only | $0-20/bln | Tidak bisa host backend, tapi best untuk frontend jika mau pisah |

### Deployment Roadmap UTOS

```
Sekarang (dev/staging)       → Railway Hobby $5/bln
    ↓
Production awal               → Railway Hobby $5/bln (+ overage ~$2-3)
    ↓
Scale up (multi-user)         → Railway Pro $20/bln (private networking, 90-day logs)
    ↓
Multi-region / high-traffic   → Fly.io (cost-effective untuk scale besar)
```

### Kapan Pindah ke Fly.io?
| Trigger | Alasan |
|---|---|
| Butuh multi-region trading | Fly.io native multi-region, Railway perlu Pro ($20) |
| Egress traffic tinggi (market data besar) | Fly.io $0.02/GB vs Railway $0.05/GB |
| Butuh private networking tanpa upgrade | Fly.io gratis, Railway perlu Pro |
| Scale ke banyak machines (>10 services) | Fly.io lebih fleksibel, no minimum commitment |
| Butuh GPU (backtesting ML) | Fly.io A100/L4, Railway tidak ada GPU |

### Kapan Pakai Vercel?
- Kalau frontend UTOS butuh CDN global + image optimization + ISR → Vercel untuk frontend + Railway untuk backend
- Kalau mau simple dan murah → Railway saja untuk semua

### Kapan Pakai Supabase?
- TIDAK perlu — UTOS sudah punya JWT auth + RBAC sendiri
- Hanya jika butuh RLS atau realtime subscriptions di masa depan

### Kapan Pakai Render?
- Hanya jika butuh compliance (SOC 2/ISO 27001) di tier rendah ($25)
- Egress $0.15/GB = deal-breaker untuk trading bot yang query DB terus

---

## 14. Deployment Strategy: Railway Dulu, Fly.io Nanti

### Rekomendasi: Railway Dulu, Fly.io Nanti

**Tidak harus Railway + Fly.io sekaligus.** Pilihannya tergantung fase project.

### Fase 1 — Sekarang sampai Production Awal
**Railway saja ($5-8/bln)**

```
Railway Project: UTOS
├── PostgreSQL (managed)
├── Redis (managed)
├── Backend (FastAPI)
└── Frontend (Next.js)
```

Cukup untuk: development, staging, production awal dengan user terbatas.

### Fase 2 — Scale Up (multi-user, traffic naik)
**Railway Pro ($20/bln)**

Upgrade untuk dapat:
- Private networking (egress DB = $0)
- 90-day log retention
- 42 replicas
- Priority support

### Fase 3 — Large Scale (multi-region, 10+ services)
**Pindah ke Fly.io**

Pindah ketika:
- Butuh multi-region trading (latency rendah ke exchange)
- Egress market data > 100GB/bln
- Services > 10
- Butuh GPU untuk backtesting ML

### Kenapa Tidak Railway + Fly.io Bersamaan?

| Alasan | Detail |
|---|---|
| Complexity | 2 platform = 2 dashboard, 2 bill, 2 config, 2 CI/CD |
| Cost lebih mahal | Railway $5 + Fly.io $14 = $19/bln vs Railway saja $5-8/bln |
| Tidak perlu split | UTOS di fase awal belum butuh multi-region |
| Migration overhead | Kalau split sekarang, nanti kalau mau konsolidasi = kerja double |

### Kapan Split Railway + Fly.io Masuk Akal?

| Scenario | Setup | Alasan |
|---|---|---|
| Frontend di Railway, Backend trading di Fly.io | Railway (Next.js + DB) + Fly.io (FastAPI + Redis) | Backend butuh multi-region dekat exchange, frontend cukup 1 region |
| Staging di Railway, Production di Fly.io | Railway (dev/staging) + Fly.io (prod) | Staging murah di Railway, production scale di Fly.io |
| DB di Railway, Compute di Fly.io | Railway (Postgres managed) + Fly.io (FastAPI machines) | Railway DB backup + PITR lebih mudah, Fly.io compute lebih murah |

Tapi ini baru masuk akal di fase 3 (large scale), bukan sekarang.

### Decision Matrix

| Pertanyaan | Jawaban | Action |
|---|---|---|
| Apakah UTOS sudah production? | Belum | Railway Hobby $5 |
| Apakah user sudah > 100? | Belum | Railway Hobby $5 |
| Apakah butuh multi-region? | Tidak | Railway Hobby $5 |
| Apakah egress > 50GB/bln? | Tidak | Railway Hobby $5 |
| Apakah butuh private networking? | Tidak (Hobby cukup) | Railway Hobby $5 |
| Apakah butuh GPU? | Tidak | Railway Hobby $5 |

**Jawaban semua "belum/tidak" → Railway Hobby $5 sudah cukup.**

### Deployment Roadmap Summary

| Phase | Platform | Cost | When |
|---|---|---|---|
| Sekarang | Railway Hobby | $5-8/bln | Dev → production awal |
| Scale up | Railway Pro | $20/bln | Multi-user, butuh private networking |
| Large scale | Fly.io | $80-200/bln | Multi-region, 10+ services, GPU |

**Jangan split sekarang. Pakai Railway saja. Pindah/partial split ke Fly.io hanya ketika udah besar dan butuh multi-region.**

---

## 15. Scaling to 100,000 Users: Long-Term Architecture

### Railway/Fly.io = MVP, Bukan Target Arsitektur 100K

Railway dan Fly.io baik untuk tahap awal, tetapi **bukan target arsitektur jangka panjang** untuk aplikasi trading dengan skala 100,000 pengguna.

| Platform | Cocok untuk 100K? | Alasan |
|---|---|---|
| Railway | ⚠️ Sampai ~10-20K user | 42 replicas max (Pro), tidak ada multi-region native |
| Fly.io | ⚠️ Sampai ~30-50K user | Unlimited machines, tapi tidak ada managed DB HA |
| VPS tunggal | ❌ Tidak cukup | Single point of failure, no autoscaling |
| Kubernetes (EKS/GKE/AKS/DOKS/Hetzner) | ✅ Sangat cocok | Unlimited pods, horizontal autoscaling, multi-region |
| Managed PostgreSQL + Redis + LB | ✅ Direkomendasikan | HA, read replica, backup, monitoring built-in |

### Catatan Penting: Trading App ≠ Blog App

100K pengguna untuk **trading app** berbeda dengan 100K pengguna blog. Setiap user mungkin punya:
- WebSocket connection persistent (market data real-time)
- Trading bot running 24/7 (background process)
- Multiple exchange API connections
- Order execution queue

Resource per user **jauh lebih berat** dari app biasa.

### Roadmap 3 Fase ke 100K Pengguna

#### Fase 1 (0–5,000 pengguna) — Validasi Produk

**Platform:** Railway Hobby → Railway Pro

```
Railway Project: UTOS
├── PostgreSQL (managed, backup + PITR)
├── Redis (managed)
├── Backend (FastAPI, 2-3 replicas)
└── Frontend (Next.js, 1-2 replicas)
```

| Aspek | Detail |
|---|---|
| Cost | $5-20/bln |
| Concurrent users | ~500-2,000 |
| Trading bots | ~50-500 |
| WebSocket connections | ~200-1,000 |
| Tujuan | Validasi produk, product-market fit |

**Kapan upgrade ke Fase 2:**
- User > 2,000
- API response time > 500ms
- Database CPU > 70%
- WebSocket disconnect mulai sering

#### Fase 2 (5,000–30,000 pengguna) — Multi-Server + Managed Services

**Platform:** Multiple VPS / Managed services / Fly.io

```
┌─ Load Balancer (Nginx/HAProxy)
│   ├── Backend API #1 (FastAPI)
│   ├── Backend API #2 (FastAPI)
│   └── Backend API #3 (FastAPI)
├─ Managed PostgreSQL (primary + read replica)
├─ Managed Redis (cluster mode)
├─ Object Storage (S3/R2 for user docs, API keys)
├─ Queue Service (Redis Streams / RabbitMQ)
└─ Frontend (Next.js, CDN-fronted)
```

| Komponen | Kapan perlu | Kenapa |
|---|---|---|
| Managed PostgreSQL | ~1,000 user | Trading = write-heavy (order, position, trade log) |
| Read replica | ~3,000 user | Read query (market data, history) mulai slow |
| Redis Cluster | ~5,000 user | Cache + session + queue mulai penuh |
| Load Balancer | ~1,000 user | Multiple backend instances |
| Object Storage | ~500 user | Store exchange API keys, user documents |
| Queue terpisah | ~2,000 user | Order execution queue terpisah dari API |
| Multiple backend instances | ~2,000 user | Horizontal scaling API layer |

| Aspek | Detail |
|---|---|
| Cost | $50-200/bln |
| Concurrent users | ~2,000-15,000 |
| Trading bots | ~500-3,000 |
| WebSocket connections | ~1,000-10,000 |
| Tujuan | Stabilitas, performance, mulai prepare untuk K8s |

**Kapan upgrade ke Fase 3:**
- User > 20,000
- Database single primary tidak cukup (CPU > 80% walau dengan read replica)
- Manual scaling mulai tidak feasible
- Butuh multi-region untuk latency ke exchange

#### Fase 3 (30,000–100,000 pengguna) — Kubernetes + Full Scale

**Platform:** Kubernetes (EKS/GKE/AKS/DOKS/Hetzner)

```
┌─ API Gateway (Kong/Envoy)
│   ├── Rate limiting, auth, routing
│   └── WebSocket gateway (sticky sessions)
├─ Kubernetes Cluster
│   ├── Backend API pods (HPA: auto-scale by CPU/metrics)
│   ├── Trading bot pods (StatefulSet, persistent volume)
│   ├── Scheduler pods (cron jobs)
│   ├── Notification pods
│   └── Background worker pods
├─ Managed PostgreSQL (sharded, primary + multiple read replicas)
├─ Redis Cluster (distributed cache + pub/sub)
├─ Message Queue (Kafka/RabbitMQ untuk order execution pipeline)
├─ Object Storage (S3/R2)
├─ CDN (Cloudflare/Fastly untuk frontend)
├─ Service Mesh (Istio/Linkerd untuk mTLS, traffic mgmt)
├─ Monitoring (Prometheus + Grafana + Loki + Tempo)
└─ Log Aggregation (ELK/CloudWatch)
```

| Komponen | Kenapa perlu |
|---|---|
| Kubernetes | Orchestrasi ratusan pods, self-healing, auto-scaling |
| Horizontal Pod Autoscaler | Auto-scale berdasarkan CPU/memory/custom metrics |
| PostgreSQL sharding | 100K user = terlalu banyak untuk single Postgres. Sharding by user_id atau by exchange |
| Redis Cluster | Distributed cache + pub/sub untuk real-time data |
| Message queue (Kafka/RabbitMQ) | Order execution pipeline, event-driven architecture |
| WebSocket gateway | Sticky sessions untuk real-time market data (Centrifugo, Socket.io adapter) |
| API gateway (Kong/Envoy) | Rate limiting, auth, routing, DDoS protection |
| Service mesh (Istio/Linkerd) | mTLS, traffic management, observability, circuit breaker |
| Dedicated exchange connection pool | Rate limit management per exchange |
| Multi-region cluster | Server dekat dengan exchange (Binance: Tokyo/Singapore, Bybit: Singapore) |

| Aspek | Detail |
|---|---|
| Cost | $500-3,000/bln |
| Concurrent users | ~30,000-100,000 |
| Trading bots | ~5,000-30,000 |
| WebSocket connections | ~10,000-50,000 |
| Tujuan | Full scale, high availability, multi-region, compliance |

### UTOS Fondasi yang Sudah Ada (Verifikasi Codebase)

UTOS sudah memiliki fondasi yang mendukung migrasi ke arsitektur besar:

| Fondasi | Status | File / Lokasi |
|---|---|---|
| Docker | ✅ Complete | `docker/docker-compose.prod.yml`, `backend/Dockerfile`, `frontend/Dockerfile` |
| CI/CD (6 workflows) | ✅ Complete | `.github/workflows/` (ci, test, security, docker, deploy, release) |
| Blue-green deploy | ✅ Complete | `scripts/auto-rollback.sh`, Nginx blue-green config |
| Observability | ✅ Complete | Prometheus + Grafana + Tempo + postgres-exporter |
| Backup | ✅ Complete | `backend/core/backup.py`, `scripts/dr-test.sh` |
| Chaos testing | ✅ Complete | `backend/tests/test_chaos/chaos_adapter.py` (timeout, dup ACK, partial fill, conn drop) |
| Monitoring alerts | ✅ Complete | `monitoring/alerts.yml`, `monitoring/prometheus.yml` |
| Smoke tests | ✅ Complete | 12 endpoint tests post-deploy |
| Environment matrix | ✅ Complete | dev / staging / production configs |
| Health checks | ✅ Complete | `/health`, `/ready`, `/live` endpoints |
| GHCR images | ✅ Complete | `ghcr.io/andra2112s/utos-backend`, `ghcr.io/andra2112s/utos-frontend` |

**Kenapa fondasi ini penting untuk migrasi ke K8s:**
- Docker images sudah ada → tinggal deploy ke K8s pods
- CI/CD sudah build ke GHCR → tinggal pull dari K8s
- Observability sudah ada → tinggal point Prometheus ke K8s cluster
- Health checks sudah ada → K8s liveness/readiness probes langsung pakai
- Blue-green sudah ada → K8s rolling update / canary deployment lebih mudah
- Chaos testing sudah ada → resilience sudah diuji sebelum scale

### Yang TIDAK Disebutkan (Trading-Specific Concerns)

| Concern | Detail | Kapan perlu |
|---|---|---|
| Exchange API rate limit | Binance: 1,200 req/menit. 100K user = queue management critical | Fase 2+ |
| WebSocket connection management | 100K user = 100K WebSocket connections. Butuh dedicated gateway | Fase 3 |
| Stateful workload | Trading bot tidak bisa di-restart sembarangan. K8s StatefulSet + PV | Fase 2+ |
| Database sharding | 100K user dengan order history = mungkin >1TB. Shard by user_id atau exchange | Fase 3 |
| Multi-region exchange latency | Server dekat exchange (Binance: Tokyo/Singapore, Bybit: Singapore) | Fase 3 |
| Compliance (SOC 2, data residency) | 100K user = mungkin butuh audit trail, data residency | Fase 3 |
| DevOps expertise | K8s butuh SRE/DevOps engineer. Tim kecil = overhead | Fase 3 |
| Cost di K8s | Managed K8s (EKS/GKE/AKS) = $73-150/bln + node costs | Fase 3 |

### Cost Estimasi per Fase

| Fase | Platform | Cost/bln | Cost/tahun |
|---|---|---|---|
| Fase 1 (0-5K) | Railway Hobby → Pro | $5-20 | $60-240 |
| Fase 2 (5K-30K) | Multi-server + managed services | $50-200 | $600-2,400 |
| Fase 3 (30K-100K) | Kubernetes + full stack | $500-3,000 | $6,000-36,000 |

### Prinsip: Bangun yang Mudah Diskalakan, Naikkan Sesuai Pertumbuhan

**Jangan membangun infrastruktur untuk 100,000 pengguna sejak hari pertama jika pengguna belum sebanyak itu.** Bangun arsitektur yang mudah diskalakan, lalu naikkan kapasitas sesuai pertumbuhan nyata.

UTOS sudah mengikuti prinsip ini:
- Docker → portable ke platform manapun (Railway → VPS → K8s)
- CI/CD → build sekali, deploy ke environment manapun
- Observability → monitoring tidak terikat platform
- Health checks → K8s probes langsung pakai
- Environment matrix → dev/staging/prod sudah terpisah

**Ini lebih hemat biaya dan lebih mudah dioperasikan daripada mengoptimalkan untuk skala maksimum sejak awal.**

---

## Quick Reference Card

### Cheapest All-in-One: Railway Hobby $5/bln
### Best for Scale: Fly.io (3x cheaper at 10+ services)
### Best for Frontend: Vercel (CDN, ISR, image opt)
### Best for Compliance: Render Pro $25 (SOC 2 + ISO 27001)
### Best for DB + Auth: Supabase (butuh platform lain untuk backend)

### UTOS = SaaS di atas PaaS
- User management: AuthService (JWT, MFA, password reset)
- Authorization: RBACService (4 roles, permission-based)
- Subscription: SubscriptionService (4 tiers, upgrade/downgrade/renew)
- Billing: BillingService (Stripe, Midtrans, Xendit, Manual)
- Database: PostgreSQL (12 tables, SQLAlchemy models)
- Frontend: Next.js 15.5 (standalone mode, portable)
- Backend: FastAPI (async, repository pattern)
- Cache: Redis (managed)
