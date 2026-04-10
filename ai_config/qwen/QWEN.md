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
