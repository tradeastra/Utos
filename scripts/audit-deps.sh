#!/bin/sh
# ─────────────────────────────────────────────
# Sprint 16C-4: Dependency Audit Script
# Runs pip-audit, npm audit, and Trivy
# Exit 1 if any Critical/High found
# ─────────────────────────────────────────────

set -e

echo "=== UTOS Dependency Audit ==="
echo ""

# ── Python (pip-audit) ───────────────────────
echo "--- Python: pip-audit ---"
pip install pip-audit 2>/dev/null
pip-audit -r backend/requirements.txt --strict --desc 2>&1 || {
    echo "pip-audit found vulnerabilities!"
    exit 1
}
echo "pip-audit: PASS (no known vulnerabilities)"
echo ""

# ── Node.js (npm audit) ──────────────────────
echo "--- Node.js: npm audit ---"
cd frontend
npm audit --audit-level=high 2>&1 || {
    echo "npm audit found high/critical vulnerabilities!"
    exit 1
}
echo "npm audit: PASS (no high/critical vulnerabilities)"
cd ..
echo ""

# ── Container (Trivy) ────────────────────────
echo "--- Container: Trivy scan ---"
if command -v trivy >/dev/null 2>&1; then
    trivy config docker/ --config docker/trivy.yaml 2>&1 || {
        echo "Trivy found Critical/High issues!"
        exit 1
    }
    echo "Trivy: PASS (no unmitigated Critical/High)"
else
    echo "Trivy not installed — skipping container scan"
    echo "Install: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
fi
echo ""

echo "=== All dependency audits passed ==="
