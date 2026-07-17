# Release Manifest — v1.0.0

**Status:** Template (fill on release)  
**Release date:** _(fill on release)_

---

## 1. Release Identity

| Item | Value |
|------|-------|
| Release version | v1.0.0 |
| Git tag | `v1.0.0` |
| Commit SHA | `_` |
| Branch | `main` |
| Previous release | v0.17.0-RC2-final |
| Release type | Major (first production release) |

---

## 2. Runtime Stack

| Component | Version |
|-----------|---------|
| Python | 3.11 |
| Node.js | 20 |
| PostgreSQL | 16-alpine |
| Redis | 7-alpine |
| Nginx | 1.25-alpine |
| Docker base (backend) | python:3.11-slim |
| Docker base (frontend) | node:20-alpine |

---

## 3. Docker Images

| Image | Digest | Registry |
|-------|--------|----------|
| `ghcr.io/andra2112s/utos-backend:v1.0.0` | `sha256:_` | GHCR |
| `ghcr.io/andra2112s/utos-frontend:v1.0.0` | `sha256:_` | GHCR |

---

## 4. Supply-Chain Artifacts

| Artifact | Format | Location |
|----------|--------|----------|
| Python SBOM | SPDX JSON | GitHub Release attachment |
| Python SBOM | CycloneDX JSON | GitHub Release attachment |
| Node.js SBOM | SPDX JSON | GitHub Release attachment |
| Node.js SBOM | CycloneDX JSON | GitHub Release attachment |
| Backend image SBOM | SPDX JSON | `cosign verify-attestation` |
| Frontend image SBOM | SPDX JSON | `cosign verify-attestation` |
| Backend image signature | Cosign (keyless) | `cosign verify` |
| Frontend image signature | Cosign (keyless) | `cosign verify` |
| Backend SLSA provenance | in-toto v0.1 | `cosign verify-attestation --type slsaprovenance` |
| Frontend SLSA provenance | in-toto v0.1 | `cosign verify-attestation --type slsaprovenance` |

### Verification Commands

```bash
# Verify image signatures
cosign verify ghcr.io/andra2112s/utos-backend:v1.0.0
cosign verify ghcr.io/andra2112s/utos-frontend:v1.0.0

# Verify SBOM attestations
cosign verify-attestation --type spdxjson ghcr.io/andra2112s/utos-backend:v1.0.0
cosign verify-attestation --type spdxjson ghcr.io/andra2112s/utos-frontend:v1.0.0

# Verify SLSA provenance
cosign verify-attestation --type slsaprovenance ghcr.io/andra2112s/utos-backend:v1.0.0
cosign verify-attestation --type slsaprovenance ghcr.io/andra2112s/utos-frontend:v1.0.0
```

---

## 5. Database

| Item | Value |
|------|-------|
| Schema version | Alembic head |
| Alembic revision | `_` |
| Migration count | `_` |
| Tables | 12 |

---

## 6. Key Dependencies (Pinned)

### Backend (Python)

| Package | Version | Role |
|---------|---------|------|
| fastapi | 0.118.0 | Web framework |
| pydantic | 2.9.2 | Data validation |
| sqlalchemy | 2.0.23 | ORM |
| asyncpg | 0.29.0 | Async PostgreSQL driver |
| redis | 5.0.1 | Redis client |
| python-jose | 3.4.0 | JWT |
| ccxt | 4.1.80 | Exchange adapter |
| aiohttp | 3.14.1 | Async HTTP |
| orjson | 3.11.6 | JSON serialization |
| prometheus-client | 0.19.0 | Metrics |
| celery | 5.3.4 | Background tasks |

### Frontend (Node.js)

| Package | Version | Role |
|---------|---------|------|
| next | 14.2.35 | React framework |
| react | 18.3.1 | UI library |
| zustand | 4.5.4 | State management |
| recharts | 2.12.7 | Charts |
| tailwindcss | 3.4.6 | CSS framework |
| vitest | 2.0.3 | Testing |

Full pinned list: `backend/requirements.txt`, `frontend/package.json`

---

## 7. Test Results

| Suite | Count | Passed | Failed | Duration |
|-------|-------|--------|--------|----------|
| Unit + Integration | 1026 | 1026 | 0 | ~3 min |
| Chaos Engineering | 74 | 74 | 0 | ~30 sec |
| **Total** | **1100** | **1100** | **0** | ~3.5 min |
| Performance benchmarks | 18 | 18 | 0 | ~5 sec |

---

## 8. Security Audit

| Scan | Tool | Findings | Status |
|------|------|----------|--------|
| Python dependencies | pip-audit | 19 residual (all transitive) | Accepted (see ACCEPTED_RISKS.md) |
| Node.js dependencies | npm audit | 10 residual (all dev deps) | Accepted (see ACCEPTED_RISKS.md) |
| Secret scan | Trivy | 0 | Clean |
| Container scan | Trivy | 0 Critical/High | Clean |

---

## 9. Accepted Risks

| Package | Severity | Reason | Mitigation |
|---------|----------|--------|------------|
| starlette | High | Requires v1.x (breaking) | Nginx normalizes requests |
| pyasn1 | Medium | Constrained by python-jose | Input validation + rate limiting |
| ecdsa | Medium | Transitive via python-jose | Same as pyasn1 |
| pytest | Low | Dev dependency only | Not in production |
| esbuild | Moderate | Build-time only | Not in production image |
| glob | High | Lint-time only | Not in production |
| minimatch | High | Lint-time only | Not in production |
| next | High | Requires v16 (breaking) | Nginx mitigates, critical fixed in 14.2.35 |

Full details: `docs/releases/ACCEPTED_RISKS.md`

---

## 10. Release Documents

| Document | Path | Status |
|----------|------|--------|
| Changelog | `CHANGELOG.md` | ✅ Updated for v1.0.0 |
| RC1 Checklist | `docs/releases/RC1_CHECKLIST.md` | ✅ Complete |
| RC2 Checklist | `docs/releases/RC2_CHECKLIST.md` | ✅ Complete |
| Chaos Report | `docs/releases/CHAOS_REPORT.md` | ✅ Complete |
| Accepted Risks | `docs/releases/ACCEPTED_RISKS.md` | ✅ Complete |
| Beta Checklist | `docs/releases/BETA_CHECKLIST.md` | ✅ Complete |
| Go-Live Checklist | `docs/releases/GO_LIVE.md` | ✅ Complete |
| Staging Deployment Report | `docs/releases/STAGING_DEPLOYMENT_REPORT.md` | ✅ Filled |
| Soak Test Report | `docs/releases/SOAK_TEST_REPORT.md` | ✅ Filled |
| Sandbox Validation | `docs/releases/SANDBOX_VALIDATION.md` | ✅ Filled |
| Go/No-Go Minutes | `docs/releases/GO_NO_GO_MINUTES.md` | ✅ Approved |
| Release Manifest | `docs/releases/RELEASE_MANIFEST_v1.0.0.md` | ✅ This document |

---

## 11. CI/CD Pipelines

| Workflow | File | Purpose |
|----------|------|---------|
| CI | `.github/workflows/ci.yml` | Lint + type check + test |
| Test | `.github/workflows/test.yml` | Full test suite |
| Security | `.github/workflows/security.yml` | pip-audit + npm audit + Trivy + secret scan + SBOM |
| Docker | `.github/workflows/docker.yml` | Build + push + Trivy scan + Cosign signing + SBOM attestation |
| Deploy | `.github/workflows/deploy.yml` | Blue-green deployment |
| Release | `.github/workflows/release.yml` | Tag + GHCR + SBOM + SLSA provenance + GitHub Release |

---

## 12. Operational Validation Results

| Phase | Result | Reference |
|-------|--------|-----------|
| Staging deployment | ⬜ Pass | `STAGING_DEPLOYMENT_REPORT.md` |
| 72h soak test | ⬜ Pass | `SOAK_TEST_REPORT.md` |
| Sandbox trading (16 scenarios) | ⬜ Pass | `SANDBOX_VALIDATION.md` |
| Go/No-Go review | ⬜ Approved | `GO_NO_GO_MINUTES.md` |

---

## 13. Release Approval

| Role | Name | Decision | Date |
|------|------|----------|------|
| Engineering Lead | _ | ⬜ Approved | _ |
| Architecture Lead | _ | ⬜ Approved | _ |
| Security Lead | _ | ⬜ Approved | _ |
| DevOps Lead | _ | ⬜ Approved | _ |
| QA Lead | _ | ⬜ Approved | _ |
| Product Owner | _ | ⬜ Approved | _ |
| Operations Lead | _ | ⬜ Approved | _ |

**Release decision:** ⬜ APPROVED — v1.0.0 released

---

## 14. Maintenance Policy

| Version pattern | Scope |
|-----------------|-------|
| v1.0.x | Bug fixes, security patches, dependency updates |
| v1.1.x | New features (backward compatible) |
| v2.0.0 | Breaking changes, major architecture changes |

---

## 15. Post-Release Monitoring

| Period | Focus | Status |
|--------|-------|--------|
| First 1h | Verify production telemetry, first requests | ⬜ |
| First 24h | Watch all alerts, verify first backup | ⬜ |
| First 7 days | Monitor stability, scheduled recovery drill | ⬜ |
| Day 7 | Retrospective, plan v1.0.1 if needed | ⬜ |

---

*This manifest is the single source of truth for what was released as v1.0.0. Any audit inquiry about the release should reference this document.*
