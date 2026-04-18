#!/bin/bash
# Безопасный перезапуск n8n через Infisical
cd /home/user/n8n-docker

echo '--- Перезапуск n8n через Infisical ---'

# Останавливаем текущие контейнеры
./scripts/compose_with_infisical.sh down

# Запускаем заново с впрыском секретов (если они используются в docker-compose.yml)
./scripts/compose_with_infisical.sh up -d

echo '--- n8n успешно перезапущен с обновленными секретами! ---'
sleep 3
