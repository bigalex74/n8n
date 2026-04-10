# Настройка системы n8n + Telegram + Proxy

## Дата настройки: 25 марта 2026 г.

## Компоненты системы

### 1. Docker контейнеры
- **n8n** - основная платформа автоматизации (порт 5678)
- **PostgreSQL 16** - база данных (порт 5432)
- **PgAdmin 4** - администрирование БД (порт 5050)

### 2. Прокси (xray)
- **Порт**: 10809
- **Адрес**: 127.0.0.1:10809
- **Назначение**: Обход блокировок Telegram в России
- **Статус**: ✅ Работает

### 3. HTTPS (Caddy)
- **Домен**: bigalexn8n.ru
- **SSL**: Let's Encrypt (автоматическое продление)
- **Статус**: ✅ Работает

## Конфигурация n8n

### Переменные окружения
```yaml
N8N_ENCRYPTION_KEY: InqHY6REAuKYfnqDgmmcZGuSnLZJFl90
DB_TYPE: postgresdb
DB_POSTGRESDB_HOST: 127.0.0.1
DB_POSTGRESDB_PORT: 5432
DB_POSTGRESDB_DATABASE: n8n_database
DB_POSTGRESDB_USER: n8n_user
DB_POSTGRESDB_PASSWORD: n8n_db_password
DB_POSTGRESDB_SCHEMA: public
N8N_HOST: bigalexn8n.ru
N8N_PROTOCOL: https
N8N_PORT: 5678
HTTP_PROXY: http://127.0.0.1:10809
HTTPS_PROXY: http://127.0.0.1:10809
NO_PROXY: localhost,127.0.0.1,::1
```

### Активные workflow (18)
- ✅ Telegram Trigger
- ✅ Добавление Глоссария
- ✅ Создание Глоссария
- ✅ 🔴 Global Error Handler
- ✅ Добавление Промта
- ✅ [Перевод] Арка
- ✅ [Перевод] Перевод чанка
- ✅ Парсинг файла для перевода
- ✅ Select From List
- ✅ [GET] /select_files
- ✅ Предварительный анализ файла для перевода
- ✅ [Перевод] Глава
- ✅ [Перевод] Обработка ошибки
- ✅ Translate Chunk
- ✅ Finish
- ✅ [GET] Document
- ✅ Настройка БД
- ✅ Start

### Telegram Credentials
- **ID**: V4jPr27PQcfRRHY9
- **Имя**: Telegram account
- **Тип**: telegramApi
- **Статус**: ✅ Настроен

## Проверка работы

### 1. Доступ к n8n
```bash
curl -k https://bigalexn8n.ru/
# HTTP Status: 200 ✅
```

### 2. Прокси
```bash
curl --proxy http://127.0.0.1:10809 https://api.telegram.org/botTEST/getMe
# {"ok":false,"error_code":404,"description":"Not Found"} ✅
```

### 3. Webhook Telegram
```bash
curl -k https://bigalexn8n.ru/webhook/telegram
# 404 (ожидаемо - GET запрос не зарегистрирован) ✅
```

## Управление системой

### Запуск/остановка
```bash
# Запуск всех сервисов
docker compose -f /home/user/n8n-docker/docker-compose.yml up -d

# Остановка
docker compose -f /home/user/n8n-docker/docker-compose.yml down

# Перезапуск n8n
docker compose -f /home/user/n8n-docker/docker-compose.yml restart n8n

# Просмотр логов
docker logs n8n-docker-n8n-1 --tail 50
```

### Доступ к интерфейсу
- **URL**: https://bigalexn8n.ru
- **PgAdmin**: http://127.0.0.1:5050

## База данных

### Подключение
```bash
docker exec n8n-docker-db-1 psql -U n8n_user -d n8n_database
```

### Основные таблицы
- workflow_entity - workflow
- credentials_entity - credentials
- telegram_send_message - Telegram сообщения
- telegram_message - входящие Telegram
- telegram_chats - чаты Telegram

## Решение проблем

### Прокси не работает
1. Проверить xray: `systemctl status xray`
2. Проверить порт: `ss -tlnp | grep 10809`
3. Перезапустить: `systemctl restart xray`

### Telegram не подключается
1. Проверить токен в credentials
2. Проверить прокси: `curl --proxy http://127.0.0.1:10809 https://api.telegram.org/`
3. Проверить webhook в Telegram через getWebhookInfo

### Workflow не активируется
1. Проверить логи: `docker logs n8n-docker-n8n-1 --tail 100`
2. Проверить БД: `SELECT * FROM workflow_entity WHERE active = true;`
3. Перезапустить n8n

## Контакты
- **Домен**: bigalexn8n.ru
- **Email**: alexei.bigalex@yandex.ru
