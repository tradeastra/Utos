# ─────────────────────────────────────────────
# Sprint 16A-1: Backend Production Dockerfile
# Multi-stage build — minimal final image
# ─────────────────────────────────────────────

# ── Stage 1: Builder ──────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies (compilers for C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency manifest first for cache
COPY backend/requirements.txt .

# Install to a prefix directory for clean copy
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────
FROM python:3.12-slim AS runtime

# Install only runtime libs (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 libssl3 curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r utos && useradd -r -g utos -d /app -s /sbin/nologin utos

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=utos:utos backend/ ./backend/

# Set environment
ENV PYTHONPATH=/app/backend \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    DEBUG=false

# Switch to non-root user
USER utos

EXPOSE 8000

# Healthcheck via curl
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -sf http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--no-access-log"]
