# Sprint 01 - Foundation

**Version:** 2.0.0  
**Status:** IN PROGRESS  
**Layer:** Core infrastructure  
**Duration:** Week 1  
**Goal:** Build a production-ready, reproducible foundation for the UTOS Trading Engine backend and frontend, including environment setup, auth skeleton, local-dev orchestration, CI/CD, linting, and automated testing.

---

## 1. Objective

Deliver a clean, working foundation that any developer can clone and run with a single command. By the end of this sprint:

- The repository is under version control with a proper `.gitignore`.
- Backend and frontend projects are bootstrapped with reproducible dependency management.
- Local development runs entirely in Docker Compose (PostgreSQL, Redis, backend, frontend).
- A JWT authentication system is implemented and tested (register, login, refresh, me, logout).
- A real health endpoint verifies database and Redis connectivity.
- Linting, formatting, type-checking, pre-commit hooks, and GitHub Actions are all green.
- Test coverage for new Sprint 1 code is greater than 80%.
- No hardcoded secrets, no critical security warnings, and no TODOs left in Sprint 1 code.

---

## 2. Scope

### 2.1 In Scope

- Repository setup (Git, `.gitignore`, `.editorconfig`, root metadata).
- Backend Python project setup with Poetry (`pyproject.toml`, `poetry.lock`).
- Frontend TypeScript project setup (Next.js 14+, React 18+, TypeScript, TailwindCSS, shadcn/ui, Zustand).
- Configuration management using Pydantic Settings and `.env`.
- Logging with structured JSON output via `structlog`.
- PostgreSQL database connection via SQLAlchemy 2.0 and `asyncpg`.
- Alembic migration setup with an initial migration for the `users` table.
- Redis cache connection and a minimal health check.
- Security utilities: password hashing (bcrypt), JWT access/refresh tokens, API-key generation.
- Authentication API: `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /users/me`.
- Response envelope (`data` + `meta` for success, `error` for failure) per `docs/API_GUIDELINES.md`.
- Global exception handlers and a consistent error response format.
- Docker Compose for local development (postgres, redis, backend, frontend).
- `Makefile` with standard commands.
- Pre-commit hooks (ruff, black, mypy, eslint, prettier, basic file checks).
- GitHub Actions CI workflow (lint, test, build).
- Unit and integration tests for all Sprint 1 features.

### 2.2 Out of Scope (DO NOT IMPLEMENT)

- Exchange adapters (`adapters/binance`, `adapters/bybit`, etc.).
- Market Hub, market data processing, WebSocket streams.
- Trading Engine, Trading Instance lifecycle, state machine.
- Grid Engine, Execution Engine, Portfolio Engine, Risk Engine.
- Profit Lock, Portfolio Lock, Take Profit logic.
- Trading strategies (Smart Grid, Adaptive Grid, Infinity Grid, DCA).
- Background workers and Celery tasks.
- Real-time frontend dashboard pages or trading UI.
- Kubernetes manifests, production deployment, monitoring stack.
- Advanced subscription/affiliate/notification features.

> **Important:** Implementing out-of-scope items will cause the sprint to be rejected. If a task is not listed in this document, it is not part of Sprint 1.

---

## 3. Deliverables

1. Fully populated `docs/sprint/SPRINT_01.md` (this document).
2. Initialized Git repository with `.gitignore` and conventional commit history for Sprint 1 work.
3. `pyproject.toml`, `poetry.lock`, and a working Poetry environment for the backend.
4. `frontend/package.json`, `package-lock.json`, `next.config.*`, `tailwind.config.*`, `tsconfig.json`, and working dev/build scripts.
5. `docker-compose.yml` and `Dockerfile`s for backend and frontend.
6. `Makefile` with documented commands.
7. `.pre-commit-config.yaml` installed and passing.
8. `.github/workflows/ci.yml` running lint/test/build on every push/PR.
9. Backend auth endpoints and health endpoint implemented and tested.
10. Alembic initial migration for `users` table.
11. Test suite with >80% coverage for Sprint 1 code.
12. Updated root `README.md` explaining how to run the project.

---

## 4. Input Documents

Before starting, read these documents in order:

1. `docs/PROJECT_BIBLE.md` - project vision and terminology.
2. `docs/ARCHITECTURE_APPROVED.md` - approved architecture decisions.
3. `docs/API_GUIDELINES.md` - response formats and endpoint conventions.
4. `docs/DATABASE.md` - data model conventions (implement only `users` table for this sprint).
5. `docs/CODING_STANDARD.md` - code style and conventions.
6. `docs/TESTING_STANDARD.md` - testing requirements.
7. `docs/ERROR_HANDLING.md` - error handling strategy.

---

## 5. Backend Tasks

### 5.1 Repository & Project Setup

- [ ] Initialize Git repository if not already valid (`git init`).
- [ ] Create `.gitignore` for Python, Node, Docker, IDEs, `.env` files, and OS files.
- [ ] Create `.editorconfig`.
- [ ] Create `README.md` with:
  - Project description.
  - Tech stack.
  - Quick start (`make install && make docker-up`).
  - Testing instructions.
  - Contribution note pointing to `docs/CONTRIBUTING.md`.
- [ ] Create `CONTRIBUTING.md` and `CHANGELOG.md` with initial content.
- [ ] Create backend `pyproject.toml` using Poetry:
  - Python `^3.11`.
  - Dependencies aligned with `backend/requirements.txt` but corrected:
    - Remove the invalid `decimal` package (use standard library `Decimal`).
    - Pin major versions as in `requirements.txt`.
  - Dev group: `pytest`, `pytest-asyncio`, `pytest-mock`, `pytest-cov`, `pytest-xdist`, `ruff`, `black`, `isort`, `mypy`, `httpx`.
  - Scripts: `test`, `lint`, `format`, `migrate`, `run`.
- [ ] Generate `poetry.lock`.
- [ ] Move/replace `backend/requirements.txt` if it duplicates `pyproject.toml` (Poetry is the source of truth; you may keep a minimal `requirements.txt` only if the CI uses it, but prefer Poetry).

### 5.2 Configuration & Environment

- [ ] Create `.env.example` at repository root with all required variables and safe placeholder values.
- [ ] Implement `backend/core/config.py` using Pydantic Settings (`pydantic-settings`):
  - Load from `.env`.
  - Required variables must fail fast if missing in production (`TESTING=false`).
  - `SECRET_KEY` must have no default in production; in local dev only, allow a clearly marked placeholder.
  - `DATABASE_URL`, `TEST_DATABASE_URL`, `REDIS_URL`, `TEST_REDIS_URL`.
  - CORS origins must be configurable; default to `http://localhost:3000` only, never `["*"]`.
  - No hardcoded credentials other than safe local-only defaults.
- [ ] Add environment validation helper that raises `ConfigurationError` for missing required values.

### 5.3 Logging

- [ ] Implement `backend/core/logging.py`:
  - Use `structlog`.
  - JSON format in production, pretty console in dev.
  - `get_logger(name)` factory.
  - Bind request ID and correlation ID where applicable.

### 5.4 Database

- [ ] Configure `backend/database/base.py`:
  - SQLAlchemy 2.0 declarative base.
  - Async engine using `create_async_engine` and `asyncpg`.
  - `AsyncSessionLocal` factory.
  - `get_db()` async generator dependency for FastAPI.
- [ ] Implement minimal `backend/models/user.py`:
  - `id`: UUID primary key.
  - `email`: unique, indexed, validated.
  - `hashed_password`: never store plain text.
  - `full_name`: optional string.
  - `is_active`: bool default true.
  - `is_verified`: bool default false.
  - `role`: enum/string default `"user"`.
  - `subscription_tier`: enum/string default `"free"`.
  - `created_at`, `updated_at`: timezone-aware datetime.
- [ ] Create Alembic configuration in `backend/alembic.ini` and `backend/alembic/` directory.
- [ ] Generate initial Alembic migration for the `users` table.
- [ ] Add repository `backend/repositories/user_repository.py` with methods:
  - `get_by_email`, `create`, `exists_by_email`.

### 5.5 Cache (Redis)

- [ ] Implement `backend/database/redis_client.py`:
  - Async Redis client from `redis.asyncio`.
  - Connection health check (`ping`).
  - Graceful handling when Redis is unavailable (log warning, do not crash app startup).

### 5.6 Security Utilities

- [ ] Implement or refine `backend/core/security.py`:
  - `PasswordManager`: bcrypt hash/verify.
  - `TokenManager`: create/verify access and refresh JWTs with explicit expiration and type claims.
  - `APIKeyManager`: generate/verify URL-safe API keys.
  - `SecurityUtils`: email validation, password strength validation, input sanitization using proper HTML escaping (e.g. `html.escape` or `bleach`/equivalent), secure token generation.
  - All secret-dependent operations must use `settings.SECRET_KEY` loaded from environment.

### 5.7 Schemas

- [ ] Create Pydantic schemas in `backend/schemas/`:
  - `auth.py`: `UserRegisterRequest`, `UserLoginRequest`, `TokenResponse`, `RefreshTokenRequest`.
  - `user.py`: `UserResponse`, `UserUpdateRequest`.
  - A consistent envelope wrapper (`ResponseEnvelope`, `ErrorResponse`) or use FastAPI response models per `docs/API_GUIDELINES.md`.

### 5.8 Authentication API

Implement endpoints under `backend/api/v1/endpoints/auth.py` and `backend/api/v1/endpoints/users.py`:

- [ ] `POST /api/v1/auth/register`
  - Validate input (email unique, password strength).
  - Hash password.
  - Create user via repository.
  - Return 201 with `UserResponse`.
  - Error: 409 if email exists.
- [ ] `POST /api/v1/auth/login`
  - Verify email/password.
  - Return access + refresh tokens.
  - Error: 401 for invalid credentials.
- [ ] `POST /api/v1/auth/refresh`
  - Accept refresh token, return new access token.
  - Error: 401 for invalid/expired refresh token.
- [ ] `POST /api/v1/auth/logout`
  - Protected endpoint; accept bearer token.
  - Return 200 success (token blocklist is optional for Sprint 1; if not implemented, document as known limitation).
- [ ] `GET /api/v1/users/me`
  - Protected endpoint.
  - Return current user profile from database (not just token payload).

### 5.9 Health API

- [ ] `GET /health` (no `/api/v1` prefix):
  - Check PostgreSQL connection.
  - Check Redis connection.
  - Return JSON with `status`, `version`, `timestamp`, and per-service health flags.
  - Return 503 if any critical dependency is down.
- [ ] `GET /api/v1/health` (optional) may return same data.

### 5.10 Exception Handling & Response Envelope

- [ ] Implement `backend/core/exceptions.py` (or refine existing) with `UTOSException` hierarchy.
- [ ] In `backend/main.py`, add exception handlers:
  - `UTOSException` → structured error response.
  - `ValidationError` / Pydantic validation errors → 422 with field details.
  - Generic `Exception` → 500 (hide details unless `DEBUG=true`).
- [ ] Ensure all success responses follow `{ data, meta }` and errors follow `{ error: { code, message, details } }`.

### 5.11 Dependency Injection & Wiring

- [ ] Update `backend/api/v1/router.py` to include `auth` and `users` routers.
- [ ] Ensure `backend/main.py` lifespan:
  - Creates async DB engine.
  - Initializes Redis client.
  - Runs Alembic upgrade to `head` (or at least verifies schema).
  - Gracefully closes connections on shutdown.
  - Remove all TODOs related to Sprint 1.

---

## 6. Frontend Tasks

### 6.1 Project Bootstrap

- [ ] Initialize Next.js 14+ project in `frontend/` with:
  - TypeScript.
  - TailwindCSS.
  - ESLint.
  - App Router.
- [ ] Install and configure:
  - `shadcn/ui` (initialize with default base color).
  - `zustand` for state management.
  - `axios` or native `fetch` wrapper for API calls.
  - `react-hook-form` and `zod` for form validation (optional but recommended).
- [ ] Create `frontend/.env.example` with `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`.
- [ ] Create `frontend/.gitignore` if not generated.

### 6.2 Minimal Structure

- [ ] Create directory structure:
  - `frontend/app/`
  - `frontend/components/ui/`
  - `frontend/lib/`
  - `frontend/services/`
  - `frontend/stores/`
  - `frontend/types/`
- [ ] Create `frontend/services/api.ts` with base URL and auth header injection.
- [ ] Create `frontend/types/auth.ts` for auth-related TypeScript types.
- [ ] Create `frontend/stores/authStore.ts` with Zustand to hold tokens and user.

### 6.3 Auth Pages (Sprint 1 only)

- [ ] `frontend/app/page.tsx` - landing page with links to login/register.
- [ ] `frontend/app/login/page.tsx` - login form calling backend `/auth/login`.
- [ ] `frontend/app/register/page.tsx` - register form calling backend `/auth/register`.
- [ ] `frontend/app/dashboard/page.tsx` - protected page that calls `GET /users/me` and displays email (placeholder only).
- [ ] Implement basic client-side route guard using Zustand auth state.

### 6.4 Frontend Tooling

- [ ] Add `frontend/package.json` scripts:
  - `dev`: `next dev -p 3000`
  - `build`: `next build`
  - `start`: `next start -p 3000`
  - `lint`: `next lint`
  - `format`: `prettier --write .`
  - `type-check`: `tsc --noEmit`
- [ ] Add Prettier configuration in `frontend/.prettierrc` or `prettier.config.js`.

---

## 7. Infrastructure & Tooling Tasks

### 7.1 Docker Compose

Create `docker-compose.yml` at repository root with services:

- [ ] `postgres`:
  - Image `postgres:16-alpine`.
  - Expose port `5432`.
  - Use `.env` for `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
  - Volume `postgres_data`.
- [ ] `redis`:
  - Image `redis:7-alpine`.
  - Expose port `6379`.
- [ ] `backend`:
  - Build from `backend/Dockerfile`.
  - Depends on `postgres` and `redis`.
  - Mount code for hot reload in dev.
  - Expose port `8000`.
  - Command runs migrations then `uvicorn` with reload.
- [ ] `frontend`:
  - Build from `frontend/Dockerfile`.
  - Depends on `backend`.
  - Mount code for hot reload in dev.
  - Expose port `3000`.
  - Command runs `npm run dev`.

Create `backend/Dockerfile` and `frontend/Dockerfile` optimized for local development (not production).

### 7.2 Makefile

Create `Makefile` with targets:

- [ ] `install` - install backend and frontend dependencies.
- [ ] `docker-up` - run `docker compose up -d`.
- [ ] `docker-down` - run `docker compose down`.
- [ ] `docker-logs` - tail logs.
- [ ] `test` - run backend tests and frontend type-check/lint.
- [ ] `test-backend` - run `pytest` with coverage.
- [ ] `test-frontend` - run frontend lint and type-check.
- [ ] `lint` - run ruff, black, mypy, eslint, prettier checks.
- [ ] `format` - run black, ruff, isort, prettier fixes.
- [ ] `migrate` - run `alembic upgrade head`.
- [ ] `migrate-make` - generate new Alembic migration.
- [ ] `run-dev` - start backend and frontend locally (optional).

### 7.3 Pre-commit

Create `.pre-commit-config.yaml` with hooks:

- [ ] `trailing-whitespace`
- [ ] `end-of-file-fixer`
- [ ] `check-yaml`
- [ ] `check-added-large-files`
- [ ] `check-merge-conflict`
- [ ] Local or repository hooks for:
  - `ruff check` and `ruff format` on Python files.
  - `black --check` or use ruff format as replacement.
  - `mypy backend/`.
  - `eslint --max-warnings=0 frontend/`.
  - `prettier --check` on frontend files.
- [ ] Run `pre-commit install` and `pre-commit run --all-files` must pass.

### 7.4 GitHub Actions CI

Create `.github/workflows/ci.yml`:

- [ ] Trigger on push to `main`/`develop` and on pull requests.
- [ ] Job 1 - Backend:
  - Checkout code.
  - Set up Python 3.11.
  - Install Poetry and project dependencies.
  - Run `make lint` (ruff, black, mypy).
  - Start Postgres and Redis services (GitHub Actions service containers).
  - Run `make test-backend`.
  - Upload coverage report.
- [ ] Job 2 - Frontend:
  - Checkout code.
  - Set up Node 20.
  - Install dependencies.
  - Run `make test-frontend`.

### 7.5 Environment Secrets Policy

- [ ] No secrets in source code.
- [ ] `.env.example` is the only committed env file.
- [ ] CI secrets must be referenced via GitHub Secrets, never hardcoded.

---

## 8. Testing Tasks

### 8.1 Backend Tests

- [ ] `backend/tests/unit/test_security.py` - test password hashing, JWT create/verify/expire, API key generation.
- [ ] `backend/tests/unit/test_config.py` - test settings load from env and fail on missing required values.
- [ ] `backend/tests/unit/test_repositories/test_user_repository.py` - test create/get/exists operations.
- [ ] `backend/tests/integration/test_health.py` - test `/health` returns 200 when DB/Redis are healthy and 503 when Redis is down (mocked).
- [ ] `backend/tests/integration/test_auth.py` - test register, login, refresh, me, logout with real async DB session.
- [ ] Use SQLite in-memory for unit repository tests if preferred, but integration tests must use test Postgres or async setup.
- [ ] Configure `pytest.ini` or `pyproject.toml` `[tool.pytest.ini_options]` with markers and coverage.

### 8.2 Frontend Tests

- [ ] `frontend/__tests__/auth-store.test.ts` - test Zustand auth store.
- [ ] `frontend/__tests__/login-page.test.tsx` - test login form submission (mock API).
- [ ] Run via `vitest` or Jest; install whichever is configured.

### 8.3 Coverage

- [ ] Backend coverage for Sprint 1 code >80% (`pytest --cov=backend --cov-report=term-missing`).
- [ ] Frontend coverage >70% for Sprint 1 components (optional but recommended).
- [ ] CI fails if backend coverage <80%.

---

## 9. Acceptance Criteria

Each criterion below must pass for Sprint 1 to be approved. Report `PASS`, `FAIL`, or `PARTIAL` during the audit.

| ID | Criterion | Verification Command / Check |
|----|-----------|------------------------------|
| AC-01 | Git repository is valid and `.gitignore` is present. | `git status` succeeds; `.env` and build artifacts are ignored. |
| AC-02 | Poetry environment resolves and installs. | `poetry install --no-root` completes without errors. |
| AC-03 | Backend starts and responds. | `poetry run uvicorn main:app --host 0.0.0.0 --port 8000` then `curl -s http://localhost:8000/health` returns HTTP 200. |
| AC-04 | Swagger UI is accessible. | `http://localhost:8000/docs` loads and lists auth endpoints. |
| AC-05 | Environment configuration works. | `cp .env.example .env`, modify `SECRET_KEY`, backend starts and rejects missing required vars. |
| AC-06 | No hardcoded secrets. | `grep -R "your-secret-key\|password=\"password\"\|SECRET_KEY =" backend/` returns nothing critical. |
| AC-07 | PostgreSQL is reachable from backend. | Health endpoint reports `database: true` and `POST /auth/register` persists user. |
| AC-08 | Redis is reachable from backend. | Health endpoint reports `redis: true`. |
| AC-09 | Alembic migration runs successfully. | `poetry run alembic upgrade head` creates `users` table. |
| AC-10 | User registration works. | `POST /api/v1/auth/register` returns 201 with user payload; duplicate email returns 409. |
| AC-11 | User login works. | `POST /api/v1/auth/login` returns 200 with `access_token` and `refresh_token`. |
| AC-12 | Token refresh works. | `POST /api/v1/auth/refresh` with valid refresh token returns new access token. |
| AC-13 | Protected endpoint validates token and database user. | `GET /api/v1/users/me` with bearer token returns current user; with invalid token returns 401. |
| AC-14 | Logout endpoint returns success. | `POST /api/v1/auth/logout` with bearer token returns 200. |
| AC-15 | Response envelope matches API Guidelines. | All success responses contain `data` and `meta`; errors contain `error.code`, `error.message`, `error.details`. |
| AC-16 | Frontend dev server starts. | `npm run dev` in `frontend/` serves `http://localhost:3000`. |
| AC-17 | Frontend login page calls backend. | Submitting login form on `http://localhost:3000/login` obtains tokens and redirects. |
| AC-18 | Docker Compose boots all services. | `make docker-up` then `docker compose ps` shows `postgres`, `redis`, `backend`, `frontend` healthy. |
| AC-19 | Health endpoint in Docker returns 200. | `curl http://localhost:8000/health` returns `{"status":"healthy",...}`. |
| AC-20 | Makefile commands work. | `make install`, `make lint`, `make test` run without errors. |
| AC-21 | Linting passes. | `ruff check backend/`, `black --check backend/`, `mypy backend/`, `next lint`, `prettier --check frontend/` are green. |
| AC-22 | Pre-commit passes on all files. | `pre-commit run --all-files` exits 0. |
| AC-23 | GitHub Actions CI passes. | CI workflow on the PR shows green checks for backend and frontend jobs. |
| AC-24 | Backend test coverage >80%. | `pytest --cov=backend --cov-fail-under=80` passes. |
| AC-25 | No critical security warnings. | No plaintext secrets, CORS is not `["*"]`, password hashing is bcrypt, JWT secret is from env. |
| AC-26 | No TODOs remain in Sprint 1 code. | `grep -R "TODO" backend/main.py backend/api/v1/endpoints backend/core backend/database` returns nothing. |

---

## 10. Definition of Done

Sprint 1 is considered **DONE** only when **all** of the following are true:

1. Every acceptance criterion in Section 9 is `PASS`.
2. `docs/sprint/SPRINT_01.md` is complete and consistent with the implementation.
3. All code is committed to a valid Git repository.
4. `make lint`, `make test`, and `pre-commit run --all-files` pass locally.
5. GitHub Actions CI is green on the latest commit.
6. Backend test coverage for Sprint 1 code is ≥80%.
7. Docker Compose can be started with `make docker-up` and all services are healthy.
8. No hardcoded secrets, no plaintext passwords, and no `["*"]` CORS origins.
9. All TODOs in Sprint 1 scope are resolved.
10. The auditor has generated a new `IMPLEMENTATION_AUDIT.md` showing Sprint 1 as **COMPLETE**.

---

## 11. Audit & Approval

After implementation, run the audit process:

1. Verify every acceptance criterion in Section 9 and record `PASS` / `FAIL` / `PARTIAL`.
2. Update or regenerate `IMPLEMENTATION_AUDIT.md` with sections 1-7 as required.
3. Only mark Sprint 1 **COMPLETE** when every acceptance criterion passes.
4. Do **not** create `SPRINT_02.md` or begin Sprint 2 work until Sprint 1 is approved.

---

## 12. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Poetry lock conflicts | Medium | Pin versions carefully; regenerate lock in CI if needed. |
| Docker Compose port conflicts | Low | Use `.env` to allow port overrides. |
| Pre-commit hook incompatibilities | Low | Test hooks locally before pushing. |
| Test flakiness with async DB | Medium | Use `pytest-asyncio` session/function scopes consistently. |
| Scope creep into trading features | High | Strictly enforce out-of-scope list above. |

---

## 13. Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-07-09 | 1.0.0 | Initial Sprint 1 specification |
| 2026-07-09 | 2.0.0 | Rewritten as full implementation contract with acceptance criteria, DoD, and out-of-scope guardrails |
