# Fly.io Database Migration Guide

## Prerequisites

```bash
# Install flyctl (Windows)
pwsh -Command "irm https://fly.io/install.ps1 | iex"

# Login
flyctl auth login
```

## Set DATABASE_URL Secret (one-time)

```bash
# Set the database URL as a Fly.io secret
flyctl secrets set -a utos-staging-backend DATABASE_URL="postgresql+asyncpg://user:password@host:5432/dbname"
```

## Usage

### Run Migration (upgrade head)

```bash
# From project root (Git Bash / WSL)
bash scripts/fly-migrate.sh upgrade
```

### Check Migration Status

```bash
bash scripts/fly-migrate.sh status
```

### Rollback One Revision

```bash
bash scripts/fly-migrate.sh downgrade -1
```

### Create New Migration

```bash
bash scripts/fly-migrate.sh revision "add_new_table"
```

### Show Migration History

```bash
bash scripts/fly-migrate.sh history
```

## Manual Command (without script)

```bash
# ❌ WRONG — will hang/stuck
flyctl ssh console -a utos-staging-backend --command "cd /app/backend && alembic upgrade head"

# ✅ CORRECT — use sh -c wrapper
flyctl ssh console -a utos-staging-backend --command "sh -c 'cd /app/backend && PYTHONPATH=/app/backend alembic upgrade head'"
```

## Why `sh -c` is Required

`flyctl ssh console` sends commands to Fly.io's SSH agent **without a shell wrapper**. Since `cd` is a shell builtin (not an executable binary), it fails without `sh -c`. The `sh -c` wrapper invokes `/bin/sh` which properly interprets `cd`, `&&`, and other shell operators.
