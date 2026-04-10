#!/bin/bash

# Скрипт остановки pgAdmin

set -e

echo "=== Остановка pgAdmin ==="
echo ""

# Проверка, запущен ли pgAdmin
if ! sudo docker ps | grep -q n8n-docker-pgadmin-1; then
    echo "ℹ️  pgAdmin не запущен"
    exit 0
fi

echo "⏹️  Остановка pgAdmin..."
sudo docker compose stop pgadmin

echo ""
echo "✅ pgAdmin остановлен"
echo ""
