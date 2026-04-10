#!/bin/bash

# Скрипт настройки прокси для Telegram в n8n

echo "=== Настройка подключения к Telegram API ==="
echo ""

# Проверка доступности Telegram API
echo "🔍 Проверка доступности api.telegram.org..."
if sudo docker exec n8n-docker-n8n-1 node -e "
const https = require('https');
const options = { hostname: 'api.telegram.org', port: 443, path: '/', method: 'GET', timeout: 5000 };
const req = https.request(options, (res) => { console.log('✅ Telegram API доступен:', res.statusCode); process.exit(0); });
req.on('error', (e) => { console.log('❌ Ошибка:', e.message); process.exit(1); });
req.on('timeout', () => { console.log('❌ Таймаут'); process.exit(1); });
req.end();
" 2>&1; then
    echo ""
    echo "✅ Telegram API доступен!"
    echo ""
    echo "Если credentials всё равно не работают:"
    echo "1. Проверьте токен бота"
    echo "2. Убедитесь что бот не заблокирован"
else
    echo ""
    echo "❌ Telegram API недоступен из контейнера n8n"
    echo ""
    echo "Возможные решения:"
    echo ""
    echo "1️⃣ Использовать прокси (рекомендуется):"
    echo "   Добавьте в docker-compose.yml для n8n:"
    echo "   environment:"
    echo "     - HTTP_PROXY=http://your-proxy:8080"
    echo "     - HTTPS_PROXY=http://your-proxy:8080"
    echo "     - NODE_TLS_REJECT_UNAUTHORIZED=0"
    echo ""
    echo "2️⃣ Попробовать обойти блокировку DNS:"
    echo "   Добавьте в docker-compose.yml:"
    echo "   dns:"
    echo "     - 8.8.8.8"
    echo "     - 1.1.1.1"
    echo ""
    echo "3️⃣ Использовать webhook вместо polling:"
    echo "   Настройте webhook через https://YOUR_DOMAIN/webhook/telegram"
    echo ""
fi
