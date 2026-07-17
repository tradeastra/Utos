# Accepted Risk Register — Residual Vulnerabilities

**Date:** 2026-07-17  
**Context:** Post-RC2 security audit  
**Audit tools:** `pip-audit --strict`, `npm audit`

---

## Summary

| Source | Initial | Fixed | Residual | Status |
|--------|---------|-------|----------|--------|
| Python (pip-audit) | 77 | 58 | 19 | Accepted |
| Node.js (npm audit) | 13 | 3 | 10 | Accepted |

All residual vulnerabilities are either transitive dependencies with version constraints that cannot be resolved without breaking changes, or development-only dependencies that do not affect production runtime.

---

## Python — Residual Vulnerabilities (19)

| Package | Version | CVE Count | Severity | Reason | Action |
|---------|---------|-----------|----------|--------|--------|
| starlette | 0.48.0 | 10 | High | Requires starlette v1.x which is a breaking change from FastAPI. FastAPI 0.118.0 pulls starlette 0.48.0. Upgrading to starlette 1.x requires FastAPI 0.120+ which has breaking API changes. | Revisit after FastAPI releases a compatible version with starlette 1.x. Target: post-v1.0.0 maintenance release. |
| pyasn1 | 0.4.8 | 1 | Medium | Constrained by `python-jose[cryptography]==3.4.0` which requires `pyasn1>=0.4.1,<0.5.0`. Cannot upgrade without breaking python-jose. | Revisit when python-jose releases a version supporting pyasn1 0.6+. |
| ecdsa | 0.19.2 | 1 | Medium | Transitive dependency via `python-jose[cryptography]`. No direct pin in requirements.txt. | Revisit when python-jose drops ecdsa dependency or patches the CVE. |
| pytest | 8.3.4 | 1 | Low | Dev dependency only. Fix requires pytest 9.0.3 but `pytest-asyncio` requires `pytest<9`. | Upgrade on next maintenance release when pytest-asyncio supports pytest 9. |

### Risk Assessment

- **starlette (High):** The CVEs relate to request smuggling and DoS vectors. Mitigated by Nginx reverse proxy which normalizes requests before reaching Starlette. Production traffic does not reach Starlette directly.
- **pyasn1 (Medium):** Used only in JWT token verification path. Exploitation requires crafted ASN.1 payloads in JWT tokens. Mitigated by input validation and rate limiting on auth endpoints.
- **ecdsa (Medium):** Used only in JWT verification. Same mitigation as pyasn1.
- **pytest (Low):** Development dependency only. Does not affect production runtime.

---

## Node.js — Residual Vulnerabilities (10)

| Package | Version | CVE Count | Severity | Reason | Action |
|---------|---------|-----------|----------|--------|--------|
| esbuild | <=0.24.2 | 1 | Moderate | Dev dependency via vitest/vite. Build-time only, not in production bundle. | Monitor upstream. Upgrade vitest when esbuild fix is available. |
| glob | 10.2.0–10.4.5 | 1 | High | Dev dependency via `eslint-config-next`. Build/lint-time only. | Upgrade eslint-config-next when glob fix is available. |
| minimatch | 9.0.0–9.0.6 | 3 | High | Dev dependency via eslint/glob. Build/lint-time only. | Resolved when glob is updated. |
| next | 14.2.35 | 5 | High | Requires Next.js 16.x which is a major breaking change (app router, API changes). Current 14.2.35 fixes critical cache poisoning and DoS. | Revisit for v1.0.0 or post-launch maintenance. |

### Risk Assessment

- **esbuild (Moderate):** Build-time only. Does not ship in production Docker image. Exploitation requires dev server accessible to attacker.
- **glob (High):** Lint-time only. Command injection vector requires CLI usage with attacker-controlled input. Not exposed in production.
- **minimatch (High):** ReDoS vulnerability in pattern matching. Lint-time only. Not exposed in production.
- **next (High):** Residual high-severity issues require Next.js 16 (breaking change). Current version 14.2.35 fixes the critical cache poisoning and DoS. Remaining issues are edge cases in image optimization and RSC deserialization. Mitigated by Nginx and not exposing dev-only features.

---

## Mitigations in Place

1. **Nginx reverse proxy:** Normalizes all HTTP requests before reaching Starlette/Next.js, mitigating request smuggling and cache poisoning vectors.
2. **Rate limiting:** Applied on all API endpoints, especially auth endpoints where pyasn1/ecdsa are used.
3. **Input validation:** Pydantic models validate all API inputs before processing.
4. **Docker security:** All containers run with `no-new-privileges`, `cap_drop: ALL`, read-only filesystems.
5. **Network isolation:** `frontend-net` and `backend-net` are separate bridge networks.
6. **No dev deps in production:** Docker images use production-only installs, dev dependencies are not shipped.

---

## Review Schedule

| Review | Target Date | Trigger |
|--------|-------------|---------|
| starlette upgrade | Post-v1.0.0 | FastAPI release with starlette 1.x support |
| pyasn1/ecdsa upgrade | Post-v1.0.0 | python-jose release with pyasn1 0.6+ support |
| pytest upgrade | Next maintenance release | pytest-asyncio support for pytest 9 |
| Next.js upgrade | Post-v1.0.0 | Next.js 16 stable release |
| esbuild/glob/minimatch | Next frontend maintenance | Upstream fixes available |

---

## Sign-off

| Role | Status | Date |
|------|--------|------|
| Engineering | ✅ | 2026-07-17 |
| Security | ✅ | 2026-07-17 |
| Architecture | ✅ | 2026-07-17 |

All residual vulnerabilities have been evaluated, documented, and accepted with mitigations in place. No Critical or unmitigated High severity vulnerabilities remain in production runtime dependencies.
