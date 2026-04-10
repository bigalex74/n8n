#!/bin/bash

# Скрипт настройки pgAdmin (добавляет сервис в docker-compose.yml)

set -e

echo "=== Настройка pgAdmin ==="
echo ""

COMPOSE_FILE="docker-compose.yml"

# Проверка, существует ли docker-compose.yml
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ Файл $COMPOSE_FILE не найден"
    exit 1
fi

# Проверка, добавлен ли уже pgAdmin
if grep -q "pgadmin:" "$COMPOSE_FILE"; then
    echo "✅ pgAdmin уже настроен в docker-compose.yml"
    echo ""
    echo "Для запуска выполните: ./start_pgadmin.sh"
    exit 0
fi

echo "📝 Добавление pgAdmin в docker-compose.yml..."

# Добавляем сервис pgadmin перед секцией networks
sed -i '/^networks:/i\
  pgadmin:\
    image: dpage/pgadmin4:latest\
    restart: unless-stopped\
    environment:\
      - PGADMIN_DEFAULT_EMAIL=admin@pgadmin.local\
      - PGADMIN_DEFAULT_PASSWORD=admin\
      - PGADMIN_CONFIG_SERVER_MODE=False\
      - PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED=False\
    ports:\
      - "5050:80"\
    volumes:\
      - pgadmin_data:/var/lib/pgadmin\
    networks:\
      - n8n-network\
    depends_on:\
      - db\
' "$COMPOSE_FILE"

# Добавляем volume для pgadmin
sed -i '/^volumes:/a\
  pgadmin_data:' "$COMPOSE_FILE"

echo "✅ pgAdmin добавлен в docker-compose.yml"
echo ""
echo "📋 Для запуска выполните:"
echo "   ./start_pgadmin.sh"
echo ""
echo "📋 Для остановки выполните:"
echo "   ./stop_pgadmin.sh"
echo ""
