#!/bin/bash
# Apply Caddyfile changes to /etc/caddy/ and reload Caddy
set -e

SOURCE="/home/user/n8n-docker/Caddyfile"
TARGET="/etc/caddy/Caddyfile"

echo "==> Backing up current Caddyfile..."
cp "$TARGET" "${TARGET}.bak.$(date +%Y%m%d%H%M%S)"

echo "==> Copying new Caddyfile..."
cp "$SOURCE" "$TARGET"

echo "==> Validating Caddyfile..."
caddy validate --config "$TARGET" --adapter caddyfile

echo "==> Reloading Caddy..."
sudo systemctl reload caddy

echo "==> Waiting 2 seconds..."
sleep 2

echo "==> Testing endpoints..."
echo "--- https://portal.bigalexn8n.ru/portal-api/data ---"
curl -sk -o /dev/null -w "HTTP %{http_code}\n" https://portal.bigalexn8n.ru/portal-api/data
echo "--- https://portal.bigalexn8n.ru/api/data ---"
curl -sk -o /dev/null -w "HTTP %{http_code}\n" https://portal.bigalexn8n.ru/api/data
echo "--- https://portal.bigalexn8n.ru/admin ---"
curl -sk -o /dev/null -w "HTTP %{http_code}\n" https://portal.bigalexn8n.ru/admin
echo "--- https://bigalexn8n.ru/portal-api/data ---"
curl -sk -o /dev/null -w "HTTP %{http_code}\n" https://bigalexn8n.ru/portal-api/data

echo ""
echo "==> Done!"
