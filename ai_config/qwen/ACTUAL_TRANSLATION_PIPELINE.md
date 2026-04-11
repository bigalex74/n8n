# ACTUAL Translation Pipeline Architecture

**Дата:** 11 апреля 2026 г.
**На основе:** Реальный анализ 30 активных workflows

---

# Полная схема перевода книг

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           START (9cjeUNeTZX3YnO1W57YTP)                 │
│  Trigger: ExecuteWorkflowTrigger                                        │
│  1. Billing: Polza.ai API ──────────────────────────► Polza.ai (внешн.) │
│  2. Billing: Neuro API ─────────────────────────────► Neuro API (внешн.)│
│  3. Проверка: Есть Глоссарий?                                           │
│     ├─ НЕТ → Создание Глоссария ──► Google Drive upload                 │
│     └─ ДА → Пропуск                                                     │
│  4. Проверка: Есть Промт?                                               │
│  5. Проверка: Есть Промт для постредакта?                               │
│  6. Настройка БД                                                        │
│  7. Парсинг файла ──────────────────────────────────────────────────┐   │
└─────────────────────────────────────────────────────────────────────┼───┘
                                                                      │
┌─────────────────────────────────────────────────────────────────────▼───┐
│           ПАРСИНГ ФАЙЛА (bC43bgf5ZtXoi_XDLDwHO)                         │
│  1. DOCX to Text (или другой формат)                                    │
│  2. Read file from DB                                                   │
│  3. Extract text from binary                                            │
│  Output: Raw text                                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                                                      │
┌─────────────────────────────────────────────────────────────────────▼───┐
│     ПРЕДВАРИТЕЛЬНЫЙ АНАЛИЗ (lSuNRX0VILP9Lgit5VKlK)                      │
│  1. Read file text from DB                                              │
│  2. Split text for structural analysis                                  │
│  3. Information Extractor ──► Gemini 2.5 Flash Lite (Polza.ai) ▲ ВНЕШН.│
│     Резервный: OpenAI Chat Model1 ───────────────────────────► (внешн.) │
│  4. Add chapters to DB (document_chapters)                              │
│  5. Create first arc (document_arcs)                                    │
│  6. Split into chunks → document_chunks (status='pending')              │
│  7. Notify: Start (Telegram)                                            │
│  8. Notify: Progress (Telegram)                                         │
│  Output: Арки + Главы + Чанки в БД                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                                                      │
┌─────────────────────────────────────────────────────────────────────▼───┐
│         TRANSLATE CHUNK LOOP (Q5TRHGg-XRblnMRpH41Ee)                    │
│  ═══════════════════════════════════════════════════════════            │
│  Цикл по всем чанкам:                                                   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. Выбрать чанк (status='pending')                              │   │
│  │ 2. [Перевод] Перевод чанка ──────────────────────────────┐     │   │
│  │    │                                                      │     │   │
│  │    │ ┌──────────────────────────────────────────────┐    │     │   │
│  │    │ │  [Перевод] ПЕРЕВОД ЧАНКА (GPARI8V4...)      │    │     │   │
│  │    │ │  1. Read glossary from DB                   │    │     │   │
│  │    │ │  2. Read prompts from DB                    │    │     │   │
│  │    │ │  3. Get rolling summary from DB             │    │     │   │
│  │    │ │  4. Get current arc from DB                 │    │     │   │
│  │    │ │  5. Запрос в LightRAG ──► sub_lightrag_api  │    │     │   │
│  │    │ │         │                                   │    │     │   │
│  │    │ │         │ ┌────────────────────────────┐   │    │     │   │
│  │    │ │         │ │ sub_lightrag_api           │   │    │     │   │
│  │    │ │         │ │ HTTP → LightRAG :9621     ▲│   │    │     │   │
│  │    │ │         │ │ LightRAG → Ollama (embed) ││   │    │     │   │
│  │    │ │         │ │ LightRAG → polza.ai (LLM) ▲│   │    │     │   │
│  │    │ │         │ └────────────────────────────┘   │    │     │   │
│  │    │ │  6. Формирование промпта (с контекстом)    │    │     │   │
│  │    │ │  7. Перевод чанка (LangChain Agent):      │    │     │   │
│  │    │ │     Primary: GPT 5.2 from Polza.ai  ▲ ВНЕШН.   │     │   │
│  │    │ │     Fallback 1: GPT 5.2 from Neuro  ▲ ВНЕШН.   │     │   │
│  │    │ │     Fallback 2: Claude 4.5 from Neuro▲ ВНЕШН.   │     │   │
│  │    │ │     Fallback 3: Claude 4.5 from Polza▲ ВНЕШН.   │     │   │
│  │    │ │  8. Проверка запрещённых слов            │    │     │   │
│  │    │ │  9. Постредактура (опционально):         │    │     │   │
│  │    │ │     Agent с GPT 5.3 (Polza) ▲ ВНЕШН.      │    │     │   │
│  │    │ │     Agent с GPT-5.2 (Neuro) ▲ ВНЕШН.      │    │     │   │
│  │    │ │     Tools: text_validator, parentheses    │    │     │   │
│  │    │ │  10. Запись в БД (status='done')          │    │     │   │
│  │    │ └──────────────────────────────────────────┘    │     │   │
│  │    │                                                 │     │   │
│  │  3. [Перевод] Глава ─────────────────────────────────┘     │   │
│  │    │ ┌────────────────────────────────────────────────┐   │   │
│  │    │ │  [Перевод] ГЛАВА (IgLfaCSszdwsPw_b4u3au)      │   │   │
│  │    │ │  1. Выбрать все переведённые чанки главы       │   │   │
│  │    │ │  2. Read glossary from DB                     │   │   │
│  │    │ │  3. Summary главы ──► Gemini 2.5 Lite ▲ ВНЕШН.│   │   │
│  │    │ │  4. Rolling Summary чанка ──► Gemini ▲ ВНЕШН. │   │   │
│  │    │ │  5. Insert into LightRAG ──► sub_lightrag_api │   │   │
│  │    │ │  6. Обновить статус главы                     │   │   │
│  │    │ └────────────────────────────────────────────────┘   │   │
│  │    │                                                      │   │
│  │  4. [Перевод] Арка ───────────────────────────────────────┘   │
│  │    │ ┌────────────────────────────────────────────────────┐   │
│  │    │ │  [Перевод] АРКА (OggkJgA8IFmasME_BNimq)          │   │
│  │    │ │  1. Определить границы арки ──► Gemini ▲ ВНЕШН.   │   │
│  │    │ │  2. Rolling Summary арки ──► Gemini ▲ ВНЕШН.      │   │
│  │    │ │  3. Insert into LightRAG ──► sub_lightrag_api     │   │
│  │    │ │  4. Обновить статус арки                          │   │
│  │    │ └────────────────────────────────────────────────────┘   │
│  │    │                                                           │
│  │  5. Все чанки переведены?                                      │
│  │     ├─ НЕТ → Следующий чанк (loop)                             │
│  │     └─ ДА → FINISH ────────────────────────────────────────────┘
│  └─────────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────┘
                                                                      │
┌─────────────────────────────────────────────────────────────────────▼───┐
│                        FINISH (vuqLp6ZGenvpkJbmVPR_6)                   │
│  1. Анотация ─────────────────────────────────────────────────────────┐ │
│     │ ┌────────────────────────────────────────────────────────────┐  │ │
│     │ │  Анотация (2kztTVutdATd1MDS)                               │  │ │
│     │ │  1. Summary book ──► OpenAI Chat Model ▲ ВНЕШН.           │  │ │
│     │ │  2. Генерация промта для картинки ──► Agent ▲ ВНЕШН.      │  │ │
│     │ │  3. Генерация обложки ──► HTTP (image API) ▲ ВНЕШН.       │  │ │
│     │ └────────────────────────────────────────────────────────────┘  │ │
│  2. Переведенный файл в Telegram                                      │ │
│  3. Переведенный файл в Google Drive                                  │ │
│  4. Notify: Finish (Telegram)                                         │ │
│  5. Update job status = 'completed'                                   │ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# Внешние LLM (все точки расхода токенов)

| # | Где используется | Модель | Провайдер | Credential | Назначение |
|---|-----------------|--------|-----------|------------|------------|
| 1 | Предварительный анализ | Gemini 2.5 Flash Lite | Polza.ai | polza.ai | Структурный анализ текста |
| 2 | Предварительный анализ (резерв) | OpenAI | Polza.ai | polza.ai | Резервный Information Extractor |
| 3 | Перевод чанка (primary) | GPT 5.2 | Polza.ai | polza.ai | **Основной перевод** |
| 4 | Перевод чанка (fallback 1) | GPT 5.2 | Neuro API | Neuroapi | Резервный перевод |
| 5 | Перевод чанка (fallback 2) | Claude 4.5 | Neuro API | Neuroapi | Резервный перевод |
| 6 | Перевод чанка (fallback 3) | Claude 4.5 | Polza.ai | Polza | Резервный перевод |
| 7 | Постредактура | GPT 5.3 | Polza.ai | Polza | Постобработка перевода |
| 8 | Постредактура (резерв) | GPT-5.2 | Neuro API | Neuroapi | Резервная постредактура |
| 9 | Summary главы | Gemini 2.5 Flash Lite | Polza.ai | polza.ai | Саммаризация главы |
| 10 | Rolling Summary чанка | Gemini 2.5 Flash Lite | Polza.ai | polza.ai | Rolling context |
| 11 | Определение арки | Gemini 2.5 Flash Lite | Polza.ai | polza.ai | Arc boundary detection |
| 12 | Rolling Summary арки | Gemini 2.5 Flash Lite | Polza.ai | polza.ai | Arc context |
| 13 | LightRAG LLM | gpt-5.4-nano | Polza.ai | (env var) | RAG ответы |
| 14 | Аннотация - Summary | OpenAI | Polza.ai | polza.ai | Summary книги |
| 15 | Аннотация - Обложка | OpenAI | Polza.ai | polza.ai | Промпт для картинки |
| 16 | Генерация обложки | Image API | (HTTP node) | — | Картинка обложки |

## Итого: 4 внешних провайдера
- **polza.ai** — GPT 5.2, GPT 5.3, Claude 4.5, Gemini 2.5, gpt-5.4-nano (LightRAG)
- **Neuro API** — GPT 5.2, Claude 4.5 (fallback)
- **Ollama** (локальный) — embeddings для LightRAG (nomic-embed-text)
- **LightRAG** (локальный, порт 9621) — использует polza.ai + Ollama

---

# Текущая отказоустойчивость

## Что уже есть:
1. **Fallback цепочка перевода**: 4 модели (GPT Polza → GPT Neuro → Claude Neuro → Claude Polza)
2. **Резервный Information Extractor**: основной + резервный
3. **Обработка ошибок**: [Перевод] Обработка ошибки workflow
4. **Global Error Handler**: подключен к workflows
5. **Error logging**: document_log table
6. **Status tracking**: document_chunks.status (pending/done/error)

## Чего НЕТ:
- ❌ Circuit breaker для Polza.ai / Neuro API
- ❌ Retry с exponential backoff
- ❌ Dead letter queue для проваленных чанков
- ❌ Детальное логирование каждой ноды (pipeline_execution_log)
- ❌ Метрики производительности (pipeline_metrics)
- ❌ Health checks для внешних API
- ❌ Alerting при сбоях
- ❌ Grafana dashboard с observability

---

# Для E2E тестирования (zero cost)

## Стратегия переключения на Ollama

| Компонент | Production | Test Mode |
|-----------|-----------|-----------|
| Предварительный анализ | Gemini 2.5 (Polza) | **Ollama llama3.2:3b** |
| Перевод чанка | GPT 5.2 (Polza) + 3 fallback | **Ollama llama3.2:3b** |
| Постредактура | GPT 5.3 (Polza) | **Ollama llama3.2:3b** |
| Summary главы/арки | Gemini 2.5 (Polza) | **Ollama llama3.2:3b** |
| LightRAG LLM | gpt-5.4-nano (Polza) | **Ollama llama3.2:3b** |
| Аннотация | OpenAI (Polza) | **Ollama llama3.2:3b** |
| Embeddings | Ollama nomic-embed-text | Без изменений (уже локально) |

## Что нужно переключить:
1. **n8n LangChain nodes** — сменить credential с polza.ai на Ollama (localhost:11434)
2. **LightRAG** — env vars: `LLM_BINDING=ollama`, `LLM_MODEL=llama3.2:3b`
3. **Создать test-only credentials** в n8n: "Ollama Local" pointing to localhost:11434

## Что предоставить:
- Тестовый файл (текст ~500-1000 слов)
- Подтверждение что llama3.2:3b достаточна для проверки логирования (не качества!)
