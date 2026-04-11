# A→B Combined Architecture: Env-Driven Test Workflows

**Дата:** 11 апреля 2026 г.
**Автор:** PRIME Agent (Researcher → Architect)
**Цель:** Совместить автоматическое переключение через Env Var (A) с изоляцией Test Workflows (B)

---

# Research Findings

## Что выяснил Researcher

### 1. n8n НЕ поддерживает dynamic credentials
- Credential выбирается на этапе **дизайна** workflow, не runtime
- LangChain nodes не поддерживают Expression для credential ID
- n8n v2.12.3 (текущая) — нет API для credential switching во время выполнения

### 2. Обходной путь через n8n API
- n8n API позволяет **создавать/обновлять credentials** программно
- Можно обновить credential data через REST API
- Но это влияет на **все** workflows использующие этот credential (опасно!)

### 3. Лучшая практика сообщества
- **Раздельные инстансы** с одинаковыми именами credentials
- **JSON find-replace** credential ID при импорте
- **Папочное разделение** (Staging vs Prod folders)
- **Environment-based** workflow copies (DEV/PROD workflows)

### 4. Ollama поддерживает OpenAI-compatible API
- `http://localhost:11434/v1` — полный OpenAI API формат
- Можно использовать существующие `lmChatOpenAi` nodes
- Нужен только credential с правильным Base URL

---

# Вариант AB-1: Shared Test Mode Workflow (рекомендую)

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENV VAR: TRANSLATION_MODE                    │
│                    "production" │ "test"                        │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
    Production           Test Router          [Test] Workflows
    Workflows          [Test Mode Check]         (copies)
    (polza.ai)               │              (Ollama credential)
                             │
                    if mode == "test":
                      → Запуск [Test] workflows
                      → Test DB tables
                      → Test Grafana dashboard
                    else:
                      → Production workflows
```

## Как работает

### Шаг 1: Environment Variables
```bash
# В docker-compose.yml или .env
TRANSLATION_MODE=production  # или "test"
TEST_MODEL=llama3.2:3b
TEST_LIGHTRAG_URL=http://localhost:9621
```

### Шаг 2: [Test Mode Router] Workflow
```
Webhook: /webhook/start-translation
    ↓
Code Node: Check Mode
    if ($env["TRANSLATION_MODE"] === "test") {
      → Execute: [Test] Start workflow
      → Return: {mode: "test", target: "[Test] Start"}
    } else {
      → Execute: Start workflow  
      → Return: {mode: "production", target: "Start"}
    }
```

### Шаг 3: [Test] Workflow Copies
Копируем production workflows с изменениями:

| Production | Test Copy | Что меняется |
|-----------|-----------|-------------|
| Start | [Test] Start | Credential → Ollama |
| [Перевод] Перевод чанка | [Test] Перевод чанка | Credential → Ollama, Model → llama3.2:3b |
| [Перевод] Глава | [Test] Глава | Credential → Ollama |
| [Перевод] Арка | [Test] Арка | Credential → Ollama |
| Finish | [Test] Finish | → Test notification channel |

### Шаг 4: Credential Switch
Для test workflows создаём credential "Ollama Test" и заменяем во всех копиях.

## Реализация

### A. Создание тестовых workflow (через SQL)
```sql
-- Копируем workflow с новым ID и префиксом [Test]
INSERT INTO workflow_entity (id, name, nodes, connections, settings, active, ...)
SELECT 
  'test-' || id,
  '[Test] ' || name,
  -- Заменяем credential ID в nodes JSON
  REPLACE(nodes::text, 'polza.ai-credential-id', 'ollama-test-credential-id')::json,
  connections, settings, false, ...
FROM workflow_entity 
WHERE name IN ('Start', '[Перевод] Перевод чанка', '[Перевод] Глава', '[Перевод] Арка', 'Finish');
```

### B. Router Workflow
```json
{
  "name": "[Test Mode Router]",
  "nodes": [
    {
      "parameters": {"jsCode": "const mode = $env['TRANSLATION_MODE'] || 'production';\nconst workflows = {\n  test: '[Test] Start',\n  production: 'Start'\n};\nreturn [{json: {mode, target: workflows[mode]}}];"},
      "type": "n8n-nodes-base.code"
    },
    {
      "parameters": {"workflowId": "={{ $json.target }}"},
      "type": "n8n-nodes-base.executeWorkflow"
    }
  ]
}
```

## Плюсы
| ✅ | Описание |
|---|---|
| Переключение | Один env var = мгновенный переход |
| Изоляция | Test workflows не влияют на production |
| Сравнение | Можно сравнить качество production vs test |
| Автоматизация | Router сам выбирает нужный путь |
| CI/CD friendly | Env var легко менять в pipeline |

## Минусы
| ❌ | Описание |
|---|---|
| Дублирование | ~5-7 test workflow копий |
| Поддержка | При изменении prod workflow нужно обновить test |
| Сложность | Нужен router + env var management |

## Время реализации: 3-4 часа

---

# Вариант AB-2: Single Workflow with Mode Metadata

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│              document_jobs.test_mode BOOLEAN                    │
│              TRUE → Ollama │ FALSE → Polza.ai                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                    Единый workflow читает test_mode
                    и выбирает LLM через Code Node
```

## Как работает

### Шаг 1: Добавляем поле в document_jobs
```sql
ALTER TABLE document_jobs ADD COLUMN test_mode BOOLEAN DEFAULT false;
ALTER TABLE document_jobs ADD COLUMN llm_model VARCHAR(100);
ALTER TABLE document_jobs ADD COLUMN llm_credential_id VARCHAR(50);
```

### Шаг 2: Конфигурационная таблица LLM
```sql
CREATE TABLE llm_config (
    mode VARCHAR(20) PRIMARY KEY,  -- 'production' или 'test'
    model VARCHAR(100),
    credential_id VARCHAR(50),
    base_url VARCHAR(200),
    api_key TEXT
);

INSERT INTO llm_config VALUES 
  ('production', 'gpt-5.2', 'polza.ai-credential-id', 'https://polza.ai/api/v1', '...'),
  ('test', 'llama3.2:3b', 'ollama-credential-id', 'http://localhost:11434/v1', 'ollama');
```

### Шаг 3: Shared Config Workflow
```
[Config] Get LLM Settings
  Input: job_id
  Query: SELECT lc.* FROM document_jobs dj 
         JOIN llm_config lc ON dj.test_mode = (lc.mode = 'test')
         WHERE dj.id = $1
  Output: {model, credential_id, base_url}
```

### Шаг 4: LangChain nodes
Используем n8n HTTP Request node вместо LangChain:
```javascript
// Code node: Dynamic LLM Call
const config = $('Config Get LLM Settings').first().json;
const response = await fetch(`${config.base_url}/chat/completions`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${config.api_key}`
  },
  body: JSON.stringify({
    model: config.model,
    messages: [{role: 'user', content: prompt}]
  })
});
return await response.json();
```

## Плюсы
| ✅ | Описание |
|---|---|
| Один workflow | Без дублирования |
| Гибкость | Легко добавить новые режимы |
| Чистота | Конфигурация в БД, не в workflow |

## Минусы
| ❌ | Описание |
|---|---|
| **LangChain nodes нельзя менять runtime** | Нужно заменить на HTTP Request |
| Трудоёмкость | ~20 LangChain nodes → HTTP Request |
| Потеря функций | LangChain agents, tools не работают через HTTP |

## Время реализации: 8-12 часов (много переделки)

---

# Вариант AB-3: Environment-Specific Credentials (n8n API trick)

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│  n8n API: Обновляем credential перед запуском теста            │
│                                                                  │
│  Production Credential (polza.ai) ──┐                           │
│                                      │                           │
│  Test Mode:                          │                           │
│  1. POST /credentials/{id}           │──→ Обновляем data         │
│     → ollama, localhost:11434/v1     │     на время теста        │
│  2. Запускаем workflow               │                           │
│  3. POST /credentials/{id}           │──→ Возвращаем polza.ai    │
└─────────────────────────────────────────────────────────────────┘
```

## Как работает

### Шаг 1: Script для переключения
```bash
#!/bin/bash
# switch-to-test.sh
CREDENTIAL_ID="polza.ai-credential-id"
N8N_API="https://bigalexn8n.ru/api/v1"
API_KEY="$N8N_API_KEY"

# Сохраняем production credential
curl -s "$N8N_API/credentials/$CREDENTIAL_ID" -H "X-N8N-API-KEY: $API_KEY" > /tmp/prod-cred-backup.json

# Обновляем на Ollama
curl -s -X PATCH "$N8N_API/credentials/$CREDENTIAL_ID" \
  -H "X-N8N-API-KEY: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "polza.ai",
    "type": "openAiApi",
    "data": {
      "baseUrl": "http://localhost:11434/v1",
      "apiKey": "ollama"
    }
  }'

echo "✅ Switched to Ollama (test mode)"
```

### Шаг 2: Возврат на production
```bash
#!/bin/bash
# switch-to-production.sh
CREDENTIAL_ID="polza.ai-credential-id"
N8N_API="https://bigalexn8n.ru/api/v1"
API_KEY="$N8N_API_KEY"

# Восстанавливаем production credential
curl -s -X PATCH "$N8N_API/credentials/$CREDENTIAL_ID" \
  -H "X-N8N-API-KEY: $API_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/prod-cred-backup.json

echo "✅ Restored production credentials"
```

### Шаг 3: E2E Test Runner
```
[Test Runner Workflow]
├── Code: Switch credentials to Ollama (n8n API call)
├── Execute: Start workflow
├── Wait for completion
├── Code: Verify logs, metrics
├── Code: Restore production credentials
└── Send Report (Telegram)
```

## Плюсы
| ✅ | Описание |
|---|---|
| Без дублирования | Один workflow, credential меняется |
| Автоматизация | Скрипты переключают автоматически |
| Быстро | 1-2 часа на настройку |

## Минусы
| ❌ | Описание |
|---|---|
| **ОПАСНО** | Если скрипт упадёт → credential не восстановится |
| Race condition | Если кто-то запустит workflow во время теста |
| Audit trail | Непонятно кто/когда менял credential |

## Время реализации: 1-2 часа

---

# Сравнительная таблица

| Критерий | AB-1: Shared Test Mode | AB-2: Single Workflow | AB-3: API Credential Switch |
|----------|----------------------|----------------------|----------------------------|
| **Время** | 3-4 часа | 8-12 часов | **1-2 часа** |
| **Безопасность** | **Высокая** | Высокая | Низкая |
| **Изоляция** | **Полная** | Полная | Отсутствует |
| **Автоматизация** | Высокая | Высокая | Средняя |
| **Поддержка** | Средняя (дубли) | **Высокая** (единый) | Высокая |
| **CI/CD** | ✅ Env var | ✅ Env var | ⚠️ Scripts |
| **Совместимость** | Полная | ⚠️ Нужна переделка | Полная |
| **Риск** | Низкий | Средний | **Высокий** |

---

# Рекомендация PRIME Agent

## Для E2E тестирования: **Вариант AB-1** (Shared Test Mode)

**Почему:**
1. ✅ Безопасность — production workflows НЕ затрагиваются
2. ✅ Автоматизация — env var переключает маршрут
3. ✅ Сравнение — можно сравнить production vs test результаты
4. ✅ CI/CD — env var легко менять в pipeline
5. ✅ Изоляция — test данные в отдельных таблицах

**Реализация:**
```bash
# Production
TRANSLATION_MODE=production
→ Router → Start → Production Workflows → polza.ai

# Test
TRANSLATION_MODE=test  
→ Router → [Test] Start → Test Workflows → Ollama llama3.2:3b
```

---

# План реализации AB-1

## Phase 1: Подготовка (30 мин)
- [ ] Создать credential "Ollama Test" (Base URL: `http://localhost:11434/v1`)
- [ ] Добавить env var `TRANSLATION_MODE=production` в docker-compose.yml
- [ ] Создать тестовый файл для перевода

## Phase 2: Test Workflows (2-3 часа)
- [ ] Создать [Test] Start (копия Start → Ollama credential)
- [ ] Создать [Test] Перевод чанка (копия → Ollama credential)
- [ ] Создать [Test] Глава (копия → Ollama credential)
- [ ] Создать [Test] Арка (копия → Ollama credential)
- [ ] Создать [Test] Finish (копия → test notification)

## Phase 3: Router (30 мин)
- [ ] Создать [Test Mode Router] workflow
- [ ] Настроить Execute Workflow nodes для переключения

## Phase 4: Test Data (30 мин)
- [ ] Создать тестовый document_jobs с test_mode=true
- [ ] Создать тестовый глоссарий
- [ ] Создать упрощённые промпты для llama3.2:3b

## Phase 5: Verification (1 час)
- [ ] Запустить test mode
- [ ] Проверить pipeline_execution_log
- [ ] Проверить Grafana dashboard
- [ ] Сравнить с production results

**Итого: 4-5 часов**

---

# Что нужно от тебя

| # | Что | Зачем | Статус |
|---|-----|-------|--------|
| 1 | **Тестовый файл** (~500-1000 слов) | Входные данные для теста | ⏳ Предоставь |
| 2 | **Подтверждение AB-1** | Согласен с вариантом? | ⏳ Подтверди |
| 3 | **Допуск к n8n UI** | Для создания test workflows | ⏳ Если нужен |
