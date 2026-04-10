# Архитектура системы перевода книг (Book Translation System)

## Обзор

Система перевода книг на базе n8n + LightRAG + Ollama с мониторингом, логированием и отказоустойчивостью.

## Компоненты архитектуры

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BOOK TRANSLATION SYSTEM                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │   Telegram   │     │    Webhook   │     │  File Upload │                │
│  │    Bot       │     │   Endpoint   │     │   (Web UI)   │                │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘                │
│         │                    │                    │                         │
│         └────────────────────┼────────────────────┘                         │
│                              │                                              │
│                     ┌────────▼────────┐                                     │
│                     │  Main Workflow  │                                     │
│                     │ [Book Translator│                                     │
│                     │     Master]     │                                     │
│                     └────────┬────────┘                                     │
│                              │                                              │
│         ┌────────────────────┼────────────────────┐                         │
│         │                    │                    │                         │
│  ┌──────▼───────┐     ┌──────▼───────┐     ┌──────▼───────┐                │
│  │   Chapter    │     │   Quality    │     │   Glossary   │                │
│  │ Translation  │     │    Check     │     │  Extraction  │                │
│  │  Sub-Workflow│     │ Sub-Workflow │     │ Sub-Workflow │                │
│  │  (LightRAG)  │     │   (Ollama)   │     │  (LightRAG)  │                │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘                │
│         │                    │                    │                         │
│         └────────────────────┼────────────────────┘                         │
│                              │                                              │
│                     ┌────────▼────────┐                                     │
│                     │  Global Error   │                                     │
│                     │    Handler      │                                     │
│                     └────────┬────────┘                                     │
│                              │                                              │
│         ┌────────────────────┼────────────────────┐                         │
│         │                    │                    │                         │
│  ┌──────▼───────┐     ┌──────▼───────┐     ┌──────▼───────┐                │
│  │  PostgreSQL  │     │   Grafana    │     │  Prometheus  │                │
│  │    (Logs)    │     │  (Dashboard) │     │   (Metrics)  │                │
│  └──────────────┘     └──────────────┘     └──────────────┘                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Интеграция с LightRAG и Ollama

### LightRAG (порт 9621, host networking)

**Использование:**
1. **Glossary Extraction** - извлечение терминов и создание глоссария
2. **Chapter Translation** - перевод с сохранением контекста через RAG
3. **Context Retrieval** - поиск предыдущих переводов для консистентности

**API Endpoints:**
- `POST http://localhost:9621/documents` - загрузка документа
- `POST http://localhost:9621/query` - query с контекстом
- `GET http://localhost:9621/health` - health check

### Ollama (порт 11434, host networking)

**Использование:**
1. **Quality Check** - оценка качества перевода
2. **Translation Scoring** - scoring вариантов перевода
3. **Style Consistency** - проверка стиля

**Модели:**
- `qwen2.5:32b` - основной для quality check (лучшее качество)
- `llama3.2:3b` - быстрые проверки (style, consistency)
- `nomic-embed-text` - embeddings для LightRAG

## База данных

### Таблицы

#### `book_translation_jobs`
```sql
CREATE TABLE book_translation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_title VARCHAR(500) NOT NULL,
    author VARCHAR(200),
    source_language VARCHAR(10) DEFAULT 'en',
    target_language VARCHAR(10) DEFAULT 'ru',
    total_chapters INTEGER DEFAULT 0,
    processed_chapters INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed, paused
    priority INTEGER DEFAULT 5, -- 1-10, 1=highest
    file_path VARCHAR(1000),
    file_size_bytes BIGINT,
    word_count INTEGER,
    character_count INTEGER,
    glossary_extracted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    metadata JSONB DEFAULT '{}'::jsonb,
    requested_by VARCHAR(200),
    telegram_chat_id BIGINT
);
```

#### `book_chapters`
```sql
CREATE TABLE book_chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES book_translation_jobs(id) ON DELETE CASCADE,
    chapter_number INTEGER NOT NULL,
    chapter_title VARCHAR(500),
    original_text TEXT NOT NULL,
    translated_text TEXT,
    word_count INTEGER,
    character_count INTEGER,
    status VARCHAR(50) DEFAULT 'pending', -- pending, translating, translated, quality_check, completed, failed
    translation_model VARCHAR(100),
    quality_score DECIMAL(5,2),
    quality_checked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    context_chunks JSONB DEFAULT '[]'::jsonb, -- RAG контекст
    glossary_terms JSONB DEFAULT '[]'::jsonb, -- применённые термины
    metadata JSONB DEFAULT '{}'::jsonb
);
```

#### `book_glossary`
```sql
CREATE TABLE book_glossary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES book_translation_jobs(id) ON DELETE CASCADE,
    term VARCHAR(200) NOT NULL,
    translation VARCHAR(200) NOT NULL,
    part_of_speech VARCHAR(50), -- noun, verb, adjective, etc.
    context TEXT,
    frequency INTEGER DEFAULT 1,
    confidence_score DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(job_id, term)
);
```

#### `book_translation_stats`
```sql
CREATE TABLE book_translation_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES book_translation_jobs(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,2) NOT NULL,
    metric_unit VARCHAR(50), -- words, seconds, percent, etc.
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `book_translation_logs`
```sql
CREATE TABLE book_translation_logs (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID REFERENCES book_translation_jobs(id) ON DELETE SET NULL,
    chapter_id UUID REFERENCES book_chapters(id) ON DELETE SET NULL,
    log_level VARCHAR(20) DEFAULT 'INFO', -- INFO, WARNING, ERROR, DEBUG
    component VARCHAR(100), -- MainWorkflow, ChapterTranslation, QualityCheck, GlossaryExtraction
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Индексы
```sql
CREATE INDEX idx_book_jobs_status ON book_translation_jobs(status);
CREATE INDEX idx_book_jobs_created ON book_translation_jobs(created_at DESC);
CREATE INDEX idx_book_chapters_job ON book_chapters(job_id);
CREATE INDEX idx_book_chapters_status ON book_chapters(status);
CREATE INDEX idx_book_glossary_job ON book_glossary(job_id);
CREATE INDEX idx_book_stats_job ON book_translation_stats(job_id, recorded_at DESC);
CREATE INDEX idx_book_logs_job ON book_translation_logs(job_id, created_at DESC);
CREATE INDEX idx_book_logs_level ON book_translation_logs(log_level, created_at DESC);
```

## Workflows

### 1. Main Workflow: [Book Translation] Master Workflow

**Trigger:**
- Webhook: `POST /webhook/book-translation/start`
- Telegram command: `/translate_book`
- Schedule: проверка pending jobs

**Steps:**
1. **Webhook/Telegram Trigger** - получение запроса
2. **Validate Input** - валидация параметров
3. **Create Job Record** - запись в `book_translation_jobs`
4. **Upload to LightRAG** - загрузка книги в LightRAG
5. **Extract Glossary** (Sub-workflow) - извлечение глоссария
6. **Split into Chapters** - разбивка на главы
7. **Create Chapter Records** - запись глав в `book_chapters`
8. **Parallel Chapter Translation** (Sub-workflow, batch=3):
   - Retrieve context from LightRAG
   - Apply glossary
   - Translate chapter
   - Quality check (Sub-workflow)
   - Update status
9. **Generate Statistics** - сбор статистики
10. **Notify Completion** - уведомление в Telegram
11. **Export Result** - выгрузка переведённой книги

### 2. Sub-Workflow: Chapter Translation (с LightRAG)

**Trigger:** Execute Workflow node из Master

**Steps:**
1. **Get Chapter Data** - получение данных главы
2. **Query LightRAG Context** - поиск похожего контекста:
   ```
   POST http://localhost:9621/query
   {
     "query": "previous translations of similar content",
     "top_k": 5
   }
   ```
3. **Load Glossary Terms** - загрузка терминов для главы
4. **Build Prompt** - формирование промпта:
   ```
   Translate the following chapter from {source_lang} to {target_lang}.
   
   Context from previous translations:
   {rag_context}
   
   Glossary (must use these translations):
   {glossary}
   
   Style requirements:
   - Maintain original tone
   - Preserve formatting
   - Keep proper nouns as-is unless known translation exists
   
   Chapter text:
   {chapter_text}
   ```
5. **Call Ollama API** - перевод:
   ```
   POST http://localhost:11434/api/generate
   {
     "model": "qwen2.5:32b",
     "prompt": "...",
     "stream": false,
     "options": {
       "temperature": 0.3,
       "top_p": 0.9
     }
   }
   ```
6. **Parse Response** - парсинг перевода
7. **Save to DB** - сохранение в `book_chapters`
8. **Log Progress** - лог в `book_translation_logs`

### 3. Sub-Workflow: Quality Check (с Ollama)

**Trigger:** Execute Workflow node после Chapter Translation

**Steps:**
1. **Get Translation** - получение оригинала и перевода
2. **Build Evaluation Prompt**:
   ```
   Evaluate the translation quality from {source_lang} to {target_lang}.
   
   Original:
   {original_text}
   
   Translation:
   {translated_text}
   
   Rate 1-10 on:
   1. Accuracy (faithfulness to original)
   2. Fluency (natural sounding)
   3. Terminology consistency
   4. Style preservation
   
   Provide JSON response:
   {
     "overall_score": 1-10,
     "accuracy_score": 1-10,
     "fluency_score": 1-10,
     "terminology_score": 1-10,
     "style_score": 1-10,
     "issues": ["list of issues"],
     "suggestions": ["improvement suggestions"]
   }
   ```
3. **Call Ollama API** (qwen2.5:32b):
   ```
   POST http://localhost:11434/api/generate
   {
     "model": "qwen2.5:32b",
     "prompt": "...",
     "format": "json",
     "stream": false
   }
   ```
4. **Parse Scores** - парсинг JSON ответа
5. **Decision**:
   - Score >= 8: Accept → Update chapter status = 'completed'
   - Score 6-7: Flag for review → status = 'needs_review'
   - Score < 6: Retry translation → Increment retry_count, re-translate
6. **Log Results** - запись в logs и stats

### 4. Sub-Workflow: Glossary Extraction (с LightRAG)

**Trigger:** Execute Workflow node в начале перевода книги

**Steps:**
1. **Get Book Text** - получение текста книги
2. **Chunk Text** - разбивка на чанки (1000 слов)
3. **Extract Terms** (для каждого чанка):
   ```
   Extract key terms, names, places, and specialized vocabulary.
   Return as JSON array:
   [
     {"term": "...", "part_of_speech": "...", "context": "..."},
     ...
   ]
   ```
4. **Call Ollama API** (llama3.2:3b для скорости)
5. **Aggregate Terms** - объединение и дедупликация
6. **Translate Terms** (с LightRAG context):
   - Query LightRAG для поиска известных переводов
   - Translate неизвестные термины
7. **Save to DB** - запись в `book_glossary`
8. **Update Job** - `glossary_extracted = TRUE`

### 5. Global Error Handler Workflow

**Trigger:** Error Trigger node

**Steps:**
1. **Capture Error** - получение данных ошибки
2. **Log Error** - запись в `book_translation_logs` (level=ERROR)
3. **Check Retry Count**:
   - retry_count < max_retries: Retry с exponential backoff
   - retry_count >= max_retries: Mark as failed
4. **Notify on Critical Error** - Telegram уведомление
5. **Update Job Status**:
   - 'failed' если критическая ошибка
   - 'processing' если retry
6. **Cleanup** - освобождение ресурсов

## Мониторинг

### Prometheus Metrics

**Custom metrics (через n8n Function node + Pushgateway):**

```
# Job metrics
book_translation_jobs_total{status="pending|processing|completed|failed"}
book_translation_jobs_duration_seconds{job_id="..."}

# Chapter metrics
book_translation_chapters_total{status="pending|translating|translated|quality_check|completed|failed"}
book_translation_chapters_duration_seconds{chapter_id="..."}
book_translation_chapters_word_count_total

# Quality metrics
book_translation_quality_score_avg
book_translation_quality_score_min
book_translation_quality_score_max

# Glossary metrics
book_translation_glossary_terms_total{job_id="..."}

# Error metrics
book_translation_errors_total{component="...", error_type="..."}
book_translation_retries_total{job_id="..."}

# Performance metrics
book_translation_ollama_request_duration_seconds
book_translation_lightrag_request_duration_seconds
book_translation_ollama_requests_total{model="..."}
```

### Grafana Dashboard

**Панели:**
1. **Overview**
   - Active jobs (gauge)
   - Success rate (%)
   - Average quality score (gauge)
   - Total words translated (stat)

2. **Job Progress**
   - Jobs by status (pie chart)
   - Chapters progress per job (bar gauge)
   - Translation speed (words/hour)

3. **Quality Metrics**
   - Quality score distribution (histogram)
   - Scores over time (time series)
   - Chapters needing review (table)

4. **Performance**
   - Ollama API latency (time series)
   - LightRAG API latency (time series)
   - Translation throughput (chapters/hour)

5. **Errors & Retries**
   - Errors by component (bar chart)
   - Retry rate (time series)
   - Recent errors (table)

6. **Glossary**
   - Terms extracted per job (stat)
   - Most frequent terms (table)

## Логирование

### Уровни логирования

- **INFO**: Старт/завершение jobs, глав, основные события
- **WARNING**: Quality score < 8, retry initiated
- **ERROR**: Ошибки translation, API failures, DB errors
- **DEBUG**: Детали API запросов, timing

### Лог события

```json
{
  "timestamp": "2026-03-31T12:00:00Z",
  "job_id": "uuid",
  "chapter_id": "uuid",
  "level": "INFO",
  "component": "ChapterTranslation",
  "message": "Chapter 5 translation completed",
  "details": {
    "word_count": 2500,
    "duration_seconds": 45.2,
    "model": "qwen2.5:32b",
    "quality_score": 8.5,
    "rag_context_chunks": 5,
    "glossary_terms_applied": 12
  }
}
```

## Отказоустойчивость

### Retry Strategy

**Exponential Backoff:**
```
retry_count=1: wait 10s
retry_count=2: wait 30s
retry_count=3: wait 90s
retry_count=4: wait 270s (max reached → fail)
```

**Retryable errors:**
- API timeouts (Ollama, LightRAG)
- Database connection errors
- Network failures
- Rate limiting

**Non-retryable errors:**
- Invalid input data
- Authentication failures
- Quota exceeded

### Circuit Breaker

**Для Ollama API:**
- Failure threshold: 5 ошибок за 2 минуты
- Reset timeout: 60 секунд
- Half-open: 1 test request

**Для LightRAG API:**
- Failure threshold: 3 ошибки за 1 минуту
- Reset timeout: 30 секунд

### Checkpointing

После каждой главы:
1. Save translated text to DB
2. Update chapter status
3. Log progress

При рестарте:
- Resume с последней未完成 главы
- Skip completed chapters

## API Endpoints

### Webhook Endpoints

```
POST /webhook/book-translation/start
{
  "book_title": "...",
  "author": "...",
  "source_language": "en",
  "target_language": "ru",
  "file_url": "https://...",
  "priority": 5,
  "telegram_chat_id": 123456789
}

GET /webhook/book-translation/status/:job_id
Response:
{
  "job_id": "...",
  "status": "processing",
  "progress": {
    "total_chapters": 20,
    "processed_chapters": 12,
    "current_chapter": 13
  },
  "quality_score": 8.7,
  "estimated_completion": "2026-03-31T18:00:00Z"
}

POST /webhook/book-translation/pause/:job_id
POST /webhook/book-translation/resume/:job_id
POST /webhook/book-translation/cancel/:job_id
```

## Интеграция с текущей архитектурой

### Не ломает текущую систему:

1. **Изолированные таблицы** - новые таблицы с префиксом `book_`
2. **Отдельные workflows** - не затрагивают существующие
3. **Shared resources**:
   - PostgreSQL (existing connection)
   - Grafana (existing instance, новый dashboard)
   - Prometheus (existing instance, новые метрики)
4. **Network** - host networking уже настроен
5. **Proxy** - использует существующий HTTP_PROXY

### Environment Variables (добавить в docker-compose.yml)

```yaml
n8n:
  environment:
    # ... existing ...
    - BOOK_TRANSLATION_LIGHTRAG_URL=http://localhost:9621
    - BOOK_TRANSLATION_OLLAMA_URL=http://localhost:11434
    - BOOK_TRANSLATION_DEFAULT_MODEL=qwen2.5:32b
    - BOOK_TRANSLATION_QUALITY_THRESHOLD=8.0
    - BOOK_TRANSLATION_MAX_PARALLEL_CHAPTERS=3
    - BOOK_TRANSLATION_MAX_RETRIES=3
```

## Развёртывание

### 1. Миграция БД

```bash
docker exec -it n8n-docker-db-1 psql -U n8n_user -d n8n_database -f /path/to/migrations/001_book_translation_schema.sql
```

### 2. Импорт workflows

```bash
# Main workflow
docker exec -i n8n-docker-n8n-1 n8n import:workflow --input=/home/node/book_translation_master.json

# Sub-workflows
docker exec -i n8n-docker-n8n-1 n8n import:workflow --input=/home/node/chapter_translation.json
docker exec -i n8n-docker-n8n-1 n8n import:workflow --input=/home/node/quality_check.json
docker exec -i n8n-docker-n8n-1 n8n import:workflow --input=/home/node/glossary_extraction.json
docker exec -i n8n-docker-n8n-1 n8n import:workflow --input=/home/node/error_handler.json
```

### 3. Обновление Grafana

```bash
# Импортировать dashboard
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @grafana/dashboards/book-translation-monitoring.json
```

### 4. Обновление Prometheus

Добавить в `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'book-translation'
    static_configs:
      - targets: ['localhost:9100']  # node exporter для system metrics
```

## Тестирование

### Integration Tests

1. **Test Glossary Extraction**
   - Загрузить тестовую главу
   - Проверить извлечение терминов
   - Verify DB records

2. **Test Chapter Translation**
   - Перевести тестовую главу
   - Проверить качество (score >= 7)
   - Проверить RAG context usage

3. **Test Quality Check**
   - Создать тестовый перевод
   - Запустить quality check
   - Verify scoring

4. **Test Error Handling**
   - Сымитировать ошибку API
   - Проверить retry logic
   - Verify error logging

5. **Test Full Pipeline**
   - Загрузить короткую книгу (5 глав)
   - Monitor progress
   - Verify final output

## Performance Targets

- **Translation Speed**: 500-1000 слов/минуту (с qwen2.5:32b)
- **Quality Score**: >= 8.0 (средний)
- **Success Rate**: >= 95%
- **Retry Rate**: <= 10%
- **End-to-End Latency**: < 2 минут на главу (2000 слов)
