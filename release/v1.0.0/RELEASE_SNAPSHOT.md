# Release Snapshot — v1.0.0

**Captured:** 2026-07-17T03:46:01Z  
**Status:** Engineering complete, pending operational validation

> **Note:** This document captures the engineering baseline commit (`ee568df`). The canonical release commit is `60e5107` (tagged `v1.0.0`). See `ERRATA_COMMIT_IDENTITY.md` for details.

---

## Identity

| Item | Value |
|------|-------|
| Commit SHA | `ee568dff04eafe5f6406c934b17993daf5c42c54` |
| Tag | `v0.17.0-engineering-complete-final` |
| Build number | 70 |
| Build timestamp (UTC) | 2026-07-17T03:46:01Z |
| Working tree | clean |
| Branch | `main` |

## Files

| File | Content |
|------|---------|
| `COMMIT_SHA.txt` | `ee568dff04eafe5f6406c934b17993daf5c42c54` |
| `BUILD_NUMBER.txt` | `70` |
| `RELEASE_TAG.txt` | `v0.17.0-engineering-complete-final` |
| `BUILD_TIMESTAMP.txt` | `2026-07-17T03:46:01Z` |

## To Be Filled (Post-Build)

| Item | Source | Status |
|------|--------|--------|
| Backend image digest | `docker buildx imagetools inspect ghcr.io/andra2112s/utos-backend:v1.0.0` | ⏳ |
| Frontend image digest | `docker buildx imagetools inspect ghcr.io/andra2112s/utos-frontend:v1.0.0` | ⏳ |
| Alembic revision | `alembic heads` | ⏳ |
| SBOM SHA-256 | `sha256sum sbom/*.json` | ⏳ |

## Integrity Rule

All four operational evidence documents must reference this exact commit SHA:

```
ee568dff04eafe5f6406c934b17993daf5c42c54
```

If a hotfix is applied, this snapshot must be regenerated and validation must restart.
