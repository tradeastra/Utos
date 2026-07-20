# Errata — Commit Identity Clarification

**Date:** 2026-07-17
**Release:** v1.0.0
**Status:** Clarification — no code changes, no snapshot invalidation

---

## Issue

The release snapshot documents (`RELEASE_SNAPSHOT.md`, `COMMIT_SHA.txt`) reference commit `ee568df` as the locked commit. However, Git tag `v1.0.0` points to commit `60e5107`.

This is not an error — it reflects a two-step process:

1. **Engineering baseline** was locked at `ee568df` (tagged `v0.17.0-engineering-complete-final`)
2. **Release snapshot commit** `60e5107` was created to add the immutable release evidence package (folder structure, snapshot documents, build metadata)

Tag `v1.0.0` was applied to `60e5107` because it is the canonical release commit that contains all release artifacts.

## Canonical Identity

| Role | Commit SHA | Tag |
|------|-----------|-----|
| Engineering baseline | `ee568dff04eafe5f6406c934b17993daf5c42c54` | `v0.17.0-engineering-complete-final` |
| Release snapshot commit (canonical) | `60e5107451dd61ab01b9e2e1653aede43534dd2d` | `v1.0.0-snapshot`, `v1.0.0` |

## Chain of Custody

```
ee568df  (engineering complete — code freeze)
  │
  └── 60e5107  (release snapshot — adds evidence package artifacts)
        │
        └── tag: v1.0.0  (canonical release identity)
```

`60e5107` is a direct descendant of `ee568df`. No code changes exist between the two commits — `60e5107` only adds release governance artifacts (documents, metadata files).

## Verification

```bash
# Confirm tag points to release snapshot commit
git show v1.0.0 --oneline --no-patch

# Confirm engineering baseline is ancestor
git merge-base --is-ancestor ee568df 60e5107 && echo "OK: ee568df is ancestor of 60e5107"

# Confirm no code changes between the two
git diff ee568df 60e5107 --stat
```

## Auditor Guidance

When verifying release identity:
- **Use `v1.0.0` tag** (`60e5107`) as the canonical release commit
- **Use `ee568df`** as the engineering baseline (code freeze point)
- The diff between the two commits contains only release governance files, no application code
