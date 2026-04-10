#!/bin/bash
# Скрипт установки Docker и n8n

echo "--- Установка Docker и Docker Compose ---"
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2

# Добавление текущего пользователя в группу docker
sudo usermod -aG docker $USER

echo "--- Запуск n8n, PostgreSQL и Caddy ---"
# Переходим в директорию
cd ~/n8n-docker

# Запускаем контейнеры
sudo docker compose up -d

echo "--- Установка завершена! ---"
echo "n8n должен быть доступен по адресу: https://${DOMAIN_NAME:-n8n.example.com}"
echo "Внимание: для работы HTTPS домен должен быть направлен на IP этого сервера."
echo "Проверьте статус контейнеров командой: sudo docker compose ps"
