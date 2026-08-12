#!/bin/sh
set -e

mkdir -p /etc/nginx/certs

if [ ! -f /etc/nginx/certs/ssl.crt ] || [ ! -f /etc/nginx/certs/ssl.key ]; then
    echo "Generating self-signed SSL certificate for Nginx..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/certs/ssl.key \
        -out /etc/nginx/certs/ssl.crt \
        -subj "/C=US/ST=State/L=City/O=VisionGuard/CN=localhost"
    echo "Self-signed SSL certificate created."
fi

exec "$@"
