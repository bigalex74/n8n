# Сводный аудиторский отчёт: n8n + Инфраструктура + AI/LLM

**Дата аудита:** 14 апреля 2026
**Аудитор:** Qwen Code
**Среда:** Linux Mint 22.3, Docker 28.2.2, PostgreSQL 16-alpine, n8n (latest)
**Источники:**
- `/home/user/n8n-docker/AUDIT_WORKFLOWS.md` — аудит 34 workflow
- `/home/user/n8n-docker/AUDIT_INFRASTRUCTURE.md` — аудит инфраструктуры
- `AUDIT_AI_LLM.md` — НЕ НАЙДЕН (файл отсутствует)

---

# Executive Summary

## Краткое состояние системы

| Категория | Статус | Критических | Высоких | Средних |
|-----------|--------|-------------|---------|---------|
| Workflow (34 шт.) | **ТРЕБУЕТ ВНИМАНИЯ** | 4 | 14 | 18 |
| Инфраструктура | **КРИТИЧЕСКОЕ** | 7 | 7 | 8 |
| AI/LLM | НЕ АУДИРОВАНО | — | — | — |

## Ключевые факты

1. **API ключи захардкожены** в 5+ workflow (Polza.ai, NeuroAPI, Telegram Bot) — критический риск утечки
2. **PostgreSQL доступен на 0.0.0.0:5432** — база данных открыта для внешней сети
3. **Portainer на 0.0.0.0:9000** с rw доступом к Docker socket — полный контроль над сервером
4. **Error rate 16.1%** (33 ошибки из 205 executions) — превышает порог 15%
5. **1 задача в статусе pending 17 дней** + 5 чанков не обработаны — конвейер перевода остановлен
6. **Нет полного бэкапа БД** — custom-таблицы (document_*, telegram_*) не бэкапятся
7. **Alertmanager не настроен** — правила оповещений есть, но уведомления некуда отправляются
8. **12 Docker-индексов никогда не использовались** — full table scan вместо индексного поиска

## Общая оценка

Система функционирует, но содержит **критические уязвимости безопасности** и **проблемы надёжности**, требующие немедленного исправления. Архитектура workflow требует рефакторинга (рекурсия, дублирование, отсутствие error handling).

---

# Критические проблемы (CRITICAL)

## CR-1: Хардкод API ключей в workflow

**Что найдено:** plaintext API ключи встроены в HTTP Request ноды workflow.
**Где именно:**
- Workflow «Start» — узлы «Billing Polza.ai» и «Billing Neuro»
- Workflow «[Send] processing» — аналогичные узлы
- Workflow «[Send] finish» — аналогичные узлы
- Workflow «[GET] /select_files» — Telegram Bot token в HTTP Request
- Workflow «Анотация» — Polza API key с пробелом на конце

**Конкретные ключи:**
- Polza.ai: `pza_PV5t0y6PTuE8GLcZ-jgvlpNDLlZm0mUT`
- NeuroAPI: `sk-JPPv8NvhqimYVBabJvm6fB5mlv80WnLV673tfVzFm6IYq67V`
- Telegram Bot: `8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0`

**Почему это проблема:** Любой, кто получит доступ к export workflow JSON или логам, сможет использовать эти ключи. Ключи нельзя ротировать без изменения workflow.

**Как исправить:**
1. Создать Credentials в n8n Credential Manager для каждого сервиса (Polza.ai, NeuroAPI, Telegram API)
2. В каждом workflow заменить hardcoded значения на ссылки на Credentials
3. Использовать `mcp__n8n-mcp__n8n_manage_credentials` для создания
4. Экспортировать workflow, заменить ключи, импортировать обратно

**Риск если не исправить:** Ключи могут быть скомпрометированы через git, бэкапы, логи. Незаметное использование ключей злоумышленником.
**Оценка усилий:** M (3-5 рабочих часов на создание credentials и обновление 5+ workflow)

---

## CR-2: PostgreSQL на 0.0.0.0:5432

**Что найдено:** PostgreSQL слушает на всех сетевых интерфейсах.
**Где именно:** `/home/user/n8n-docker/docker-compose.yml`, секция `ports` сервиса `db`

**Почему это проблема:** Любой хост в сети может попытаться подключиться к базе данных. Несмотря на аутентификацию, это поверхность для brute-force атак.

**Как исправить:**
1. В `docker-compose.yml` изменить `ports: - "5432:5432"` на `ports: - "127.0.0.1:5432:5432"`
2. Перезапустить контейнер: `docker compose up -d db`
3. Проверить: `ss -tlnp | grep 5432` — должно быть `127.0.0.1:5432`

**Риск если не исправить:** Внешний доступ к БД, потенциальная утечка/порча данных.
**Оценка усилий:** S (10 минут)

---

## CR-3: Portainer на 0.0.0.0:9000 с Docker socket RW

**Что найдено:** Portainer слушает на всех интерфейсах и имеет read-write доступ к `/var/run/docker.sock`.
**Где именно:** docker-compose.yml, контейнер `portainer`

**Почему это проблема:** Docker socket с rw доступом = root доступ к хосту. Публичный порт = любой может получить контроль над всеми контейнерами.

**Как исправить:**
1. Изменить `ports: - "9000:9000"` на `ports: - "127.0.0.1:9000:9000"`
2. Перезапустить: `docker compose up -d portainer`
3. Доступ только через Caddy (docker.bigalexn8n.ru с TLS)

**Риск если не исправить:** Полный компромисс сервера через Docker API.
**Оценка усилий:** S (5 минут)

---

## CR-4: SQL-инъекции в workflow

**Что найдено:** Данные вставляются напрямую в SQL через `{{ }}` шаблоны, с неполной защитой.
**Где именно:**
- Workflow «[Перевод] Перевод чанка» — `result_text = '{{ $json.output.replaceAll("'", "''") }}'`
- Workflow «[Перевод] Обработка ошибки» — `error_text = '{{ $json.error_text.replaceAll("'","''") }}'`
- Workflow «Select From List» — `WHERE date_time > '{{ ... }}'`

**Почему это проблема:** Метод `replaceAll("'", "''")` не защищает от всех видов SQL-инъекций в PostgreSQL (например, через backslash-escaping). Прямая вставка выражений без параметризации.

**Как исправить:**
1. Во всех PostgreSQL нодах заменить прямую вставку на `queryReplacement` (параметризированные запросы)
2. Пример: вместо `UPDATE SET col = '{{ value }}'` использовать `UPDATE SET col = $1` с `queryReplacement: "={{ value }}"`

**Риск если не исправить:** Возможность SQL-инъекции через манипуляцию входными данными.
**Оценка усилий:** M (2-3 часа, обновление 3+ workflow)

---

## CR-5: Нет errorWorkflow в ~10 workflow

**Что найдено:** Большинство workflow не делегируют ошибки на Global Error Handler.
**Где именно:**
- Translate Chunk, [GET] /select_files, Добавление Глоссария, Добавление Промта, Добавление промта для постредакта, Постредактура, Добавление ресурсов в бд, sub_lightrag_api, Ручной выбор файлов, [Перевод] Перевод чанка

**Почему это проблема:** При ошибке execution просто завершается без уведомления, без логирования, без retry. Пользователь не узнает о проблеме.

**Как исправить:**
1. В каждом workflow установить `settings.errorWorkflow = "global-error-handler-36id"`
2. Использовать `n8n_update_partial_workflow` с операцией `updateSettings`
3. Проверить что Global Error Handler корректно логирует в document_log

**Риск если не исправить:** Тихие падения, потеря данных, отсутствие observability.
**Оценка усилий:** S (30 минут на 10 workflow через API)

---

## CR-6: Застрявшая задача и чанки

**Что найдено:**
- 1 задача в `document_jobs` со статусом `pending` от 28 марта (17 дней назад)
- 5 чанков в `document_chunks` со статусом `pending`

**Где именно:** PostgreSQL, таблицы `document_jobs`, `document_chunks`

**Почему это проблема:** Конвейер перевода остановлен. Ресурсы могут быть заблокированы. Пользователь не получил результат.

**Как исправить:**
```sql
-- Проверить застрявшую задачу
SELECT * FROM document_jobs WHERE status = 'pending';
-- Проверить чанки
SELECT * FROM document_chunks WHERE status = 'pending';
-- Решить: либо обработать, либо отметить как error/failed
UPDATE document_jobs SET status = 'failed', error_text = 'Стала pending более 7 дней' WHERE status = 'pending' AND created_at < NOW() - INTERVAL '7 days';
```

**Риск если не исправить:** Блокировка ресурсов, накопление мёртвых данных, путаница.
**Оценка усилий:** S (15 минут)

---

## CR-7: Error rate 16.1% превышает порог

**Что найдено:** 33 ошибки из 205 executions = 16.1% error rate (порог warning = 15%).
**Где именно:** Таблица `execution_entity`

**Почему это проблема:** Система работает с повышенной частотой ошибок. Это указывает на системные проблемы в workflow.

**Как исправить:**
1. Проанализировать 33 ошибки: `SELECT status, COUNT(*) FROM execution_entity GROUP BY status`
2. Определить топ ошибок по workflow
3. Устранить root causes (скорее всего связаны с CR-5 — отсутствием error handling)

**Риск если не исправить:** Продолжающаяся потеря данных, недовольство пользователей, деградация системы.
**Оценка усилий:** L (1-2 дня анализа и исправлений)

---

# Высокий приоритет (HIGH)

## HI-1: Рекурсивный вызов Translate Chunk

**Что найдено:** Workflow вызывает сам себя для обработки каждого чанка.
**Где именно:** Workflow «Translate Chunk» (Q5TRHGg-XRblnMRpH41Ee), узел «Переход на следующий чанк»

**Почему это проблема:** При 4000+ чанках — риск переполнения стека вызовов, memory exhaustion, таймаутов.

**Как исправить:** Переписать с использованием SplitInBatches + Loop Over Items pattern. Каждый чанк обрабатывается в цикле, без рекурсии.

**Риск:** Memory exhaustion при больших документах.
**Оценка усилий:** L (полная переработка логики, 4-8 часов)

---

## HI-2: Google Drive public access с ролью writer

**Что найдено:** Файлы и папки на Google Drive создаются с `type: anyone, role: writer`.
**Где именно:** Workflow «Создание Глоссария», «Переведенный файл в Google Drive»

**Почему это проблема:** Любой человек с ссылкой может РЕДАКТИРОВАТЬ файлы. Это утечка и риск порчи данных.

**Как исправить:** Изменить `role: writer` на `role: reader` или `role: commenter`. Или использовать `type: user` с конкретным email.

**Риск:** Несанкционированное редактирование файлов, утечка глоссариев.
**Оценка усилий:** S (15 минут, изменение 2-3 нод)

---

## HI-3: Billing-запросы с onError: continueRegularOutput

**Что найдено:** При ошибке биллинга workflow продолжает выполнение без данных о балансе.
**Где именно:** Workflow «Start», «[Send] processing», «[Send] finish» — узлы «Billing Polza.ai» и «Billing Neuro»

**Почему это проблема:** Workflow работает без информации о балансе, может превысить лимиты или работать некорректно.

**Как исправить:** Добавить fallback на нулевые значения при ошибке billing. Использовать Set node для установки значений по умолчанию.

**Риск:** Неожиданное поведение при недоступности billing API.
**Оценка усилий:** S (30 минут)

---

## HI-4: [GET] /select_files — 72 узла с дублированием

**Что найдено:** Самый большой workflow с 72 узлами. Паттерн copy-paste для каждого типа файла (7 Delete + 7 SQL + 7 Update).
**Где именно:** Workflow «[GET] /select_files» (MmfiOXrCt2lkZ4TxZMyWS)

**Почему это проблема:** Сложность поддержки, трудно обновлять, высокий риск ошибок при изменениях.

**Как исправить:** Использовать SplitInBatches + Loop для обработки каждого типа файла. Один набор нод вместо 7 копий.

**Риск:** Трудно поддерживать, высокий риск ошибок.
**Оценка усилий:** L (6-10 часов рефакторинга)

---

## HI-5: Grafana на 0.0.0.0:3000 без аутентификации

**Что найдено:** Grafana доступна на всех интерфейсах, подтверждено отсутствие аутентификации в Caddyfile.
**Где именно:** docker-compose.yml, контейнер `grafana`

**Почему это проблема:** Метрики инфраструктуры публично доступны. Злоумышленник может изучить архитектуру системы.

**Как исправить:**
1. Изменить `ports: - "3000:3000"` на `ports: - "127.0.0.1:3000:3000"`
2. Доступ только через Caddy (grafana.bigalexn8n.ru)

**Риск:** Утечка информации о инфраструктуре.
**Оценка усилий:** S (5 минут)

---

## HI-6: Open-WebUI на 0.0.0.0:8080 без защиты

**Что найдено:** Open-WebUI (AI интерфейс) доступен на всех интерфейсах.
**Где именно:** docker-compose.yml (lightrag проект), контейнер `open-webui`

**Почему это проблема:** AI интерфейс без защиты — любой может использовать модели.

**Как исправить:** Ограничить на 127.0.0.1, доступ только через Caddy (ai.bigalexn8n.ru с basicauth).

**Риск:** Несанкционированное использование AI моделей.
**Оценка усилий:** S (5 минут)

---

## HI-7: Нет полного бэкапа БД

**Что найдено:** Бэкапятся только 7 системных таблиц n8n. Custom-таблицы (document_*, telegram_*) НЕ бэкапятся.
**Где именно:** `/home/user/n8n-backups/`, скрипт `cron_backup.sh`

**Почему это проблема:** При падении БД будут потеряны все данные о задачах перевода, чанках, сообщениях Telegram.

**Как исправить:**
1. Добавить `pg_dump` для всех custom-таблиц
2. Настроить расписание (например, каждые 6 часов)
3. Добавить offsite backup (S3, Google Drive)

**Риск:** Потеря всех пользовательских данных при отказе БД.
**Оценка усилий:** M (2-4 часа настройки бэкапа)

---

## HI-8: Alertmanager не настроен

**Что найдено:** Prometheus alert rules существуют, но Alertmanager не настроен — уведомления некуда отправляются.
**Где именно:** Prometheus configuration

**Почему это проблема:** Оповещения генерируются, но никто их не получает. Monitoring бесполезен без notification.

**Как исправить:**
1. Установить Alertmanager контейнер
2. Настроить notification channel (Telegram webhook, email, или Slack)
3. Привязать alert rules к Alertmanager

**Риск:** Пропуск критических инцидентов.
**Оценка усилий:** M (2-3 часа)

---

## HI-9: Billing API timeout 1 секунда

**Что найдено:** Billing-запросы с `timeout: 1000` (1 секунда) — может быть недостаточно.
**Где именно:** Workflow «[Send] processing»

**Почему это проблема:** При высокой нагрузке billing API может отвечать дольше 1 секунды, что приведёт к ложным ошибкам.

**Как исправить:** Увеличить timeout до 5000-10000мс. Добавить retry с exponential backoff.

**Риск:** Ложные ошибки billing, неправильное поведение workflow.
**Оценка усилий:** S (10 минут)

---

## HI-10: Пустое условие IF в «[Перевод] Перевод чанка»

**Что найдено:** Узел «Если не ERROR?» с пустым условием (`"" == ""`) — всегда true, error-ветка недостижима.
**Где именно:** Workflow «[Перевод] Перевод чанка», узел If

**Почему это проблема:** Fallback «Резервный перевод чанка» никогда не срабатывает. AI ошибки не обрабатываются.

**Как исправить:** Установить корректное условие: проверка на наличие поля `error` или статуса ответа от AI.

**Риск:** AI ошибки без fallback, потеря чанков перевода.
**Оценка усилий:** S (15 минут)

---

## HI-11: Настройка БД — TRUNCATE job_current

**Что найдено:** При каждом запуске выполняется `TRUNCATE TABLE job_current` — удаляет ВСЕ данные.
**Где именно:** Workflow «Настройка БД» (UnqVdfxubclgfA7tafBwo)

**Почему это проблема:** При параллельных переводах TRUNCATE удалит данные другого активного перевода.

**Как исправить:** Заменить `TRUNCATE` на `DELETE WHERE job_id = ...` для конкретного job.

**Риск:** Потеря данных параллельных переводов.
**Оценка усилий:** S (15 минут)

---

## HI-12: Credentials в plaintext

**Что найдено:** DB password, N8N_ENCRYPTION_KEY, Google OAuth Token в plaintext файлах.
**Где именно:**
- `/home/user/n8n-docker/docker-compose.yml` — DB password, N8N_ENCRYPTION_KEY
- `/home/user/.env` — Google OAuth Token

**Почему это проблема:** Любой с доступом к файловой системе видит секреты.

**Как исправить:**
1. `chmod 600 /home/user/.env`
2. `chmod 600 /home/user/n8n-docker/docker-compose.yml`
3. Рассмотреть Docker secrets для secrets management

**Риск:** Утечка секретов через файловую систему.
**Оценка усилий:** S (10 минут)

---

## HI-13: PGAdmin CSRF отключён

**Что найдено:** `PGADMIN_CONFIG_ENFORCE_CSRF=False`, `MASTER_PASSWORD_REQUIRED=False`.
**Где именно:** docker-compose.yml, контейнер pgadmin4

**Почему это проблема:** Уязвимость к CSRF атакам — злоумышленник может выполнить запросы через браузер пользователя.

**Как исправить:**
1. `PGADMIN_CONFIG_ENFORCE_CSRF=True`
2. `PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED=True`
3. Перезапустить контейнер

**Риск:** CSRF атаки на pgAdmin.
**Оценка усилий:** S (10 минут)

---

## HI-14: Rate limiting отсутствует

**Что найдено:** Ни один endpoint в Caddy не имеет rate limiting.
**Где именно:** `/etc/caddy/Caddyfile`

**Почему это проблема:** DDoS атаки, brute-force, злоупотребление API.

**Как исправить:** Добавить rate limiting в Caddyfile для всех публичных endpoint:
```
rate_limit {
    zone api {
        window 1m
        events 60
    }
}
```

**Риск:** DDoS, brute-force атаки.
**Оценка усилий:** M (1-2 часа)

---

# Средний приоритет (MEDIUM)

## MD-1: Start workflow — нарушение single responsibility

**Что найдено:** Главный оркестратор делает слишком много: биллинг, настройка БД, парсинг, анализ, глоссарий, промты.
**Где именно:** Workflow «Start» (9cjeUNeTZX3YnO1W57YTP), 21 узел

**Почему это проблема:** Трудно поддерживать, отлаживать, изменять. Одно изменение может сломать множество функций.

**Как исправить:** Разделить на sub-workflows:
- `Init Translation` — инициализация и настройка
- `Billing Check` — проверка баланса
- `Process Document` — парсинг и анализ
- `Apply Glossary/Prompts` — применение настроек

**Риск:** Сложность поддержки, хрупкость системы.
**Оценка усилий:** XL (1-2 дня)

---

## MD-2: Merge-узел с 5 входами

**Что найдено:** Merge1 с 5 параллельными путями — при падении одного Merge зависнет.
**Где именно:** Workflow «Start», узел Merge1

**Почему это проблема:** Нет механизма timeout или fallback для Merge. Если один из 5 путей упадёт — остальные будут ждать вечно.

**Как исправить:** Добавить timeout на каждый путь или использовать Error Trigger для досрочного завершения.

**Риск:** Workflow зависает навсегда при ошибке одного пути.
**Оценка усилий:** M (2-3 часа)

---

## MD-3: Polling вместо webhook

**Что найдено:**
- «Получение сообщения» — polling Telegram каждые 5 минут
- «[Send] wait» — polling getUpdates каждые 1 секунду
- «Обработка ошибки» — polling каждые 5 секунд

**Почему это проблема:** Избыточная нагрузка на Telegram API, задержки обработки, wasted resources.

**Как исправить:** Перейти на Telegram Webhook Trigger (n8n поддерживает).

**Риск:** Задержки, rate limiting от Telegram API.
**Оценка усилий:** M (2-4 часа)

---

## MD-4: Billing-код дублируется в 3 workflow

**Что найдено:** Billing Polza.ai и Billing Neuro встречаются в Start, [Send] processing, [Send] finish — 3 копии.
**Где именно:** 3 workflow

**Почему это проблема:** Изменение billing логики требует обновления 3 мест. Риск рассинхронизации.

**Как исправить:** Создать sub-workflow «Get Billing Info» и вызывать через Execute Workflow node.

**Риск:** Рассинхронизация billing логики.
**Оценка усилий:** M (2-3 часа)

---

## MD-5: PinData в production workflow

**Что найдено:** PinData присутствует в 8 workflow: Start, Finish, Перевод чанка, Создание Глоссария, Добавление Глоссария, Добавление Промта, sub_lightrag_api, Ручной выбор файлов.

**Почему это проблема:** PinData — это тестовые данные, закреплённые в workflow. Может привести к неверному поведению в production.

**Как исправить:** Удалить PinData из всех production workflow через n8n UI или API.

**Риск:** Неверное поведение workflow из-за тестовых данных.
**Оценка усилий:** S (30 минут)

---

## MD-6: Устаревшие typeVersion

**Что найдено:** Некоторые PostgreSQL узлы используют typeVersion 2.1 вместо актуального 2.6.
**Где именно:** Workflow «Парсинг файла для перевода», «Добавление Промта», «Добавление промта для постредакта»

**Почему это проблема:** Старые версии могут не поддерживать новые функции, могут быть баги.

**Как исправить:** Обновить typeVersion до 2.6 через n8n UI или API.

**Риск:** Устаревшее поведение, потенциальные баги.
**Оценка усилий:** S (15 минут)

---

## MD-7: Missing индексы БД

**Что найдено:**
- `document_jobs` — нет индекса на `status`, `file_id`
- `telegram_send_message` — нет индекса на `chat_id`, `created_at`

**Почему это проблема:** Full table scan при каждом запросе к этим таблицам.

**Как исправить:**
```sql
CREATE INDEX idx_document_jobs_status ON document_jobs(status);
CREATE INDEX idx_document_jobs_file_id ON document_jobs(file_id);
CREATE INDEX idx_telegram_send_message_chat_id ON telegram_send_message(chat_id);
CREATE INDEX idx_telegram_send_message_created_at ON telegram_send_message(created_at);
```

**Риск:** Медленные запросы, деградация производительности.
**Оценка усилий:** S (5 минут)

---

## MD-8: telegram_send_message без TTL и status

**Что найдено:** Таблица не имеет колонки `status`, записи копятся навсегда (14 записей).

**Почему это проблема:** Нет механизма отслеживания отправки и очистки. Таблица растёт бесконечно.

**Как исправить:**
1. Добавить колонку `status` (sent, pending, failed)
2. Настроить TTL-очистку (удаление записей старше 7 дней)

**Риск:** Рост таблицы, невозможность отследить статус отправки.
**Оценка усилий:** M (1-2 часа)

---

## MD-9: Monitoring gaps

**Что найдено:** 10+ метрик без coverage:
- Blackbox Exporter не установлен (alert rules ссылаются на `probe_success`)
- cAdvisor не установлен (нет мониторинга ресурсов контейнеров)
- n8n custom metrics не экспортируются
- Firecrawl monitoring отсутствует
- Docker daemon metrics отсутствуют
- Log aggregation (ELK/Loki) не настроен
- SSL cert expiry monitoring отсутствует

**Почему это проблема:** Невозможно обнаружить проблемы до того как они станут критическими.

**Как исправить:** Поэтапно установить и настроить missing components (см. План рефакторинга).

**Риск:** Пропуск инцидентов, слепое пятно в мониторинге.
**Оценка усилий:** L (1-2 дня)

---

## MD-10: 12 индексов БД никогда не использовались

**Что найдено:** Все primary key индексы custom-таблиц имеют 0 сканирований.
**Где именно:** document_jobs, document_chunks, document_chapters, document_characters, document_arcs, document_glossary, document_log, telegram_chats, telegram_message, job_current, temp_table, chat_hub_sessions, chat_hub_messages, webhook_entity

**Почему это проблема:** Запросы идут через full table scan. ORM (n8n PostgreSQL node) может не использовать индексы эффективно.

**Как исправить:** Проверить запросы к этим таблицам. Убедиться что WHERE clauses используют индексированные колонки.

**Риск:** Медленные запросы.
**Оценка усилий:** M (2-4 часа анализа и оптимизации)

---

## MD-11: 3 пустых Docker сети

**Что найдено:** `n8n-docker_n8n-network`, `lightrag_lightrag_net`, `lightrag_default` — пустые сети без контейнеров.

**Почему это проблема:** wasted ресурсы, путаница.

**Как исправить:** `docker network rm n8n-docker_n8n-network lightrag_lightrag_net lightrag_default`

**Риск:** Минимальный (wasted ресурсы).
**Оценка усилий:** S (5 минут)

---

## MD-12: 15 anonymous volumes

**Что найдено:** 15 анонимных Docker volumes.

**Почему это проблема:** Затрудняют бэкап и мониторинг. Невозможно понять что хранится.

**Как исправить:** Проверить каждый volume, удалить неиспользуемые.

**Риск:** Затруднённый бэкап.
**Оценка усилий:** M (1-2 часа)

---

## MD-13: test-runner exited (1) 5 дней

**Что найдено:** Контейнер test-runner в exited статусе с ошибкой 5 дней.

**Почему это проблема:** wasted ресурсы, потенциальная проблема требующая исправления.

**Как исправить:** Удалить контейнер: `docker rm <container_id>` или починить и перезапустить.

**Риск:** Минимальный.
**Оценка усилий:** S (2 минуты)

---

## MD-14: Нет дашборда Translation Pipeline

**Что найдено:** Alert rules ссылаются на Translation Pipeline дашборд, но он не существует.
**Где именно:** Grafana

**Почему это проблема:** При срабатывании алерта нет дашборда для investigation.

**Как исправить:** Создать Grafana дашборд с метриками translation pipeline.

**Риск:** Трудная диагностика проблем pipeline.
**Оценка усилий:** M (2-4 часа)

---

## MD-15: 169 Docker образов, ~15-20 GB

**Что найдено:** Большое количество образов, включая ~10 dangling.

**Почему это проблема:** Занимают место на диске.

**Как исправить:** `docker image prune -a` (сэкономит ~5-10 GB)

**Риск:** Минимальный (удаление неиспользуемых образов).
**Оценка усилий:** S (5 минут)

---

# Низкий приоритет (LOW)

## LW-1: Мёртвые узлы и код

**Что найдено:**
- Replace Me (WF #9), Replace Me1 (WF #11) — забытые placeholder
- If (WF #3) — пустое условие, всегда false
- Empty output connections (WF #12 «Сообщение Старт обработки», WF #7 «to log»)
- Закомментированный код: `// const done = Math.floor(Math.random() * total);` (WF #15)

**Как исправить:** Удалить все мёртвые узлы и закомментированный код.
**Оценка усилий:** S (30 минут)

---

## LW-2: Нет комментариев/notes на узлах

**Что найдено:** Большинство узлов в 34 workflow не имеют notes.

**Как исправить:** Добавить описания к ключевым узлам через поле «Notes» в n8n UI.
**Оценка усилий:** M (2-4 часа)

---

## LW-3: Опечатки в именах узлов

**Что найдено:**
- «Нчало новой арки?» → «Начало новой арки?» (WF #5)
- «Cоздание стартового Summary» — кириллическая 'C' (WF #5)

**Как исправить:** Переименовать узлы.
**Оценка усилий:** S (5 минут)

---

## LW-4: Дублирование JS-кода

**Что найдено:**
- «Без доп Промта» и «Без доп Промта1» — одинаковый SQL UPDATE (WF #1)
- «Формирование промтов для перевода» и «...1» — одинаковый JS-код (WF #3)

**Как исправить:** Объединить в один узел или вынести в sub-workflow.
**Оценка усилий:** M (1-2 часа)

---

## LW-5: Ручной выбор файлов — race condition

**Что найдено:** DataTable «select_files» создаётся/удаляется каждый раз — race condition при параллельных запусках.
**Где именно:** Workflow «Ручной выбор файлов» (AnPEATb8u6yyFa54)

**Как исправить:** Использовать уникальные имена таблиц per execution или использовать временные таблицы с session ID.
**Оценка усилий:** M (2-3 часа)

---

## LW-6: Activate Translation Workflows — webhook без авторизации

**Что найдено:** Workflow «Activate Translation Workflows» описан как «[NOT USED]» но активен. Webhook без авторизации.

**Как исправить:** Либо деактивировать, либо добавить авторизацию на webhook.
**Оценка усилий:** S (5 минут)

---

## LW-7: TG caption limit 1024 — обрезка без предупреждения

**Что найдено:** В WF #17 обрезка caption до 1024 символов без уведомления пользователя.

**Как исправить:** Добавить уведомление «caption обрезан до 1024 символов».
**Оценка усилий:** S (10 минут)

---

## LW-8: get_file без retryOnFail

**Что найдено:** В WF #8 Telegram node `get_file` не имеет `retryOnFail`.

**Как исправить:** Включить `retryOnFail: true` с `maxTries: 3`.
**Оценка усилий:** S (5 минут)

---

# Quick Wins — исправления за 15 минут

| # | Проблема | Действие | Время |
|---|----------|----------|-------|
| 1 | PostgreSQL 0.0.0.0 | `127.0.0.1:5432` в compose | 5 мин |
| 2 | Portainer 0.0.0.0 | `127.0.0.1:9000` в compose | 5 мин |
| 3 | Grafana 0.0.0.0 | `127.0.0.1:3000` в compose | 5 мин |
| 4 | chmod для .env | `chmod 600 /home/user/.env` | 1 мин |
| 5 | chmod для compose | `chmod 600 docker-compose.yml` | 1 мин |
| 6 | Удалить test-runner | `docker rm <id>` | 2 мин |
| 7 | Пустые сети | `docker network rm ...` | 5 мин |
| 8 | Missing индексы БД | 4 CREATE INDEX | 5 мин |
| 9 | TRUNCATE → DELETE | Изменить SQL в «Настройка БД» | 15 мин |
| 10 | Опечатки узлов | Переименовать 2 узла | 5 мин |
| 11 | typeVersion 2.1→2.6 | Обновить в 3 workflow | 15 мин |
| 12 | Activate WF — деактивировать | Отключить unused workflow | 2 мин |
| 13 | Docker image prune | `docker image prune -a` | 5 мин |
| 14 | IF пустое условие | Исправить в WF #3 | 15 мин |
| 15 | Google Drive writer→reader | Изменить role в 2 нодах | 10 мин |

**Общее время Quick Wins:** ~1.5 часа

---

# Технический долг

## Накопившиеся проблемы

### 1. Архитектурный долг workflow
- **Старый подход:** рекурсивный вызов вместо SplitInBatches (WF «Translate Chunk»)
- **Copy-paste программирование:** 72 узла в `/select_files`, дублирование billing в 3 workflow
- **Отсутствие error handling:** ~10 workflow без errorWorkflow — копилось со временем
- **PinData в production:** тестовые данные в production workflow — признак недостаточного тестирования

### 2. Инфраструктурный долг
- **Caddy на хосте, не в Docker:** архитектурное решение без документации (почему так?)
- **Anonymous volumes:** 15 штук — результат многочисленных docker compose up/down без cleanup
- **Пустые сети:** 3 сети от старых конфигураций, не удалены
- **No offsite backup:** всё на одной машине — один сбой = полная потеря данных
- **16.1% error rate:** 33 ошибки из 205 — накапливались без системного анализа

### 3. Мониторинговый долг
- **Alert rules без Alertmanager:** правила написаны, но уведомления не работают
- **Missing exporters:** Blackbox, cAdvisor не установлены — мониторинг неполный
- **Нет дашбордов:** Translation Pipeline, PostgreSQL, Firecrawl, Docker — ключевые компоненты без визуализации
- **n8n custom metrics:** alert rules ссылаются на метрики, которые n8n не экспортирует

### 4. БД долг
- **12 неиспользуемых индексов:** ORM не использует индексы — возможно, неправильные запросы
- **No TTL cleanup:** telegram_send_message растёт бесконечно
- **No status column:** telegram_send_message без колонки статуса — невозможно отследить отправку
- **Застрявшие данные:** pending задача 17 дней, 5 pending чанков — никто не мониторит

### 5. Security долг
- **Hardcoded credentials:** API ключи в workflow вместо Credential Manager — самый старый и опасный долг
- **Public ports:** PostgreSQL, Portainer, Grafana на 0.0.0.0 — базовая security не настроена
- **No rate limiting:** все endpoint без защиты от DDoS
- **pgAdmin CSRF disabled:** базовая security настройка не включена

---

# Архитектурные рекомендации

## 1. Разделение ответственности workflow

Текущая архитектура: Start workflow делает ВСЁ.
Рекомендуемая архитектура:

```
Main Orchestrator (Start)
├── Init & Billing (sub-workflow)
│   ├── Check Billing Polza
│   ├── Check Billing Neuro
│   └── Init DB Connection
├── Document Analysis (sub-workflow)
│   ├── Parse File
│   ├── Analyze Structure
│   └── Create Glossary
├── Translation Pipeline (sub-workflow)
│   ├── Process Chapter
│   │   └── Process Chunks (Loop, NOT recursion)
│   └── Rolling Summary
└── Delivery (sub-workflow)
    ├── Upload to Google Drive
    └── Send via Telegram
```

## 2. Event-driven архитектура

Текущий подход: polling каждые N секунд.
Рекомендуемый подход: webhook + event queue.

- Telegram webhook → n8n Webhook Trigger (без polling)
- Long-running задачи → очередь через RabbitMQ (уже есть в Firecrawl)
- Обработка ошибок → Dead Letter Queue

## 3. Credential Management

Все секреты должны храниться в n8n Credential Manager:
- API ключи (Polza, NeuroAPI, Telegram)
- Database credentials
- Google OAuth tokens
- N8N_ENCRYPTION_KEY (для шифрования credentials в БД)

## 4. Backup стратегия

```
Ежечасно: pg_dump custom таблиц
Ежедневно: pg_dump полной БД + n8n workflow export
Еженедельно: offsite backup (S3/Google Drive)
Ежемесячно: тестирование восстановления
```

## 5. Observability

- Grafana дашборды для: Translation Pipeline, PostgreSQL, Firecrawl, Docker containers
- Alertmanager с Telegram notification
- Centralized logging (Loki + Grafana)
- Custom n8n metrics через webhook → Prometheus pushgateway

## 6. Security hardening

- Все порты на 127.0.0.1, доступ через Caddy с TLS
- Rate limiting в Caddy для всех endpoint
- Docker socket read-only для Portainer (если возможно)
- Regular security audit (ежемесячно)
- API key rotation (ежеквартально)

---

# План рефакторинга

## Фаза 0: Экстренные меры (Day 0, 2 часа)

| Шаг | Действие | Оценка |
|-----|----------|--------|
| 0.1 | Ограничить PostgreSQL на 127.0.0.1 | S |
| 0.2 | Ограничить Portainer на 127.0.0.1 | S |
| 0.3 | Ограничить Grafana на 127.0.0.1 | S |
| 0.4 | chmod 600 для .env и docker-compose.yml | S |
| 0.5 | Проверить и обработать pending задачу и чанки | S |
| 0.6 | Удалить test-runner контейнер | S |

## Фаза 1: Безопасность (Day 1-2, 8-12 часов)

| Шаг | Действие | Оценка |
|-----|----------|--------|
| 1.1 | Создать Credentials в n8n для всех API ключей | M |
| 1.2 | Заменить hardcoded ключи в 5+ workflow | M |
| 1.3 | Исправить SQL-инъекции → queryReplacement | M |
| 1.4 | Google Drive writer → reader | S |
| 1.5 | PGAdmin CSRF + master password | S |
| 1.6 | Настроить rate limiting в Caddy | M |

## Фаза 2: Error Handling (Day 2-3, 6-8 часов)

| Шаг | Действие | Оценка |
|-----|----------|--------|
| 2.1 | Установить errorWorkflow во все workflow | S |
| 2.2 | Проверить Global Error Handler логирует в document_log | M |
| 2.3 | Исправить пустое IF условие в WF #3 | S |
| 2.4 | Добавить billing fallback на нулевые значения | S |
| 2.5 | Увеличить billing timeout до 5-10 сек | S |

## Фаза 3: БД оптимизация (Day 3, 3-4 часа)

| Шаг | Действие | Оценка |
|-----|----------|--------|
| 3.1 | Создать missing индексы | S |
| 3.2 | Заменить TRUNCATE на DELETE WHERE | S |
| 3.3 | Добавить status колонку в telegram_send_message | M |
| 3.4 | Настроить TTL-очистку | M |
| 3.5 | Проанализировать неиспользуемые индексы | M |

## Фаза 4: Workflow рефакторинг (Day 4-7, 20-30 часов)

| Шаг | Действие | Оценка |
|-----|----------|--------|
| 4.1 | Переписать Translate Chunk: рекурсия → SplitInBatches | L |
| 4.2 | Рефакторинг /select_files: 72 → ~20 узлов | L |
| 4.3 | Вынести billing в sub-workflow | M |
| 4.4 | Разделить Start workflow на sub-workflows | XL |
| 4.5 | Polling → webhook для Telegram | M |
| 4.6 | Удалить PinData из всех workflow | S |
| 4.7 | Удалить мёртвые узлы | S |
| 4.8 | Обновить typeVersion | S |
| 4.9 | Добавить notes к узлам | M |

## Фаза 5: Backup (Day 7-8, 6-8 часов)

| Шаг | Действие | Оценка |
|-----|----------|--------|
| 5.1 | Настроить pg_dump для всех custom-таблиц | M |
| 5.2 | Добавить ежедневный полный pg_dump | M |
| 5.3 | Настроить offsite backup (S3/Google Drive) | L |
| 5.4 | Протестировать восстановление | M |
| 5.5 | Настроить backup Prometheus/Grafana данных | M |

## Фаза 6: Monitoring (Day 8-12, 15-20 часов)

| Шаг | Действие | Оценка |
|-----|----------|--------|
| 6.1 | Установить Blackbox Exporter | M |
| 6.2 | Установить cAdvisor | M |
| 6.3 | Настроить Alertmanager | M |
| 6.4 | Создать Translation Pipeline дашборд | M |
| 6.5 | Создать PostgreSQL дашборд | M |
| 6.6 | Создать Docker containers дашборд | M |
| 6.7 | Настроить Firecrawl monitoring | M |
| 6.8 | Настроить n8n custom metrics (pushgateway) | L |
| 6.9 | Настроить centralized logging (Loki) | L |

## Фаза 7: Cleanup (Day 12, 2-3 часа)

| Шаг | Действие | Оценка |
|-----|----------|--------|
| 7.1 | docker image prune -a | S |
| 7.2 | Удалить пустые сети | S |
| 7.3 | Проверить и удалить anonymous volumes | M |
| 7.4 | Деактивировать unused workflow | S |

---

# Чеклист Best Practices

## Безопасность

- [ ] Все API ключи в n8n Credential Manager (не hardcoded)
- [ ] Все порты на 127.0.0.1 (кроме Caddy 80/443)
- [ ] Docker socket read-only (где возможно)
- [ ] .env и docker-compose.yml с chmod 600
- [ ] Rate limiting на всех публичных endpoint
- [ ] pgAdmin: CSRF enabled, master password required
- [ ] Google Drive: role: reader (не writer)
- [ ] SQL-запросы через queryReplacement (параметризированные)
- [ ] Регулярная ротация API ключей

## Обработка ошибок

- [ ] errorWorkflow установлен во ВСЕХ workflow
- [ ] Global Error Handler логирует в document_log
- [ ] Retry с exponential backoff для внешних API
- [ ] Fallback значения для критических данных (billing)
- [ ] No continueOnFail без явной причины

## Архитектура

- [ ] Single Responsibility для каждого workflow
- [ ] Sub-workflows для повторяющейся логики
- [ ] SplitInBatches вместо рекурсии
- [ ] No copy-paste: циклы вместо дублирования
- [ ] Webhook вместо polling (где возможно)
- [ ] Merge nodes с timeout/fallback

## База данных

- [ ] Индексы на часто используемых колонках
- [ ] Foreign Keys для целостности данных
- [ ] TTL-очистка для временных данных
- [ ] Regular VACUUM ANALYZE
- [ ] Мониторинг размера таблиц

## Бэкапы

- [ ] Ежедневный pg_dump всей БД
- [ ] Offsite backup (S3/Google Drive)
- [ ] n8n workflow export (ежедневно)
- [ ] Тестирование восстановления (ежемесячно)
- [ ] Backup Docker volumes
- [ ] Backup Prometheus/Grafana данных

## Мониторинг

- [ ] Alertmanager с notification channel (Telegram/email)
- [ ] Grafana дашборды для всех ключевых компонентов
- [ ] Blackbox Exporter для uptime monitoring
- [ ] cAdvisor для контейнерных метрик
- [ ] Centralized logging (Loki)
- [ ] SSL cert expiry monitoring
- [ ] Error rate monitoring (< 5% target)

## Best Practices n8n

- [ ] No PinData в production
- [ ] Актуальные typeVersion
- [ ] Notes на ключевых узлах
- [ ] Нет мёртвых узлов/кода
- [ ] Workflow naming: [Project] [Function] - [Env]
- [ ] No hardcoded credentials
- [ ] Sub-workflows при >10-15 узлов

---

# Оценка усилий

| Категория | Улучшение | Оценка | Время |
|-----------|-----------|--------|-------|
| **Security** | Ограничить порты (PostgreSQL, Portainer, Grafana) | S | 15 мин |
| **Security** | chmod для .env и compose | S | 2 мин |
| **Security** | n8n Credential Manager для API ключей | M | 3-5 часов |
| **Security** | Исправить SQL-инъекции | M | 2-3 часа |
| **Security** | Rate limiting в Caddy | M | 1-2 часа |
| **Security** | pgAdmin security | S | 10 мин |
| **Security** | Google Drive access fix | S | 10 мин |
| **Reliability** | errorWorkflow во все workflow | S | 30 мин |
| **Reliability** | Исправить IF условие | S | 15 мин |
| **Reliability** | Billing fallback | S | 30 мин |
| **Reliability** | Billing timeout | S | 10 мин |
| **Reliability** | TRUNCATE → DELETE | S | 15 мин |
| **Reliability** | Pending data cleanup | S | 15 мин |
| **Performance** | Missing индексы БД | S | 5 мин |
| **Performance** | Telegram polling → webhook | M | 2-4 часа |
| **Performance** | Unused index analysis | M | 2-4 часа |
| **Performance** | telegram_send_message TTL | M | 1-2 часа |
| **Architecture** | Translate Chunk рефакторинг | L | 4-8 часов |
| **Architecture** | /select_files рефакторинг | L | 6-10 часов |
| **Architecture** | Billing sub-workflow | M | 2-3 часа |
| **Architecture** | Start workflow разделение | XL | 1-2 дня |
| **Architecture** | Merge timeout/fallback | M | 2-3 часа |
| **Best Practices** | Удалить PinData | S | 30 мин |
| **Best Practices** | Обновить typeVersion | S | 15 мин |
| **Best Practices** | Удалить мёртвые узлы | S | 30 мин |
| **Best Practices** | Notes на узлах | M | 2-4 часа |
| **Backup** | pg_dump custom таблиц | M | 2-4 часа |
| **Backup** | Offsite backup | L | 4-8 часов |
| **Backup** | Тестирование восстановления | M | 2-3 часа |
| **Monitoring** | Alertmanager | M | 2-3 часа |
| **Monitoring** | Blackbox Exporter | M | 2-3 часа |
| **Monitoring** | cAdvisor | M | 2-3 часа |
| **Monitoring** | Grafana дашборды (4 шт.) | M | 6-10 часов |
| **Monitoring** | n8n custom metrics | L | 4-8 часов |
| **Monitoring** | Centralized logging (Loki) | L | 4-8 часов |
| **Cleanup** | Docker image prune | S | 5 мин |
| **Cleanup** | Пустые сети | S | 5 мин |
| **Cleanup** | test-runner удалить | S | 2 мин |
| **Cleanup** | Anonymous volumes | M | 1-2 часа |

**ИТОГО:**
- **Quick Wins (S):** ~1.5 часа
- **Security (S+M):** 6-10 часов
- **Reliability (S):** ~2 часа
- **Performance (S+M):** 5-11 часов
- **Architecture (M+L+XL):** 15-30 часов
- **Backup (M+L):** 8-15 часов
- **Monitoring (M+L):** 18-30 часов
- **Cleanup (S+M):** 1.5-2.5 часа

**Общая оценка:** ~55-100 часов (7-13 рабочих дней)

---

*Отчёт сгенерирован: 14 апреля 2026*
*Источники: AUDIT_WORKFLOWS.md, AUDIT_INFRASTRUCTURE.md*
*AUDIT_AI_LLM.md — НЕ НАЙДЕН (файл отсутствует в /home/user/n8n-docker/)*
