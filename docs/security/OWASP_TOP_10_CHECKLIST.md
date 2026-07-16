# Sprint 16C-5: OWASP Top 10 Checklist

## A01: Broken Authentication
- [x] JWT tokens with expiration (access: 30min, refresh: 7d)
- [x] Password hashing with bcrypt (PasswordManager)
- [x] Password strength validation (min 8 chars, upper, lower, digit, special)
- [x] Rate limiting on login endpoint (5/min)
- [x] Rate limiting on register endpoint (5/min)
- [x] Refresh token rotation
- [x] No hardcoded secrets — production validation enforces secure SECRET_KEY

## A02: Cryptographic Failures
- [x] TLS 1.2+ enforced in Nginx
- [x] HSTS header (max-age=63072000, includeSubDomains, preload)
- [x] JWT signed with HS256 using SECRET_KEY (min 32 chars in production)
- [x] Passwords hashed with bcrypt (adaptive cost)
- [x] API keys hashed with bcrypt before storage
- [x] No sensitive data in URLs (all via POST body or Authorization header)
- [x] Database password via environment variable (not in code)

## A03: Injection
- [x] SQLAlchemy ORM with parameterized queries (no raw SQL string concatenation)
- [x] Pydantic input validation on all API endpoints
- [x] No shell=True in subprocess calls
- [x] No eval() or exec() on user input
- [x] Input sanitization utility (SecurityUtils.sanitize_input)

## A04: Insecure Design
- [x] Architecture Freeze (ADR-011) — no ad-hoc changes to core
- [x] Threat model: trading engine isolated from internet via Nginx proxy
- [x] Rate limiting on all API endpoints (100/min default, 5/min auth)
- [x] Health checks separate from business logic
- [x] Graceful degradation (Redis down → fail open on rate limit)

## A05: Security Misconfiguration
- [x] DEBUG=false enforced in production (config validator)
- [x] Non-root Docker containers (utos user, nextjs user)
- [x] .env.example provided, .env in .gitignore
- [x] Nginx security headers (7 headers)
- [x] /metrics endpoint restricted to internal networks
- [x] Docker images minimal (slim/alpine base, multi-stage builds)
- [x] No default credentials in production config

## A06: Vulnerable and Outdated Components
- [ ] pip-audit in CI (Sprint 16E)
- [ ] npm audit in CI (Sprint 16E)
- [ ] Trivy container scan in CI (Sprint 16E)
- [x] Trivy configuration ready (docker/trivy.yaml)
- [x] Audit script ready (scripts/audit-deps.sh)
- [x] requirements.txt with pinned versions

## A07: Identification and Authentication Failures
- [x] JWT verification on every protected endpoint
- [x] Token type checking (access vs refresh)
- [x] Expiration validation server-side
- [x] User session via Zustand store with token management
- [x] Logout invalidates client-side tokens

## A08: Software and Data Integrity Failures
- [x] Pydantic schema validation on all inputs
- [x] SQLAlchemy ORM prevents data type confusion
- [x] Correlation ID propagation for audit trail
- [x] Structured JSON logging with correlation IDs
- [ ] Container image signing (post-RC)

## A09: Security Logging and Monitoring Failures
- [x] Structured JSON logging (Sprint 01)
- [x] Correlation ID middleware (Sprint 16B)
- [x] Prometheus metrics for all API requests (Sprint 16B)
- [x] Grafana dashboards for monitoring (Sprint 16B)
- [x] Alert rules for critical conditions (Sprint 16B polish)
- [x] Error logging with stack traces (generic exception handler)

## A10: Server-Side Request Forgery (SSRF)
- [x] No user-controlled outbound HTTP requests
- [x] Exchange adapter URLs configured via environment, not user input
- [x] Webhook URLs for notifications validated against allowlist (Sprint 13)
- [x] No internal URL fetching from user parameters

## Summary
| Category | Status |
|----------|--------|
| A01: Broken Authentication | ✅ Pass |
| A02: Cryptographic Failures | ✅ Pass |
| A03: Injection | ✅ Pass |
| A04: Insecure Design | ✅ Pass |
| A05: Security Misconfiguration | ✅ Pass |
| A06: Vulnerable Components | ⏳ CI pending (16E) |
| A07: Auth Failures | ✅ Pass |
| A08: Integrity Failures | ✅ Pass |
| A09: Logging/Monitoring | ✅ Pass |
| A10: SSRF | ✅ Pass |
