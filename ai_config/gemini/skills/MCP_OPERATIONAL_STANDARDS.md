# Операционные стандарты и навыки MCP (Staff+ Edition)

## 🛠 Общие правила для всех MCP
1. **Atoms over Bulks**: Предпочитать мелкие, точные вызовы инструментов массовым операциям, если это не вредит эффективности контекста.
2. **Verification First**: После любого действия, изменяющего состояние (GitHub, Google Workspace, Docker), выполнять проверочный вызов (ls, ps, status).
3. **DryRun Pattern**: Если инструмент поддерживает превью (как filesystem или sql), всегда запрашивать план изменений перед записью.

---

## 🏗 Специфические навыки по серверам

### 1. n8n & Workflow Management
- **Skill**: Глубокое понимание JSON-структуры n8n v1.x/2.x.
- **Rule**: При активации воркфлоу через MCP всегда проверять наличие необходимых Credentials в системе.
- **Optimization**: Использовать `listWorkflows` с фильтрацией, чтобы не раздувать контекст.

### 2. GitHub (Account: bigalex74)
- **Skill**: Управление жизненным циклом PR и Issues.
- **Rule**: Никогда не пушить в `main` напрямую без создания Issue или ветки, если не указано иное.
- **Pattern**: Conventional Commits для всех описаний через MCP.

### 3. Google Workspace
- **Skill**: Работа с иерархией папок Drive и структурой Sheets.
- **Rule**: При создании документов на Drive всегда задавать четкие Permissions сразу после создания.
- **Standard**: Использовать `MIME types` при поиске, чтобы минимизировать шум.

### 4. Context7 (Docs Expert)
- **Skill**: Актуальная документация любой библиотеки прямо в контексте.
- **Rule**: ВСЕГДА использовать перед написанием кода с незнакомым/обновлённым API.
- **Workflow**: `resolve-library-id` → `query-docs` → адаптировать под стек (не копировать слепо).
- **Limit**: Не более 3 вызовов на один вопрос. Запрос = конкретная задача, не тема.
- **Версии**: Указывать если критично (`/fastapi/fastapi/0.115.13`). Без версии → latest.
- **Полная документация**: `/home/user/.gemini/skills/CONTEXT7_MCP.md`

### 5. Chrome DevTools MCP (Browser Inspector)
- **Skill**: Прямой доступ к браузеру — навигация, DOM, скриншоты, консоль, сеть, Performance.
- **Rule**: `list_pages` → `navigate_page` → `wait_for` → `take_snapshot` → действие → `take_screenshot`.
- **Приоритет**: Использовать ВМЕСТО `browser_subagent` для точечных проверок UI.
- **Антипаттерн**: Не кликать по uid без предварительного `take_snapshot()` — uid устаревают после ре-рендера.
- **Полная документация**: `/home/user/.gemini/skills/CHROME_DEVTOOLS_MCP.md`

### 6. Docker & Infrastructure
- **Skill**: Оркестрация через Docker Compose.
- **Rule**: Перед перезапуском контейнера (restart) всегда проверять логи на наличие критических ошибок (Panic/Fatal).
- **Security**: Не выводить переменные окружения (`env`) в открытый лог сессии.

### 7. Postgres (n8n_database)
- **Skill**: Оптимизация SQL запросов и работа с индексами.
- **Rule**: Всегда использовать `LIMIT 100` для исследовательских запросов.
- **Standard**: Использовать транзакции (если поддерживается MCP) для связанных обновлений `document_jobs` и `document_chunks`.

### 8. Search & Crawling (SearXNG, Firecrawl)
- **Skill**: Эффективный веб-скрапинг и фильтрация мусора.
- **Rule**: Использовать `onlyMainContent: true` в Firecrawl для экономии токенов.
- **Standard**: SearXNG использовать для технических форумов и GitHub issues при поиске багов.

### 9. Observability (Grafana)
- **Skill**: Чтение метрик и поиск аномалий.
- **Rule**: При обнаружении аномалий в Grafana немедленно проверять `docker logs` соответствующего сервиса.

### 10. Browser Automation (Playwright)
- **Skill**: E2E тестирование фронтенда — `make test:e2e`, `make visual-check`.
- **Rule**: `channel: 'chrome'` для системного браузера (не требует `playwright install`).
- **Standard**: `headless: false` для визуальной проверки, `PWHEADLESS=true` для CI.
