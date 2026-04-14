# Аудит Инфраструктуры n8n

**Дата:** 14 апреля 2026 г.
**Среда:** Linux Mint 22.3, Docker 28.2.2, PostgreSQL 16-alpine

---

## 1. АНАЛИЗ БАЗЫ ДАННЫХ (PostgreSQL 16-alpine)

### 1.1 Общая информация
- **База данных:** n8n_database
- **Размер:** 50 MB
- **Таблиц:** 81 (public schema)
- **Подключений в пуле:** не исчерпаны (alert не срабатывал)

### 1.2 Индексы

**Всего индексов:** ~120 (покрытие хорошее)

**Проблемные индексы (0 сканирований):**

| Таблица | Индекс | Сканирований | Статус |
|---------|--------|-------------|--------|
| `document_jobs` | pkey | 0 | **НИКОГДА НЕ ИСПОЛЬЗОВАЛСЯ** |
| `document_chunks` | pkey | 0 | **НИКОГДА НЕ ИСПОЛЬЗОВАЛСЯ** |
| `document_chunks` | job_id_chunk_index_status_idx | 0 | **НИКОГДА НЕ ИСПОЛЬЗОВАЛСЯ** |
| `document_chapters` | pkey | 0 | **НИКОГДА НЕ ИСПОЛЬЗОВАЛСЯ** |
| `document_characters` | pkey | 0 | **НИКОГДА НЕ ИСПОЛЬЗОВАЛСЯ** |
| `document_arcs` | pkey | 0 | **НИКОГДА НЕ ИСПОЛЬЗОВАЛСЯ** |
| `document_glossary` | pkey | 0 | **НИКОГДА НЕ ИСПОЛЬЗОВАЛСЯ** |
| `document_log` | pkey | 0 | **НИКОГДА НЕ ИСПОЛЬЗОВАЛСЯ** |
| `telegram_chats` | pkey + chat_idx | 0 | **НИКОГДА НЕ ИСПОЛЬЗОВАЛСЯ** |
| `telegram_message` | pkey | 0 | **НИКОГДА НЕ ИСПОЛЬЗОВАЛСЯ** |
| `job_current` | pkey | 0 | **НИКОГДА НЕ ИСПОЛЬЗОВАЛСЯ** |
| `temp_table` | pkey | 0 | **НИКОГДА НЕ ИСПОЛЬЗОВАЛСЯ** |
| `chat_hub_sessions` | pkey + owner_lastmsg | 0 | **НИКОГДА НЕ ИСПОЛЬЗОВАЛСЯ** |
| `chat_hub_messages` | pkey + sessionId | 0 | **НИКОГДА НЕ ИСПОЛЬЗОВАЛСЯ** |
| `webhook_entity` | composite index | 0 | **НИКОГДА НЕ ИСПОЛЬЗОВАЛСЯ** |

**Анализ:** Все таблицы custom-домена (document_*, telegram_*) имеют нулевые сканирования индексов. Это означает, что **запросы к этим таблицам идут через full table scan** или ORM-запросы не используют индексы эффективно.

**Хорошие индексы (активные):**
- `workflow_entity_pkey` — 26,240 сканирований (отлично)
- `execution_entity_pkey` — 3,514 сканирований
- `credentials_entity_pkey` — 3,511 сканирований
- `idx_execution_entity_wait_till_status_deleted_at` — 2,073 сканирований

**Отсутствующие индексы:**
- `telegram_send_message` — нет индекса на `chat_id` и `created_at` (таблица без индексов кроме PK)
- `document_jobs` — нет индекса на `status`, `file_id` (частые фильтры)

### 1.3 Foreign Keys

**Всего FK:** 85 — **отлично, все связи защищены**

Ключевые пользовательские FK:
- `document_chunks.job_id` -> `document_jobs(id) ON DELETE CASCADE`
- `document_chunks.chapter` -> `document_chapters(id) ON DELETE CASCADE`
- `telegram_message.chat_id` -> `telegram_chats(id) ON DELETE CASCADE`
- `document_arcs.job_id` -> `document_jobs(id) ON DELETE CASCADE`
- `document_chapters.job_id` -> `document_jobs(id) ON DELETE CASCADE`
- `document_glossary.job_id` -> `document_jobs(id) ON DELETE CASCADE`
- `document_log.job_id` -> `document_jobs(id) ON DELETE CASCADE`

### 1.4 Размер таблиц

**Оценка через pg_statio:** данные недоступны из-за ошибки, но общий размер БД = 50 MB, что очень мало. Это подтверждает низкую нагрузку на кастомные таблицы.

### 1.5 Deadlock / Блокировки

**Текущих блокировок:** 0 — чисто

### 1.6 Состояние данных

**document_jobs:**
| Статус | Кол-во |earliest | latest |
|---------|--------|---------|--------|
| pending | 1 | 2026-03-28 | 2026-03-28 |

**КРИТИЧНО:** 1 задача в статусе `pending` уже **17 дней** (с 28 марта). Вероятно, застрявшая задача.

**document_chunks:**
| Статус | Кол-во |
|---------|--------|
| pending | 5 |
| done | 5 |

**КРИТИЧНО:** 5 чанков в статусе `pending` — не обработаны. Общая обработка документов остановилась.

**telegram_send_message:**
- **Всего записей:** 14
- **Нет статуса!** Таблица не имеет колонки `status` — она содержит только `id`, `chat_id`, `message`, `created_at`
- **Неочищенные записи:** 14 записей хранятся навсегда, нет механизма очистки
- Последние 2 записи имеют `chat_id = 923741104` (Alexei) с сообщениями `create_job`

**execution_entity:**
| Статус | Кол-во |
|---------|--------|
| success | 165 |
| error | 33 |
| waiting | 2 |
| **Итого** | **205** |

**Error rate:** 33/205 = **16.1%** — превышает порог warning (15%) в Prometheus

### 1.7 Рекомендации по БД

1. **Добавить индексы:**
   ```sql
   CREATE INDEX idx_document_jobs_status ON document_jobs(status);
   CREATE INDEX idx_document_jobs_file_id ON document_jobs(file_id);
   CREATE INDEX idx_telegram_send_message_chat_id ON telegram_send_message(chat_id);
   CREATE INDEX idx_telegram_send_message_created_at ON telegram_send_message(created_at);
   ```

2. **Очистить застрявшие данные:**
   - Проверить document_jobs с status='pending' от 28 марта
   - Обработать или удалить 5 pending чанков в document_chunks

3. **Добавить TTL-очистку для telegram_send_message** — сейчас записи копятся навсегда

4. **Добавить колонку `status` в telegram_send_message** для отслеживания отправки

5. **Удалить temp_table** — если не используется

---

## 2. АНАЛИЗ DOCKER-ИНФРАСТРУКТУРЫ

### 2.1 Общее состояние

| Параметр | Значение |
|----------|---------|
| Docker Version | 28.2.2 |
| Контейнеров | 21 (20 running, 1 stopped) |
| Образов | 169 |
| Driver | overlay2 |
| Cgroup | systemd v2 |
| Security | apparmor + seccomp (builtin) |
| CPU | 12 ядер |
| RAM | 33.4 GB |

### 2.2 Контейнеры (по проектам)

**n8n-docker проект:**
| Контейнер | Статус | Сеть | Порты |
|-----------|--------|------|-------|
| n8n | running (Up 2h) | host | 5678 |
| db (PostgreSQL) | running | n8n-docker_default | 5432:5432 |
| pgadmin4 | running | n8n-docker_default | 127.0.0.1:5055:80 |
| node-exporter | running | n8n-docker_default | 9100 |
| prometheus | running | n8n-docker_default | 9090 |
| postgres-exporter | running | n8n-docker_default | 9187 |
| backup-exporter | running | n8n-docker_default | 9199 |
| **caddy** | **НЕ ЗАПУЩЕН** | - | 80, 443 (systemd на хосте) |

**Важно:** Caddy запущен как systemd-сервис на хосте (`/etc/caddy/Caddyfile`), НЕ как контейнер. Это архитектурное решение.

**lightrag проект:**
| Контейнер | Статус | Сеть |
|-----------|--------|------|
| ollama | running (Up 34h) | host |
| open-webui | running (Up 34h, healthy) | host |
| apps-hub | running (Up 2h) | host |
| test-runner | **exited (1)** 5 days ago | host |

**firecrawl проект:**
| Контейнер | Статус | Сеть |
|-----------|--------|------|
| firecrawl-api | running | firecrawl_backend |
| firecrawl-playwright | running | firecrawl_backend |
| firecrawl-worker | running | firecrawl_backend |
| firecrawl-rabbitmq | running (healthy) | firecrawl_backend |
| firecrawl-nuq-postgres | running | firecrawl_backend |

**Другие:**
| Контейнер | Статус | Сеть | Примечание |
|-----------|--------|------|------------|
| portainer | running (Up 34h) | bridge | 0.0.0.0:9000 — **ПУБЛИЧНЫЙ** |
| grafana | running (Up 34h) | bridge | 0.0.0.0:3000 — **ПУБЛИЧНЫЙ** |
| drawio | running | - | 127.0.0.1:24700 |
| searxng | running | searxng_default | 127.0.0.1:8888 |
| crontab-ui | running | crontab_default | 127.0.0.1:8001 |

### 2.3 Сети

| Сеть | Driver | Subnet | Назначение |
|------|--------|--------|------------|
| n8n-docker_default | bridge | 172.18.0.0/16 | n8n проект |
| n8n-docker_n8n-network | bridge | 172.19.0.0/16 | **ПУСТАЯ** (не используется) |
| firecrawl_backend | bridge | 172.22.0.0/16 | Firecrawl изоляция |
| lightrag_lightrag_net | bridge | 172.20.0.0/16 | **ПУСТАЯ** (host networking) |
| lightrag_default | bridge | 172.21.0.0/16 | **ПУСТАЯ** (host networking) |
| searxng_default | bridge | 172.23.0.0/16 | SearXNG |
| crontab_default | bridge | 172.24.0.0/16 | Crontab |
| lightrag-kb_default | bridge | 172.25.0.0/16 | LightRAG KB |
| bridge | bridge | 172.17.0.0/16 | Default (Grafana, Portainer) |
| host | host | - | Ollama, Open-WebUI, Apps-Hub, N8N |

**Проблема:** 3 пустых сети (n8n-network, lightrag_net, lightrag_default) — тратят ресурсы.

### 2.4 Volumes

**Именованные volumes (критичные):**
| Volume | Назначение |
|--------|-----------|
| n8n-docker_db_storage | PostgreSQL данные |
| n8n-docker_n8n_storage | n8n workflow/credentials |
| n8n-docker_prometheus_data | Prometheus TSDB |
| n8n-docker_grafana_storage | Grafana данные |
| n8n-docker_pgadmin_data | pgAdmin настройки |
| lightrag_ollama_storage | Ollama модели |
| lightrag_open-webui-data | Open WebUI данные |
| portainer_data | Portainer данные |

**Анонимные volumes:** 15 — **проблема**. Anonymous volumes затрудняют бэкап и мониторинг.

### 2.5 Docker-образы

**Образы без тегов (dangling):** ~10 образов без тегов, включая несколько `firecrawl-nuq-postgres` промежуточных слоёв.

**Общий размер образов:** ~15-20 GB (включая Playwright 2.2GB, Open-WebUI 4.7GB, SD-WebUI 4.2GB)

### 2.6 Рекомендации по Docker

1. **Удалить пустые сети:** `n8n-docker_n8n-network`, `lightrag_lightrag_net`, `lightrag_default`
2. **Удалить anonymous volumes** после проверки что не нужны
3. **Удалить test-runner** контейнер (exited 5 дней назад)
4. **Prune образов:** `docker image prune -a` (сэкономит ~5-10 GB)
5. **Portainer** — порт 9000 слушает `0.0.0.0`, должен быть `127.0.0.1`
6. **Grafana** — порт 3000 слушает `0.0.0.0`, должен быть `127.0.0.1`

---

## 3. АНАЛИЗ БЕЗОПАСНОСТИ

### 3.1 Критические уязвимости

| Проблема | Риск | Статус |
|----------|------|--------|
| **DB пароль в docker-compose.yml** | **КРИТИЧНО** | Пароли `n8n_db_password`, `n8n_user` в plaintext в файле |
| **N8N_ENCRYPTION_KEY в compose** | **КРИТИЧНО** | Ключ шифрования в plaintext |
| **Google OAuth Token в .env** | **КРИТИЧНО** | Токен в `/home/user/.env` |
| **Portainer 0.0.0.0:9000** | **ВЫСОКИЙ** | Docker management API публично доступен |
| **Grafana 0.0.0.0:3000** | **ВЫСОКИЙ** | Без аутентификации (подтверждено в Caddyfile) |
| **PostgreSQL 0.0.0.0:5432** | **ВЫСОКИЙ** | БД доступна извне |
| **Docker socket RW в Portainer** | **ВЫСОКИЙ** | `/var/run/docker.sock` с rw доступом |
| **pgADMIN: SERVER_MODE=False** | **СРЕДНИЙ** | Нет master password |
| **pgADMIN: MASTER_PASSWORD_REQUIRED=False** | **СРЕДНИЙ** | |
| **pgADMIN: ENFORCE_CSRF=False** | **СРЕДНИЙ** | Уязвимость к CSRF |

### 3.2 Открытые порты (хост)

| Порт | Процесс | Доступ | Риск |
|------|---------|--------|------|
| 80 | Caddy | 0.0.0.0 | OK (HTTPS redirect) |
| 443 | Caddy | 0.0.0.0 | OK (TLS) |
| 5432 | PostgreSQL | **0.0.0.0** | **КРИТИЧНО** |
| 3000 | Grafana | **0.0.0.0** | **ВЫСОКИЙ** |
| 3002 | Firecrawl API | **0.0.0.0** | **СРЕДНИЙ** |
| 8000 | Apps-Hub | **0.0.0.0** | **СРЕДНИЙ** |
| 8080 | Open-WebUI | **0.0.0.0** | **ВЫСОКИЙ** |
| 8888 | SearXNG | **0.0.0.0** | Low (basicauth через Caddy) |
| 9000 | Portainer | **0.0.0.0** | **КРИТИЧНО** |
| 9090 | Prometheus | **0.0.0.0** | **СРЕДНИЙ** |
| 9100 | Node Exporter | **0.0.0.0** | OK (read-only) |
| 9199 | Backup Exporter | **0.0.0.0** | Low |
| 9621 | LightRAG | **0.0.0.0** | OK |
| 9622 | LightRAG KB | **0.0.0.0** | OK |
| 11434 | Ollama | **0.0.0.0** | OK (basicauth через Caddy) |
| 24700 | Draw.io | **0.0.0.0** | OK |
| 5678 | n8n | **0.0.0.0** | OK (через Caddy TLS) |
| 22 | SSH | **0.0.0.0** | Зависит от настроек |

### 3.3 SSL/TLS

- **Caddy** автоматически управляет Let's Encrypt сертификатами для всех доменов
- **TLS issuer:** alexei.bigalex@yandex.ru
- Все домены bigalexn8n.ru покрыты HTTPS
- **Проблема:** прямые IP-доступы (0.0.0.0) bypass Caddy TLS

### 3.4 Docker Socket

- Portainer имеет **rw** доступ к `/var/run/docker.sock`
- Это означает **полный root-доступ к хосту** через Docker
- Portainer — единственный контейнер с таким доступом
- **Рекомендация:** использовать read-only socket где возможно

### 3.5 File Permissions

- `/home/user/.env` — содержит Google OAuth token в plaintext
- `/home/user/n8n-docker/docker-compose.yml` — содержит DB credentials в plaintext
- **Рекомендация:** `chmod 600` для `.env`, перенести секреты в Docker secrets

### 3.6 Rate Limiting

- **Caddy:** rate limiting НЕ настроен ни для одного домена
- **n8n:** встроенный rate limiting НЕ включён
- **Firecrawl:** только basic auth на /admin, API без rate limit
- **Ollama:** basic auth через Caddy, но без rate limit
- **Рекомендация:** добавить rate limiting в Caddy для всех публичных endpoint

---

## 4. АНАЛИЗ ИНФРАСТРУКТУРЫ

### 4.1 Prometheus — Собираемые метрики

| Job | Target | Interval | Статус |
|-----|--------|----------|--------|
| prometheus | localhost:9090 | 15s | OK |
| node_exporter | node-exporter:9100 | 15s | OK |
| postgres_exporter | postgres-exporter:9187 | 15s | OK |
| ollama-health | localhost:11434/api/health | 30s | OK |
| lightrag-health | localhost:9621/health | 30s | OK |
| n8n | localhost:5678/healthz | 30s | OK |
| backup-exporter | backup-exporter:9199 | 60s | OK |

**Проблемы:**
- Prometheus alert rules ссылаются на `probe_success{job="ollama-health"}` — но **blackbox exporter НЕ настроен**. Метрика `probe_success` не будет генерироваться.
- Alert `N8NProcessDown` использует `up{job="n8n"}` — но n8n на host networking, метрика `up` может не работать корректно.
- Custom metrics (`n8n_workflow_errors_total`, `n8n_workflow_executions_total`, `n8n_workflow_duration_seconds_bucket`, `ollama_loaded_models`, `dlq_pending_tasks`, `circuit_breaker_state`) — **требуют кастомных exporters или instrumentation**, которые могут не быть реализованы.

### 4.2 Grafana — Дашборды

| UID | Название | Теги | Статус |
|-----|----------|------|--------|
| rYdddlPWk | Node Exporter Full | linux | OK (стандартный) |
| n8n-backup-dashboard | n8n Backup Dashboard | backup, monitoring, n8n | OK |

**Missing dashboards:**
- Нет дашборда для PostgreSQL мониторинга (postgres_exporter данные собираются но не визуализируются)
- Нет дашборда для Translation Pipeline (упоминается в alert annotations)
- Нет дашборда для Firecrawl monitoring
- Нет дашборда для Docker контейнеров

### 4.3 Backup Strategy

**Механизм:** Git-based sync через cron
- **Скрипт:** `/home/user/n8n-backups/cron_backup.sh` -> `sync_n8n.sh`
- **Последний запуск:** 2026-04-14 05:14:36 (сегодня)
- **Бэкапит:** 0 workflows (API не отвечает?), 37 docs, 74 AI config, 632 app files

**Бэкапы БД:**
- `/home/user/n8n-backups/system_db_backups/` — SQL дампы 7 таблиц (credentials, project, user, workflow_entity и др.)
- **НО:** нет автоматического `pg_dump` всей БД
- `document_jobs`, `document_chunks`, `telegram_messages` **НЕ бэкапятся**

**Проблемы:**
1. **Нет полного pg_dump** — только выборочные таблицы
2. **Custom-таблицы не бэкапятся** — document_*, telegram_* таблицы без бэкапа
3. **Workflow export = 0** — API экспорта не работает или нет workflows
4. **Нет offsite backup** — всё на одной машине
5. **Нет тестирования восстановления**
6. **Нет backup Prometheus/Grafana данных**
7. **Нет backup Docker volumes**

### 4.4 Monitoring Gaps

**Чего НЕ хватает:**

1. **Blackbox Exporter** — alert rules ссылаются на `probe_success` но blackbox exporter не установлен
2. **cAdvisor** — нет мониторинга контейнерных ресурсов (CPU, RAM per container)
3. **Alertmanager** — не настроен. Alert rules есть, но куда они отправляются?
4. **n8n custom metrics** — alert rules ссылаются на `n8n_workflow_errors_total` и др., но n8n не экспортирует эти метрики из коробки
5. **Firecrawl monitoring** — нет job_name для Firecrawl в Prometheus
6. **Docker metrics** — нет мониторинга Docker daemon
7. **Log aggregation** — логи分散 в json-file, нет ELK/Loki
8. **Uptime monitoring** — нет внешнего мониторинга доступности
9. **Disk I/O monitoring** — нет alert на disk latency
10. **SSL cert expiry** — нет мониторинга истечения сертификатов

---

## 5. СВОДКА КРИТИЧЕСКИХ ПРОБЛЕМ

### КРИТИЧНО (требует немедленного исправления)

1. **PostgreSQL на 0.0.0.0:5432** — БД доступна из любой сети
2. **Portainer на 0.0.0.0:9000** с Docker socket rw — полный контроль над сервером
3. **Credentials в plaintext** — DB password, N8N_ENCRYPTION_KEY в docker-compose.yml
4. **Google OAuth Token** в /home/user/.env
5. **Застрявшая задача** — document_jobs status=pending 17 дней
6. **5 pending чанков** — обработка документов остановлена
7. **Error rate 16.1%** — превышает threshold 15%

### ВЫСОКИЙ ПРИОРИТЕТ

8. **Grafana на 0.0.0.0:3000** без аутентификации
9. **Open-WebUI на 0.0.0.0:8080** — AI interface без защиты
10. **Нет полного бэкапа БД** — custom таблицы не бэкапятся
11. **No offsite backup** — всё на одной машине
12. **Alertmanager не настроен** — alert rules без notification channel
13. **pgAdmin CSRF отключён** — уязвимость к CSRF атакам
14. **Rate limiting отсутствует** — все endpoint без rate limit

### СРЕДНИЙ ПРИОРИТЕТ

15. **15 anonymous volumes** — затрудняют бэкап
16. **3 пустых Docker сети** — wasted resources
17. **Missing индексы** на telegram_send_message и document_jobs
18. **telegram_send_message без TTL** — записи копятся навсегда
19. **169 Docker образов** — занимают ~15-20 GB, нужен prune
20. **Monitoring gaps** — 10+ метрик без coverage
21. **test-runner exited (1)** 5 дней — нужно удалить или починить
22. **Нет дашборда Translation Pipeline** — alert references несуществующий дашборд

---

## 6. RECOMMENDED ACTION PLAN

### Phase 1: Security (Day 1)
```bash
# 1. Ограничить доступ к PostgreSQL
# В docker-compose.yml: ports: - 127.0.0.1:5432:5432

# 2. Ограничить Portainer
# В docker-compose.yml: ports: - 127.0.0.1:9000:9000

# 3. Ограничить Grafana
# ports: - 127.0.0.1:3000:3000

# 4. chmod 600 для .env
chmod 600 /home/user/.env

# 5. pgAdmin security fix
# PGADMIN_CONFIG_ENFORCE_CSRF=True
```

### Phase 2: Data Fix (Day 1-2)
```sql
-- Добавить индексы
CREATE INDEX idx_document_jobs_status ON document_jobs(status);
CREATE INDEX idx_telegram_send_message_chat_id ON telegram_send_message(chat_id);

-- Проверить застрявшую задачу
SELECT * FROM document_jobs WHERE status = 'pending';
```

### Phase 3: Backup (Day 2-3)
1. Настроить `pg_dump` для всех таблиц
2. Добавить offsite backup (S3/Google Drive)
3. Протестировать восстановление

### Phase 4: Monitoring (Day 3-5)
1. Установить Blackbox Exporter
2. Установить cAdvisor
3. Настроить Alertmanager с notification channel
4. Создать Translation Pipeline dashboard
5. Добавить Firecrawl monitoring

### Phase 5: Cleanup (Day 5)
1. `docker image prune -a`
2. Удалить пустые сети
3. Удалить test-runner
4. Настроить log rotation
