#!/bin/bash

# Скрипт настройки xray (HApp) для приёма подключений из Docker

set -e

echo "=== Настройка xray для Docker ==="
echo ""

CONFIG_FILE="/home/user/.config/Happ/config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Конфигурационный файл не найден: $CONFIG_FILE"
    exit 1
fi

# Создать резервную копию
cp "$CONFIG_FILE" "$CONFIG_FILE.backup"
echo "✅ Резервная копия создана: $CONFIG_FILE.backup"

# Обновить конфигурацию — добавить HTTP прокси inbound
echo "📝 Обновление конфигурации..."

python3 << 'PYTHON'
import json

with open('/home/user/.config/Happ/config.json', 'r') as f:
    config = json.load(f)

# Добавить HTTP inbound для Docker
http_inbound = {
    "type": "http",
    "tag": "http-in",
    "listen": "0.0.0.0",
    "listen_port": 10809
}

# Проверить есть ли уже такой inbound
exists = False
for inbound in config.get('inbounds', []):
    if inbound.get('type') == 'http' and inbound.get('listen_port') == 10809:
        exists = True
        break

if not exists:
    if 'inbounds' not in config:
        config['inbounds'] = []
    config['inbounds'].append(http_inbound)
    print("✅ Добавлен HTTP inbound на порт 10809")
else:
    print("ℹ️  HTTP inbound уже существует")

# Обновить существующий socks inbound для приёма извне
for inbound in config.get('inbounds', []):
    if inbound.get('type') == 'socks':
        inbound['listen'] = '0.0.0.0'
        inbound['listen_port'] = 10808
        print("✅ Socks inbound обновлён для приёма извне")

with open('/home/user/.config/Happ/config.json', 'w') as f:
    json.dump(config, f, indent=4)

print("✅ Конфигурация обновлена")
PYTHON

# Перезапустить HApp
echo ""
echo "🔄 Перезапуск HApp..."

# Найти процесс Happ
HAPP_PID=$(pgrep -f "sing-box.*Happ" | head -1)

if [ -n "$HAPP_PID" ]; then
    echo "📋 HApp процесс найден (PID: $HAPP_PID)"
    # Отправить SIGTERM для graceful shutdown
    sudo kill -TERM $HAPP_PID 2>/dev/null || true
    sleep 3
fi

# Запустить HApp заново через systemctl или напрямую
if systemctl is-active --quiet happ 2>/dev/null; then
    sudo systemctl restart happ
    echo "✅ HApp перезапущен через systemctl"
else
    echo "⚠️  HApp не найден в systemctl. Перезапустите вручную."
fi

# Проверка
sleep 3
echo ""
echo "📋 Проверка портов..."
ss -tlnp | grep -E "10809|10808" | head -5

echo ""
echo "✅ Готово!"
echo ""
echo "Теперь прокси доступен:"
echo "  - HTTP: http://YOUR_SERVER_IP:10809"
echo "  - SOCKS5: socks://YOUR_SERVER_IP:10808"
echo ""
echo "Для Docker используйте:"
echo "  - HTTP_PROXY=http://host.docker.internal:10809"
echo "  - HTTPS_PROXY=http://host.docker.internal:10809"
