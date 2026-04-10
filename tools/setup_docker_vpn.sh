#!/bin/bash

# Скрипт настройки Docker для работы через VPN (HApp)

set -e

echo "=== Настройка Docker для работы через VPN ==="
echo ""

# Найти интерфейс VPN
VPN_INTERFACE=$(ip addr show | grep -E "inet.*tun" | awk '{print $NF}' | head -1)

if [ -z "$VPN_INTERFACE" ]; then
    echo "❌ VPN интерфейс не найден"
    exit 1
fi

echo "✅ VPN интерфейс: $VPN_INTERFACE"

# Получить IP VPN
VPN_IP=$(ip addr show $VPN_INTERFACE | grep "inet " | awk '{print $2}' | cut -d'/' -f1)
echo "✅ VPN IP: $VPN_IP"

# Проверить маршрут по умолчанию через VPN
DEFAULT_VIA_VPN=$(ip route | grep "default via" | grep -v "wlp59s0" | head -1)

if [ -n "$DEFAULT_VIA_VPN" ]; then
    echo "✅ Маршрут через VPN активен: $DEFAULT_VIA_VPN"
else
    echo "⚠️  Маршрут по умолчанию не через VPN"
fi

# Перезапустить Docker сеть
echo ""
echo "🔄 Перезапуск Docker сетей..."

# Остановить контейнеры
cd /home/user/n8n-docker
sudo docker compose down

# Очистить сети
sudo docker network prune -f

# Удалить старые сети
sudo docker network rm n8n-docker_n8n-network 2>/dev/null || true

# Запустить заново
sudo docker compose up -d

echo ""
echo "✅ Docker сети пересозданы"
echo ""

# Проверить доступность Telegram
echo "🔍 Проверка доступа к Telegram API..."

sleep 5

if sudo docker exec n8n-docker-n8n-1 node -e "
const https = require('https');
const options = { hostname: 'api.telegram.org', port: 443, path: '/bot8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0/getMe', method: 'GET', timeout: 10000 };
const req = https.request(options, (res) => { console.log('✅ Telegram API:', res.statusCode); process.exit(0); });
req.on('error', (e) => { console.log('❌ Ошибка:', e.message); process.exit(1); });
req.on('timeout', () => { console.log('❌ Таймаут'); process.exit(1); });
req.end();
" 2>&1; then
    echo ""
    echo "🎉 Telegram API доступен!"
else
    echo ""
    echo "❌ Telegram API всё ещё недоступен"
    echo ""
    echo "Попробуйте:"
    echo "1. Переподключить VPN"
    echo "2. Проверить что VPN работает на хосте:"
    echo "   curl https://api.telegram.org/bot8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0/getMe"
    echo "3. Использовать прокси вместо VPN"
fi

echo ""
echo "📋 Статус контейнеров:"
sudo docker ps --format "table {{.Names}}\t{{.Status}}"
