#!/bin/bash
# Безопасный перезапуск n8n через Infisical
cd /home/user/n8n-docker

echo '--- Перезапуск n8n через Infisical ---'

# Останавливаем текущие контейнеры
sudo docker compose down

# Запускаем заново с впрыском секретов (если они используются в docker-compose.yml)
# Или просто запускаем контейнеры, если n8n внутри них сам пойдет в Infisical
infisical run --domain https://secrets.bigalexn8n.ru --env dev -- sudo docker compose up -d

echo '--- n8n успешно перезапущен с обновленными секретами! ---'
sleep 3
