# 🏗️ Архитектура n8n Translation System

**Дата:** 9 апреля 2026 г.
**Версия:** 1.0

---

# Содержание

1. [Общая архитектура](#общая-архитектура)
2. [Инфраструктурная диаграмма](#инфраструктурная-диаграмма)
3. [Архитектура workflows](#архитектура-workflows)
4. [Потоки данных](#потоки-данных)
5. [Архитектура базы данных](#архитектура-базы-данных)
6. [Сетевая архитектура](#сетевая-архитектура)
7. [Архитектура мониторинга](#архитектура-мониторинга)
8. [Архитектура безопасности](#архитектура-безопасности)

---

# Общая архитектура

## High-Level Architecture

```mermaid
graph TB
    User[👤 User] -->|Telegram| TG[🤖 Telegram Bot]
    User -->|Web UI| Caddy[🌐 Caddy Reverse Proxy]
    
    TG -->|Webhook| Caddy
    Caddy -->|bigalexn8n.ru| n8n[🔄 n8n Workflow Engine]
    
    n8n -->|Queries| DB[(💾 PostgreSQL 16)]
    n8n -->|API calls| LightRAG[🧠 LightRAG RAG System]
    n8n -->|API calls| Ollama[🤖 Ollama LLM]
    
    LightRAG -->|Embeddings| Ollama
    LightRAG -->|LLM API| PolzaAPI[🌐 polza.ai API]
    
    n8n -->|Notifications| TG
    
    DB -->|Metrics| PGExporter[📊 Postgres Exporter]
    Node[💻 Node Exporter] -->|Host Metrics| Prom[📈 Prometheus]
    PGExporter -->|DB Metrics| Prom
    Prom -->|Query| Grafana[📊 Grafana Dashboard]
    
    style User fill:#e1f5ff
    style n8n fill:#ff6b6b
    style DB fill:#4ecdc4
    style LightRAG fill:#ffe66d
    style Ollama fill:#a8e6cf
    style Grafana fill:#ff8b94
```

## Layered Architecture

```mermaid
graph LR
    subgraph "Presentation Layer"
        TG[Telegram Bot]
        WebUI[Web Interface]
        pgAdmin[pgAdmin 4]
        GrafanaUI[Grafana UI]
        Portainer[Portainer]
    end
    
    subgraph "Orchestration Layer"
        n8n[n8n Workflows]
        CronUI[Crontab UI]
    end
    
    subgraph "Business Logic Layer"
        LightRAG[LightRAG API]
        Ollama[Ollama LLM]
        Scripts[Python Scripts]
    end
    
    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL 81 tables)]
        VectorDB[(LightRAG Vector DB)]
        FileSystem[File System]
    end
    
    Presentation --> Orchestration
    Orchestration --> Business
    Business --> Data
    
    style Presentation fill:#e1f5ff
    style Orchestration fill:#ff6b6b
    style Business fill:#ffe66d
    style Data fill:#4ecdc4
```

---

# Инфраструктурная диаграмма

## Docker Compose Projects

```mermaid
graph TB
    subgraph "n8n-docker Project"
        n8n[n8n:5678]
        DB[(PostgreSQL:5432)]
        pgAdmin[pgAdmin4:5055]
        Prom[Prometheus:9090]
        Grafana[Grafana:3000]
        NodeExp[Node Exporter:9100]
        PGExp[Postgres Exporter:9187]
    end
    
    subgraph "lightrag Project"
        Ollama[Ollama:11434]
        LightRAG[LightRAG:9621]
        AppsHub[Telegram Apps]
        Portainer[Portainer:9000]
    end
    
    subgraph "Standalone"
        CronUI[Crontab UI:8001]
    end
    
    n8n -.->|host network| Proxy[🔒 Xray Proxy:10808]
    LightRAG -.->|host network| Proxy
    
    Proxy -->|HTTP/HTTPS| TelegramAPI[📱 Telegram API]
    
    style n8n fill:#ff6b6b
    style DB fill:#4ecdc4
    style Ollama fill:#a8e6cf
    style Proxy fill:#ffe66d
```

## Resource Allocation

```mermaid
pie title Container Resource Distribution
    "n8n (1.17GB image)" : 25
    "PostgreSQL + Data" : 20
    "Ollama + Models" : 30
    "LightRAG" : 10
    "Monitoring Stack" : 10
    "Other Services" : 5
```

---

# Архитектура Workflows

## Workflow Dependency Graph

```mermaid
graph TB
    subgraph "Triggers"
        TGTrigger[Telegram Trigger]
        DBTrigger[DB Trigger: telegram_send_message]
        WebhookTrigger[Webhook Trigger]
        ManualTrigger[Manual Trigger]
    end
    
    subgraph "Main Pipeline"
        ParseFile[Parsing File]
        Analysis[File Analysis]
        ExtractGlossary[Glossary Extraction]
        TranslateChapter[Chapter Translation]
        QualityCheck[Quality Check]
        PostEdit[Post-Editing]
    end
    
    subgraph "Notification System"
        SendMessage[Send Message Orchestrator]
        GetContext[Get Context]
        TaskCreate[Task: Create]
        TaskStart[Task: Start]
        TaskProcess[Task: Process]
        TaskError[Task: Error]
        TaskFinish[Task: Finish]
        TaskStop[Task: Stop]
        NotifyTelegram[Notify Telegram]
    end
    
    subgraph "Utilities"
        LightRAGAPI[LightRAG API Integration]
        GlossaryMgmt[Glossary Management]
        PromptMgmt[Prompt Management]
        ErrorHandling[Global Error Handler]
    end
    
    TGTrigger --> ParseFile
    DBTrigger --> SendMessage
    WebhookTrigger --> Analysis
    
    ParseFile --> Analysis
    Analysis --> ExtractGlossary
    ExtractGlossary --> TranslateChapter
    TranslateChapter --> QualityCheck
    QualityCheck -->|Low Score| PostEdit
    QualityCheck -->|High Score| Export[Export & Notify]
    
    SendMessage --> GetContext
    GetContext --> Router{Router}
    Router -->|create| TaskCreate
    Router -->|start| TaskStart
    Router -->|process| TaskProcess
    Router -->|error| TaskError
    Router -->|finish| TaskFinish
    Router -->|stop| TaskStop
    
    TaskCreate --> NotifyTelegram
    TaskStart --> NotifyTelegram
    TaskProcess --> NotifyTelegram
    TaskError --> NotifyTelegram
    TaskFinish --> NotifyTelegram
    TaskStop --> NotifyTelegram
    
    TranslateChapter --> LightRAGAPI
    QualityCheck --> LightRAGAPI
    ExtractGlossary --> LightRAGAPI
    
    style Triggers fill:#e1f5ff
    style Main_Pipeline fill:#ff6b6b
    style Notification_System fill:#ffe66d
    style Utilities fill:#a8e6cf
```

## Notification System Architecture

```mermaid
sequenceDiagram
    participant DB as PostgreSQL
    participant n8n as n8n DB Trigger
    participant Orchestrator as Send Message Orchestrator
    participant Context as Get Context
    participant Router as Message Router
    participant Task as Task_* Formatter
    participant Telegram as Telegram API
    participant Log as DB Logger
    
    DB->>n8n: INSERT into telegram_send_message
    n8n->>Orchestrator: Trigger workflow
    Orchestrator->>Orchestrator: Validate Payload
    Orchestrator->>Context: Get job context (1 SQL)
    Context-->>Orchestrator: Return context
    
    Orchestrator->>Router: Route by message type
    alt create_job
        Router->>Task: task_create
    else start_processing
        Router->>Task: task_start_processing
    else processing
        Router->>Task: task_process
    else error
        Router->>Task: task_error
    else finish
        Router->>Task: task_finish
    else stop
        Router->>Task: task_stop
    end
    
    Task-->>Orchestrator: Formatted message
    Orchestrator->>Telegram: Send/Edit message (idempotent)
    Telegram-->>Orchestrator: Message ID
    Orchestrator->>Log: Log to telegram_send_message
```

---

# Потоки данных

## Document Translation Flow

```mermaid
flowchart TD
    Start([User sends document]) --> TG[Telegram Bot]
    TG --> Webhook[Webhook: /webhook/telegram]
    Webhook --> n8n[n8n Workflow]
    
    n8n --> Parse[Parse File]
    Parse --> Analyze[Analyze Structure]
    
    Analyze -->|LLM| Arcs[Detect Arcs]
    Analyze -->|LLM| Chapters[Detect Chapters]
    
    Arcs --> Glossary[Extract Glossary]
    Chapters --> Glossary
    
    Glossary --> Review{Human Review?}
    Review -->|Yes| UI[TWA/React UI]
    UI --> Approve[Approve Glossary]
    Review -->|No| Approve
    
    Approve --> Batch[Batch Processing]
    
    Batch -->|Chapter 1| Translate1[Translate Ch 1]
    Batch -->|Chapter 2| Translate2[Translate Ch 2]
    Batch -->|Chapter 3| Translate3[Translate Ch 3]
    
    Translate1 --> QC1[Quality Check 1]
    Translate2 --> QC2[Quality Check 2]
    Translate3 --> QC3[Quality Check 3]
    
    QC1 -->|Score >= 8| Save1[Save to DB]
    QC1 -->|Score < 8| Retry1[Retry Translation]
    
    QC2 -->|Score >= 8| Save2[Save to DB]
    QC2 -->|Score < 8| Retry2[Retry Translation]
    
    QC3 -->|Score >= 8| Save3[Save to DB]
    QC3 -->|Score < 8| Retry3[Retry Translation]
    
    Save1 --> Notify[Notify Progress]
    Save2 --> Notify
    Save3 --> Notify
    
    Notify --> AllDone{All chapters done?}
    AllDone -->|No| Batch
    AllDone -->|Yes| Export[Export Document]
    
    Export --> SendFile[Send to User]
    SendFile --> End([Translation Complete])
    
    style Start fill:#e1f5ff
    style End fill:#a8e6cf
    style n8n fill:#ff6b6b
    style QC1 fill:#ffe66d
    style QC2 fill:#ffe66d
    style QC3 fill:#ffe66d
```

## Notification Flow

```mermaid
flowchart LR
    A[Pipeline Event] -->|INSERT| B[(telegram_send_message)]
    B -->|Trigger| C[n8n PostgresTrigger]
    C --> D{Validate Payload}
    D -->|Invalid| E[Log Error]
    D -->|Valid| F[Get Context]
    F --> G{Message Type?}
    
    G -->|create| H[task_create]
    G -->|start| I[task_start_processing]
    G -->|process| J[task_process]
    G -->|error| K[task_error]
    G -->|finish| L[task_finish]
    G -->|stop| M[task_stop]
    
    H --> N{message_id exists?}
    I --> N
    J --> N
    K --> N
    L --> N
    M --> N
    
    N -->|Yes| O[Edit Message]
    N -->|No| P[Send Message]
    
    O --> Q[Telegram API]
    P --> Q
    
    Q --> R{Success?}
    R -->|Yes| S[Log Success]
    R -->|No| T[Log Error]
    
    S --> End([Done])
    T --> End
    
    style A fill:#e1f5ff
    style B fill:#4ecdc4
    style C fill:#ff6b6b
    style Q fill:#ffe66d
    style End fill:#a8e6cf
```

---

# Архитектура базы данных

## Entity Relationship Diagram

```mermaid
erDiagram
    document_jobs ||--o{ document_arcs : has
    document_jobs ||--o{ document_chapters : has
    document_jobs ||--o{ document_glossary : has
    document_jobs ||--o{ document_chunks : contains
    document_jobs ||--o{ document_log : logs
    document_jobs ||--o{ document_characters : has
    
    document_arcs ||--o{ document_chapters : contains
    
    document_chapters ||--o{ document_chunks : contains
    
    telegram_chats ||--o{ telegram_message : receives
    
    telegram_send_message ||--o| telegram_send_message : "idempotent edit"
    
    translate_prompts ||--o{ n8n_workflows : used_by
    
    document_jobs {
        int id PK
        text file_name
        text status
        text translated_file
        text glossary_file
        text billing_polza
        text billing_neuro
        timestamp created_at
        timestamp updated_at
        timestamp finished_at
    }
    
    document_arcs {
        int id PK
        int job_id FK
        int arc_number
        int start_chapter
        int end_chapter
        json summary
        timestamp updated_at
    }
    
    document_chapters {
        int id PK
        int job_id FK
        int arc_id FK
        int chapter_number
        json summary
        json roller_summary
        int line_start
        int line_finish
        text status
        timestamp updated_at
    }
    
    document_chunks {
        int id PK
        int job_id FK
        int chapter FK
        int chunk_index
        text chunk_text
        text prev_line
        text result_text
        text raw_translate_text
        text status
        text error_text
        timestamp updated_at
    }
    
    document_glossary {
        int id PK
        int job_id FK
        text name
        text translate
        text gender
        timestamp updated_at
    }
    
    document_log {
        int id PK
        int job_id FK
        timestamp date_time
        text node
        text type
        text log
    }
    
    telegram_chats {
        int id PK
        text chat
    }
    
    telegram_message {
        int id PK
        int chat_id FK
        text message_id
        text delete_id
    }
    
    telegram_send_message {
        int id PK
        bigint chat_id
        text message
        timestamp created_at
    }
    
    translate_prompts {
        int id PK
        varchar agent_name UK
        text prompt_text
        timestamp updated_at
    }
```

## Table Relationships

```mermaid
graph TB
    DJ[document_jobs] -->|1:N| DA[document_arcs]
    DJ -->|1:N| DC[document_chapters]
    DJ -->|1:N| DG[document_glossary]
    DJ -->|1:N| DCh[document_chunks]
    DJ -->|1:N| DL[document_log]
    
    DA -->|1:N| DC
    
    DC -->|1:N| DCh
    
    TC[telegram_chats] -->|1:N| TM[telegram_message]
    
    TSM[telegram_send_message] -.->|trigger| n8n[n8n workflow]
    
    style DJ fill:#ff6b6b
    style DA fill:#ffe66d
    style DC fill:#ffe66d
    style DG fill:#a8e6cf
    style DCh fill:#4ecdc4
```

---

# Сетевая архитектура

## Network Topology

```mermaid
graph TB
    subgraph "External Network"
        Internet[🌐 Internet]
        TelegramAPI[📱 Telegram API]
        PolzaAPI[🤖 polza.ai API]
    end
    
    subgraph "Server (Host Network)"
        Proxy[🔒 Xray Proxy:10808]
        n8n[🔄 n8n:5678]
        LightRAG[🧠 LightRAG:9621]
        Ollama[🤖 Ollama:11434]
        AppsHub[📱 Apps Hub]
    end
    
    subgraph "Docker Bridge Network: n8n-docker_default"
        DB[(PostgreSQL:5432)]
        pgAdmin[pgAdmin:80]
    end
    
    subgraph "Docker Bridge Network: lightrag_default"
        Portainer[Portainer:9000]
    end
    
    Internet -->|HTTPS:443| Caddy[Caddy Reverse Proxy]
    Caddy -->|localhost:5678| n8n
    Caddy -->|localhost:3000| Grafana[Grafana]
    
    n8n -->|HTTP Proxy| Proxy
    Proxy -->|HTTPS| TelegramAPI
    
    n8n -->|HTTP:9621| LightRAG
    LightRAG -->|HTTP:11434| Ollama
    LightRAG -->|HTTPS| PolzaAPI
    
    n8n -->|TCP:5432| DB
    
    style Internet fill:#e1f5ff
    style Proxy fill:#ffe66d
    style n8n fill:#ff6b6b
    style DB fill:#4ecdc4
```

## Reverse Proxy Configuration

```mermaid
flowchart LR
    User[User Browser] -->|https://bigalexn8n.ru| Caddy
    
    Caddy -->|/webhook/telegram*| n8n[localhost:5678]
    Caddy -->|/*| n8n
    
    User -->|https://grafana.bigalexn8n.ru| CaddyGrafana
    CaddyGrafana -->|BasicAuth| Grafana[localhost:3000]
    
    User -->|http://127.0.0.1:5055| pgAdmin[pgAdmin:80]
    User -->|http://localhost:9090| Prometheus
    User -->|http://localhost:9000| Portainer
    
    style User fill:#e1f5ff
    style Caddy fill:#ffe66d
    style n8n fill:#ff6b6b
    style Grafana fill:#ff8b94
```

---

# Архитектура мониторинга

## Monitoring Stack

```mermaid
graph TB
    subgraph "Data Collection"
        NodeExp[Node Exporter:9100]
        PGExp[Postgres Exporter:9187]
        n8nExec[n8n Executions]
    end
    
    subgraph "Storage"
        Prometheus[(Prometheus TSDB:9090)]
        PostgreSQL[(PostgreSQL Logs)]
    end
    
    subgraph "Visualization"
        Grafana[Grafana Dashboards:3000]
    end
    
    subgraph "Alerting"
        TelegramAlert[📱 Telegram Alerts]
    end
    
    NodeExp -->|Scrape every 15s| Prometheus
    PGExp -->|Scrape every 15s| Prometheus
    
    n8nExec -->|SQL Query| PostgreSQL
    PostgreSQL -->|Grafana Query| Grafana
    
    Prometheus -->|Query| Grafana
    
    Grafana -->|Alert Rule| TelegramAlert
    
    style NodeExp fill:#a8e6cf
    style PGExp fill:#4ecdc4
    style Prometheus fill:#ffe66d
    style Grafana fill:#ff8b94
    style TelegramAlert fill:#ff6b6b
```

## Grafana Dashboard Structure

```mermaid
graph TB
    Dashboard[n8n Monitoring Dashboard]
    
    Dashboard --> Overview[Overview Row]
    Dashboard --> Executions[Executions Row]
    Dashboard --> Documents[Documents Row]
    Dashboard --> Telegram[Telegram Row]
    Dashboard --> Errors[Errors Row]
    
    Overview --> TotalExec[Total Executions]
    Overview --> SuccessRate[Success Rate]
    Overview --> AvgDuration[Average Duration]
    Overview --> ActiveChats[Active Chats]
    
    Executions --> ExecByStatus[Executions by Status]
    Executions --> ExecByTime[Executions Over Time]
    Executions --> TopErrors[Top Error Workflows]
    
    Documents --> DocByStatus[Documents by Status]
    Documents --> DocOverTime[Documents Over Time]
    Documents --> RecentDocs[Recent Documents Table]
    
    Telegram --> MsgOverTime[Messages Over Time]
    Telegram --> SendErrors[Send Errors]
    
    Errors --> ErrorByComponent[Errors by Component]
    Errors --> RecentErrors[Recent Errors Table]
    
    style Dashboard fill:#ff6b6b
    style Overview fill:#e1f5ff
    style Executions fill:#ffe66d
    style Documents fill:#4ecdc4
    style Telegram fill:#a8e6cf
    style Errors fill:#ff8b94
```

---

# Архитектура безопасности

## Security Layers

```mermaid
graph TB
    subgraph "Perimeter Security"
        Firewall[🔥 Firewall]
        CaddyTLS[Caddy TLS: Let's Encrypt]
    end
    
    subgraph "Application Security"
        BasicAuth[BasicAuth for Grafana]
        WebhookValidation[Webhook Validation]
        ProxyAuth[Proxy Authentication]
    end
    
    subgraph "Data Security"
        DBAuth[(DB Password)]
        n8nEncrypt[n8n Encryption Key]
        SecretsInEnv[Secrets in .env]
    end
    
    subgraph "Network Security"
        HostNetwork[Host Network Mode]
        ProxyRouting[Proxy-based Routing]
        NOProxy[NO_PROXY for local]
    end
    
    Firewall --> CaddyTLS
    CaddyTLS --> BasicAuth
    CaddyTLS --> WebhookValidation
    
    BasicAuth --> DBAuth
    WebhookValidation --> ProxyAuth
    
    DBAuth --> n8nEncrypt
    ProxyAuth --> HostNetwork
    
    HostNetwork --> ProxyRouting
    ProxyRouting --> NOProxy
    
    style Firewall fill:#ff6b6b
    style CaddyTLS fill:#ffe66d
    style DBAuth fill:#4ecdc4
    style HostNetwork fill:#a8e6cf
```

## Access Control

```mermaid
quadrantChart
    title Access Control Matrix
    x-axis "Public" --> "Private"
    y-axis "Read" --> "Write"
    "n8n Web UI": [0.7, 0.8]
    "Telegram Webhook": [0.3, 0.7]
    "Grafana Dashboard": [0.8, 0.6]
    "pgAdmin": [0.9, 0.9]
    "Prometheus": [0.6, 0.5]
    "Portainer": [0.9, 0.9]
    "PostgreSQL": [0.95, 0.95]
```

---

**Документация создана:** 9 апреля 2026 г.
**Автор:** AI Architecture Team
**Статус:** На утверждении
