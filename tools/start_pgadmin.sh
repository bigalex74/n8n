#!/bin/bash

# Скрипт запуска pgAdmin для подключения к PostgreSQL n8n

set -e

echo "=== pgAdmin для n8n PostgreSQL ==="
echo ""

# Проверка Docker
if ! sudo docker ps &>/dev/null; then
    echo "❌ Docker не запущен"
    exit 1
fi

# Проверка, запущен ли уже pgAdmin
if sudo docker ps | grep -q n8n-docker-pgadmin-1; then
    echo "✅ pgAdmin уже запущен"
    sudo docker ps --filter "name=pgadmin" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo "Доступ: http://localhost:5050"
    echo "Email: admin@admin.com"
    echo "Пароль: admin"
    exit 0
fi

echo "🚀 Запуск pgAdmin..."

# Добавляем pgAdmin в docker-compose, если ещё не добавлен
if ! grep -q "pgadmin:" docker-compose.yml; then
    echo "⚠️  pgAdmin не найден в docker-compose.yml"
    echo "Сначала выполните: ./setup_pgadmin.sh"
    exit 1
fi

# Запускаем только pgAdmin
sudo docker compose up -d pgadmin

echo ""
echo "✅ pgAdmin запущен!"
echo ""
echo "📍 Доступ: http://localhost:5050"
echo "📧 Email: admin@pgadmin.local"
echo "🔑 Пароль: admin"
echo ""
echo "📋 Параметры подключения к PostgreSQL:"
echo "   Host: db"
echo "   Port: 5432"
echo "   Database: n8n_database"
echo "   Username: n8n_user"
echo "   Password: n8n_db_password"
echo ""
