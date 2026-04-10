#!/bin/bash

# Скрипт запуска прокси для Telegram
# Добавь в автозагрузку: ~/.config/autostart/

set -e

echo "=== Запуск прокси для Telegram ==="

# Проверка что Happ запущен
if ! pgrep -f "Happ" > /dev/null; then
    echo "⚠️  Happ не запущен. Запускаю..."
    /opt/happ/bin/Happ &
    sleep 5
fi

# Проверка что xray запущен
if ! pgrep -f "xray" > /dev/null; then
    echo "⚠️  xray не запущен. Пробую запустить..."
    # Ждём пока Happ запустит xray
    for i in {1..10}; do
        if pgrep -f "xray" > /dev/null; then
            echo "✅ xray запущен"
            break
        fi
        sleep 1
    done
fi

# Проверка порта
if ! ss -tlnp | grep -q "10809"; then
    echo "⚠️  Порт 10809 не слушается. Запускаю socat..."
    socat TCP-LISTEN:10809,reuseaddr,fork TCP:127.0.0.1:10809 &
    echo "✅ socat запущен (PID: $!)"
fi

echo ""
echo "✅ Прокси готов!"
echo "   HTTP: http://127.0.0.1:10809"
echo "   SOCKS5: http://127.0.0.1:10808"
