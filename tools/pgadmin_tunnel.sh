#!/bin/bash

# SSH-туннель для доступа к pgAdmin с локальной машины

echo "=== SSH-туннель для pgAdmin ==="
echo ""
echo "📋 Откройте браузер и перейдите на: http://localhost:5050"
echo ""
echo "🔑 Логин: admin@admin.com"
echo "🔑 Пароль: admin"
echo ""
echo "⏹️  Для остановки нажмите Ctrl+C"
echo ""

ssh -L 5050:localhost:5050 user@bigalexn8n.ru
