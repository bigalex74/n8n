#!/bin/bash

# Скрипт проверки и настройки прокси для Telegram

echo "=== Проверка прокси для Telegram ==="
echo ""

# Список бесплатных прокси для теста
PROXY_LIST=(
    "http://103.155.210.100:8181"
    "http://103.155.210.101:8181"
    "http://185.199.229.156:7493"
    "http://185.199.228.220:7300"
    "http://178.128.232.230:8080"
)

echo "🔍 Проверка бесплатных прокси..."
echo ""

for proxy in "${PROXY_LIST[@]}"; do
    echo -n "Проверка $proxy ... "
    RESULT=$(curl -s --max-time 5 -x "$proxy" "https://api.telegram.org/bot8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0/getMe" 2>&1)
    
    if echo "$RESULT" | grep -q '"ok":true'; then
        echo "✅ РАБОТАЕТ!"
        echo ""
        echo "Используйте этот прокси:"
        echo ""
        echo "1. Откройте docker-compose.yml"
        echo "2. Добавьте в секцию n8n environment:"
        echo "   - HTTP_PROXY=$proxy"
        echo "   - HTTPS_PROXY=$proxy"
        echo ""
        echo "3. Перезапустите n8n:"
        echo "   cd /home/user/n8n-docker"
        echo "   sudo docker compose up -d n8n"
        echo ""
        exit 0
    else
        echo "❌"
    fi
done

echo ""
echo "❌ Ни один бесплатный прокси не работает"
echo ""
echo "Рекомендации:"
echo "1. Купите платный прокси (IPRoyal, Smartproxy, Proxy-Seller)"
echo "2. Используйте свой прокси на VPS"
echo "3. Почините VPN подключение (HApp не работает)"
echo ""
