#!/bin/bash
# ─────────────────────────────────────────────
# SBOM Generation Script
# Generates Software Bill of Materials in SPDX and CycloneDX formats
# for Python and Node.js dependencies.
#
# Requires: syft (https://github.com/anchore/syft)
# Install:  curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
#
# Usage: bash scripts/generate-sbom.sh [version]
#   version: tag name (e.g. v0.17.0-RC2). Defaults to "dev"
# ─────────────────────────────────────────────

set -euo pipefail

VERSION="${1:-dev}"
OUTPUT_DIR="sbom"

mkdir -p "$OUTPUT_DIR"

echo "=== UTOS SBOM Generation ==="
echo "Version: $VERSION"
echo "Output:  $OUTPUT_DIR/"
echo ""

# Check syft is installed
if ! command -v syft &> /dev/null; then
    echo "ERROR: syft not found. Install with:"
    echo "  curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin"
    exit 1
fi

# ── Python SBOM ──────────────────────────────
echo -n "Generating Python SBOM (SPDX)... "
syft dir:backend --output "spdx-json=${OUTPUT_DIR}/sbom-python-${VERSION}.spdx.json" 2>/dev/null
echo "done"

echo -n "Generating Python SBOM (CycloneDX)... "
syft dir:backend --output "cyclonedx-json=${OUTPUT_DIR}/sbom-python-${VERSION}.cyclonedx.json" 2>/dev/null
echo "done"

# ── Node.js SBOM ─────────────────────────────
echo -n "Generating Node.js SBOM (SPDX)... "
syft dir:frontend --output "spdx-json=${OUTPUT_DIR}/sbom-nodejs-${VERSION}.spdx.json" 2>/dev/null
echo "done"

echo -n "Generating Node.js SBOM (CycloneDX)... "
syft dir:frontend --output "cyclonedx-json=${OUTPUT_DIR}/sbom-nodejs-${VERSION}.cyclonedx.json" 2>/dev/null
echo "done"

# ── Docker image SBOM (optional) ─────────────
if command -v docker &> /dev/null; then
    for target in backend frontend; do
        IMAGE="ghcr.io/andra2112s/utos-${target}:${VERSION}"
        echo -n "Generating Docker image SBOM ($target)... "
        syft "$IMAGE" --output "spdx-json=${OUTPUT_DIR}/sbom-${target}-image-${VERSION}.spdx.json" 2>/dev/null || {
            echo "skipped (image not available)"
            continue
        }
        echo "done"
    done
fi

# ── Summary ──────────────────────────────────
echo ""
echo "=== SBOM Generation Complete ==="
echo "Files generated:"
ls -lh "$OUTPUT_DIR"/sbom-*-${VERSION}.* 2>/dev/null || echo "  (no files found)"
echo ""
echo "Formats: SPDX JSON, CycloneDX JSON"
echo "Scopes: Python (backend/), Node.js (frontend/)"
