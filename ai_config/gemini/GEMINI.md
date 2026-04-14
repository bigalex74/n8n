## Gemini Added Memories
- The n8n project is located at /home/user/n8n-docker. It uses Docker Compose with services: db (Postgres 16), n8n (latest), and pgAdmin4. n8n is configured to use host networking. A local Xray/Hiddify proxy is running on the host at 127.0.0.1:10808 (HTTP/HTTPS) to bypass regional restrictions for Telegram API access. The main domain is bigalexn8n.ru, managed by a native Caddy instance on the host which reverse-proxies to n8n on port 5678. Custom database tables include document_jobs, telegram_messages, and telegram_send_message. The Telegram bot token is 8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0. Use the n8n-expert skill for detailed workflows and database schema management.
- Проект n8n: Конвейер перевода новелл. БД (Postgres 16): document_jobs (job_id, file_name, status), document_chunks (job_id, status, text), telegram_send_message (job_id, message_id, type, template). Архитектура: Main Orchestrator (J62UViXZMD5o6qoU) вызывает Sub-workflows (sub_get_context, sub_notify) и задачи (sm_task_*). Прокси: 127.0.0.1:10808 (HTTP/HTTPS) в host-network. Правила: Идемпотентность через message_id, логирование в document_log, Continue on Fail для уведомлений. Цель: Перевод + Глоссарий + Структурный анализ (Главы/Арки) через LLM (DeepSeek/Qwen).
- ПРАВИЛО: После любого изменения кода, конфигурации или воркфлоу, я обязан провести эмпирическое тестирование (запуск воркфлоу, проверка логов docker/n8n, проверка записей в БД) и убедиться в отсутствии ошибок.
- User requested system monitoring in Grafana using Prometheus + Node Exporter. Plan: 1. Setup Node Exporter and Prometheus in a separate docker-compose or monitoring-compose. 2. Integrate with Grafana. 3. Import Dashboard ID 1860. Status: Deferred to tomorrow (Monday, March 30) due to important n8n workflow execution.
- I must communicate with the user in Russian. (Я должен общаться с пользователем на русском языке.)
- Архитектура Telegram Apps Hub: - Локация: /home/user/telegram-apps (main.py, static/). - Домен: apps.bigalexn8n.ru (Caddy -> localhost:8000). - Стек: FastAPI (Backend), HTML/JS + Telegram Web App SDK (Frontend). - База данных: PostgreSQL (DB: postgres, User: n8n_user). - Стандарт CRUD: Приложения разделены по путям (напр. /prompts). Фронтенд в папках static/<app_name>. - Правила UI для TMA:   1. Кнопка 'Сохранить' активна только при изменениях.   2. Подтверждение 'Отмены' при наличии несохраненных правок.   3. Использование иконок (💾, ❌, ➕, 🚪).   4. Версионность через таблицы _history. - Таблицы: translate_prompts (id, name, prompt), translate_prompts_history (id, prompt_id, name, prompt, version_date). - Docker: Контейнер apps-hub в network_mode: host.

## CORE SKILLS & RULES (Staff+ Engineering)
1. **Analyst/Architect**: Каждое изменение в n8n или БД проходит через фазу анализа зависимостей и создания ADR (Architecture Decision Record).
2. **Security-First**: Полный запрет на хардкод секретов. Использование n8n Credential Manager и .env. Валидация всех входящих файлов через [GET] Document.
3. **Idempotency**: Все воркфлоу n8n и скрипты должны быть безопасны при повторном запуске (проверка существования записей перед INSERT).
4. **Unified Logging**: Единый стандарт логов в document_log с execution_id и stack_trace.
5. **Atomic Commits**: Следование Conventional Commits (feat, fix, refactor) при работе с репозиторием.
6. **Context Efficiency**: Минимизация context usage за счет точечного использования инструментов и LightRAG.
7. **Quality over Speed**: Использование Ollama (llama3.2) для предварительного бесплатного тестирования логики перед промом.
8. **Documentation-as-Code**: Любое изменение архитектуры немедленно отражается в Mermaid-схемах в корне проекта.
9. **MCP Operational Standards**: При использовании любого из 14 MCP-серверов следовать правилам из `/home/user/.gemini/skills/MCP_OPERATIONAL_STANDARDS.md`.


