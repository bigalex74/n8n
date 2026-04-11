# AI Gateway Workflow Architecture

**Дата:** 11 апреля 2026 г.
**Автор:** PRIME Agent
**Идея:** Вынести все AI вызовы в отдельный workflow с переключением prod/dev

---

# Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                   [AI Gateway] Workflow                         │
│                   ID: ai-gateway                              │
│                                                                  │
│  Trigger: ExecuteWorkflowTrigger                                │
│  Input:                                                         │
│    - task: translate │ summary │ extract │ annotate │ chat     │
│    - text: входной текст                                        │
│    - context: rolling summary, glossary, RAG (опционально)     │
│    - mode: production │ dev                                     │
│    - options: temperature, max_tokens (опционально)            │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Mode Router                                               │ │
│  │ if mode == "production":                                  │ │
│  │   → polza.ai / NeuroAPI credentials                       │ │
│  │   → gpt-5.2, claude-4.5, gemini-2.5                       │ │
│  │ else:                                                     │ │
│  │   → Ollama credential                                     │ │
│  │   → llama3.2:3b (быстрая) или qwen2.5:32b (качество)      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Task Router                                               │ │
│  │ switch(task):                                             │ │
│  │   "translate"  → Translation Agent                        │ │
│  │   "summary"    → Summary Information Extractor            │ │
│  │   "extract"    → Glossary/Structure Extraction            │ │
│  │   "annotate"   → Annotation + Cover Generation            │ │
│  │   "chat"       → General Chat                             │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Fallback Chain (production mode)                          │ │
│  │ 1. GPT 5.2 (Polza) ──fail──→ 2. GPT 5.2 (Neuro)         │ │
│  │   ──fail──→ 3. Claude 4.5 (Neuro) ──fail──→ 4. Claude    │ │
│  │   (Polza) ──fail──→ ERROR                                 │ │
│  │                                                           │ │
│  │ Fallback Chain (dev mode)                                 │ │
│  │ 1. llama3.2:3b (быстрая) ──fail──→ 2. qwen2.5:32b        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Output:                                                        │
│    - result: ответ модели                                       │
│    - model: использованная модель                               │
│    - mode: production │ dev                                     │
│    - duration_ms: время выполнения                             │
│    - tokens: расход (если известен)                             │
│    - fallback_count: сколько раз был fallback                   │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Как вызывают другие workflows

```javascript
// В [Перевод] Перевод чанка:
const result = await $workflow.execute('ai-gateway', {
  task: 'translate',
  text: chunk.text,
  context: {
    glossary: chunk.glossary,
    rolling_summary: chapter.summary,
    arc_context: arc.summary
  },
  mode: $env['TRANSLATION_MODE'] || 'production'
});

// В [Перевод] Глава:
const summary = await $workflow.execute('ai-gateway', {
  task: 'summary',
  text: chapter.all_chunks_joined,
  mode: $env['TRANSLATION_MODE'] || 'production'
});
```

---

# Плюсы

| ✅ | Описание |
|---|---|
| **Единая точка управления** | Все LLM вызовы в одном месте. Меняешь модель — меняется везде |
| **Нет дублирования** | Не нужно копировать workflows для test mode |
| **Централизованный fallback** | Одна логика fallback для всех, легко поддерживать |
| **Метрики из коробки** | Каждый вызов логамирует модель, время, fallback_count |
| **A/B тестирование** | Легко добавить 3-й режим (например, "canary" с 50/50 split) |
| **Безопасность** | Production workflows НЕ меняются, меняется только вызов gateway |
| **Масштабируемость** | Добавить новую модель = добавить в gateway, не трогать 20 workflows |
| **Стоимость** | Логирование token usage в одном месте — легко считать расходы |
| **Rate limiting** | Централизованный контроль запросов к внешним API |
| **Кэширование** | Можно добавить кэш для повторяющихся запросов |

---

# Минусы

| ❌ | Описание | Митигация |
|---|---|---|
| **Переделка всех workflow'ов** | ~20 LangChain nodes → ExecuteWorkflow → AI Gateway | Частичная — меняем постепенно |
| **Единая точка отказа** | Gateway упадёт → весь перевод встанет | Health check + fallback внутри gateway |
| **Latency** | +1 hop (ExecuteWorkflow overhead ~50-100ms) | Незначительно для перевода (секунды/минуты) |
| **Сложность отладки** | Ошибка внутри gateway → сложнее трейсить | Подробное логирование внутри gateway |
| **Потеря LangChain features** | Agents, Tools, Memory — сложно через gateway | Gateway поддерживает все task types |
| **n8n limitation** | ExecuteWorkflow не передаёт binary data | Для перевода binary не нужен |

---

# Структура AI Gateway Workflow

```
[AI Gateway] (15-20 нод)
│
├── 1. ExecuteWorkflowTrigger (вход)
│
├── 2. Validate Input (Code)
│   └── Проверка: task, text, mode
│
├── 3. Log Request (PostgreSQL → pipeline_execution_log)
│   └── Записываем: execution_id, task, mode, input_text (hash)
│
├── 4. Mode Router (IF node)
│   ├─ production → [Production LLM Chain]
│   └─ dev → [Dev LLM Chain]
│
├── 5. [Production LLM Chain]
│   ├─ Task Router (Switch node)
│   │   ├─ translate → Translation Agent
│   │   │   ├─ GPT 5.2 Polza ─fail→ GPT 5.2 Neuro ─fail→ Claude Neuro ─fail→ Claude Polza
│   │   ├─ summary → Summary Extractor (Gemini Polza)
│   │   ├─ extract → Information Extractor (Gemini Polza)
│   │   └─ annotate → Annotation Agent (OpenAI Polza)
│   └─ Fallback Handler (если все модели упали)
│
├── 6. [Dev LLM Chain]
│   ├─ Task Router (Switch node)
│   │   ├─ translate → Translation Agent (Ollama llama3.2:3b)
│   │   ├─ summary → Summary Extractor (Ollama llama3.2:3b)
│   │   ├─ extract → Information Extractor (Ollama llama3.2:3b)
│   │   └─ annotate → Annotation Agent (Ollama qwen2.5:32b)
│   └─ Fallback: llama3.2:3b ─fail→ qwen2.5:32b
│
├── 7. Validate Output (Code)
│   └── Проверка: результат не пустой, формат корректный
│
├── 8. Log Response (PostgreSQL → pipeline_execution_log)
│   └── Записываем: output, model, duration_ms, fallback_count, tokens
│
└── 9. Return Result (Set node)
    └── {result, model, mode, duration_ms, tokens, fallback_count}
```

---

# Изменения в существующих workflows

## Было (сейчас):
```
[Перевод] Перевод чанка:
  → GPT 5.2 from Polza.ai (LangChain Agent)
  → GPT 5.2 from Neuro AI (LangChain Agent)
  → CLAUDE 4.5 from Neuro (LangChain Agent)
  → CLAUDE 4.5 from Polza.ai (LangChain Agent)
  → Резервный перевод чанка (LangChain Agent)
```

## Стало:
```
[Перевод] Перевод чанка:
  → Code: Подготовить input
  → Execute Workflow: [AI Gateway]
     Input: {task: "translate", text, context, mode: $env["TRANSLATION_MODE"]}
  ← Output: {result, model, duration_ms, fallback_count}
  → Code: Обработать результат
```

**Было: 34 ноды → Стало: ~15 нод** (убираем 5 LangChain nodes + fallback логику)

---

# env vars для управления

```bash
# В docker-compose.yml или .env

# Основной режим: production | dev
TRANSLATION_MODE=production

# Dev модель (быстрая для тестов)
DEV_MODEL=llama3.2:3b

# Dev fallback модель (качественнее но медленная)
DEV_FALLBACK_MODEL=qwen2.5:32b

# Production модели
PROD_PRIMARY_MODEL=gpt-5.2
PROD_FALLBACK_1_MODEL=gpt-5.2
PROD_FALLBACK_2_MODEL=claude-4.5
PROD_FALLBACK_3_MODEL=claude-4.5

# URL'ы
DEV_BASE_URL=http://localhost:11434/v1
PROD_BASE_URL=https://polza.ai/api/v1
```

---

# План реализации

## Phase 1: Создать AI Gateway (2-3 часа)
- [ ] Создать workflow [AI Gateway]
- [ ] Настроить Mode Router (IF node)
- [ ] Настроить Task Router (Switch node)
- [ ] Настроить Production LLM Chain (LangChain nodes)
- [ ] Настроить Dev LLM Chain (LangChain nodes → Ollama credential)
- [ ] Добавить fallback chain
- [ ] Добавить логирование в pipeline_execution_log
- [ ] Протестировать: вызвать gateway вручную

## Phase 2: Интеграция (3-4 часа)
- [ ] Изменить [Перевод] Перевод чанка → AI Gateway
- [ ] Изменить [Перевод] Глава → AI Gateway
- [ ] Изменить [Перевод] Арка → AI Gateway
- [ ] Изменить Предварительный анализ → AI Gateway
- [ ] Изменить Постредактура → AI Gateway
- [ ] Изменить Анотация → AI Gateway

## Phase 3: Тестирование (1-2 часа)
- [ ] Production mode test
- [ ] Dev mode test (Ollama llama3.2:3b)
- [ ] Fallback test
- [ ] E2E pipeline test
- [ ] Verify logging в pipeline_execution_log

## Phase 4: Cleanup (30 мин)
- [ ] Удалить старые LangChain nodes из workflows
- [ ] Обновить документацию
- [ ] Закоммитить в backup

**Итого: 6-9 часов**

---

# Сравнение с AB-1 (Test Mode Workflow)

| Критерий | AB-1: Test Workflows | **AI Gateway** |
|----------|---------------------|----------------|
| **Время реализации** | 3-4 часа | **6-9 часов** |
| **Дублирование** | ~5-7 workflow копий | **0 копий** |
| **Поддержка** | Обновлять prod + test | **Обновлять gateway** |
| **Гибкость** | Только prod/test | **Много режимов, A/B** |
| **Метрики** | Отдельные для test | **Единые для всех** |
| **Чистота** | Много workflows | **Один gateway** |
| **Fallback** | В каждом workflow | **Централизованный** |
| **Новая модель** | Менять во всех копиях | **Менять в gateway** |
| **Latency** | 0 | +50-100ms (ExecuteWorkflow) |
| **Сложность** | Простая | **Средняя** |

---

# Вердикт PRIME Agent

## 👍 Поддерживаю этот подход

**Почему это лучше AB-1:**
1. ✅ Нет дублирования workflows
2. ✅ Централизованное управление моделями
3. ✅ Легко добавлять новые режимы (canary, staging)
4. ✅ Централизованные метрики и fallback
5. ✅ Чистая архитектура (SRP — один workflow = одна ответственность)

**Риски:**
- ⚠️ Больше начальных изменений (6-9 часов vs 3-4)
- ⚠️ Единая точка отказа (нужен health check)

**Митигация рисков:**
- Health check workflow для gateway
- Circuit breaker внутри gateway
- Подробное логирование каждого вызова

---

# Что нужно для старта

| # | Что | Статус |
|---|-----|--------|
| 1 | Credential "Ollama Test" (Base URL: `http://localhost:11434/v1`) | ⏳ Создать |
| 2 | Env vars в docker-compose.yml | ⏳ Добавить |
| 3 | Тестовый файл для перевода | ⏳ Предоставь |
| 4 | Подтверждение подхода | ⏳ Скажи ОК |
