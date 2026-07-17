# Branch Policy — Post Engineering Complete

**Effective:** v0.17.0-engineering-complete  
**Applies until:** v1.0.0 release

---

## `main` is Immutable

No direct commits to `main` for features, refactoring, or non-critical changes.

| Change type | Allowed? | Process |
|-------------|----------|---------|
| Blocker found during staging/soak/sandbox | ✅ | `hotfix/description` → PR → review → merge |
| Security patch (Critical/High) | ✅ | `hotfix/security-*` → PR → review → merge |
| Documentation fix (typo, clarification) | ✅ | `docs/fix-*` → PR → review → merge |
| New feature | ❌ | Backlog → v1.1.0 |
| Refactoring | ❌ | Backlog → v1.1.0 |
| UX improvement | ❌ | Backlog → v1.1.0 |
| Dependency update (non-critical) | ❌ | Backlog → v1.1.0 |
| Performance optimization | ❌ | Backlog → v1.1.0 |

---

## Hotfix Process

```
main (immutable)
  │
  ├── hotfix/fix-duplicate-order-race
  │     ├── Fix the issue
  │     ├── Add regression test
  │     ├── Run full test suite (1100+)
  │     ├── PR review
  │     └── Merge to main
  │
  └── main (updated, re-tag if needed)
```

### Rules

1. Every hotfix must include a regression test
2. Full test suite must pass before merge
3. If hotfix changes dependencies, re-run security scans
4. If hotfix changes Docker image, re-sign with Cosign
5. Document the hotfix in CHANGELOG.md

---

## Version Policy

| Version | Scope | Branch |
|---------|-------|--------|
| v1.0.x | Bug fixes, security patches, dependency updates | `hotfix/*` → `main` |
| v1.1.x | New features (backward compatible) | `develop` → `main` |
| v1.2.x | New features (backward compatible) | `develop` → `main` |
| v2.0.0 | Breaking changes, major architecture | `develop` → `main` |

---

## Evidence Integrity

The four operational evidence documents must reflect the exact code deployed:

| Evidence | Must match |
|----------|------------|
| `STAGING_DEPLOYMENT_REPORT.md` | Commit SHA in deployment |
| `SOAK_TEST_REPORT.md` | Same commit SHA, 72h unchanged |
| `SANDBOX_VALIDATION.md` | Same commit SHA |
| `GO_NO_GO_MINUTES.md` | Same commit SHA as all above |

If a hotfix is applied mid-validation, validation must restart from deployment.
