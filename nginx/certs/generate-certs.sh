#!/bin/bash
# Generate self-signed SSL certificate for Vision Guard Nginx reverse proxy

CERTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$CERTS_DIR"

if [ ! -f "$CERTS_DIR/ssl.crt" ] || [ ! -f "$CERTS_DIR/ssl.key" ]; then
    echo "Generating self-signed SSL certificate in $CERTS_DIR..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$CERTS_DIR/ssl.key" \
        -out "$CERTS_DIR/ssl.crt" \
        -subj "/C=US/ST=State/L=City/O=VisionGuard/OU=Security/CN=localhost"
    echo "SSL certificates created successfully."
else
    echo "SSL certificates already exist in $CERTS_DIR."
fi
