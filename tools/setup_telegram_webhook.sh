#!/bin/bash

# Скрипт настройки Telegram Webhook для n8n

set -e

echo "=== Настройка Telegram Webhook ==="
echo ""

# Запрос токена бота
read -p "Введите токен вашего Telegram бота: " BOT_TOKEN

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Токен не введён"
    exit 1
fi

# URL webhook
WEBHOOK_URL="https://bigalexn8n.ru/webhook/telegram"

echo ""
echo "🔗 URL webhook: $WEBHOOK_URL"
echo ""

# Установка webhook через Telegram API
echo "📡 Установка webhook..."
RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\":\"$WEBHOOK_URL\",\"allowed_updates\":[\"message\",\"callback_query\"]}")

echo ""
echo "Ответ Telegram API:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Проверка статуса
echo "📋 Проверка статуса webhook..."
STATUS=$(curl -s "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo")
echo ""
echo "Статус webhook:"
echo "$STATUS" | python3 -m json.tool 2>/dev/null || echo "$STATUS"
echo ""

# Сохранение токена в .env
if [ -f /home/user/n8n-docker/.env ]; then
    if grep -q "TELEGRAM_BOT_TOKEN" /home/user/n8n-docker/.env; then
        sed -i "s/^TELEGRAM_BOT_TOKEN=.*/TELEGRAM_BOT_TOKEN=$BOT_TOKEN/" /home/user/n8n-docker/.env
    else
        echo "TELEGRAM_BOT_TOKEN=$BOT_TOKEN" >> /home/user/n8n-docker/.env
    fi
    echo "✅ Токен сохранён в .env"
fi

echo ""
echo "📋 Следующие шаги:"
echo "1. Откройте n8n: https://bigalexn8n.ru/"
echo "2. Создайте новый workflow или откройте существующий"
echo "3. Добавьте ноду 'Telegram Trigger'"
echo "4. В настройках укажите:"
echo "   - Credential: создайте новый с вашим токеном"
echo "   - Updates: message, callback_query"
echo "5. Активируйте workflow"
echo ""
echo "🎉 Готово! Webhook настроен на: $WEBHOOK_URL"
