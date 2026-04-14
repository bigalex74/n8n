# n8n Book Translation System: Complete Architecture Documentation

**Project:** Korean-to-Russian Book Translation Automation (KO->RU)
**Date:** April 14, 2026
**Version:** 2.0 (based on live system analysis)
**Domain:** bigalexn8n.ru
**Status:** Production

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Infrastructure](#2-infrastructure)
3. [Database Schema](#3-database-schema)
4. [Complete Workflow Catalog](#4-complete-workflow-catalog)
5. [Data Flow: Korean Text to Russian Text](#5-data-flow-korean-text-to-russian-text)
6. [Telegram Bot Interaction Flow](#6-telegram-bot-interaction-flow)
7. [AI Models & Prompts](#7-ai-models--prompts)
8. [LightRAG Integration](#8-lightrag-integration)
9. [Error Handling Strategy](#9-error-handling-strategy)
10. [Glossary & Prompt Management](#10-glossary--prompt-management)

---

## 1. Project Overview

### 1.1 Purpose

An automated system for translating full-length fiction books from Korean to Russian using AI, with context preservation through LightRAG knowledge graph, glossary-based terminology consistency, and hierarchical summarization (chunk -> chapter -> arc) for maintaining narrative coherence across long documents.

### 1.2 Key Design Principles

- **Chunk-based processing**: Documents split into manageable chunks (~4-8K tokens each), translated individually
- **Hierarchical context**: Rolling summaries at chunk, chapter, and arc levels provide context for subsequent translations
- **Multi-provider AI fallback**: 4-model cascade (GPT Polza -> GPT Neuro -> Claude Neuro -> Claude Polza) ensures resilience
- **Glossary-driven terminology**: Extracted terms enforced during translation via system prompts
- **LightRAG-powered retrieval**: Graph-based RAG provides semantic context from previously translated content
- **Telegram-first UX**: Users interact entirely through Telegram bot (file upload, progress tracking, result delivery)
- **PostgreSQL persistence**: All state stored in database for crash recovery and progress tracking

### 1.3 System Architecture Diagram

```mermaid
graph TB
    subgraph "User Interface"
        TG[Telegram Bot]
    end

    subgraph "Entry Layer"
        WEB[Получение сообщения<br/>Webhook Handler]
        GETDOC[[GET] Document<br/>File Download]
        SEL[[GET] /select_files<br/>File Selection UI]
    end

    subgraph "Orchestration"
        START[Start Workflow<br/>Main Orchestrator]
        CHKLOOP[Translate Chunk<br/>Loop Controller]
    end

    subgraph "Translation Pipeline"
        CHUNK[[Перевод] Перевод чанка<br/>AI Translation]
        CHAPTER[[Перевод] Глава<br/>Chapter Management]
        ARC[[Перевод] Арка<br/>Arc Management]
        ERR[[Перевод] Обработка ошибки<br/>Error Handler]
    end

    subgraph "Support Workflows"
        SETUP[Настройка БД<br/>DB Init]
        PARSE[Парсинг файла<br/>Document Parser]
        ANALYSIS[Предварительный анализ<br/>Structure Detection]
        GLOSSARY[Создание Глоссария<br/>AI Glossary Gen]
        POSTEDIT[Постредактура<br/>AI Post-Editing]
        ANNOT[Анотация<br/>Book Annotation]
    end

    subgraph "Notification System"
        SENDMSG[Send Message<br/>Dispatcher]
        SEND_CREATE[[Send] create_job]
        SEND_WAIT[[Send] wait]
        SEND_PROC[[Send] processing]
        SEND_ERR[[Send] error]
        SEND_FINISH[[Send] finish]
    end

    subgraph "Output"
        FINISH[Finish Workflow<br/>Cleanup & Delivery]
        GDRIVE[Google Drive Upload]
        TGFILE[Telegram File Send]
    end

    subgraph "External Services"
        LIGHTRAG[LightRAG API<br/>:9621]
        POLZA[Polza.ai API<br/>GPT/Claude/Gemini]
        NEURO[Neuro API<br/>GPT/Claude]
        OLLAMA[Ollama<br/>Embeddings]
    end

    subgraph "Storage"
        PG[(PostgreSQL 16<br/>n8n_database)]
    end

    TG --> WEB
    WEB --> GETDOC
    GETDOC --> SEL
    SEL --> START
    START --> SETUP
    START --> PARSE
    START --> ANALYSIS
    START --> GLOSSARY
    START --> CHKLOOP
    CHKLOOP --> CHUNK
    CHUNK --> CHAPTER
    CHAPTER --> ARC
    CHUNK --> ERR
    CHKLOOP --> SEND_PROC
    ARC --> CHKLOOP
    CHKLOOP -->|All Done| FINISH
    FINISH --> GDRIVE
    FINISH --> TGFILE
    FINISH --> ANNOT
    FINISH --> SEND_FINISH
    CHUNK --> LIGHTRAG
    CHAPTER --> LIGHTRAG
    ARC --> LIGHTRAG
    LIGHTRAG --> OLLAMA
    LIGHTRAG --> POLZA
    CHUNK --> POLZA
    CHUNK --> NEURO
    POSTEDIT --> POLZA
    POSTEDIT --> NEURO
    ANALYSIS --> POLZA
    GLOSSARY --> POLZA
    SETUP --> PG
    PARSE --> PG
    ANALYSIS --> PG
    CHUNK --> PG
    CHAPTER --> PG
    ARC --> PG
    SENDMSG --> SEND_CREATE
    SENDMSG --> SEND_WAIT
    SENDMSG --> SEND_PROC
    SENDMSG --> SEND_ERR
    SENDMSG --> SEND_FINISH
```

### 1.4 Statistics

| Metric | Value |
|--------|-------|
| Active Workflows | 34 |
| Database Tables (custom) | 12 |
| AI Providers | 2 (Polza.ai, Neuro API) |
| AI Models | 5 (GPT 5.2, GPT 5.3, Claude 4.5, Gemini 2.5 Flash Lite, gpt-5.4-nano) |
| External Services | 4 (Telegram, LightRAG, Google Drive, Ollama) |
| Fallback Chain Depth | 4 models |

---

## 2. Infrastructure

### 2.1 Docker Compose Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| **db** | postgres:16-alpine | 5432 | Primary database (n8n + application data) |
| **n8n** | n8nio/n8n:latest | 5678 (host) | Workflow orchestration engine |
| **pgadmin** | dpage/pgadmin4:latest | 127.0.0.1:5055 | Database administration UI |
| **node-exporter** | prom/node-exporter:latest | 9100 | Host metrics for Prometheus |
| **prometheus** | prom/prometheus:latest | 9090 | Metrics collection & storage |
| **backup-exporter** | python:3.11-alpine | 9199 | Backup monitoring metrics |
| **postgres-exporter** | prometheuscommunity/postgres-exporter:latest | 9187 | PostgreSQL metrics |

### 2.2 External Services (Not in Docker Compose)

| Service | URL/Port | Purpose |
|---------|----------|---------|
| **Caddy** | :80, :443 | Reverse proxy, TLS termination (systemd service on host) |
| **LightRAG** | http://localhost:9621 | Knowledge graph RAG API |
| **Ollama** | http://localhost:11434 | Embedding model (nomic-embed-text) |
| **Telegram Bot API** | https://api.telegram.org | Bot communication |
| **Polza.ai API** | https://api.polza.ai | AI models (GPT, Claude, Gemini) |
| **Neuro API** | https://api.neuro.ai | AI models (GPT, Claude) |
| **Google Drive API** | OAuth2 | File storage |

### 2.3 Network Configuration

- **n8n uses `network_mode: host`** -- runs directly on host network to access local proxy
- **HTTP Proxy**: `http://127.0.0.1:10808` (Xray/Hiddify) for external API calls
- **NO_PROXY**: `localhost,127.0.0.1,::1,192.168.1.124,bigalexn8n.ru,www.bigalexn8n.ru`
- **Domain**: `bigalexn8n.ru` -> Caddy reverse proxy -> `127.0.0.1:5678`

### 2.4 Key Environment Variables

```
N8N_ENCRYPTION_KEY=InqHY6REAuKYKYfnqDgmmcZGuSnLZJFl90
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=127.0.0.1
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n_database
N8N_HOST=bigalexn8n.ru
N8N_PROTOCOL=https
N8N_PORT=5678
WEBHOOK_URL=https://bigalexn8n.ru/
HTTP_PROXY=http://127.0.0.1:10808
HTTPS_PROXY=http://127.0.0.1:10808
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=168
```

### 2.5 Caddy Reverse Proxy Domains

| Domain | Backend | Auth |
|--------|---------|------|
| bigalexn8n.ru | 127.0.0.1:5678 (n8n) | None |
| grafana.bigalexn8n.ru | 127.0.0.1:3000 | None |
| pgadmin.bigalexn8n.ru | 127.0.0.1:5055 | None |
| prometheus.bigalexn8n.ru | 127.0.0.1:9090 | None |
| lightrag.bigalexn8n.ru | 127.0.0.1:9621 | None |
| ollama.bigalexn8n.ru | 127.0.0.1:11434 | BasicAuth |
| ai.bigalexn8n.ru | 127.0.0.1:8080 (Open WebUI) | None |
| firecrawl.bigalexn8n.ru | 127.0.0.1:3002 | BasicAuth (/admin) |
| search.bigalexn8n.ru | 127.0.0.1:8888 (SearXNG) | BasicAuth |
| cron.bigalexn8n.ru | 127.0.0.1:8001 | BasicAuth |
| docker.bigalexn8n.ru | 127.0.0.1:9000 (Portainer) | None |

### 2.6 Dependencies Graph

```mermaid
graph LR
    n8n[n8n :5678] --> PG[(PostgreSQL :5432)]
    n8n --> TG[Telegram API]
    n8n --> POLZA[Polza.ai API]
    n8n --> NEURO[Neuro API]
    n8n --> LIGHTRAG[LightRAG :9621]
    n8n --> GDRIVE[Google Drive API]
    LIGHTRAG --> OLLAMA[Ollama :11434]
    LIGHTRAG --> POLZA
    Caddy[Caddy :443] --> n8n
    Prometheus[Prometheus :9090] --> n8n
    Prometheus --> PG
    Prometheus --> NODE[node-exporter :9100]
    Prometheus --> PGEXP[postgres-exporter :9187]
```

---

## 3. Database Schema

### 3.1 Overview

All application data is stored in PostgreSQL database `n8n_database` (separate from n8n's internal tables). Connection: `postgresql://n8n_user:n8n_db_password@127.0.0.1:5432/n8n_database`

### 3.2 Entity Relationship Diagram

```mermaid
erDiagram
    document_jobs ||--o{ document_chunks : "contains"
    document_jobs ||--o{ document_glossary : "contains"
    document_jobs ||--o{ document_arcs : "contains"
    document_jobs ||--o{ document_chapters : "contains"
    document_jobs ||--o{ document_characters : "contains"
    document_jobs ||--o{ document_files : "contains"
    document_jobs ||--o{ document_log : "logs"
    document_chunks }o--|| document_chapters : "belongs to"
    telegram_send_message ||--o| document_jobs : "references"
    telegram_messages ||--|| telegram_chats : "from"
    translate_prompts ||--o{ document_jobs : "used by"
```

### 3.3 Table: document_jobs

**Purpose**: Master record for each translation job. Tracks lifecycle from file upload to completion.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Unique job identifier |
| `file_name` | TEXT | NOT NULL | Original filename |
| `status` | TEXT | NOT NULL | Job status: `pending`, `parsing`, `processing`, `done`, `error`, `waiting` |
| `chat_id` | BIGINT | NOT NULL | Telegram chat ID for notifications |
| `translate_file` | TEXT | | Path or reference to source file |
| `glossary_file` | TEXT | | Path to glossary file (user-provided) |
| `glossary_make` | TEXT | | Flag: auto-generate glossary |
| `book_prompt` | TEXT | | Custom book-specific prompt |
| `billing_neuro` | TEXT | | Neuro API billing/usage tracking |
| `billing_polza` | TEXT | | Polza.ai API billing/usage tracking |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Job creation time |
| `started_at` | TIMESTAMP | | When processing began |
| `finished_at` | TIMESTAMP | | When processing completed |
| `translated_file` | TEXT | | Path to translated output file |
| `web_view_link` | TEXT | | Google Drive shareable link |

**Status Transitions**:
```
pending -> parsing -> processing -> done
                     -> error
                     -> waiting (paused by user)
```

### 3.4 Table: document_chunks

**Purpose**: Individual text segments to be translated. The core unit of processing.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Unique chunk identifier |
| `job_id` | INTEGER | FK -> document_jobs(id) | Parent job |
| `chapter` | INTEGER | NOT NULL | Chapter number this chunk belongs to |
| `chunk_index` | INTEGER | NOT NULL | Position within chapter |
| `chunk_text` | TEXT | NOT NULL | Original Korean text |
| `result_text` | TEXT | | Translated Russian text (NULL until done) |
| `status` | TEXT | DEFAULT 'pending' | `pending`, `processing`, `done`, `error` |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Last modification time |

**Processing Order**: Chunks processed sequentially by `(chapter, chunk_index)` within each job.

### 3.5 Table: document_glossary

**Purpose**: Terminology dictionary -- Korean terms and their Russian translations, with gender information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Unique entry |
| `job_id` | INTEGER | FK -> document_jobs(id) | Parent job |
| `name` | TEXT | NOT NULL | Korean term/character name |
| `translate` | TEXT | NOT NULL | Russian translation |
| `gender` | TEXT | | Gender info (M/F/Unknown) -- used for Russian grammar |

### 3.6 Table: document_arcs

**Purpose**: Arc-level narrative units (groups of chapters). Each arc has a rolling summary for context.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Unique arc |
| `job_id` | INTEGER | FK -> document_jobs(id) | Parent job |
| `arc_number` | INTEGER | NOT NULL | Arc sequence number |
| `summary` | TEXT | | Rolling summary of entire arc (used as context for translation) |

### 3.7 Table: document_chapters

**Purpose**: Chapter-level organization within arcs.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Unique chapter |
| `job_id` | INTEGER | FK -> document_jobs(id) | Parent job |
| `chapter` | TEXT | | Chapter identifier |
| `chapter_number` | INTEGER | NOT NULL | Chapter sequence number |
| `roller_summary` | TEXT | | Rolling summary of chapter (accumulated as chunks are translated) |

### 3.8 Table: document_characters

**Purpose**: Named character entities extracted from the document.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Unique character |
| `job_id` | INTEGER | FK -> document_jobs(id) | Parent job |
| `name` | TEXT | NOT NULL | Character name (Korean) |
| `description` | TEXT | | Character description/role |

### 3.9 Table: document_files

**Purpose**: Binary file storage (files stored as bytea).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Unique file record |
| `job_id` | INTEGER | FK -> document_jobs(id) | Parent job |
| `source` | TEXT | | File source/origin |
| `translate_file` | BYTEA | | Original document binary |
| `glossary` | BYTEA | | Glossary file binary |
| `prompt` | BYTEA | | Book prompt binary |
| `post_prompt` | BYTEA | | Post-production prompt binary |

### 3.10 Table: document_log

**Purpose**: Execution log for debugging and audit trail.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Unique log entry |
| `job_id` | INTEGER | FK -> document_jobs(id) | Parent job |
| `date_time` | TIMESTAMP | DEFAULT NOW() | Log timestamp |
| `node` | TEXT | | Workflow node name that generated the log |
| `type` | TEXT | | Log type (info, error, warning) |
| `log` | TEXT | | Log message content |

### 3.11 Table: telegram_messages

**Purpose**: Incoming Telegram message storage.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Unique message |
| `chat_id` | BIGINT | NOT NULL | Sender chat ID |
| `message_id` | BIGINT | | Telegram message ID |
| `text` | TEXT | | Message text content |
| `file_id` | TEXT | | Telegram file ID (for documents) |
| `file_path` | TEXT | | Downloaded file path |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Message receipt time |

### 3.12 Table: telegram_send_message

**Purpose**: Outbound message queue. n8n workflows INSERT rows; the Send Message workflow triggers on new rows via postgresTrigger.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Unique message |
| `chat_id` | BIGINT | NOT NULL | Target chat ID |
| `message` | TEXT | NOT NULL | Message text to send |
| `template` | TEXT | | Message template type: `create_job`, `wait`, `processing`, `error`, `finish` |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Queue time |

### 3.13 Table: telegram_chats

**Purpose**: Authorized chat registry for the Telegram bot.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Unique chat |
| `chat_id` | BIGINT | NOT NULL UNIQUE | Telegram chat ID |
| `username` | TEXT | | Telegram username |
| `first_name` | TEXT | | User's first name |
| `authorized` | BOOLEAN | DEFAULT false | Whether this chat can use the bot |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Registration time |

### 3.14 Table: translate_prompts

**Purpose**: System prompts for translation agents. Editable via n8n workflows.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Unique prompt |
| `agent_name` | TEXT | NOT NULL | Agent identifier: `BP Default`, `BP BL`, `PP Default` |
| `prompt_text` | TEXT | NOT NULL | The actual prompt content |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Last modification time |

---

## 4. Complete Workflow Catalog

### 4.1 Workflow Categories

| Category | Count | Workflows |
|----------|-------|-----------|
| Translation Pipeline (core) | 6 | Start, Translate Chunk, [Перевод] Перевод чанка, [Перевод] Глава, [Перевод] Арка, [Перевод] Обработка ошибки |
| File Processing | 5 | [GET] Document, [GET] /select_files, Парсинг файла, Предварительный анализ, Ручной выбор файлов |
| Telegram Messaging (output) | 6 | Send Message, [Send] create_job, [Send] wait, [Send] processing, [Send] error, [Send] finish |
| Telegram Input | 2 | Получение сообщения, Select From List |
| Glossary & Prompts | 5 | Создание Глоссария, Добавление Глоссария, Добавление Промта, Добавление промта для постредакта, Постредактура |
| Database & Utils | 7 | Настройка БД, Добавление ресурсов в бд, sub_lightrag_api, Переведенный файл в Google Drive, Переведенный файл в Telegram, Анотация, Перезапуск прослушки Telegram |
| System | 2 | Global Error Handler, [Book Translation] Activate [NOT USED] |
| Finish | 1 | Finish |

---

### 4.2 Translation Pipeline (Core)

#### 4.2.1 Start (ID: 9cjeUNeTZX3YnO1W57YTP)

**Nodes**: 21 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Main orchestrator workflow. Validates inputs, checks billing, and calls all sub-workflows in sequence.

**Execution Flow**:
1. **Input Validation** -- checks for required files: `translate_file`, `glossary_file`, `glossary_make`, `book_prompt`, `post_production`
2. **Billing Check (Polza.ai)** -- queries Polza.ai API for remaining credits/balance
3. **Billing Check (Neuro)** -- queries Neuro API for remaining credits/balance
4. **Glossary Check** -- if no glossary provided, triggers **Создание Глоссария** workflow
5. **Prompt Check** -- validates book prompt availability
6. **Post-production Prompt Check** -- validates post-editing prompt availability
7. **Call: Настройка БД** -- initializes database records for the job
8. **Call: Парсинг файла** -- converts document to text and splits into chunks
9. **Call: Предварительный анализ** -- detects chapter/arc structure, creates DB records
10. **Merge Step** -- merges parsed text with analysis results
11. **Call: Translate Chunk (ExecuteWorkflow)** -- starts the chunk translation loop

**Inputs**:
- `job_id` (from calling workflow)
- `translate_file` (file path or reference)
- `glossary_file` (optional, user-provided glossary)
- `glossary_make` (flag to auto-generate)
- `book_prompt` (custom translation prompt)
- `post_production` (post-editing flag)

**Outputs**:
- Initiates Translate Chunk loop
- All DB records created

**Connections**:
- -> Настройка БД
- -> Парсинг файла
- -> Предварительный анализ
- -> Translate Chunk (ExecuteWorkflow)
- -> Создание Глоссария (conditional)

---

#### 4.2.2 Translate Chunk (ID: Q5TRHGg-XRblnMRpH41Ee)

**Nodes**: 17 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Chunk processing loop controller. Iterates through all pending chunks, calling translation sub-workflows and managing chapter/arc updates.

**Execution Flow** (loop):
1. **Select Next Chunk** -- SQL query: `SELECT * FROM document_chunks WHERE job_id = ? AND status = 'pending' ORDER BY chapter, chunk_index LIMIT 1`
2. **Call: [Перевод] Перевод чанка** -- translate the selected chunk
3. **Check Translation Success** -- if error, log and handle
4. **Call: [Перевод] Глава** -- update chapter context after chunk translation
5. **Check: New Chapter?** -- if chunk starts new chapter, create chapter record
6. **Call: [Перевод] Арка** -- update arc context if arc boundary detected
7. **Send Progress Notification** -- INSERT into `telegram_send_message` with template `processing`
8. **Loop Check** -- if more pending chunks, go to step 1; else proceed to Finish

**Inputs**:
- `job_id`
- Chunk queue state from `document_chunks` table

**Outputs**:
- All chunks translated (`status = 'done'`)
- Chapter and arc summaries updated
- Progress notifications sent

**Connections**:
- -> [Перевод] Перевод чанка
- -> [Перевод] Глава
- -> [Перевод] Арка
- -> [Send] processing (via DB trigger)
- -> Finish (when all done)
- -> [Перевод] Обработка ошибки (on error)

---

#### 4.2.3 [Перевод] Перевод чанка (ID: GPARI8V4RBSPL1h39_kHW)

**Nodes**: 34 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Core translation engine. Translates a single chunk using AI with glossary, context, and RAG support.

**Execution Flow**:
1. **Read Glossary from DB** -- `SELECT name, translate, gender FROM document_glossary WHERE job_id = ?`
2. **Read Prompts from DB** -- `SELECT prompt_text FROM translate_prompts WHERE agent_name = 'BP Default'`
3. **Read Rolling Summary** -- get chapter rolling summary from `document_chapters`
4. **Read Current Arc** -- get arc summary from `document_arcs`
5. **Query LightRAG** -- call `sub_lightrag_api` with chunk text for semantic context retrieval
6. **Build Translation Prompt** -- combine: system prompt + glossary + arc summary + chapter summary + LightRAG context + chunk text
7. **Translate with AI Cascade** (LangChain Agent):
   - **Primary**: GPT 5.2 via Polza.ai
   - **Fallback 1**: GPT 5.2 via Neuro API
   - **Fallback 2**: Claude 4.5 via Neuro API
   - **Fallback 3**: Claude 4.5 via Polza.ai
8. **Forbidden Words Check** -- validate output against list of forbidden/incorrect terms
9. **Optional Post-Production** -- if enabled, call **Постредактура** workflow:
   - Post-edit with GPT 5.3 (Polza.ai) or GPT-5.2 (Neuro API)
   - Tools: `text_validator`, `parentheses` checker
10. **Save Result to DB** -- `UPDATE document_chunks SET result_text = ?, status = 'done' WHERE id = ?`
11. **Log Execution** -- INSERT into `document_log`

**Inputs**:
- `chunk_id`
- `chunk_text` (Korean)
- `job_id`
- `chapter` number
- `arc_number`

**Outputs**:
- `result_text` (Russian) saved to `document_chunks`
- Execution logs in `document_log`

**Connections**:
- -> sub_lightrag_api (LightRAG query)
- -> Постредактура (conditional)
- -> document_chunks (save result)
- -> document_log (logging)

---

#### 4.2.4 [Перевод] Глава (ID: IgLfaCSszdwsPw_b4u3au)

**Nodes**: 26 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Chapter management. Maintains rolling chapter summary and saves chapter content to LightRAG when complete.

**Execution Flow**:
1. **Select All Translated Chunks** -- `SELECT * FROM document_chunks WHERE job_id = ? AND chapter = ? AND status = 'done'`
2. **Read Glossary from DB** -- for consistent terminology in summary
3. **Generate Chapter Summary** -- AI call: Gemini 2.5 Flash Lite (Polza.ai)
4. **Update Rolling Summary** -- append new chunk to chapter's rolling summary
5. **Check: All Chunks in Chapter Done?** -- `SELECT COUNT(*) FROM document_chunks WHERE job_id = ? AND chapter = ? AND status != 'done'`
6. **If All Done**:
   - Create comprehensive chapter summary with AI
   - Save chapter summary to LightRAG via `sub_lightrag_api`
   - Update `document_chapters.roller_summary`
7. **Update Chapter Status**

**Inputs**:
- `job_id`
- `chapter_number`
- Newly translated chunk text

**Outputs**:
- Updated `document_chapters.roller_summary`
- Chapter summary in LightRAG (when complete)

**Connections**:
- -> sub_lightrag_api (save chapter summary)
- -> document_chapters (update summary)

---

#### 4.2.5 [Перевод] Арка (ID: OggkJgA8IFmasME_BNimq)

**Nodes**: 31 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Arc management. Detects arc boundaries, maintains rolling arc summary, and saves arc content to LightRAG.

**Execution Flow**:
1. **Determine Arc Boundaries** -- AI call: Gemini 2.5 Flash Lite (Polza.ai) analyzes if current chunk crosses arc boundary
2. **If New Arc Detected**:
   - Create new arc record in `document_arcs`
   - Initialize new arc summary
3. **Update Rolling Summary** -- append current chapter content to arc's rolling summary via Gemini 2.5 Flash Lite
4. **Save to LightRAG** -- INSERT arc summary via `sub_lightrag_api`
5. **Update Arc Status** -- `UPDATE document_arcs SET summary = ? WHERE id = ?`

**Inputs**:
- `job_id`
- `arc_number`
- Current chapter summary

**Outputs**:
- Updated `document_arcs.summary`
- Arc summary in LightRAG
- New arc records created when boundaries detected

**Connections**:
- -> sub_lightrag_api (save arc summary)
- -> document_arcs (update/create)

---

#### 4.2.6 [Перевод] Обработка ошибки (ID: ImJpqAA5WlJZDK5jMtQSM)

**Nodes**: 14 | **Trigger**: Error Trigger

**Purpose**: Handles translation errors at the chunk level. Logs errors, updates chunk status, and decides whether to retry or skip.

**Execution Flow**:
1. **Capture Error** -- receives error event from parent workflow
2. **Log Error** -- INSERT into `document_log` with error details
3. **Update Chunk Status** -- `UPDATE document_chunks SET status = 'error' WHERE id = ?`
4. **Update Job Status** -- optionally update `document_jobs.status = 'error'`
5. **Send Error Notification** -- INSERT into `telegram_send_message` with template `error`
6. **Decision**: retry or skip based on error type

**Inputs**:
- Error event data (error message, node name, chunk info)

**Outputs**:
- Error logged in `document_log`
- Error notification sent to Telegram
- Chunk marked as `error`

---

### 4.3 File Processing Workflows

#### 4.3.1 [GET] Document (ID: sLo74sUgMdcJEmxJoRJQ-)

**Nodes**: 14 | **Trigger**: Webhook

**Purpose**: Downloads file from Telegram and converts document formats (DOCX, TXT, XLSX) to plain text.

**Execution Flow**:
1. **Receive Webhook** -- HTTP GET with file_id or document reference
2. **Download from Telegram** -- use Telegram Bot API to download file
3. **Detect Format** -- check file extension (docx, txt, xlsx)
4. **Convert to Text**:
   - DOCX: extract text from Office Open XML
   - TXT: read directly
   - XLSX: extract text from cells
5. **Save to DB** -- store text in `document_files` or temporary storage
6. **Return Text** -- output plain text for downstream processing

**Inputs**:
- `file_id` (Telegram file ID)
- Or file path reference

**Outputs**:
- Plain text content (Korean)
- File metadata (format, size)

---

#### 4.3.2 [GET] /select_files (ID: MmfiOXrCt2lkZ4TxZMyWS)

**Nodes**: 72 | **Trigger**: Webhook + Form

**Purpose**: Interactive file selection UI via Telegram inline buttons. Allows user to choose source file, glossary, prompts, and settings.

**Execution Flow**:
1. **Display File List** -- show available files from DB
2. **User Selects Source File** -- inline button callback
3. **User Selects Glossary** -- choose existing or create new
4. **User Selects Book Prompt** -- choose existing or custom
5. **User Configures Settings** -- post-production on/off, glossary auto-generation
6. **Validate Selection** -- check all required fields present
7. **Submit to Start Workflow** -- call Start workflow with selected parameters

**Inputs**:
- User selections via inline buttons
- Callback data from Telegram

**Outputs**:
- Configuration object for Start workflow
- All required file references

---

#### 4.3.3 Парсинг файла для перевода (ID: bC43bgf5ZtXoi_XDLDwHO)

**Nodes**: 10 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Splits document text into chunks for processing.

**Execution Flow**:
1. **Read Document Text** -- from DB or file
2. **Split into Chunks** -- chunk by character count (~4-8K tokens per chunk)
3. **Save Chunks to DB** -- INSERT into `document_chunks` with `status = 'pending'`
4. **Return Chunk Count** -- for progress tracking

**Inputs**:
- Plain text document (Korean)
- `job_id`

**Outputs**:
- Multiple rows in `document_chunks` (status: pending)
- Total chunk count

---

#### 4.3.4 Предварительный анализ файла для перевода (ID: lSuNRX0VILP9Lgit5VKlK)

**Nodes**: 27 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Pre-analysis of document structure. Detects chapters, arcs, characters, and creates corresponding DB records.

**Execution Flow**:
1. **Read File Text from DB** -- get the full document text
2. **Split for Structural Analysis** -- divide into sections for AI analysis
3. **Information Extractor** -- AI call: Gemini 2.5 Flash Lite (Polza.ai), fallback: OpenAI (Polza.ai)
   - Detect chapter boundaries
   - Detect arc boundaries
   - Extract character names
4. **Create Chapter Records** -- INSERT into `document_chapters`
5. **Create First Arc** -- INSERT into `document_arcs`
6. **Create Character Records** -- INSERT into `document_characters`
7. **Send Start Notification** -- INSERT into `telegram_send_message` template `create_job`
8. **Send Progress Notification** -- initial progress message

**Inputs**:
- Plain text document
- `job_id`

**Outputs**:
- Chapter records in `document_chapters`
- Arc records in `document_arcs`
- Character records in `document_characters`
- Start notification sent

---

#### 4.3.5 Ручной выбор файлов (ID: AnPEATb8u6yyFa54)

**Nodes**: 30 | **Trigger**: Manual

**Purpose**: Manual file selection workflow for edge cases or debugging.

---

### 4.4 Telegram Messaging (Output)

#### 4.4.1 Send Message (ID: J62UViXZMD5o6qoU)

**Nodes**: 12 | **Trigger**: postgresTrigger (on INSERT into `telegram_send_message`)

**Purpose**: Central notification dispatcher. Routes messages to appropriate formatter workflows based on template type.

**Execution Flow**:
1. **Trigger on DB INSERT** -- postgresTrigger fires when new row in `telegram_send_message`
2. **Read Message Data** -- get `chat_id`, `message`, `template` from triggered row
3. **Route by Template**:
   - `create_job` -> **[Send] create_job**
   - `wait` -> **[Send] wait**
   - `processing` -> **[Send] processing**
   - `error` -> **[Send] error**
   - `finish` -> **[Send] finish**
4. **Send to Telegram** -- use Telegram node to send/edit message

**Inputs**:
- `telegram_send_message` row (via postgresTrigger)

**Outputs**:
- Telegram message sent or edited

---

#### 4.4.2 [Send] create_job (ID: ScNLD3LbRTVAJOK4)

**Nodes**: 8 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Send "job created" notification.

**Message Format**: New job confirmation with filename.

---

#### 4.4.3 [Send] wait (ID: OWLYY2oiQ6YPBJ7M)

**Nodes**: 10 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Send "translation paused" notification with resume button, polls for resume action.

**Features**:
- Inline button for resume
- Polls for user response
- Updates job status on resume

---

#### 4.4.4 [Send] processing (ID: 9uUyj9OamISRPudJ)

**Nodes**: 13 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Send/edit progress message with chunk completion statistics and billing info.

**Message Format**:
- Progress bar: `[=====>    ] 50%`
- Chunks done / total: `5/10 chunks`
- Billing info: Polza.ai + Neuro usage

**Features**: Idempotent -- edits existing message instead of sending new one.

---

#### 4.4.5 [Send] error (ID: 2uhp8PCTjxiKj91n)

**Nodes**: 5 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Send error notification with error details.

---

#### 4.4.6 [Send] finish (ID: hoUl3ewz23AwAHlq)

**Nodes**: 19 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Send completion notification with full statistics, annotation, and billing summary.

**Message Format**:
- Completion confirmation
- Translation statistics (chunks translated, time elapsed)
- Annotation summary
- Billing breakdown (Polza.ai + Neuro usage)
- Google Drive link (if applicable)

---

### 4.5 Telegram Input

#### 4.5.1 Получение сообщения (ID: CHSGtgO88LgGVbV8)

**Nodes**: 8 | **Trigger**: Webhook

**Purpose**: Webhook handler for incoming Telegram messages. Routes to Document processing or resource addition workflows.

**Execution Flow**:
1. **Receive Webhook** -- Telegram sends update to n8n webhook URL
2. **Validate Message** -- check chat_id is authorized
3. **Route by Message Type**:
   - File/Document -> **[GET] Document** workflow
   - Text/Command -> **Добавление ресурсов** workflow
4. **Save to DB** -- INSERT into `telegram_messages`

**Inputs**:
- Telegram webhook payload (Update object)

**Outputs**:
- Message saved in `telegram_messages`
- Routed to appropriate workflow

---

#### 4.5.2 Select From List (ID: CJ7lDvgGlmoP8Ymbgqd0A)

**Nodes**: 10 | **Trigger**: Callback

**Purpose**: Handles inline button callbacks from Telegram. Waits for user selection from interactive lists.

**Execution Flow**:
1. **Receive Callback** -- inline button callback_data
2. **Parse Selection** -- extract selected item from callback
3. **Wait for User** -- if multi-step, wait for additional input
4. **Return Selection** -- pass selected item to calling workflow

---

### 4.6 Glossary & Prompts

#### 4.6.1 Создание Глоссария (ID: t8Dmavjx9KS5Ms3SB3Qdj)

**Nodes**: 17 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: AI-generated glossary from document text. Extracts character names, terms, and their translations.

**Execution Flow**:
1. **Read Document Text**
2. **Extract Terms** -- AI call to extract Korean terms
3. **Translate Terms** -- AI call for Russian translations
4. **Determine Gender** -- AI identifies gender for character names
5. **Save to DB** -- INSERT into `document_glossary`

**Outputs**:
- Glossary entries in `document_glossary`

---

#### 4.6.2 Добавление Глоссария (ID: ZdsvkMfRDAU4yLbL3DPcK)

**Nodes**: 9 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Add user-provided glossary to DB.

---

#### 4.6.3 Добавление Промта (ID: TVHpHR7HlCdrqEvAF3WNP)

**Nodes**: 10 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Add book-specific prompt to `translate_prompts` table.

---

#### 4.6.4 Добавление промта для постредакта (ID: FuVQL0O5ik3aocbx)

**Nodes**: 10 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Add post-production (post-editing) prompt to DB.

---

#### 4.6.5 Постредактура (ID: A8zKJVQgROH1cnkv)

**Nodes**: 9 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: AI post-editing of translated text. Improves quality after initial translation.

**Execution Flow**:
1. **Read Translated Text** -- from chunk result
2. **Read Post-Production Prompt** -- from DB
3. **Post-Edit with AI**:
   - Primary: GPT 5.3 (Polza.ai)
   - Fallback: GPT-5.2 (Neuro API)
   - Tools: `text_validator`, `parentheses` checker
4. **Save Improved Text** -- update `document_chunks.result_text`

**Inputs**:
- Translated chunk text (Russian)
- Post-production prompt

**Outputs**:
- Improved translated text

---

### 4.7 Database & Utils

#### 4.7.1 Настройка БД (ID: UnqVdfxubclgfA7tafBwo)

**Nodes**: 8 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Database initialization for new translation job.

**Execution Flow**:
1. **Create Job Record** -- INSERT into `document_jobs` with `status = 'pending'`
2. **Initialize Related Tables** -- ensure all FK relationships ready
3. **Return Job ID** -- for downstream workflows

---

#### 4.7.2 Добавление ресурсов в бд (ID: rlk5lgq3uE4N0yl0)

**Nodes**: 23 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Add resources (files, glossary, prompts) to database.

---

#### 4.7.3 sub_lightrag_api (ID: AW58nseQdLtJn5ZO)

**Nodes**: 5 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: LightRAG API wrapper. Handles query and insert operations.

**Operations**:
- **Query**: POST to `http://localhost:9621` with chunk text, returns semantic context
- **Insert**: POST to `http://localhost:9621` with chapter/arc summary for indexing

**Inputs**:
- `operation` (query/insert)
- `text` (content to query or insert)
- `labels` (metadata tags)

**Outputs**:
- LightRAG API response (JSON)

---

#### 4.7.4 Переведенный файл в Google Drive (ID: KebWQcS1WmNtgdgA)

**Nodes**: 11 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Upload translated file to Google Drive and get shareable link.

---

#### 4.7.5 Переведенный файл в Telegram (ID: sv73wrV6anQE7cTv)

**Nodes**: 9 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Send translated file directly to user via Telegram.

---

#### 4.7.6 Анотация (ID: 2kztTVutdATd1MDS)

**Nodes**: 7 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Generate book annotation including summary, cover image prompt, and cover image.

**Execution Flow**:
1. **Summarize Book** -- AI call (OpenAI via Polza.ai)
2. **Generate Cover Image Prompt** -- AI call for image description
3. **Generate Cover Image** -- HTTP request to image generation API

**Outputs**:
- Book summary text
- Cover image
- Annotation for completion message

---

#### 4.7.7 Перезапуск прослушки Telegram (ID: GiqH3FrsgKjwIbUfcS6-j)

**Nodes**: 4 | **Trigger**: Manual

**Purpose**: Restart Telegram webhook listener when connection issues occur.

---

### 4.8 Finish Workflow

#### 4.8.1 Finish (ID: vuqLp6ZGenvpkJbmVPR_6)

**Nodes**: 10 | **Trigger**: ExecuteWorkflowTrigger

**Purpose**: Final cleanup and file delivery after all chunks are translated.

**Execution Flow**:
1. **Clear Binary Data from DB** -- remove temporary binary data from `document_files`
2. **Generate Annotation** -- call **Анотация** workflow
3. **Upload to Google Drive** -- call **Переведенный файл в Google Drive** (if configured)
4. **Send via Telegram** -- call **Переведенный файл в Telegram** (if configured)
5. **Update Job Status** -- `UPDATE document_jobs SET status = 'done', finished_at = NOW(), translated_file = ?`
6. **Send Completion Notification** -- INSERT into `telegram_send_message` template `finish`
7. **Log Completion** -- INSERT into `document_log`

---

### 4.9 System

#### 4.9.1 Global Error Handler

**Nodes**: 2 | **Trigger**: Error Trigger (global)

**Purpose**: Catches unhandled errors from all workflows. Logs and notifies.

#### 4.9.2 [Book Translation] Activate Translation Workflows [NOT USED]

**Nodes**: 5 | **Trigger**: Manual

**Purpose**: Self-deactivating workflow. Previously used for batch activation.

---

## 5. Data Flow: Korean Text to Russian Text

### 5.1 Complete Pipeline (Step by Step)

```mermaid
sequenceDiagram
    participant User
    participant TG as Telegram Bot
    participant Web as Получение сообщения
    participant GetDoc as [GET] Document
    participant Sel as [GET] /select_files
    participant Start as Start Workflow
    participant DB as Настройка БД
    participant Parse as Парсинг файла
    participant Analysis as Предварительный анализ
    participant Loop as Translate Chunk Loop
    participant Chunk as [Перевод] Перевод чанка
    participant Lightrag as LightRAG
    participant AI as AI Provider
    participant Chapter as [Перевод] Глава
    participant Arc as [Перевод] Арка
    participant Notify as Send Message
    participant Finish as Finish Workflow
    participant GDrive as Google Drive
    participant PG as PostgreSQL

    User->>TG: Send document file
    TG->>Web: Webhook: message with file
    Web->>GetDoc: Route: file detected
    GetDoc->>TG: Download file by file_id
    GetDoc->>GetDoc: Convert DOCX/TXT/XLSX to text
    GetDoc->>PG: Save text to document_files

    GetDoc->>Sel: Route to file selection
    Sel->>User: Show inline buttons: file, glossary, prompt
    User->>Sel: Select file + glossary + prompt + settings
    Sel->>Start: Call with configuration

    Start->>Start: Check billing (Polza.ai + Neuro)
    Start->>Start: Validate inputs
    alt No glossary provided
        Start->>Start: Call Создание Глоссария
    end
    Start->>DB: Initialize job in DB
    DB->>PG: INSERT document_jobs (status=pending)
    DB->>Start: Return job_id

    Start->>Parse: Split document into chunks
    Parse->>PG: INSERT document_chunks (status=pending)
    Parse->>Start: Return chunk count

    Start->>Analysis: Detect structure
    Analysis->>AI: Gemini 2.5: detect chapters, arcs, characters
    Analysis->>PG: INSERT document_chapters
    Analysis->>PG: INSERT document_arcs
    Analysis->>PG: INSERT document_characters
    Analysis->>Notify: INSERT telegram_send_message (create_job)
    Notify->>User: "Job created: filename.ko"

    Start->>Loop: Begin chunk translation

    loop For each chunk (chapter, chunk_index)
        Loop->>PG: SELECT next pending chunk
        Loop->>Chunk: Translate chunk
        Chunk->>PG: Read glossary for job
        Chunk->>PG: Read prompts for job
        Chunk->>PG: Read chapter rolling summary
        Chunk->>PG: Read arc summary
        Chunk->>Lightrag: Query semantic context
        Lightrag->>Lightrag: Graph + vector search
        Lightrag->>Chunk: Return context
        Chunk->>Chunk: Build prompt (system + glossary + context + chunk)
        Chunk->>AI: Translate (GPT 5.2 Polza.ai)
        alt Primary fails
            Chunk->>AI: Fallback 1: GPT 5.2 Neuro
        end
        alt Fallback 1 fails
            Chunk->>AI: Fallback 2: Claude 4.5 Neuro
        end
        alt Fallback 2 fails
            Chunk->>AI: Fallback 3: Claude 4.5 Polza.ai
        end
        AI->>Chunk: Return Russian translation
        Chunk->>Chunk: Check forbidden words
        alt Post-production enabled
            Chunk->>Chunk: Call Постредактура
            Chunk->>AI: Post-edit (GPT 5.3 Polza.ai)
            AI->>Chunk: Return improved text
        end
        Chunk->>PG: UPDATE document_chunks (result_text, status=done)

        Loop->>Chapter: Update chapter context
        Chapter->>AI: Gemini 2.5: rolling summary
        Chapter->>PG: UPDATE document_chapters.roller_summary
        alt Chapter complete
            Chapter->>AI: Full chapter summary
            Chapter->>Lightrag: Insert chapter summary
        end

        Loop->>Arc: Update arc context
        Arc->>AI: Gemini 2.5: check arc boundary
        Arc->>AI: Gemini 2.5: rolling summary
        Arc->>PG: UPDATE document_arcs.summary
        Arc->>Lightrag: Insert arc summary

        Loop->>Notify: INSERT telegram_send_message (processing)
        Notify->>User: Edit progress: "5/10 chunks [=====>    ] 50%"
    end

    Loop->>Finish: All chunks done

    Finish->>Finish: Clear binary data from DB
    Finish->>Finish: Call Анотация
    Finish->>AI: Summarize book
    Finish->>AI: Generate cover image
    Finish->>GDrive: Upload translated file
    GDrive->>Finish: Return shareable link
    Finish->>PG: UPDATE document_jobs (status=done, translated_file, web_view_link)
    Finish->>Notify: INSERT telegram_send_message (finish)
    Notify->>User: "Translation complete! Stats + Drive link"
```

### 5.2 Intermediate Data States

| Stage | document_jobs.status | document_chunks | document_chapters | document_arcs | LightRAG |
|-------|---------------------|-----------------|-------------------|---------------|----------|
| **File received** | `pending` | Empty | Empty | Empty | Empty |
| **After parsing** | `parsing` | N rows, `pending` | Empty | Empty | Empty |
| **After analysis** | `processing` | N rows, `pending` | M chapters created | 1 arc created | Empty |
| **Chunk N translated** | `processing` | N rows `done`, rest `pending` | Chapter summary updated | Arc summary updated | N chunks indexed |
| **Chapter complete** | `processing` | All chapter chunks `done` | Full summary, LightRAG indexed | Arc summary updated | Chapter summary indexed |
| **Arc complete** | `processing` | All arc chunks `done` | All chapters summarized | Full summary, LightRAG indexed | Arc summary indexed |
| **All done** | `done` | All `done` | All summarized | All summarized | Full book indexed |
| **Error** | `error` | Some `error` | Partial | Partial | Partial |

### 5.3 Chunk Translation Detail

```
Input (Korean chunk):
  "그는 문을 열고 방 안으로 들어갔다. 방안은 어두웠지만 창문으로 들어오는 달빛이 바닥을 비추고 있었다."

Context gathered:
  - Glossary: {그: he/him (M), 문: door, 방: room}
  - Chapter Rolling Summary: "Protagonist enters abandoned building..."
  - Arc Summary: "First arc: protagonist explores the mysterious mansion..."
  - LightRAG Context: "Similar scene in chapter 2: dark room, moonlight..."

AI Prompt:
  System: "You are a professional Korean-Russian translator..."
  Glossary: "Use these terms: 그 -> он, 문 -> дверь, 방 -> комната"
  Context: "Chapter summary: ...\nArc summary: ...\nRAG context: ..."
  Chunk: "그는 문을 열고 방 안으로 들어갔다..."

Output (Russian):
  "Он открыл дверь и вошёл в комнату. В комнате было темно, но лунный свет, проникавший через окно, освещал пол."

Saved to: document_chunks.result_text
```

---

## 6. Telegram Bot Interaction Flow

### 6.1 User Journey

```mermaid
sequenceDiagram
    participant U as User
    participant B as Telegram Bot
    participant W as Webhook
    participant N as n8n
    participant DB as PostgreSQL

    Note over U,DB: Phase 1: File Upload
    U->>B: Send document file (.docx/.txt/.xlsx)
    B->>W: POST /webhook/telegram (Update with document)
    W->>N: Получение сообщения workflow
    N->>B: Download file via Telegram API
    N->>DB: Save to telegram_messages

    Note over U,DB: Phase 2: File Selection & Configuration
    N->>U: Inline buttons: Select file, glossary, prompt
    U->>B: Click "Select File" button
    B->>W: callback_query
    W->>N: Select From List workflow
    N->>U: Show file list as inline buttons
    U->>B: Select source file
    N->>U: "Add glossary?" (Yes/No)
    alt Yes
        U->>B: Upload glossary file
    end
    N->>U: "Add book prompt?" (Yes/No)
    alt Yes
        U->>B: Upload prompt file
    end
    N->>U: "Enable post-production?" (Yes/No)
    U->>B: Click Yes/No

    Note over U,DB: Phase 3: Translation Starts
    N->>U: "Job created: filename.ko" (create_job)
    N->>U: "Analysis in progress..." (processing 0%)

    Note over U,DB: Phase 4: Progress Updates
    loop Every chunk translated
        N->>U: Edit message: "3/10 chunks [===>      ] 30%" (processing)
    end

    Note over U,DB: Phase 5: Completion
    N->>U: "Translation complete! Stats: 10 chunks, 2.5 hours. Billing: X tokens" (finish)
    N->>U: Send translated file (.txt/.docx)
    N->>U: Google Drive link: "https://drive.google.com/..."

    Note over U,DB: Optional: Pause/Resume
    U->>B: Send /pause command
    N->>U: "Translation paused. [Resume]" (wait)
    U->>B: Click "Resume" button
    N->>U: "Translation resumed" (processing)
```

### 6.2 Message Templates

| Template | When Sent | Content |
|----------|-----------|---------|
| `create_job` | After file analysis | "New job created: {filename}. {chunk_count} chunks detected." |
| `processing` | After each chunk | "{done}/{total} chunks [{progress_bar}] {percent}%. Billing: Polza {X}, Neuro {Y}" |
| `wait` | When user pauses | "Translation paused. Click Resume to continue." + [Resume] button |
| `error` | On translation error | "Error processing {filename}: {error_message}" |
| `finish` | After all chunks done | "Translation complete! Stats: {chunks} chunks, {time} elapsed. Billing: {breakdown}. File: {link}" |

### 6.3 Inline Button Callbacks

| Button | Callback Data | Action |
|--------|--------------|--------|
| Select File | `select_file:{file_id}` | Open file selection |
| Glossary: Use Existing | `glossary:{id}` | Use existing glossary |
| Glossary: Create New | `glossary_create` | Trigger Создание Глоссария |
| Prompt: Use Existing | `prompt:{id}` | Use existing prompt |
| Post-production: Yes | `post_edit:true` | Enable post-production |
| Post-production: No | `post_edit:false` | Skip post-production |
| Resume | `resume:{job_id}` | Resume paused translation |

---

## 7. AI Models & Prompts

### 7.1 Model Inventory

| # | Model | Provider | Purpose | When Used | Fallback Order |
|---|-------|----------|---------|-----------|----------------|
| 1 | **GPT 5.2** | Polza.ai | **Primary translation** | Chunk translation (step 7a) | 1st |
| 2 | **GPT 5.2** | Neuro API | Fallback translation | Chunk translation (step 7b) | 2nd |
| 3 | **Claude 4.5** | Neuro API | Fallback translation | Chunk translation (step 7c) | 3rd |
| 4 | **Claude 4.5** | Polza.ai | Fallback translation | Chunk translation (step 7d) | 4th |
| 5 | **GPT 5.3** | Polza.ai | Post-production editing | Post-editing (if enabled) | Primary |
| 6 | **GPT-5.2** | Neuro API | Post-production fallback | Post-editing fallback | Fallback |
| 7 | **Gemini 2.5 Flash Lite** | Polza.ai | Structural analysis | Pre-analysis (chapter/arc detection) | Primary |
| 8 | **OpenAI (fallback)** | Polza.ai | Structural analysis fallback | Pre-analysis | Fallback |
| 9 | **Gemini 2.5 Flash Lite** | Polza.ai | Chapter/arc summaries | Summary generation | Only |
| 10 | **gpt-5.4-nano** | Polza.ai | LightRAG LLM | RAG query responses | Only |
| 11 | **OpenAI** | Polza.ai | Book annotation | Final annotation summary | Only |
| 12 | **OpenAI** | Polza.ai | Cover image prompt | Cover image generation | Only |

### 7.2 Fallback Strategy (Chunk Translation)

```mermaid
graph TD
    A[Start Translation] --> B{GPT 5.2 Polza.ai}
    B -->|Success| C[Check Forbidden Words]
    B -->|Fail| D{GPT 5.2 Neuro}
    D -->|Success| C
    D -->|Fail| E{Claude 4.5 Neuro}
    E -->|Success| C
    E -->|Fail| F{Claude 4.5 Polza.ai}
    F -->|Success| C
    F -->|Fail| G[Mark Chunk as Error]
    G --> H[Log to document_log]
    H --> I[Notify User via Telegram]
    C --> J{Post-Production?}
    J -->|Yes| K[GPT 5.3 Polza.ai]
    K -->|Fail| L[GPT-5.2 Neuro]
    J -->|No| M[Save to DB]
    L --> M
```

### 7.3 Prompt Structure

#### Translation System Prompt (translate_prompts table, agent_name: "BP Default")

The translation prompt stored in `translate_prompts` contains:

1. **Role Definition**: "You are a professional Korean-to-Russian literary translator"
2. **Glossary Enforcement**: List of Korean->Russian term mappings that MUST be used
3. **Style Guidelines**: Literary style, tone, register specifications
4. **Context Injection**: Chapter summary, arc summary, LightRAG context
5. **Input Format**: The Korean chunk text to translate
6. **Output Format**: Russian translation only, no explanations

#### Post-Production Prompt (agent_name: "PP Default")

1. **Role**: "You are a professional Russian text editor"
2. **Tasks**: Fix grammar, improve flow, check consistency with glossary
3. **Tools**: `text_validator` (grammar/spelling), `parentheses` (matching check)

#### Book Prompt (user-provided)

User can provide custom instructions for specific book (style preferences, character name preferences, specific terminology).

### 7.4 Token Cost Estimation

| Operation | Model | Avg Tokens per Call | Calls per Book (100 chunks) |
|-----------|-------|---------------------|----------------------------|
| Pre-analysis | Gemini 2.5 Flash Lite | ~8K (full text) | 1 |
| Chunk Translation | GPT 5.2 | ~4K input + ~2K output | 100 (x4 on full fallback) |
| Post-Production | GPT 5.3 | ~2K input + ~2K output | 100 (if enabled) |
| Chapter Summary | Gemini 2.5 Flash Lite | ~4K input + ~500 output | ~20 (5 chunks/chapter) |
| Arc Summary | Gemini 2.5 Flash Lite | ~8K input + ~1K output | ~5 (4 chapters/arc) |
| LightRAG Query | gpt-5.4-nano | ~2K input + ~500 output | 100 |
| Annotation | OpenAI | ~16K input + ~1K output | 1 |

---

## 8. LightRAG Integration

### 8.1 Architecture

```mermaid
graph LR
    n8n[n8n Workflows] -->|HTTP POST| LR[LightRAG API :9621]
    LR -->|Query| LDB[(LightRAG DB<br/>Vector + Graph)]
    LR -->|Embed| OLL[Ollama :11434<br/>nomic-embed-text]
    LR -->|LLM| POLZA[Polza.ai<br/>gpt-5.4-nano]

    subgraph "What n8n Sends to LightRAG"
        CS[Chapter Summaries] --> LR
        AS[Arc Summaries] --> LR
    end

    subgraph "What n8n Queries from LightRAG"
        LR -->|Semantic context| CT[Context for Chunk Translation]
    end
```

### 8.2 When LightRAG is Queried

LightRAG is queried **once per chunk** during translation (in **[Перевод] Перевод чанка** workflow, step 5):

1. **Query Input**: Current chunk text (Korean)
2. **Query Method**: HTTP POST to `http://localhost:9621` via `sub_lightrag_api`
3. **Query Mode**: `mix` (combines local vector search + global graph retrieval)
4. **Query Output**: Relevant context from previously translated content -- character mentions, plot points, terminology usage

### 8.3 What is Stored in LightRAG

| Content Type | When Inserted | Source Workflow | Purpose |
|-------------|---------------|-----------------|---------|
| **Chapter Summary** | When all chunks in chapter are translated | [Перевод] Глава | Provides chapter-level context for subsequent translations |
| **Arc Summary** | When arc boundary detected or arc completes | [Перевод] Арка | Provides arc-level narrative context |
| **Translated Chunks** | After each chunk is translated | [Перевод] Перевод чанка (optional) | Individual chunk content for fine-grained retrieval |

### 8.4 How LightRAG Results are Used

The LightRAG response is injected into the translation prompt as **additional context**:

```
[System Prompt]
You are a professional Korean-Russian translator...

[Glossary]
그 -> он (M), 문 -> дверь, 방 -> комната

[Chapter Rolling Summary]
The protagonist enters the abandoned building and explores the dark rooms...

[Arc Summary]
First arc: protagonist discovers the mysterious mansion and begins investigating...

[LightRAG Context]  <-- ADDED HERE
Similar scene from chapter 2: "He walked through the dark corridor, moonlight..."
Character "Min-jun" was previously described as tall and quiet...

[Input Chunk]
그는 문을 열고 방 안으로 들어갔다...
```

### 8.5 LightRAG Internal Architecture

LightRAG itself uses:
- **Embeddings**: Ollama `nomic-embed-text` (local, :11434)
- **LLM**: Polza.ai `gpt-5.4-nano` for response generation
- **Storage**: Local vector database + graph database (entities + relationships)

---

## 9. Error Handling Strategy

### 9.1 Multi-Layer Error Handling

```mermaid
graph TD
    A[Chunk Translation Error] --> B{Error Type}
    B -->|AI API Error| C[Try Next Model in Fallback Chain]
    B -->|DB Error| D[Log and Retry]
    B -->|Network Error| E[Retry with Backoff]
    B -->|Validation Error| F[Mark Chunk Error]

    C -->|All 4 Models Fail| F
    D -->|Retry Fails| F
    E -->|Retry Fails| F

    F --> G[[Перевод] Обработка ошибки]
    G --> H[Log to document_log]
    G --> I[Update chunk status = error]
    G --> J[Notify User via Telegram]

    K[Workflow-Level Error] --> L[Global Error Handler]
    L --> M[Log Error]
    L --> N[Notify User]

    O[Job-Level Error] --> P[Update document_jobs.status = error]
    P --> Q[Send Error Notification]
```

### 9.2 Error Types and Handling

| Error Type | Source | Handling | User Impact |
|-----------|--------|----------|-------------|
| **AI API Timeout** | Polza.ai / Neuro API | Try next model in fallback chain | Transparent (if fallback succeeds) |
| **AI API Rate Limit** | Polza.ai / Neuro API | Try next model, or wait and retry | Delayed processing |
| **AI API Unauthorized** | Polza.ai / Neuro API | All fallbacks fail -> mark error | Translation stops, user notified |
| **DB Connection Error** | PostgreSQL | Retry 3 times -> mark error | Translation stops |
| **LightRAG Unavailable** | LightRAG API | Translate without RAG context | Reduced translation quality |
| **Network Error** | Proxy / Internet | Retry -> fallback | Delayed processing |
| **Forbidden Words Detected** | Validation node | Trigger post-production or re-translate | Transparent |
| **Chunk Too Large** | Token limit | Split chunk -> re-process | Increased chunk count |

### 9.3 Error Logging

All errors are logged to `document_log` table:

```sql
INSERT INTO document_log (job_id, date_time, node, type, log)
VALUES (?, NOW(), '[Перевод] Перевод чанка', 'error',
  'GPT 5.2 (Polza.ai) failed: Connection timeout. Trying fallback...')
```

### 9.4 Current Gaps (Not Implemented)

- [ ] Circuit breaker for Polza.ai / Neuro API
- [ ] Retry with exponential backoff
- [ ] Dead letter queue for failed chunks
- [ ] Per-node execution timing metrics
- [ ] Pipeline performance metrics table
- [ ] Health check endpoints for external APIs
- [ ] Grafana dashboard with real-time observability
- [ ] Alert thresholds (e.g., >3 consecutive chunk errors)

---

## 10. Glossary & Prompt Management

### 10.1 Glossary Lifecycle

```mermaid
stateDiagram-v2
    [*] --> NoGlossary: User uploads file
    NoGlossary --> UserProvided: User uploads glossary file
    NoGlossary --> AutoGenerated: glossary_make = true

    UserProvided --> Validated: Validate format
    AutoGenerated --> Created: AI generates from document

    Validated --> AddedToDB: Добавление Глоссария workflow
    Created --> AddedToDB: Auto-saved

    AddedToDB --> UsedInTranslation: Перевод чанка reads glossary
    UsedInTranslation --> Enforced: Glossary terms in system prompt
    Enforced --> [*]
```

### 10.2 Glossary Sources (Priority Order)

1. **User-Provided Glossary** -- User uploads a file with Korean->Russian term mappings
2. **Auto-Generated Glossary** -- AI extracts terms from document during **Создание Глоссария** workflow
3. **System Glossary** -- Pre-defined terms from `translate_prompts` table

### 10.3 Glossary Format

Stored in `document_glossary`:

| name (Korean) | translate (Russian) | gender |
|---------------|-------------------|--------|
| 민준 | Минджун | M |
| 서연 | Соён | F |
| 한강 | Ханган | - |

### 10.4 Prompt Types

| Type | Table | agent_name Values | Purpose |
|------|-------|------------------|---------|
| **Translation Prompt** | translate_prompts | `BP Default`, `BP BL` | Main translation system prompt |
| **Post-Production Prompt** | translate_prompts | `PP Default` | Post-editing system prompt |
| **Book Prompt** | document_jobs.book_prompt | N/A | User-provided custom instructions per book |

### 10.5 Prompt Injection Order (During Translation)

When translating a chunk, the following are combined into the final AI prompt:

1. **System Prompt** -- from `translate_prompts` (agent_name = 'BP Default')
2. **Book Prompt** -- from `document_jobs.book_prompt` (if provided)
3. **Glossary** -- from `document_glossary` (all entries for the job)
4. **Chapter Rolling Summary** -- from `document_chapters.roller_summary`
5. **Arc Summary** -- from `document_arcs.summary`
6. **LightRAG Context** -- from LightRAG API query
7. **Chunk Text** -- the Korean text to translate

### 10.6 Managing Glossary and Prompts via n8n

| Workflow | Purpose |
|----------|---------|
| **Добавление Глоссария** | Add user-provided glossary entries to DB |
| **Создание Глоссария** | AI-generate glossary from document |
| **Добавление Промта** | Add translation prompt to `translate_prompts` |
| **Добавление промта для постредакта** | Add post-production prompt to `translate_prompts` |
| **Добавление ресурсов в бд** | General resource management |

---

## Appendix A: Workflow ID Reference

| Workflow Name | ID | Nodes |
|--------------|-----|-------|
| Start | 9cjeUNeTZX3YnO1W57YTP | 21 |
| Translate Chunk | Q5TRHGg-XRblnMRpH41Ee | 17 |
| [Перевод] Перевод чанка | GPARI8V4RBSPL1h39_kHW | 34 |
| [Перевод] Глава | IgLfaCSszdwsPw_b4u3au | 26 |
| [Перевод] Арка | OggkJgA8IFmasME_BNimq | 31 |
| [Перевод] Обработка ошибки | ImJpqAA5WlJZDK5jMtQSM | 14 |
| [GET] Document | sLo74sUgMdcJEmxJoRJQ- | 14 |
| [GET] /select_files | MmfiOXrCt2lkZ4TxZMyWS | 72 |
| Парсинг файла для перевода | bC43bgf5ZtXoi_XDLDwHO | 10 |
| Предварительный анализ файла для перевода | lSuNRX0VILP9Lgit5VKlK | 27 |
| Ручной выбор файлов | AnPEATb8u6yyFa54 | 30 |
| Send Message | J62UViXZMD5o6qoU | 12 |
| [Send] create_job | ScNLD3LbRTVAJOK4 | 8 |
| [Send] wait | OWLYY2oiQ6YPBJ7M | 10 |
| [Send] processing | 9uUyj9OamISRPudJ | 13 |
| [Send] error | 2uhp8PCTjxiKj91n | 5 |
| [Send] finish | hoUl3ewz23AwAHlq | 19 |
| Получение сообщения | CHSGtgO88LgGVbV8 | 8 |
| Select From List | CJ7lDvgGlmoP8Ymbgqd0A | 10 |
| Finish | vuqLp6ZGenvpkJbmVPR_6 | 10 |
| Создание Глоссария | t8Dmavjx9KS5Ms3SB3Qdj | 17 |
| Добавление Глоссария | ZdsvkMfRDAU4yLbL3DPcK | 9 |
| Добавление Промта | TVHpHR7HlCdrqEvAF3WNP | 10 |
| Добавление промта для постредакта | FuVQL0O5ik3aocbx | 10 |
| Постредактура | A8zKJVQgROH1cnkv | 9 |
| Настройка БД | UnqVdfxubclgfA7tafBwo | 8 |
| Добавление ресурсов в бд | rlk5lgq3uE4N0yl0 | 23 |
| sub_lightrag_api | AW58nseQdLtJn5ZO | 5 |
| Переведенный файл в Google Drive | KebWQcS1WmNtgdgA | 11 |
| Переведенный файл в Telegram | sv73wrV6anQE7cTv | 9 |
| Анотация | 2kztTVutdATd1MDS | 7 |
| Перезапуск прослушки Telegram | GiqH3FrsgKjwIbUfcS6-j | 4 |
| Global Error Handler | global-error-handler-36id | 2 |
| [Book Translation] Activate [NOT USED] | activate-translation-workflows | 5 |

## Appendix B: API Credentials Reference

| Service | Credential Type | Location |
|---------|----------------|----------|
| Telegram Bot | Bot Token | n8n Telegram credential node |
| Polza.ai | Bearer Token | n8n HTTP/LangChain credential |
| Neuro API | Bearer Token | n8n HTTP/LangChain credential |
| Google Drive | OAuth2 | n8n Google Drive credential |
| LightRAG | None (local) | HTTP node, no auth |
| PostgreSQL | User/Password | n8n Postgres credential |

## Appendix C: File Format Support

| Format | Supported | Method |
|--------|-----------|--------|
| DOCX | Yes | Extract text from Office Open XML |
| TXT | Yes | Direct read |
| XLSX | Yes | Extract text from cells |
| PDF | No | Not currently supported |
| EPUB | No | Not currently supported |

---

**Document maintained**: April 14, 2026
**Based on**: Live system analysis of 34 active workflows
**Next review**: After any workflow changes or new feature additions
