# Инструкция по настройке Telegram Webhook для n8n

## 📋 Описание

Telegram Webhook позволяет получать сообщения от бота напрямую на ваш сервер n8n без polling.

**URL webhook:** `https://bigalexn8n.ru/webhook/telegram`

## 🚀 Быстрая настройка

### 1. Создайте бота в Telegram

1. Откройте [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`
3. Введите имя и username бота
4. Скопируйте токен (выглядит как `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Настройте webhook

**Вариант A: Автоматически (рекомендуется)**

```bash
cd /home/user/n8n-docker
./setup_telegram_webhook.sh
```

Введите токен бота когда потребуется.

**Вариант B: Вручную через curl**

```bash
BOT_TOKEN="ваш_токен_бота"
curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\":\"https://bigalexn8n.ru/webhook/telegram\"}"
```

### 3. Проверьте статус

```bash
BOT_TOKEN="ваш_токен_бота"
curl "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"
```

Должны увидеть:
```json
{
  "ok": true,
  "result": {
    "url": "https://bigalexn8n.ru/webhook/telegram",
    "has_custom_webhook": true,
    "pending_update_count": 0
  }
}
```

## 🔧 Настройка workflow в n8n

### Вариант 1: Использовать готовый workflow

1. Откройте n8n: https://bigalexn8n.ru/
2. Нажмите **☰ Menu** → **Import from File**
3. Выберите файл `telegram_webhook_workflow.json`
4. Откройте workflow
5. Замените ноду "Telegram Webhook" на **Telegram Trigger** из каталога нод
6. Создайте credentials для Telegram с вашим токеном
7. Активируйте workflow

### Вариант 2: Создать вручную

1. Откройте https://bigalexn8n.ru/
2. Создайте новый workflow
3. Добавьте ноду **Telegram Trigger**
4. В настройках:
   - **Credential:** Create New → Telegram API
   - **Token:** ваш токен от BotFather
   - **Updates:** message, callback_query
5. Добавьте ноду **Respond to Webhook** (опционально)
6. Активируйте workflow

## 📝 Примеры workflow

### Простой эхо-бот

```
Telegram Trigger → Telegram (Send Message)
```

### Бот с кнопками

```
Telegram Trigger → Switch (по типу сообщения)
  ├→ Telegram (Send Message с keyboard)
  └→ Telegram (Send Message с текстом)
```

## 🔍 Troubleshooting

### Webhook не устанавливается

**Проблема:** Telegram не может подключиться к серверу

**Решение:**
1. Проверьте что сервер доступен: `curl -I https://bigalexn8n.ru/`
2. Проверьте что Caddy работает: `sudo docker ps | grep caddy`
3. Проверьте логи: `sudo docker logs n8n-docker-caddy-1`

### Webhook установлен, но сообщения не приходят

**Проблема:** n8n не обрабатывает webhook

**Решение:**
1. Убедитесь что workflow активирован
2. Проверьте что путь webhook совпадает: `/webhook/telegram`
3. Посмотрите логи n8n: `sudo docker logs n8n-docker-n8n-1 | grep telegram`

### Ошибка "Unauthorized"

**Проблема:** Неверный токен бота

**Решение:**
1. Проверьте токен в @BotFather (`/token`)
2. Пересоздайте credentials в n8n
3. Обновите webhook: `./setup_telegram_webhook.sh`

### Ошибка "Connection closed"

**Проблема:** Блокировка Telegram

**Решение:**
- Используйте прокси (см. `check_telegram.sh`)
- Или используйте polling вместо webhook

## 📊 Полезные команды

```bash
# Проверка статуса webhook
curl "https://api.telegram.org/botTOKEN/getWebhookInfo" | python3 -m json.tool

# Удаление webhook
curl -X POST "https://api.telegram.org/botTOKEN/deleteWebhook"

# Пересоздание webhook
curl -X POST "https://api.telegram.org/botTOKEN/setWebhook" \
    -H "Content-Type: application/json" \
    -d '{"url":"https://bigalexn8n.ru/webhook/telegram"}'

# Логи n8n
sudo docker logs n8n-docker-n8n-1 | tail -50

# Логи Caddy
sudo docker logs n8n-docker-caddy-1 | tail -50
```

## 🔐 Безопасность

1. **Храните токен в секрете** — не коммитьте в git
2. **Используйте .env файл** для токена:
   ```bash
   TELEGRAM_BOT_TOKEN=ваш_токен
   ```
3. **Ограничьте доступ** к webhook через Caddy (basicauth)
4. **Проверяйте origin** запросов в workflow

## 📁 Файлы

| Файл | Описание |
|------|----------|
| `setup_telegram_webhook.sh` | Скрипт автоматической настройки |
| `telegram_webhook_workflow.json` | Готовый workflow для импорта |
| `check_telegram.sh` | Проверка доступности Telegram API |

## 🆘 Помощь

Если возникли проблемы:
1. Проверьте логи: `sudo docker logs n8n-docker-n8n-1`
2. Проверьте webhook info через API Telegram
3. Убедитесь что workflow активирован в n8n
