# 📘 n8n Translation System - Полная Документация Проекта

**Версия:** 2.0
**Дата:** 9 апреля 2026 г.
**Статус:** Production (с активной разработкой)
**Автор:** Алексей (bigalex)

---

# Содержание

1. [Обзор проекта](#обзор-проекта)
2. [Инфраструктура](#инфраструктура)
3. [Архитектура системы](#архитектура-системы)
4. [База данных](#база-данных)
5. [Workflows](#workflows)
6. [Мониторинг](#мониторинг)
7. [Безопасность](#безопасность)
8. [Сетевая конфигурация](#сетевая-конфигурация)
9. [Интеграции](#интеграции)
10. [Операционные процедуры](#операционные-процедуры)

---

# Обзор проекта

## Назначение

Промышленная система автоматизированного перевода документов (веб-новеллы, книги) с использованием:
- **n8n** - оркестрация workflows
- **LightRAG** - управление контекстом (RAG система)
- **Ollama** - локальная LLM для перевода
- **PostgreSQL** - хранение данных и состояния
- **Telegram Bot** - интерфейс пользователя
- **Grafana/Prometheus** - мониторинг

## Ключевые возможности

1. **Автоматический перевод документов**
   - Парсинг файлов (PDF, TXT, и др.)
   - Разбиение на арки и главы (LLM-based)
   - Извлечение глоссария (имена, термины, локации)
   - Перевод с сохранением контекста (RAG)
   - Контроль качества (LLM scoring)
   - Постредактура

2. **Telegram интеграция**
   - Уведомления о статусе перевода
   - Получение файлов через бота
   - Отправка результатов
   - Интерактивные кнопки (повтор, остановка)

3. **Мониторинг и логирование**
   - Real-time dashboard в Grafana
   - Метрики в Prometheus
   - Логи в PostgreSQL
   - Экспорт метрик хоста и БД

## Статистика проекта

| Метрика | Значение |
|---------|----------|
| Всего workflows | 55 |
| Активных workflows | 33 |
| Таблиц в БД | 81 |
| Документов в обработке | 1 (тестовый) |
| Chunk'ей переведено | 5 из 10 |
| Telegram чатов | 1 |
| Uptime системы | 2+ дня |

---

# Инфраструктура

## Docker Контейнеры

### n8n-docker проект

| Контейнер | Образ | Порт | Назначение | Статус |
|-----------|-------|------|------------|--------|
| n8n-docker-n8n-1 | n8nio/n8n:latest | 5678 (через Caddy) | Workflow automation | ✅ Up 50m |
| n8n-docker-db-1 | postgres:16-alpine | 5432 | База данных | ✅ Up 2d |
| n8n-docker-pgadmin-1 | dpage/pgadmin4:latest | 127.0.0.1:5055 | DB admin UI | ✅ Up 2d |
| prometheus | prom/prometheus:latest | 9090 | Metrics collection | ✅ Up 2d |
| n8n-grafana | grafana/grafana:11.5.0 | 3000 | Visualization | ✅ Up 2d |
| node-exporter | prom/node-exporter:latest | 9100 | Host metrics | ✅ Up 2d |
| postgres-exporter | postgres-exporter:latest | 9187 | DB metrics | ✅ Up 2d |

### lightrag проект

| Контейнер | Образ | Порт | Назначение | Статус |
|-----------|-------|------|------------|--------|
| ollama | ollama/ollama:latest | 11434 | Local LLM inference | ✅ Up 27h |
| lightrag | lightrag-lightrag (custom) | 9621 | RAG system | ✅ Up |
| apps-hub | telegram-apps (custom) | - | Telegram apps | ✅ Up 16h |
| portainer | portainer/portainer-ce:latest | 9000 | Docker management | ✅ Up |

### Отдельные контейнеры

| Контейнер | Порт | Назначение |
|-----------|------|------------|
| crontab-ui | 8001 | Task scheduling UI |

## Volume'ы

### Критичные данные
- `n8n-docker_db_storage` - PostgreSQL данные
- `n8n-docker_n8n_storage` - n8n конфигурация
- `n8n-docker_caddy_data` - SSL сертификаты
- `ollama_storage` - LLM модели

### Временные/Кэшируемые
- `n8n-docker_prometheus_data` - метрики
- `n8n-docker_grafana_storage` - дашборды
- `lightrag_ollama_storage` - Ollama кэш

## Ресурсы сервера

- **OS:** Linux (Linux Mint)
- **GPU:** NVIDIA (для Ollama)
- **Сеть:** host networking (n8n, lightrag)
- **Домен:** bigalexn8n.ru
- **SSL:** Let's Encrypt (автоматическое продление)

---

# Архитектура системы

## Слои системы

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│  Telegram Bot │ Webhook API │ pgAdmin │ Grafana │ Portainer│
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    ORCHESTRATION LAYER                       │
│                         n8n Workflows                        │
│  Main Pipeline │ Sub-workflows │ Error Handler │ Notifications│
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                      │
│  LightRAG API │ Ollama API │ Custom Python Scripts          │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    DATA LAYER                                │
│  PostgreSQL (81 table) │ File System │ Lightrag Vector DB   │
└─────────────────────────────────────────────────────────────┘
```

## Потоки данных

### 1. Перевод документа (основной pipeline)

```
User → Telegram Bot → n8n Trigger → Parse File → Split Chapters
                                           ↓
                                     Extract Glossary
                                           ↓
                              Human Review (optional)
                                           ↓
                              Translate Chapters (parallel)
                                           ↓
                              Quality Check (LLM scoring)
                                           ↓
                              Post-Editing (if needed)
                                           ↓
                              Export & Notify User
```

### 2. Система уведомлений

```
DB Trigger (telegram_send_message INSERT)
         ↓
n8n PostgresTrigger → Validate Payload
         ↓
    Get Context (1 SQL query)
         ↓
    Router (by message type)
         ↓
    Task_* Formatter
         ↓
    Notify Telegram (idempotent)
         ↓
    Log to DB
```

### 3. Мониторинг

```
Node Exporter → Prometheus → Grafana
Postgres Exporter → Prometheus → Grafana
n8n Executions → PostgreSQL → Grafana
```

---

# База данных

## Основные таблицы

### document_jobs - Задачи перевода
```sql
-- Ключевые поля
id (PK), file_name, status, translated_file, glossary_file
billing_polza, billing_neuro
web_view_link, web_chapters_link, web_raw_link
created_at, updated_at, finished_at
```

**Статусы:** pending, processing, completed, failed, paused

### document_chapters - Главы документов
```sql
-- Ключевые поля
id (PK), job_id (FK), arc_id (FK), chapter_number
summary, roller_summary
line_start, line_finish, status
```

**Статусы:** pending, processing, translated, reviewed, completed

### document_chunks - Чанки текста
```sql
-- Ключевые поля
id (PK), job_id (FK), chapter (FK), chunk_index
chunk_text, prev_line
result_text, raw_translate_text
status, error_text
```

**Статусы:** pending, translating, done, error

**Индексы:** `document_chunks_job_id_chunk_index_status_idx`

### document_glossary - Глоссарий
```sql
-- Ключевые поля
id (PK), job_id (FK), name, translate, gender
```

### document_arcs - Арки
```sql
-- Ключевые поля
id (PK), job_id (FK), arc_number
start_chapter, end_chapter
summary (JSON)
```

### document_log - Логи обработки
```sql
-- Ключевые поля
id (PK), job_id (FK), date_time, node, type, log
```

### telegram_send_message - Очередь уведомлений
```sql
-- Ключевые поля
id (PK), chat_id, message, created_at
```

**Триггер:** `tg_n8n_send_message` → уведомляет n8n workflow

### telegram_chats - Авторизованные чаты
```sql
-- Ключевые поля
id (PK), chat (Telegram chat_id)
```

### telegram_message - Входящие сообщения
```sql
-- Ключевые поля
id (PK), chat_id (FK), message_id, delete_id
```

### translate_prompts - Промпты для перевода
```sql
-- Ключевые поля
id (PK), agent_name (UNIQUE), prompt_text, updated_at
```

**Текущие промпты:**
- translator - Промпт для переводчика
- editor - Промпт для редактора

## Связи таблиц

```
document_jobs (1)
    ├── (N) document_arcs
    │       └── (N) document_chapters
    │              └── (N) document_chunks
    ├── (N) document_glossary
    ├── (N) document_log
    └── (N) document_characters

telegram_chats (1)
    └── (N) telegram_message

telegram_send_message (standalone, trigger для n8n)
```

---

# Workflows

## Классификация workflows

### 1. Pipeline Перевода (8 workflows)

| Workflow | ID | Active | Назначение |
|----------|-----|--------|------------|
| [Перевод] Арка | - | ✅ | Обработка арки документа |
| [Перевод] Глава | - | ✅ | Обработка главы |
| [Перевод] Перевод чанка | - | ✅ | Перевод отдельвого чанка |
| [Перевод] Обработка ошибки | - | ✅ | Error handling для перевода |
| Парсинг файла для перевода | - | ✅ | Initial file parsing |
| Предварительный анализ файла для перевода | - | ✅ | File analysis |
| sub_lightrag_api | - | ✅ | LightRAG API integration |
| Анотация | - | ✅ | Annotation generation |

### 2. Система уведомлений (9 workflows)

| Workflow | ID | Active | Назначение |
|----------|-----|--------|------------|
| Send Message | J62UViXZMD5o6qoU | ✅ | Main orchestrator |
| [Send] create_job | - | ✅ | Notification: job created |
| [Send] wait | - | ✅ | Notification wait logic |
| [Send] error | - | ✅ | Error notification |
| [Send] finish | - | ✅ | Completion notification |
| [Send] processing | - | ✅ | Progress notification |
| sub_get_context | - | ❌ | Context provider |
| sub_notify | - | ❌ | Telegram notification service |
| Select From List | - | ✅ | Interactive selection |

### 3. Task Workflows (6 workflows - Message Formatters)

| Workflow | ID | Active | Назначение |
|----------|-----|--------|------------|
| SM - Task - Create | - | ❌ | Format "create" message |
| SM - Task - Start Processing | - | ❌ | Format "start" message |
| SM - Task - Process | - | ❌ | Format "process" message |
| SM - Task - Error | - | ❌ | Format "error" message |
| SM - Task - Finish | - | ❌ | Format "finish" message |
| SM - Task - Stop | - | ❌ | Format "stop" message (with button) |

### 4. Telegram Integration (6 workflows)

| Workflow | ID | Active | Назначение |
|----------|-----|--------|------------|
| Telegram Trigger | - | ❌ | Main telegram trigger |
| Перезапуск прослушки Telegram | - | ✅ | Restart Telegram listener |
| Получение сообщения | - | ✅ | Message reception |
| Telegram Final | - | ❌ | Final telegram logic |
| Telegram Simple | - | ❌ | Simple telegram test |
| Telegram Webhook Handler | - | ❌ | Webhook handler |
| 🔄 Telegram Polling (n8n) | - | ❌ | Polling-based reception |

### 5. Система и утилиты (7 workflows)

| Workflow | ID | Active | Назначение |
|----------|-----|--------|------------|
| 🔴 Global Error Handler | - | ✅ | Global error handling |
| System - Stats Dashboard | - | ❌ | Analytics dashboard |
| System - Proxy Check | - | ❌ | Proxy connectivity check |
| System - Novel Pipeline Test | - | ❌ | Pipeline integrity test |
| Start | - | ✅ | System initialization |
| Finish | - | ✅ | Completion logic |
| Translate Chunk | - | ✅ | Chunk translation utility |

### 6. Файлы и ресурсы (5 workflows)

| Workflow | ID | Active | Назначение |
|----------|-----|--------|------------|
| [GET] /select_files | - | ✅ | File selection endpoint |
| [GET] Document | - | ✅ | Document retrieval |
| [Send] create_job | - | ✅ | Job creation |
| Переведенный файл в Telegram | - | ✅ | Send to Telegram |
| Переведенный файл в Google Drive | - | ✅ | Backup to Drive |

### 7. Управление ресурсами (4 workflows)

| Workflow | ID | Active | Назначение |
|----------|-----|--------|------------|
| Добавление Глоссария | - | ✅ | Glossary management |
| Создание Глоссария | - | ✅ | Glossary creation |
| Добавление Промта | - | ✅ | Prompt management |
| Добавление промта для постредакта | - | ✅ | Post-edit prompts |
| Добавление ресурсов в бд | - | ✅ | Resource DB management |
| Настройка БД | - | ✅ | DB initialization |

### 8. Тестовые и deprecated (10 workflows)

| Workflow | ID | Active | Назначение |
|----------|-----|--------|------------|
| Activate All Workflows (Mass) | - | ❌ | Mass activation utility |
| Test Webhook Trigger | - | ❌ | Webhook testing |
| [TEST] Error Handler Check | - | ❌ | Error handler test |
| [TEST] Manual Error Test | - | ❌ | Manual error test |
| Test Minimal Webhook | - | ❌ | Minimal webhook test |
| My workflow | - | ❌ | Default/unused |
| [depricated] Send Message (RESTORED) | - | ❌ | Old version |
| SM - Task workflows (5) | - | ❌ | Old task workflows |

---

# Мониторинг

## Prometheus Targets

| Target | Port | Status | Назначение |
|--------|------|--------|------------|
| node_exporter | 9100 | ✅ up | System metrics (CPU, RAM, disk) |
| postgres_exporter | 9187 | ✅ up | PostgreSQL metrics |

## Grafana Dashboards

### n8n Monitoring Dashboard

**Панели:**
1. **Всего executions** - общее количество запусков
2. **Executions по статусу** - success vs error
3. **Executions по времени** - временная серия
4. **Среднее время выполнения** - performance metric
5. **Топ workflow по ошибкам** - error-prone workflows
6. **Документы по статусам** - document pipeline status
7. **Последние документы** - таблица с деталями
8. **Входящие/Исходящие сообщения Telegram** - коммуникация
9. **Активные чаты** - количество пользователей

### Метрики

```sql
-- Ключевые SQL запросы
SELECT COUNT(*) FROM execution;
SELECT status, COUNT(*) FROM document_jobs GROUP BY status;
SELECT success, COUNT(*) FROM execution GROUP BY success;
SELECT chat_id, COUNT(*) FROM telegram_chats WHERE is_authorized = true;
```

---

# Безопасность

## Credentials

### Telegram Bot
- **Token:** 8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0
- **Chat ID:** 923741104 (1 авторизованный чат)
- **Webhook:** https://bigalexn8n.ru/webhook/telegram

### База данных
- **User:** n8n_user
- **Password:** n8n_db_password (в .env)
- **Database:** n8n_database
- **Port:** 5432 (доступен локально)

### n8n
- **Encryption Key:** InqHY6REAuKYfnqDgmmcZGuSnLZJFl90
- **Domain:** bigalexn8n.ru
- **Protocol:** HTTPS (Let's Encrypt)

### External APIs
- **polza.ai LLM:** pza_PV5t0y6PTuE8GLcZ-jgvlpNDLlZm0mUT

## Прокси

- **Тип:** Xray/Hiddify
- **Адрес:** 127.0.0.1:10808 (HTTP/HTTPS)
- **Назначение:** Обход блокировок Telegram
- **NO_PROXY:** localhost,127.0.0.1,::1,192.168.1.124,bigalexn8n.ru

## Доступы

### pgAdmin
- **URL:** http://127.0.0.1:5055
- **Email:** alexei.bigalex@yandex.ru
- **Password:** admin

### Grafana
- **URL:** https://grafana.bigalexn8n.ru
- **BasicAuth:** admin / JDJhJDE0JHhOWGxMYzNKM1ZvV3RQc0xMY3RZeE91Q053WkxZQ3pYbGF5eE5oNXN6VnBxYnZGMnRLUzBNZy9l

### Portainer
- **URL:** http://localhost:9000

---

# Сетевая конфигурация

## Reverse Proxy (Caddy)

### Домены

| Домен | Порт | Назначение |
|-------|------|------------|
| bigalexn8n.ru | 443 | n8n web interface |
| www.bigalexn8n.ru | 443 | Redirect → bigalexn8n.ru |
| grafana.bigalexn8n.ru | 443 | Grafana dashboard (BasicAuth) |

### Webhook Endpoints

| Path | Описание |
|------|----------|
| /webhook/telegram* | Telegram webhook (без аутентификации) |
| /webhook/* | General webhooks |

### Caddy Configuration

```
bigalexn8n.ru {
    reverse_proxy localhost:5678
    @telegram_webhook path /webhook/telegram*
    handle @telegram_webhook → reverse_proxy
}
```

## Network Modes

| Service | Network | Причина |
|---------|---------|---------|
| n8n | host | Доступ к локальному прокси |
| LightRAG | host | Прямой доступ к Ollama |
| Ollama | host | GPU access, performance |
| PostgreSQL | bridge | Isolation, security |
| Prometheus/Grafana | bridge | Standard Docker networking |

---

# Интеграции

## LightRAG Integration

### API Endpoints
- **Base URL:** http://localhost:9621
- **POST /documents** - Upload document
- **POST /query** - Query with context
- **GET /health** - Health check

### Configuration
```
LLM_BINDING=openai
LLM_MODEL=openai/gpt-5.4-nano
LLM_BASE_URL=https://polza.ai/api/v1
EMBEDDING_BINDING=ollama
EMBEDDING_MODEL=nomic-embed-text
CHUNK_SIZE=500
CHUNK_OVERLAP_SIZE=50
```

## Ollama Integration

### Models
- **qwen2.5:32b** - Quality check, translation
- **llama3.2:3b** - Fast operations
- **nomic-embed-text** - Embeddings for LightRAG

### API
- **URL:** http://localhost:11434
- **Endpoint:** /api/generate

## Telegram Integration

### Bot Features
- Webhook-based (not polling)
- Idempotent notifications
- Interactive buttons
- File reception
- Status updates

### Message Types
1. create_job - 🆕 Задача создана
2. start_processing - ▶️ Обработка началась
3. processing - 🔄 Перевод в процессе (с прогресс-баром)
4. error_processing - ⚠️ Ошибка обработки
5. finish_processing - ✅ Перевод завершен
6. stop_processing - 🚨 Перевод остановлен (с кнопкой)

---

# Операционные процедуры

## Запуск системы

```bash
# 1. Запуск n8n-docker
cd /home/user/n8n-docker
docker compose up -d

# 2. Запуск lightrag
cd /home/user/lightrag
docker compose up -d

# 3. Проверка
docker ps
curl -I https://bigalexn8n.ru
```

## Остановка системы

```bash
# n8n-docker
cd /home/user/n8n-docker
docker compose down

# lightrag
cd /home/user/lightrag
docker compose down
```

## Резервное копирование

```bash
# Бэкап БД
docker exec n8n-docker-db-1 pg_dump -U n8n_user n8n_database > backup.sql

# Бэкап workflows
# Через n8n UI: Settings → Export

# Скрипт бэкапа
/home/user/n8n-docker/backup_n8n.sh
```

## Перезапуск сервисов

```bash
# Перезапуск n8n
docker restart n8n-docker-n8n-1

# Перезапуск Telegram listener
# Через workflow "Перезапуск прослушки Telegram"

# Перезапуск прокси
/home/user/n8n-docker/start_proxy.sh
```

## Мониторинг

```bash
# Логи n8n
docker logs n8n-docker-n8n-1 --tail 100

# Логи БД
docker logs n8n-docker-db-1 --tail 50

# Prometheus
curl http://localhost:9090/api/v1/targets

# Telegram webhook
curl https://api.telegram.org/bot8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0/getWebhookInfo
```

## Troubleshooting

### Прокси не работает
```bash
/home/user/n8n-docker/check_proxy.sh
curl --proxy http://127.0.0.1:10808 https://api.telegram.org
```

### Webhook не работает
```bash
# Проверка Caddy
docker logs n8n-docker-caddy-1

# Проверка webhook в Telegram
curl https://api.telegram.org/botTOKEN/getWebhookInfo
```

### Workflow не активируется
```sql
SELECT name, active, "updatedAt" FROM workflow_entity WHERE name = 'Workflow Name';
UPDATE workflow_entity SET active = true WHERE name = 'Workflow Name';
```

---

# Скрипты и утилиты

## Скрипты в /home/user/n8n-docker/

| Скрипт | Назначение |
|--------|------------|
| backup_n8n.sh | Резервное копирование |
| check_proxy.sh | Проверка прокси |
| check_telegram.sh | Проверка Telegram API |
| create_error_handler.py | Создание Global Error Handler |
| import_workflow.sh | Импорт workflow |
| import_workflows_to_db.py | Массовый импорт |
| pgadmin_tunnel.sh | SSH туннель для pgAdmin |
| restart_n8n.sh | Перезапуск n8n |
| setup_n8n.sh | Начальная настройка |
| setup_pgadmin.sh | Настройка pgAdmin |
| setup_telegram_webhook.sh | Настройка webhook |
| setup_xray_proxy.sh | Настройка Xray прокси |
| start_pgadmin.sh | Запуск pgAdmin |
| start_proxy.sh | Запуск прокси |
| stop_pgadmin.sh | Остановка pgAdmin |

## Файлы конфигурации

| Файл | Назначение |
|------|------------|
| .env | Переменные окружения |
| docker-compose.yml | Docker конфигурация |
| Caddyfile | Reverse proxy конфигурация |
| prometheus/prometheus.yml | Prometheus конфигурация |
| xray-config/config.json | Xray прокси конфигурация |

---

# Известные проблемы

1. **55 workflows, 33 активны** - много неактивных/тестовых
2. **Нет документации по некоторым workflow** - требуется инвентаризация
3. **document_jobs: 1 тестовый документ** - нет реальных данных
4. **Telegram: 1 чат** - требуется расширение
5. **sub_get_context, sub_notify неактивны** - возможно deprecated
6. **Дублирование task workflows** - старые и новые версии
7. **Нет автоматического бэкапа** - только ручной скрипт

---

# Рекомендации

1. **Провести ревизию workflows** - удалить/архивировать неактивные
2. **Документировать все workflows** - создать workflow map
3. **Автоматизировать бэкапы** - cron + external storage
4. **Настроить alerting** - Grafana → Telegram при ошибках
5. **Добавить health checks** - для всех сервисов
6. **Оптимизировать БД** - индексы, analyze, vacuum
7. **Версионировать workflows** - Git sync (уже есть, использовать)

---

**Документация создана:** 9 апреля 2026 г.
**Последнее обновление:** 9 апреля 2026 г.
**Следующая проверка:** 16 апреля 2026 г.
