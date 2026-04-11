# AI Gateway: Detailed Analysis — Why One Gateway Won't Work

**Дата:** 11 апреля 2026 г.
**Автор:** PRIME Agent
**Вопрос:** Один AI Gateway для всего или специализированные на каждый workflow?

---

# Реальная картина (анализ LangChain nodes)

## 1. Agent Nodes — ДИНАМИЧЕСКИЕ промпты ✅

| Workflow | Node | Промпт |
|----------|------|--------|
| [Перевод] Перевод чанка | Перевод чанка | `={{ $json.SystemPrompt }}` ← из Code node |
| [Перевод] Перевод чанка | Резервный перевод | `={{ $('Формирование...').first().json.SystemPrompt }}` |
| Постредактура | Перевод чанка | `={{ $json.SystemPrompt }}` ← из Code node |
| Анотация | Генерация промта для картинки | **Захаркожен** (арт-директор, английский) |

**Вывод:** Translate и PostEdit уже принимают промпт динамически! Gateway может передать.

## 2. Information Extractor — ЗАХАРКОЖЕНЫ ❌

| Workflow | Node | Промпт |
|----------|------|--------|
| [Перевод] Арка | Rolling Summary арки | Захаркожен в ноде |
| [Перевод] Арка | Определение границ арки | Захаркожен в ноде |
| [Перевод] Арка | Cоздание стартового Summary | Захаркожен в ноде |
| [Перевод] Глава | Rolling Summary чанка | Захаркожен в ноде |
| [Перевод] Глава | Summary главы | Захаркожен в ноде |
| Предварительный анализ | Information Extractor | Захаркожен в ноде |
| Предварительный анализ | Резервный Information Extractor | Захаркожен в ноде |

**Вывод:** Information Extractor НЕ поддерживает dynamic prompt. Нельзя сделать универсальным.

## 3. lmChatOpenAi — модели привязаны к credential

| Workflow | Node | Модель | Credential |
|----------|------|--------|-----------|
| [Перевод] Арка | Gemini 2.5 Flash Lite from Polza.ai | Gemini 2.5 | polza.ai |
| [Перевод] Глава | Gemini 2.5 Flash Lite from Polza.ai | Gemini 2.5 | polza.ai |
| Перевод чанка | GPT 5.2 from Polza.ai | GPT 5.2 | polza.ai |
| Перевод чанка | GPT 5.2 from Neuro AI | GPT 5.2 | Neuroapi |
| Перевод чанка | CLAUDE 4.5 from Neuro | Claude 4.5 | Neuroapi |
| Перевод чанка | CLAUDE 4.5 from Polza.ai | Claude 4.5 | Polza |
| Постредактура | GPT 5.3 from Polza | GPT 5.3 | Polza |
| Постредактура | GPT-5.2 from Neuro | GPT-5.2 | Neuroapi |
| Анотация | OpenAI Chat Model | GPT-5.x | polza.ai |
| Предварительный анализ | OpenAI Chat Model | GPT-5.x | polza.ai |
| Предварительный анализ | OpenAI Chat Model1 | GPT-5.x | polza.ai |

**Вывод:** 11 модельных нод, каждая со своей моделью и credential.

## 4. Tools — уникальные для каждого task

| Task | Tools |
|------|-------|
| Перевод | Нет tools |
| Постредактура | text_validator (Code), parentheses_checker (Code), check_forbidden_words (PostgresTool) |
| Анотация | Нет tools |
| Extract/Summary | Нет tools |

---

# Почему ОДИН универсальный AI Gateway НЕ работает

| Проблема | Описание |
|----------|----------|
| **Information Extractor не поддерживает dynamic prompt** | Промпт захаркожен в ноде — нельзя передать извне |
| **Разные типы LangChain nodes** | Agent ≠ Information Extractor ≠ Chat Model ≠ Chain |
| **Разные tools** | Постредактура требует 3 Code tools + 1 PostgresTool |
| **Разные fallback chains** | Перевод: 4 модели, Summary: 1 модель, Extract: 2 модели |
| **Разные входные данные** | Перевод: text+glossary+context, Summary: all chunks joined, Extract: full text |

---

# Правильная архитектура: AI Gateway HUB

## НЕ один gateway, НЕ по gateway на workflow

## А: Gateway Hub — роутер к специализированным AI chains

```
┌─────────────────────────────────────────────────────────────────┐
│                    [AI Gateway Hub]                             │
│                    (роутер, 5-7 нод)                            │
│                                                                  │
│  Input:                                                         │
│    - task: translate │ post_edit │ summary │ extract │ annotate │
│    - text: входной текст                                        │
│    - prompt: (опционально, для translate/post_edit)             │
│    - mode: production │ dev                                     │
│    - context: {glossary, rolling_summary, arc_context}          │
│    - tools_config: (опционально)                                │
│                                                                  │
│  Switch(task):                                                   │
│    ├─ "translate"  → Execute: [AI Translate]                   │
│    ├─ "post_edit"  → Execute: [AI Post-Edit]                   │
│    ├─ "summary"    → Execute: [AI Summary]                     │
│    ├─ "extract"    → Execute: [AI Extract]                     │
│    └─ "annotate"   → Execute: [AI Annotate]                    │
│                                                                  │
│  Output: {result, model, mode, duration_ms, fallback_count}     │
└─────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│[AI Translate]│ │[AI PostEdit]│ │[AI Summary] │ │[AI Extract] │
│  (15 нод)   │ │  (12 нод)   │ │  (10 нод)   │ │  (10 нод)   │
│             │ │             │ │             │ │             │
│ Mode Router │ │ Mode Router │ │ Mode Router │ │ Mode Router │
│ prod: 4     │ │ prod: 2     │ │ prod: 1     │ │ prod: 2     │
│ fallback    │ │ fallback    │ │ fallback    │ │ fallback    │
│ dev: 2      │ │ dev: 2      │ │ dev: 1      │ │ dev: 2      │
│ fallback    │ │ fallback    │ │ fallback    │ │ fallback    │
│             │ │ + Tools     │ │             │ │             │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

## Структура каждого специализированного AI workflow

### [AI Translate]
```
Trigger: ExecuteWorkflowTrigger
  Input: {text, prompt, context, mode}
    ↓
Mode Router (IF)
  ├─ production → [Production Translate Chain]
  │   ├─ GPT 5.2 Polza ─fail→ GPT 5.2 Neuro ─fail→ Claude Neuro ─fail→ Claude Polza
  │   └─ Model: LangChain Agent (lmChatOpenAi + credential)
  └─ dev → [Dev Translate Chain]
      ├─ llama3.2:3b (Ollama) ─fail→ qwen2.5:32b (Ollama)
      └─ Model: LangChain Agent (lmChatOpenAi → Ollama credential)
    ↓
Log to pipeline_execution_log
    ↓
Return: {result, model, mode, duration_ms, fallback_count}
```

### [AI Post-Edit]
```
Trigger: ExecuteWorkflowTrigger
  Input: {text, prompt, mode}
    ↓
Mode Router (IF)
  ├─ production → [Production Post-Edit Chain]
  │   ├─ GPT 5.3 Polza ─fail→ GPT-5.2 Neuro
  │   └─ + Tools: text_validator, parentheses_checker, check_forbidden_words
  └─ dev → [Dev Post-Edit Chain]
      ├─ llama3.2:3b (Ollama)
      └─ + Code tools (аналоги через Code nodes)
    ↓
Log → Return
```

### [AI Summary] / [AI Extract]
```
Trigger: ExecuteWorkflowTrigger
  Input: {text, mode}
    ↓
Mode Router (IF)
  ├─ production → Gemini 2.5 Flash Lite (Polza)
  │   └─ LangChain Information Extractor
  └─ dev → llama3.2:3b (Ollama)
      └─ Code node: prompt + HTTP to Ollama /v1/chat/completions
         (Information Extractor не работает с Ollama, делаем через HTTP)
    ↓
Log → Return
```

### [AI Annotate]
```
Trigger: ExecuteWorkflowTrigger
  Input: {text, mode}
    ↓
Mode Router (IF)
  ├─ production → OpenAI Chat Model (Polza)
  │   └─ LangChain Chain: book summary → cover prompt generation
  └─ dev → qwen2.5:32b (Ollama)
      └─ Code node: HTTP to Ollama
    ↓
Log → Return
```

---

# Итого: что создаём

| Workflow | Нод | Назначение | Mode Router |
|----------|-----|-----------|-------------|
| **[AI Gateway Hub]** | 5-7 | Роутер по task type | Нет |
| **[AI Translate]** | ~15 | Перевод чанков | ✅ prod/dev |
| **[AI Post-Edit]** | ~12 | Постредактура | ✅ prod/dev |
| **[AI Summary]** | ~10 | Summary глав/арк/чанков | ✅ prod/dev |
| **[AI Extract]** | ~10 | Information Extraction (арки, анализ) | ✅ prod/dev |
| **[AI Annotate]** | ~10 | Аннотация + обложка | ✅ prod/dev |

**Всего: ~60-65 нод (vs 20+ LangChain nodes сейчас, которые меняем)**

---

# Изменения в существующих workflows

## [Перевод] Перевод чанка
```
БЫЛО (34 ноды):
  5 LangChain Agent nodes × 4 модели + fallback logic

СТАЛО (~18 нод):
  Подготовить input → Execute: [AI Gateway Hub] {task: "translate"}
  ← {result, model, duration_ms, fallback_count}
  Обработать результат
```

## [Перевод] Глава
```
БЫЛО (26 нод):
  3 Information Extractor nodes + Gemini

СТАЛО (~15 нод):
  Подготовить input → Execute: [AI Gateway Hub] {task: "summary"}
  ← {result, model, duration_ms}
  Обработать результат
```

## [Перевод] Арка
```
БЫЛО (31 нода):
  3 Information Extractor + Gemini

СТАЛО (~15 нод):
  Подготовить input → Execute: [AI Gateway Hub] {task: "extract"}
  ← {result, model, duration_ms}
  Обработать результат
```

## Предварительный анализ
```
БЫЛО (27 нод):
  2 Information Extractor + 2 OpenAI Chat Model

СТАЛО (~16 нод):
  Подготовить input → Execute: [AI Gateway Hub] {task: "extract"}
  ← {result, model, duration_ms}
  Обработать результат
```

## Постредактура
```
БЫЛО (9 нод):
  Agent + 2 lmChatOpenAi + 3 tools

СТАЛО (~12 нод):
  Подготовить input → Execute: [AI Gateway Hub] {task: "post_edit"}
  ← {result, model, duration_ms}
  Обработать результат
```

## Анотация
```
БЫЛО (7 нод):
  Chain + lmChatOpenAi + Agent

СТАЛО (~10 нод):
  Подготовить input → Execute: [AI Gateway Hub] {task: "annotate"}
  ← {result, model, duration_ms}
  Обработать результат
```

---

# Плюсы Gateway Hub

| ✅ | Описание |
|---|---|
| **Нет дублирования** | Один роутер + 5 специализированных AI chains |
| **Каждый task type = свой workflow** | Правильные промпты, tools, fallback |
| **Mode router везде одинаковый** | prod/dev переключение в одном месте на chain |
| **Централизованные метрики** | Каждая chain логамирует в pipeline_execution_log |
| **Легко добавить新模式** | Новый task type = новая chain |
| **Можно тестировать по одному** | Тестируем Translate отдельно от Summary |
| **A/B тестирование** | Mode router легко расширить до canary |

---

# Минусы Gateway Hub

| ❌ | Описание | Митигация |
|---|---|---|
| **6 новых workflows** | Hub + 5 chains = 6 workflows | Каждый маленький и понятный |
| **Information Extractor ≠ HTTP** | Ollama не поддерживает Information Extractor | Для dev mode используем HTTP call к /v1/chat/completions |
| **Tools в Post-Edit** | Code tools нужно дублировать для dev mode | Code tools работают с любой моделью |
| **Начальная сложность** | 6-9 часов на реализацию | Окупается при первом добавлении модели |

---

# Сравнение подходов

| Критерий | Один Gateway | Gateway Hub | Per-workflow AI |
|----------|-------------|-------------|-----------------|
| **Гибкость** | Низкая | **Высокая** | Средняя |
| **Поддержка** | Простая | **Средняя** | Сложная |
| **Правильность** | ❌ Невозможно | ✅ Правильно | ✅ Правильно |
| **Тестируемость** | Сложная | **Легко** | Легко |
| **Кол-во workflow'ов** | 1 | **6** | 20+ |
| **Реализация** | ❌ Не работает | ✅ Работает | ✅ Работает |

---

# Вердикт

## **Gateway Hub** — правильный подход

НЕ один универсальный gateway.
НЕ по gateway на каждый workflow.
А **Hub + специализированные AI chains**.

Это баланс между:
- Централизацией (один entry point)
- Специализацией (правильные промпты/tools для каждого task type)
- Тестируемостью (каждую chain тестируем отдельно)

---

# План реализации

## Phase 1: AI Gateway Hub (1 час)
- [ ] Создать workflow [AI Gateway Hub]
- [ ] Switch node по task type
- [ ] Execute Workflow nodes к каждой chain

## Phase 2: [AI Translate] (2-3 часа)
- [ ] Создать workflow
- [ ] Mode Router (IF node)
- [ ] Production chain: 4 модели + fallback
- [ ] Dev chain: llama3.2:3b → qwen2.5:32b
- [ ] Логирование
- [ ] Тест

## Phase 3: [AI Summary] (1-2 часа)
- [ ] Создать workflow
- [ ] Mode Router
- [ ] Production: Gemini 2.5 (Polza)
- [ ] Dev: llama3.2:3b (HTTP call)
- [ ] Логирование
- [ ] Тест

## Phase 4: [AI Extract] (1-2 часа)
- [ ] Создать workflow
- [ ] Mode Router
- [ ] Production: Gemini 2.5 (Polza)
- [ ] Dev: llama3.2:3b (HTTP call)
- [ ] Логирование
- [ ] Тест

## Phase 5: [AI Post-Edit] (1-2 часа)
- [ ] Создать workflow
- [ ] Mode Router
- [ ] Production: GPT 5.3 → GPT-5.2
- [ ] + Tools: text_validator, parentheses_checker, check_forbidden_words
- [ ] Dev: llama3.2:3b + Code tools
- [ ] Логирование
- [ ] Тест

## Phase 6: [AI Annotate] (1 час)
- [ ] Создать workflow
- [ ] Mode Router
- [ ] Production: OpenAI (Polza)
- [ ] Dev: qwen2.5:32b
- [ ] Логирование
- [ ] Тест

## Phase 7: Интеграция (2-3 часа)
- [ ] Заменить LangChain nodes в [Перевод] Перевод чанка → AI Gateway Hub
- [ ] Заменить в [Перевод] Глава → AI Gateway Hub
- [ ] Заменить в [Перевод] Арка → AI Gateway Hub
- [ ] Заменить в Предварительный анализ → AI Gateway Hub
- [ ] Заменить в Постредактура → AI Gateway Hub
- [ ] Заменить в Анотация → AI Gateway Hub

## Phase 8: E2E Test (1-2 часа)
- [ ] Production mode test
- [ ] Dev mode test (Ollama)
- [ ] Fallback test
- [ ] Verify pipeline_execution_log
- [ ] Verify Grafana

**Итого: 10-16 часов**

---

# Что нужно от тебя

| # | Что | Статус |
|---|-----|--------|
| 1 | Подтверждение Gateway Hub подхода | ⏳ Скажи ОК |
| 2 | Тестовый файл для перевода | ⏳ Предоставь |
| 3 | Время на реализацию | ⏳ 10-16 часов |
