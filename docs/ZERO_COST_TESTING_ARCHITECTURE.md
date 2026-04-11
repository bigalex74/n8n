# Architecture: Zero-Cost Translation Test Pipeline

**Дата:** 11 апреля 2026 г.  
**Автор:** PRIME Agent  
**Цель:** Запустить ПОЛНЫЙ цикл перевода без расходов платных токенов (Polza.ai, NeuroAPI)

---

# Текущее состояние

## Уже есть:
- ✅ Ollama credential в n8n (`UFgRdu0SIGkqO3Iz` — "Ollama account")
- ✅ Модели: qwen2.5:32b (20GB), llama3.2:3b (2GB), nomic-embed-text (0.3GB)
- ✅ LightRAG запущен (порт 9621)
- ✅ Все LangChain nodes используют `@n8n/n8n-nodes-langchain.lmChatOpenAi` (поддерживают Ollama!)

## Точки расхода токенов (16 мест):

| # | Workflow | Node | Текущий LLM | Credential |
|---|----------|------|-------------|------------|
| 1 | Предварительный анализ | OpenAI Chat Model | GPT-5.x | polza.ai |
| 2 | Предварительный анализ | OpenAI Chat Model1 | GPT-5.x | polza.ai |
| 3 | Предварительный анализ | Резервный Information Extractor | GPT-5.x | polza.ai |
| 4 | [Перевод] Перевод чанка | GPT 5.2 from Polza.ai | GPT 5.2 | polza.ai |
| 5 | [Перевод] Перевод чанка | GPT 5.2 from Neuro AI | GPT 5.2 | Neuroapi |
| 6 | [Перевод] Перевод чанка | CLAUDE 4.5 from Neuro | Claude 4.5 | Neuroapi |
| 7 | [Перевод] Перевод чанка | CLAUDE 4.5 from Polza.ai | Claude 4.5 | Polza |
| 8 | [Перевод] Глава | Gemini 2.5 Flash Lite | Gemini | polza.ai |
| 9 | [Перевод] Арка | Gemini 2.5 Flash Lite | Gemini | polza.ai |
| 10-12 | [Перевод] Арка (3 ноды extract) | Gemini | polza.ai |
| 13 | Постредактура | GPT 5.3 from Polza | GPT 5.3 | Polza |
| 14 | Постредактура | GPT-5.2 from Neuro | GPT-5.2 | Neuroapi |
| 15 | Анотация | OpenAI Chat Model | GPT-5.x | polza.ai |
| 16 | LightRAG API | HTTP request | gpt-5.4-nano | httpHeaderAuth |

---

# Вариант A: Test Mode через Environment Variable (рекомендую)

## Архитектура

```
┌─────────────────────────────────────────────────┐
│              n8n Container                       │
│                                                  │
│  Env: TRANSLATION_MODE=test                      │
│  Env: TEST_MODEL=llama3.2:3b                     │
│                                                  │
│  Code Node (в начале каждого workflow):           │
│  if ($env["TRANSLATION_MODE"] === "test") {      │
│    → Switch LangChain node → Ollama credential   │
│    → Switch LightRAG API → /api/ollama           │
│  }                                                │
└──────────────────────────────────────────────────┘
```

## Как работает

1. Создаём env vars в n8n container:
   ```
   TRANSLATION_MODE=test
   TEST_MODEL=llama3.2:3b
   ```

2. В каждом workflow добавляем Code Node на входе:
   ```javascript
   // Проверяем режим
   const mode = $env["TRANSLATION_MODE"] || "production";
   return [{json: {mode, model: mode === "test" ? $env["TEST_MODEL"] : "gpt-5.2"}}];
   ```

3. LangChain nodes настраиваем через Expression:
   - Model: `={{ $json.mode === "test" ? "llama3.2:3b" : "gpt-5.2" }}`
   - Base URL: `={{ $json.mode === "test" ? "http://localhost:11434/v1" : "https://polza.ai/api/v1" }}`
   - Credential: переключаем на Ollama account когда mode=test

4. LightRAG: переключаем env при запуске теста

## Плюсы
| ✅ | Описание |
|---|---|
| Безопасность | Production workflow НЕ меняется |
| Переключение | Один env var = мгновенный переход |
| Наглядность | Видно в каком режиме работаем |
| Гибкость | Можно тестировать разные модели |

## Минусы
| ❌ | Описание |
|---|---|
| Трудоёмкость | Нужно модифицировать ~20 LangChain nodes |
| Сложность | Expression в credential не поддерживается напрямую |
| LightRAG | Нужно отдельно переключать |

## Оценка реализации
- **Время:** 4-6 часов
- **Риск:** Низкий (production не затрагивается)
- **Совместимость:** n8n LangChain nodes поддерживают Ollama

---

# Вариант B: Parallel Test Workflows (самый безопасный)

## Архитектура

```
Production Workflows:          Test Workflows:
┌─────────────────┐           ┌─────────────────┐
│ Start           │           │ [Test] Start    │
│ [Перевод] Арка  │           │ [Test] Арка     │
│ [Перевод] Глава │     VS    │ [Test] Глава    │
│ Перевод чанка   │           │ Перевод чанка   │
│ Finish          │           │ Finish          │
└─────────────────┘           └─────────────────┘
  Credential: polza.ai         Credential: Ollama
  Model: GPT-5.x               Model: llama3.2:3b
  Cost: $$$                    Cost: $0
```

## Как работает

1. Копируем все production workflows с префиксом `[Test]`
2. В копиях заменяем credential на Ollama account
3. Запускаем test workflow через webhook
4. Результаты идут в отдельные test таблицы БД
5. После теста — удаляем test workflows

## Плюсы
| ✅ | Описание |
|---|---|
| Безопасность | 100% изоляция — production НЕ трогается |
| Простота | Каждый workflow самодостаточен |
| Сравнение | Можно сравнить качество production vs test |
| Отладка | Легко дебажить без влияния на prod |

## Минусы
| ❌ | Описание |
|---|---|
| Дублирование | ~20 workflows скопировано |
| Поддержка | При изменении prod нужно менять и test |
| Захламление | +20 workflows в n8n UI |

## Оценка реализации
- **Время:** 3-4 часа
- **Риск:** Минимальный
- **Совместимость:** Полная

---

# Вариант C: Dynamic Credential Switching (эlegant но сложный)

## Архитектура

```
┌─────────────────────────────────────────────┐
│  Shared Configuration Workflow              │
│  ┌───────────────────────────────────────┐  │
│  │ Get Translation Config               │  │
│  │ - Читает document_jobs.metadata      │  │
│  │ - Если test_mode=true:               │  │
│  │   → Возвращает Ollama credential ID  │  │
│  │   → Возвращает llama3.2:3b           │  │
│  │ - Если test_mode=false:              │  │
│  │   → Возвращает polza.ai credential   │  │
│  │   → Возвращает gpt-5.2               │  │
│  └───────────────────────────────────────┘  │
│                                              │
│  Каждый workflow вызывает эту конфигурацию   │
│  и использует returned credential/model      │
└──────────────────────────────────────────────┘
```

## Как работает

1. В document_jobs добавляем поле `test_mode BOOLEAN DEFAULT false`
2. Создаём shared workflow `[Config] Translation Settings`:
   ```javascript
   const job = $input.first().json;
   if (job.test_mode) {
     return [{json: {credential: "ollama", model: "llama3.2:3b", baseUrl: "http://localhost:11434/v1"}}];
   } else {
     return [{json: {credential: "polza.ai", model: "gpt-5.2", baseUrl: "https://polza.ai/api/v1"}}];
   }
   ```
3. В каждом workflow добавляем Execute Workflow node → [Config]
4. LangChain nodes используют возвращённые параметры

## Плюсы
| ✅ | Описание |
|---|---|
| Элегантность | Одна точка управления |
| Масштабируемость | Легко добавить новые режимы |
| Чистота | Без дублирования workflows |

## Минусы
| ❌ | Описание |
|---|---|
| Сложность | LangChain nodes не поддерживают dynamic credentials |
| Хрупкость | Credential нельзя менять expression-ом |
| n8n limitation | Credential выбирается на этапе дизайна, не runtime |

## Оценка реализации
- **Время:** 8-12 часов (много хаков)
- **Риск:** Средний (может сломаться при обновлении n8n)
- **Совместимость:** ⚠️ n8n не поддерживает dynamic credentials для LangChain

---

# Вариант D: Ollama через OpenAI-Compatible API (самый простой)

## Архитектура

```
┌──────────────────────────────────────────────┐
│  Ollama (localhost:11434/v1)                 │
│  ├── Поддерживает OpenAI API формат          │
│  ├── Модели: llama3.2:3b, qwen2.5:32b       │
│  └── Бесплатно, локально                     │
│                                              │
│  n8n: Создаём credential "Ollama Test"       │
│  ├── Type: OpenAI API                        │
│  ├── Base URL: http://localhost:11434/v1     │
│  ├── API Key: ollama (любое значение)        │
│  └── Model: llama3.2:3b                      │
│                                              │
│  Для теста: вручную меняем credential        │
│  в LangChain nodes с polza.ai → Ollama Test  │
│  После теста: меняем обратно                 │
└──────────────────────────────────────────────┘
```

## Как работает

1. Создаём credential "Ollama Test":
   - Type: OpenAI API
   - Base URL: `http://localhost:11434/v1`
   - API Key: `ollama` (placeholder)
   
2. Для теста: открываем каждый LangChain node → меняем credential → Ollama Test
3. Запускаем pipeline
4. После теста: меняем credential обратно на polza.ai

## Плюсы
| ✅ | Описание |
|---|---|
| Простота | Минимум изменений |
| Быстрота | 30 минут на настройку |
| Безопасность | Меняем credential, не workflow логику |

## Минусы
| ❌ | Описание |
|---|---|
| Ручная работа | Нужно менять credential в ~20 нодах |
| Риск ошибки | Можно забыть переключить какую-то ноду |
| Не автоматизировано | Нет кнопки "test mode" |

## Оценка реализации
- **Время:** 30-60 минут
- **Риск:** Низкий (credential меняется, workflow нет)
- **Совместимость:** Полная (Ollama поддерживает OpenAI API)

---

# Сравнительная таблица

| Критерий | A: Env Var | B: Parallel | C: Dynamic | D: Ollama API |
|----------|-----------|-------------|------------|---------------|
| **Время реализации** | 4-6 часов | 3-4 часа | 8-12 часов | **30 мин** |
| **Безопасность prod** | Высокая | **Максимальная** | Средняя | Высокая |
| **Автоматизация** | **Высокая** | Средняя | Высокая | Низкая |
| **Поддержка** | Средняя | Низкая | Высокая | Низкая |
| **Риск** | Низкий | **Минимальный** | Средний | Низкий |
| **Чистота архитектуры** | Высокая | Низкая | **Высокая** | Низкая |

---

# Рекомендация PRIME Agent

## Для быстрого старта: Вариант D (Ollama через OpenAI API)
- ⏱️ Настроим за 30 минут
- ✅ Безопасно (credential, не логику меняем)
- ✅ Ollama credential уже существует в n8n
- ✅ Ollama поддерживает OpenAI-compatible API

## Для долгосрочной работы: Вариант B (Parallel Test Workflows)
- 🔒 100% изоляция от production
- 📊 Можно сравнивать качество
- 🧪 Легко дебажить и итерировать

---

# План реализации (Вариант D → Вариант B)

## Phase 1: Быстрый старт (30 мин) — Вариант D
1. ✅ Создать credential "Ollama Test" (Base URL: `http://localhost:11434/v1`)
2. ✅ Вручную переключить LangChain nodes в ключевых workflow
3. ✅ Запустить тестовый перевод
4. ✅ Проверить логи и метрики

## Phase 2: Автоматизация (3-4 часа) — Вариант B
1. Создать тестовые копии workflows с `[Test]` префиксом
2. Настроить на Ollama credential
3. Создать тестовые данные (файл, глоссарий, промпты)
4. Настроить E2E test runner workflow
5. Добавить верификацию логов и Grafana

---

# Что нужно от тебя

| # | Что | Зачем | Статус |
|---|-----|-------|--------|
| 1 | **Тестовый файл** для перевода | Входные данные | ⏳ Предоставь |
| 2 | **Подтверждение модели** | llama3.2:3b достаточна для теста? | ⏳ Подтверди |
| 3 | **Допуск к n8n UI** | Для смены credentials | ⏳ Если нужно |

**Я могу создать:**
- [ ] Credential "Ollama Test" (через SQL)
- [ ] Тестовый файл-заглушку (500 слов)
- [ ] Тестовый глоссарий
- [ ] E2E test runner workflow
- [ ] Тестовые промпты для llama3.2:3b