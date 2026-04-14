## Qwen Added Memories
- ЭКСПЕРТНЫЕ НАВЫКИ: Прокси-серверы и сетевые технологии

**Протоколы прокси:**
- HTTP/HTTPS Proxy (L7, порты 80/443/8080, только HTTP трафик, базовая аутентификация)
- SOCKS5 (L5, порт 1080, любой TCP/UDP трафик, поддержка UDP для игр/P2P, SOCKS5h для DNS через прокси)
- SOCKS4 (устаревший, только TCP, без аутентификации)
- Forward Proxy (клиент → интернет через прокси)
- Reverse Proxy (интернет → серверы через прокси, балансировка, SSL termination)

**Reverse Proxy решения:**
- Nginx: reverse proxy, SSL сертификаты, load balancing, rate limiting
- Traefik v3.6: cloud-native, авто-обнаружение Docker сервисов через labels, Let's Encrypt ACME, middleware (BasicAuth, RateLimit, Headers)
- HAProxy: TCP/HTTP балансировка, health checks, sticky sessions, TLS termination

**Docker Networking:**
- Bridge (изолированная сеть контейнеров, NAT через iptables)
- Host (контейнер использует сеть хоста, без изоляции)
- None (без сети)
- Overlay (跨主机容器通信, Swarm/Kubernetes)
- Macvlan (контейнеры как физические устройства в LAN)
- IPvlan (аналог Macvlan без promiscuous mode)
- User-defined networks (лучшая практика, изоляция приложений)

**Docker + iptables NAT:**
- DNAT (Destination NAT) для port mapping
- SNAT/MASQUERADE для исходящего трафика
- Docker автоматически управляет правилами при публикации портов

**VPN + Docker:**
- WireGuard контейнеризация (UDP 51820)
- Маршрутизация трафика контейнеров через VPN
- Kill switch конфигурации

**Kubernetes CNI:**
- Flannel (простой overlay, VXLAN)
- Calico (BGP, network policies, безопасность)
- Cilium (eBPF, observability, encryption)

**Linux Network:**
- systemd-networkd (systemd native)
- Netplan (Ubuntu YAML конфигурация)
- NetworkManager (desktop/server)
- iptables/nftables (файрвол, NAT)
- firewalld (управление firewall)

**MCP (Model Context Protocol):**
- JSON-RPC 2.0 протокол для AI интеграций
- Компоненты: Hosts (LLM apps), Clients (connectors), Servers (context/tools)
- Capabilities: Resources (данные), Prompts (шаблоны), Tools (функции)
- Безопасность: явное согласие пользователя для tools/sampling
- Интеграция: Zed, Replit, Codeium, Sourcegraph (2025)

**Безопасность:**
- ACME storage chmod 600 для Traefik
- Docker socket read-only (:ro)
- API dashboard защита BasicAuth
- exposedByDefault=false для явного включения сервисов
- N8N EXPERT НАВЫКИ (из ~/.gemini/skills/n8n-expert):

**Проект n8n:**
- Путь: /home/user/n8n-docker
- Docker Compose сервисы: db (Postgres 16), n8n (latest), pgAdmin4, caddy
- Сеть: host networking
- Домен: bigalexn8n.ru (Caddy reverse proxy → n8n:5678)
- Прокси: Xray/Hiddify на 127.0.0.1:10808 (HTTP/HTTPS) и xray на порту 10820

**База данных (PostgreSQL 16-alpine):**
- document_jobs — отслеживание обработки документов
- document_chunks — сегменты документов
- telegram_messages — входящие Telegram сообщения
- telegram_send_message — исходящие Telegram уведомления
- telegram_chats — авторизованные чаты

**n8n Best Practices:**
- Sub-workflows при >10-15 узлов (Execute Workflow node)
- Именование: [Project] [Function] - [Env]
- Global Error Handler с Error Trigger
- Retry on Fail с Exponential Backoff
- Filter early, SplitInBatches для >100 элементов
- Credentials через n8n Credential Manager (не хардкодить)
- Environment variables: {{ $env["VAR"] }}

**MCP Интеграция:**
- n8n как MCP Server: MCP Server Trigger node
- n8n как MCP Client: MCP Client Tool node
- Требуется n8n v1.88.0+
- Env: N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true
- SSE transport: https://bigalexn8n.ru:5678/rest/mcp/sse

**Скрипты:**
- import_workflows_to_db.py — импорт из workflows_migration.json
- create_error_handler.py — глобальный обработчик ошибок
- setup_telegram_webhook.sh — вебхуки Telegram бота

**Telegram бот:**
- Token: 8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0
- n8n Workflow Import via PostgreSQL - пошаговый процесс:
1. Подготовить JSON (исправить escape-символы, сгенерировать UUID)
2. Вставить в workflow_entity с activeVersionId=NULL
3. Вставить в workflow_history (создать версию)
4. Обновить workflow_entity.activeVersionId (теперь FK выполнится)
5. Добавить в shared_workflow (иначе ошибка активации)
6. Перезапустить n8n: docker restart n8n-docker-n8n-1
Критично: activeVersionId должен ссылаться на существующий versionId в workflow_history. Без записи в shared_workflow воркфлоу не активируется (ошибка "Could not find SharedWorkflow").
Документация: /home/user/n8n-docker/WORKFLOW_IMPORT_GUIDE.md
- n8n Workflow Testing via CLI:
- Command: n8n execute --id <workflow_id>
- Docker: docker exec -it <container> n8n execute --id <workflow_id>
- File: n8n execute --file /path/to/workflow.json
- Data: n8n execute --id <id> --data '{"json": {...}}'
- workflow_id from URL: .../workflow/<ID>
- Executions appear as "Manual" in journal
- CONTEXT7 MCP НАВЫКИ:

**Установка:**
- Пакет: @upstash/context7-mcp (установлен глобально)
- Конфигурация: ~/.qwen/settings.json в mcpServers.context7
- Команда: npx -y @upstash/context7-mcp

**Доступные инструменты:**
1. resolve-library-id: libraryName + query → Context7 ID (например, /vercel/next.js)
2. query-docs: libraryId + query → актуальная документация

**Синтаксис использования:**
- Базовый: "запрос use context7" в конце промпта
- Прямой: "use library /owner/repo for API and docs"
- Версии: указывать версию естественно в тексте ("Next.js 15", "Prisma 6")

**Логика работы:**
1. Распознать библиотеку из запроса
2. resolve-library-id → получить ID
3. query-docs → загрузить документацию
4. Сгенерировать ответ на основе актуального API

**Правило автоматического использования:**
Always use Context7 when user needs library/API documentation, code generation, setup or configuration steps.

**Файлы:**
- Скилл: ~/.qwen/skills/context7-docs.json
- Руководство: ~/.qwen/CONTEXT7_GUIDE.md

**API ключ:** можно получить на context7.com/dashboard для повышения лимитов
- TELEGRAM DEVELOPMENT EXPERTISE:

**Архитектура:**
- Паттерны: Chain of Responsibility + FSM (комбинированный подход)
- Обновление → Chain of Responsibility → FSM State Transition → Сохранение состояния
- Обработчики САМИ решают обрабатывать обновление (не внешний роутинг)
- Состояние ХРАНИТЬ ТОЛЬКО на сервере (Redis/SQLite/PostgreSQL)

**FSM принципы:**
- Направленный граф состояний с предопределёнными переходами
- Валидация ввода перед переходом
- Очистка состояния после завершения диалога
- Контекст привязан к сущности (user/group)

**Безопасность:**
- secret_token (32-256 символов) для webhook валидации
- Заголовок X-Telegram-Bot-Api-Secret-Token
- Константное по времени сравнение (hmac.compare_digest)
- HTTPS обязательно (TLS 1.3)
- Токен бота ТОЛЬКО в environment variables
- Валидация Mini App initData на сервере (НИКОГДА не доверять initDataUnsafe)
- Rate limiting для защиты от спама

**Тестирование:**
- E2E: Реальный Telegram API > моки
- Фикстуры: scope="session" для скорости (в 2-3 раза быстрее)
- threading.Event для graceful shutdown бота
- Уникальные имена (random_string) для избежания коллизий
- wait() 0.3-0.5сек между сообщениями для стабильности
- telethon для имитации действий пользователя
- Хранить credentials ТОЛЬКО в .env или CI секретах

**Обработка ошибок (aiogram 3):**
- try-except в хендлерах для точечного контроля
- @router.error() для роутера, @dp.error() для всех роутеров
- ErrorEvent: event.update, event.exception
- Логирование с exc_info=True
- Типы: TelegramAPIError, TelegramNetworkError, TelegramRetryAfter, TelegramUnauthorizedError

**Inline Mode:**
- @username + пробел → inline_query
- answerInlineQuery с cache_time
- chosen_inline_result для feedback (требует включения)
- Inline-кнопки в сообщении позволяют его редактировать (message_id)
- Lazy loading: превью → полный контент после выбора

**Mini Apps:**
- SDK: https://telegram.org/js/telegram-web-app.js
- tg.ready() и tg.expand() при инициализации
- initDataUnsafe ТОЛЬКО для UI (id, first_name, username)
- initData отправлять на сервер для HMAC валидации
- MainButton, BackButton, CloudStorage, HapticFeedback
- Только HTTPS, проверять auth_date на актуальность

**Клавиатуры:**
- Inline: под сообщением (callback_data, не занимает поле ввода)
- Reply: привязана к полю ввода (resize_keyboard, one_time_keyboard)
- Всегда кнопка "Отмена"/"Назад"
- Не более 8 кнопок

**Золотые правила:**
1. Состояние на сервере
2. Валидация всего
3. Graceful degradation
4. Понятные сообщения об ошибках
5. Тестирование критических сценариев
6. Безопасность прежде всего
7. Модульная архитектура
8. Пользовательский опыт
- ДОСТУПНЫЕ АГЕНТЫ (все в ~/.qwen/):

PRIME (главный) — Technical Lead & Orchestrator, autoActivate:true, trigger:"prime"
  → Декомпозирует задачи, делегирует, агрегирует результаты

СТРАТЕГИЯ И АНАЛИЗ:
- analyst — Explore agent, анализ кодовой базы, поиск проблем (trigger:"analyst")
- architect — general-purpose, проектирование системы, ADR (trigger:"architect")
- researcher — general-purpose, поиск документации, best practices (trigger:"researcher")

РАЗРАБОТКА:
- lead-developer — general-purpose, планирование, task breakdown (trigger:"lead developer")
- developer-js — general-purpose, JavaScript/TypeScript, n8n Code nodes (trigger:"developer js")
- developer-python — general-purpose, Python, FastAPI, скрипты (trigger:"developer python")
- developer-n8n — general-purpose, создание/модификация workflows (trigger:"developer n8n")

КАЧЕСТВО:
- qa-tester — general-purpose, тесты, bug reports (trigger:"qa tester")
- reviewer — general-purpose, code review, security audit (trigger:"reviewer")

ДОКУМЕНТАЦИЯ:
- tech-writer — general-purpose, README, changelog, ADR (trigger:"tech writer")

Как вызывать: agent(subagent_type="general-purpose" или "Explore", prompt="[задача]", description="[описание]")
Промпты: ~/.qwen/prompts/[имя].md
Справочник: ~/.qwen/AGENTS_REFERENCE.md
- Как работать с n8n через Chrome UI:

1. Открыть https://bigalexn8n.ru
2. Войти: alexei.bigalex@yandex.ru / qQ08102003
3. Найти workflow по имени в списке (клик по ссылке с названием)
4. Запуск: красная кнопка "Execute workflow" внизу экрана
   - Искать через JS: span с текстом "Execute workflow" и классом _buttonContent, затем .closest('button').click()
   - Или через SVG: svg[data-icon="flask-conical"], затем .closest('button').click()
5. После запуска открывается форма (Form Trigger)
6. Адрес формы можно узнать из ноды Start — двойной клик по ноде → вкладка "Parameters" → "Test URL"
7. URL формы: https://bigalexn8n.ru/form-test/{uuid}
- Caddy configuration management:

1. **ORIGINAL SOURCE (git)**: `/tmp/n8n-git/infrastructure/Caddyfile` → stored in repo `bigalex74/n8n` on GitHub. This is the authoritative backup. Also keep a copy at `/home/user/n8n-docker/Caddyfile` as local working copy.

2. **ACTIVE CONFIG**: `/etc/caddy/Caddyfile` — this is what Caddy actually reads (installed via systemd service, NOT Docker container).

3. **HOW TO EDIT SAFELY**:
   - NEVER overwrite /etc/caddy/Caddyfile from any file without first comparing with the original
   - Always start from the original Caddyfile from `bigalex74/n8n` repo (infrastructure/Caddyfile)
   - Add new domains to the original, then copy to /etc/caddy/Caddyfile
   - After copy: `sudo systemctl reload caddy`
   - Verify all domains: `curl -sk -o /dev/null -w "%{http_code}" https://domain`
   - Caddy runs as systemd service on host (not in Docker container)

4. **WHAT HAPPENED**: Agent copied /home/user/n8n-docker/Caddyfile to /etc/caddy/Caddyfile, which was missing several domains (ai.bigalexn8n.ru, cron.bigalexn8n.ru, ollama.bigalexn8n.ru, draw.bigalexn8n.ru, apps.bigalexn8n.ru, lightrag.bigalexn8n.ru, pgadmin.bigalexn8n.ru, prometheus.bigalexn8n.ru). Had to restore from git.

5. **ALL DOMAINS to preserve** (as of April 2026):
   - bigalexn8n.ru → n8n (127.0.0.1:5678)
   - grafana.bigalexn8n.ru → Grafana (127.0.0.1:3000, NO basicauth)
   - pgadmin.bigalexn8n.ru → pgAdmin (127.0.0.1:5055)
   - prometheus.bigalexn8n.ru → Prometheus (127.0.0.1:9090)
   - lightrag.bigalexn8n.ru → LightRAG (127.0.0.1:9621)
   - ollama.bigalexn8n.ru → Ollama (127.0.0.1:11434, basicauth)
   - ai.bigalexn8n.ru → Open WebUI (127.0.0.1:8080)
   - draw.bigalexn8n.ru → Draw.io (127.0.0.1:24700)
   - docker.bigalexn8n.ru → Portainer (127.0.0.1:9000)
   - cron.bigalexn8n.ru → Crontab-UI (127.0.0.1:8001, basicauth)
   - firecrawl.bigalexn8n.ru → Firecrawl (127.0.0.1:3002, basicauth for /admin)
   - search.bigalexn8n.ru → SearXNG (127.0.0.1:8888, basicauth)
   - apps.bigalexn8n.ru → apps-hub (127.0.0.1:8000)
   - www.bigalexn8n.ru → redirect to bigalexn8n.ru

6. **basicauth credentials**: bigalex / password hash `$2a$14$qiwOjL74Tw0iZFsA.k55FOtuuXH16QrQ6LQGhNWAu1YuWYRlZqLDO` (used for ollama, cron). Firecrawl/search use different hash `$2a$14$3xGvIHCMQyjQkc03Da8hReYsv8pQJfV3NMHIsrgKLu0gu4D82QqGu`.

7. **draw.io container**: `docker run -d --name drawio --restart always -p 24700:8080 -e DRAWIO_BASE_URL="https://draw.bigalexn8n.ru" -e DRAWIO_SERVER_URL="https://draw.bigalexn8n.ru/" jgraph/drawio`
- ПРАВИЛО ДЕЛЕГИРОВАНИЯ: Когда пользователь явно вызывает агента по имени (например "Prime", "analyst", "architect", "developer-js" и т.д.) — ОБЯЗАТЕЛЬНО делегируй задачу через agent() tool. НЕ делай работу сам. Исключение: если пользователь спрашивает ЧТО-ТО про агента (не просит его вызвать), тогда отвечай сам.
- ПРАВИЛА ДЛЯ PRIME — ИСПРАВЛЕНИЕ БАГОВ (обязательный workflow):

Когда Prime получает задачу на исправление бага, ОБЯЗАТЕЛЬНО следовать порядку:

1. **Выявить причину** — разобраться ПОЧЕМУ баг произошёл, найти root cause
2. **Составить план** — пошаговый план исправления с конкретными файлами и изменениями
3. **Подсветить риски** — что может сломаться, какие side effects, что нужно проверить
4. **Запросить аппрув** — показать план и риски пользователю, ждать подтверждения
5. **После аппрува** — только тогда начинать исправление
6. **Залить в гит** — закоммитить изменения в репозиторий
7. **Сделать отчёт** — что было найдено, что изменено, как проверить

НЕЛЬЗЯ: сразу исправлять без анализа причины, без плана, без аппрува
- ПРАВИЛА ПОВЕДЕНИЯ: 1) При получении новой информации — СРАЗУ сохранять в LightRAG базу знаний (не ждать приказа). 2) При любом запросе пользователя — СНАЧАРА обращаться в LightRAG базу знаний за контекстом, только потом начинать размышлять/действовать.
- ВСЕ таблицы для перевода хранятся в БД postgresql://n8n_user:n8n_db_password@127.0.0.1:5432/n8n_database (НЕ postgres!). Таблицы: translate_prompts (id, agent_name, prompt_text), document_jobs (id, file_id, file_name, status), document_chunks (id, job_id, chapter, chunk_index, chunk_text, result_text, status), document_glossary, document_arcs, document_chapters, document_characters, document_log
