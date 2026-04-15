#!/bin/bash
# Автозапуск n8n через Infisical с проверкой базы данных
# Секреты хранятся в облаке Infisical (https://secrets.bigalexn8n.ru)

cd /home/user/n8n-docker

while true; do
    # Ждем доступности базы данных (проверка на порту 5432)
    until nc -z 127.0.0.1 5432 2>/dev/null; do
        echo "$(date): Waiting for database..."
        sleep 5
    done
    
    echo "$(date): Starting n8n with Infisical Secrets Injection..."
    
    # Запуск n8n с впрыском переменных окружения из Infisical
    infisical run --domain https://secrets.bigalexn8n.ru --env dev -- n8n start
    
    echo "$(date): n8n exited, restarting..."
    sleep 5
done
