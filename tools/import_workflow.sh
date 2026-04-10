#!/bin/bash

# Скрипт импорта workflow и credentials в n8n через API

set -e

N8N_URL="https://bigalexn8n.ru:5678"
WORKFLOW_FILE="/home/user/workflows_migration.json"
CREDENTIALS_FILE="/home/user/credentials_migration.json"

echo "=== Импорт в n8n ==="
echo ""

# Проверка файлов
if [ ! -f "$WORKFLOW_FILE" ]; then
    echo "❌ Файл workflow не найден: $WORKFLOW_FILE"
    exit 1
fi

if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "❌ Файл credentials не найден: $CREDENTIALS_FILE"
    exit 1
fi

echo "📁 Файлы найдены:"
echo "   - $WORKFLOW_FILE"
echo "   - $CREDENTIALS_FILE"
echo ""

# Получение API ключа (нужно ввести вручную в n8n)
echo "🔑 Для импорта требуется API ключ n8n"
echo ""
echo "Как получить API ключ:"
echo "1. Откройте https://bigalexn8n.ru:5678"
echo "2. Нажмите на иконку профиля (справа вверху)"
echo "3. Выберите 'API Key'"
echo "4. Создайте новый ключ и скопируйте его"
echo ""

read -p "Введите API ключ n8n: " API_KEY

if [ -z "$API_KEY" ]; then
    echo "❌ API ключ не введён"
    exit 1
fi

# Импорт credentials
echo ""
echo "📤 Импорт credentials..."
CREDENTIALS_RESPONSE=$(curl -s -X POST "$N8N_URL/api/v1/credentials/import" \
    -H "X-N8N-API-KEY: $API_KEY" \
    -H "Content-Type: application/json" \
    -d @"$CREDENTIALS_FILE")

echo "Ответ сервера (credentials): $CREDENTIALS_RESPONSE"

# Импорт workflows
echo ""
echo "📤 Импорт workflows..."
WORKFLOW_RESPONSE=$(curl -s -X POST "$N8N_URL/api/v1/workflows/import" \
    -H "X-N8N-API-KEY: $API_KEY" \
    -H "Content-Type: application/json" \
    -d @"$WORKFLOW_FILE")

echo "Ответ сервера (workflow): $WORKFLOW_RESPONSE"

echo ""
echo "✅ Импорт завершён!"
echo ""
echo "📋 Проверьте в n8n:"
echo "   - Workflows: https://bigalexn8n.ru:5678/workflow"
echo "   - Credentials: https://bigalexn8n.ru:5678/credential"
