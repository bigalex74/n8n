#!/bin/bash
# Запуск n8n с прокси для Telegram

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
export GENERIC_TIMEZONE="Europe/Moscow"
export EXECUTIONS_DATA_PRUNE="true"
export EXECUTIONS_DATA_MAX_AGE="168"
export NODE_TLS_REJECT_UNAUTHORIZED="0"

exec n8n start
