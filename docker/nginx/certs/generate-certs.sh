#!/bin/sh
# ─────────────────────────────────────────────
# Sprint 16A-4: Generate self-signed TLS certs
# Usage: ./generate-certs.sh
# For staging only — use Let's Encrypt in production
# ─────────────────────────────────────────────

set -e

CERT_DIR="${1:-./docker/nginx/certs}"
CONF_FILE="./docker/nginx/certs/openssl.cnf"

mkdir -p "$CERT_DIR"

echo "Generating self-signed TLS certificates..."
echo "Output directory: $CERT_DIR"
echo ""

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$CERT_DIR/privkey.pem" \
    -out "$CERT_DIR/fullchain.pem" \
    -config "$CONF_FILE" \
    -extensions req_ext

echo ""
echo "Certificates generated:"
echo "  $CERT_DIR/fullchain.pem"
echo "  $CERT_DIR/privkey.pem"
echo ""
echo "WARNING: These are self-signed certificates for staging only."
echo "For production, use Let's Encrypt or your CA-issued certificates."
