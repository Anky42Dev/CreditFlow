#!/usr/bin/env bash
# Generates a self-signed cert for local docker-compose.prod TLS testing.
# Real deploys should replace deploy/nginx/certs/* with a CA-issued cert
# (e.g. Let's Encrypt) instead of running this.
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p certs

openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout certs/privkey.pem \
  -out certs/fullchain.pem \
  -days 365 \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

echo "Wrote deploy/nginx/certs/fullchain.pem and privkey.pem"
