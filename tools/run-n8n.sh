#!/bin/bash
# Автозапуск n8n с проверкой базы данных

while true; do
    # Ждем доступности базы данных
    until docker ps | grep -q n8n-docker-db-1 && nc -z 127.0.0.1 5432 2>/dev/null; do
        echo "$(date): Waiting for database..."
        sleep 5
    done
    
    echo "$(date): Starting n8n..."
    export HTTP_PROXY="http://127.0.0.1:10820"
    export HTTPS_PROXY="http://127.0.0.1:10820"
    export NO_PROXY="localhost,127.0.0.1"
    export N8N_ENCRYPTION_KEY="InqHY6REAuKYfnqDgmmcZGuSnLZJFl90"
    export DB_TYPE="postgresdb"
    export DB_POSTGRESDB_HOST="127.0.0.1"
    export DB_POSTGRESDB_PORT="5432"
    export DB_POSTGRESDB_DATABASE="n8n_database"
    export DB_POSTGRESDB_USER="n8n_user"
    export DB_POSTGRESDB_PASSWORD="n8n_db_password"
    export N8N_HOST="bigalexn8n.ru"
    export N8N_PROTOCOL="https"
    export N8N_PORT="5678"
    export N8N_EDITOR_BASE_URL="https://bigalexn8n.ru/"
    export WEBHOOK_URL="https://bigalexn8n.ru/"
    export N8N_BASIC_AUTH_ACTIVE="true"
    export N8N_BASIC_AUTH_USER="bigalex"
    export N8N_BASIC_AUTH_PASSWORD="qQ08102003"
    export GENERIC_TIMEZONE="Europe/Moscow"
    export EXECUTIONS_DATA_PRUNE="true"
    export EXECUTIONS_DATA_MAX_AGE="168"
    export NODE_TLS_REJECT_UNAUTHORIZED="0"
    
    n8n start
    echo "$(date): n8n exited, restarting..."
    sleep 5
done
