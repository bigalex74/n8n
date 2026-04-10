# 🔧 План рефакторинга и декомпозиции n8n Translation System

**Дата:** 9 апреля 2026 г.
**Версия:** 1.0
**Приоритет:** HIGH
**Статус:** На утверждении

---

# Содержание

1. [Обзор проблем](#обзор-проблем)
2. [Цели рефакторинга](#цели-рефакторинга)
3. [План по фазам](#план-по-фазам)
4. [Детальные задачи](#детальные-задачи)
5. [Оценка рисков](#оценка-рисков)
6. [Метрики успеха](#метрики-успеха)

---

# Обзор проблем

## Критичные проблемы (P0)

### 1. Отсутствие единой точки входа для Translation Pipeline
**Проблема:** Нет master workflow, который координирует весь процесс перевода
**Влияние:** Сложно отслеживать статус, управлять ошибками, масштабировать
**Решение:** Создать [Master] Translation Pipeline workflow

### 2. Дублирование task workflows
**Проблема:** 6 отдельных task_* workflows с одинаковой структурой
**Влияние:** Сложность поддержки, дублирование кода, баги в нескольких местах
**Решение:** Параметризовать в 1 workflow

### 3. Неактивные sub_get_context и sub_notify
**Проблеma:** Критичные workflows неактивны, но используются через Execute Workflow node
**Влияние:** Путаница, потенциальные ошибки при активации
**Решение:** Пересмотреть архитектуру или активировать

### 4. Отсутствие автоматических бэкапов
**Проблема:** Только ручной скрипт backup_n8n.sh
**Влияние:** Риск потери данных при сбоях
**Решение:** Автоматизировать через cron + external storage

## Важные проблемы (P1)

### 5. Недостаточная документация workflows
**Проблема:** Многие workflows без описания, inputs/outputs не документированы
**Влияние:** Сложно onboard новых разработчиков, трудно debug
**Решение:** Добавить descriptions ко всем workflows

### 6. Отсутствие health checks
**Проблема:** Нет автоматической проверки состояния сервисов
**Влияние:** Позднее обнаружение проблем
**Решение:** Health check workflow + monitoring

### 7. Hardcoded credentials в workflow files
**Проблема:** Потенциальный риск безопасности
**Влияние:** Утечка credentials при экспорте
**Решение:** Использовать n8n Credentials Manager

### 8. Неоптимизированные SQL запросы
**Проблема:** Возможность N+1 queries, отсутствие индексов
**Влияние:** Медленная performance при больших данных
**Решение:** Оптимизировать запросы, добавить индексы

## Улучшения (P2)

### 9. Отсутствие workflow тегов
**Проблема:** Нет категоризации workflows
**Влияние:** Сложно искать и фильтровать
**Решение:** Добавить теги (Pipeline, Notification, Utility, etc.)

### 10. No retry logic в критичных местах
**Проблема:** API calls без retry, no exponential backoff
**Влияние:** Failures при временных проблемах
**Решение:** Добавить retry logic

### 11. Отсутствие rate limiting
**Проблема:** Telegram API имеет rate limits
**Влияние:** Bans при интенсивной отправке
**Решение:** Rate limiting queue

### 12. Нет audit log
**Проблема:** Неясно кто/что изменил в workflows
**Влияние:** Сложно track changes
**Решение:** Audit logging workflow

---

# Цели рефакторинга

## Основные цели

1. **Уменьшить сложность**: 55 → 40 workflows (архивация deprecated)
2. **Повысить надежность**: 100% workflows с error handling
3. **Улучшить производительность**: -30% SQL query time
4. **Упростить поддержку**: 100% workflows с документацией
5. **Автоматизировать операции**: Backups, health checks, alerts

## KPI

| Метрика | Текущее | Цель | Измерение |
|---------|---------|------|-----------|
| Workflows всего | 55 | 40 | COUNT |
| Workflows активные | 33 | 35 | COUNT |
| Workflows с error handling | ~15 | 100% | % |
| Workflows с документацией | ~20 | 100% | % |
| SQL queries per translation | ~15 | ~10 | COUNT |
| Backup frequency | Manual | Every 6h | Schedule |
| Mean Time To Recovery (MTTR) | Unknown | < 15 min | Time |
| Error detection time | Manual | < 5 min | Time |

---

# План по фазам

## Фаза 1: Cleanup и инвентаризация (1-2 дня)

### Задачи

#### 1.1. Архивация deprecated workflows
```sql
-- Archive old/unused workflows
UPDATE workflow_entity 
SET "isArchived" = true 
WHERE name IN (
    'My workflow',
    '[depricated] Send Message (RESTORED)',
    'Telegram Final',
    'Telegram Simple',
    'Telegram Webhook Handler',
    '🔄 Telegram Polling (n8n)',
    'Test Webhook Trigger',
    '[TEST] Error Handler Check',
    '[TEST] Manual Error Test',
    'Test Minimal Webhook',
    'Activate All Workflows (Mass)'
);
```

**Результат:** 55 → 44 workflows

#### 1.2. Добавить descriptions ко всем workflows
```sql
-- Update workflow descriptions
UPDATE workflow_entity 
SET description = 'Main translation pipeline orchestrator'
WHERE name = '[Перевод] Арка';

-- ... для всех workflows
```

**Результат:** 100% workflows с описаниями

#### 1.3. Экспорт и бэкап текущих workflows
```bash
# Export all workflows
docker exec n8n-docker-n8n-1 n8n export:workflow --all --output=/backup/workflows_$(date +%Y%m%d).json

# Backup database
docker exec n8n-docker-db-1 pg_dump -U n8n_user n8n_database > /backup/db_$(date +%Y%m%d).sql
```

**Результат:** Full backup перед изменениями

---

## Фаза 2: Consolidation (2-3 дня)

### Задачи

#### 2.1. Consolidate task_* workflows в один

**Current:**
```
task_create (6 nodes)
task_start_processing (6 nodes)
task_process (6 nodes)
task_error (6 nodes)
task_finish (6 nodes)
task_stop (6 nodes)
Total: 36 nodes
```

**Proposed:**
```
task_format_message (12 nodes)
├── Input: message_type, context
├── Router by message_type
├── 6 Code nodes (message formatting)
├── Output: {message, type, button}
```

**Implementation:**
```javascript
// Code node: Format Message
const messageType = $input.first().json.message_type;
const context = $input.first().json.context;

const formatters = {
  'create': () => `🆕 Задача создана\n\n📄 Документ: ${context.file_name}`,
  'start': () => `▶️ Обработка началась\n\n📄 Документ: ${context.file_name}\n📊 Прогресс: 0% (0/${context.chunks_total})`,
  'process': () => {
    const progress = Math.round(context.chunks_done / context.chunks_total * 100);
    const bar = '█'.repeat(progress/5) + '░'.repeat(20 - progress/5);
    return `🔄 Перевод в процессе\n\n📄 Документ: ${context.file_name}\n📊 Прогресс: ${progress}% [${bar}] (${context.chunks_done}/${context.chunks_total})`;
  },
  'error': () => `⚠️ Ошибка обработки\n\n📄 Документ: ${context.file_name}\n❌ Ошибка: ${context.error_text}`,
  'finish': () => `✅ Перевод завершен!\n\n📄 Документ: ${context.file_name}\n📥 Файл: ${context.translated_file}`,
  'stop': () => ({
    message: `🚨 Перевод остановлен\n\n📄 Документ: ${context.file_name}`,
    button: { text: '🔁 Повторить', callback: 'repeat_translate' }
  })
};

return { json: formatters[messageType]() };
```

**Результат:** 36 → 12 nodes, easier maintenance

#### 2.2. Создать [Master] Translation Pipeline

**Architecture:**
```
[Master] Translation Pipeline
├── Trigger: Webhook / Manual / Telegram
├── 1. Validate Input
├── 2. Create Job Record
├── 3. Parse File
├── 4. Analyze Structure (arcs, chapters)
├── 5. Extract Glossary
├── 6. [Optional] Human Review
├── 7. Process Arcs (parallel)
│   └── [Sub] Arc Processing
│       └── Process Chapters (batch=3)
│           └── [Sub] Chapter Translation
│               ├── Translate Chunks
│               ├── Quality Check
│               └── Save to DB
├── 8. Export Results
│   ├── To Telegram
│   └── To Google Drive
├── 9. Notify Completion
└── Error Handler: Global Error Handler
```

**Implementation:** Создать новый workflow с Execute Workflow nodes

**Результат:** Single entry point, better tracking

#### 2.3. Создать Shared Utility workflows

**Utility Workflows:**
1. **[Utils] SQL Executor** - безопасное выполнение SQL
2. **[Utils] Telegram Sender** - rate-limited sending
3. **[Utils] Error Logger** - centralized logging
4. **[Utils] Retry Handler** - exponential backoff logic

**Результат:** Reusable components, less duplication

---

## Фаза 3: Optimization (2-3 дня)

### Задачи

#### 3.1. Оптимизировать SQL запросы

**Current issues:**
- Multiple queries for job context
- No indexes on frequently queried columns
- Potential N+1 queries

**Optimizations:**

```sql
-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_document_jobs_status ON document_jobs(status);
CREATE INDEX IF NOT EXISTS idx_document_jobs_created ON document_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_document_chunks_job_status ON document_chunks(job_id, status);
CREATE INDEX IF NOT EXISTS idx_document_log_job_date ON document_log(job_id, date_time DESC);
CREATE INDEX IF NOT EXISTS idx_telegram_send_message_chat ON telegram_send_message(chat_id, created_at DESC);

-- Optimize context query (already done in sub_get_context)
-- Verify it uses indexes
EXPLAIN ANALYZE
SELECT j.job_id, j.file_name, j.translated_file,
       j.billing_polza, j.billing_neuro,
       (SELECT COUNT(*) FROM document_chunks WHERE job_id = j.id) as chunks_total,
       (SELECT COUNT(*) FROM document_chunks WHERE job_id = j.id AND status = 'done') as chunks_done
FROM document_jobs j
WHERE j.id = 1;
```

**Результат:** -30% query time

#### 3.2. Добавить caching для повторяющихся данных

**Cache candidates:**
- Glossary terms (per job)
- Translate prompts
- Telegram chat IDs

**Implementation:**
```javascript
// Code node: Cache Get
const cache = $workflow.staticData.cache || {};
const key = `glossary_${job_id}`;

if (cache[key] && Date.now() - cache[key].timestamp < 3600000) {
  return { json: { cached: true, data: cache[key].data } };
}

// Fetch from DB and cache
const result = await fetchFromDB();
cache[key] = { data: result, timestamp: Date.now() };
$workflow.staticData.cache = cache;

return { json: { cached: false, data: result } };
```

**Результат:** -50% DB queries for repeated data

#### 3.3. Implement connection pooling

**Current:** Direct DB connections per workflow execution
**Proposed:** Use n8n connection pooling settings

```yaml
# docker-compose.yml
n8n:
  environment:
    - DB_POSTGRESDB_CONNECTION_TIMEOUT=10000
    - DB_POSTGRESDB_MAX_CONNECTIONS=20
```

**Результат:** Better performance under load

---

## Фаза 4: Reliability (2-3 дня)

### Задачи

#### 4.1. Настроить автоматические бэкапы

**Crontab UI Setup:**
```bash
# Access Crontab UI at http://localhost:8001

# Add backup job
0 */6 * * * docker exec n8n-docker-db-1 pg_dump -U n8n_user n8n_database | gzip > /backups/db_$(date +\%Y\%m\%d_\%H\%M).sql.gz

# Add workflow export job
0 0 * * * docker exec n8n-docker-n8n-1 n8n export:workflow --all --output=/backups/workflows_$(date +\%Y\%m\%d).json
```

**Retention policy:**
- Daily backups: keep 7 days
- Weekly backups: keep 4 weeks
- Monthly backups: keep 12 months

**Результат:** Automated backups every 6 hours

#### 4.2. Создать Health Check workflow

**Workflow: [System] Health Check**
```
Trigger: Schedule (every 5 minutes)
├── Check PostgreSQL connection
├── Check LightRAG API (/health)
├── Check Ollama API
├── Check Telegram Bot API (getMe)
├── Check disk space
├── Check memory usage
├── If any check fails → Send alert to Telegram
└── Log results to DB
```

**Implementation:**
```javascript
// Code node: Health Checks
const checks = {
  postgresql: await checkPostgreSQL(),
  lightrag: await checkLightRAG(),
  ollama: await checkOllama(),
  telegram: await checkTelegram(),
  disk: await checkDiskSpace(),
  memory: await checkMemory()
};

const failed = Object.entries(checks).filter(([_, status]) => !status.ok);

if (failed.length > 0) {
  await sendAlert(`Health check failed: ${failed.map(([name]) => name).join(', ')}`);
}

await logHealthCheck(checks);
```

**Результат:** Early problem detection

#### 4.3. Добавить retry logic к API calls

**Pattern: Exponential Backoff**
```javascript
// Code node: Retry Wrapper
async function withRetry(fn, maxRetries = 3, baseDelay = 1000) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      
      const delay = baseDelay * Math.pow(2, i);
      console.log(`Retry ${i + 1}/${maxRetries} after ${delay}ms`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

// Usage
const result = await withRetry(() => callLightRAGAPI(query));
```

**Apply to:**
- LightRAG API calls
- Ollama API calls
- Telegram API calls
- Database operations

**Результат:** Better fault tolerance

#### 4.4. Настроить alerting в Telegram

**Alert conditions:**
- Workflow execution failed
- Health check failed
- Disk space < 20%
- Memory usage > 90%
- Backup failed

**Implementation:**
```sql
-- Insert into telegram_send_message
INSERT INTO telegram_send_message (chat_id, message, created_at)
VALUES (923741104, '⚠️ Alert: Health check failed - PostgreSQL connection timeout', NOW());
```

**Результат:** Real-time problem notification

---

## Фаза 5: Security (1-2 дня)

### Задачи

#### 5.1. Мigrate credentials to n8n Credentials Manager

**Current:** Potentially hardcoded in workflows
**Proposed:** Use n8n Credentials Manager

```javascript
// Instead of hardcoded:
// const token = '8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0';

// Use credentials:
const credentials = await $credentials.get('telegramApi');
const token = credentials.token;
```

**Migration steps:**
1. Export all workflows
2. Search for potential credentials (tokens, passwords, API keys)
3. Create credentials in n8n UI
4. Update workflows to use credentials
5. Re-import workflows

**Результат:** No hardcoded secrets

#### 5.2. Add input validation к webhook endpoints

**Current:** Potentially unvalidated inputs
**Proposed:** Validate all inputs

```javascript
// Code node: Validate Webhook Input
const payload = $input.first().json;

const schema = {
  file_name: { type: 'string', required: true, max: 500 },
  source_lang: { type: 'string', required: true, pattern: /^[a-z]{2}$/ },
  target_lang: { type: 'string', required: true, pattern: /^[a-z]{2}$/ },
  priority: { type: 'number', min: 1, max: 10 }
};

for (const [field, rules] of Object.entries(schema)) {
  if (rules.required && !payload[field]) {
    throw new Error(`Missing required field: ${field}`);
  }
  if (payload[field] && typeof payload[field] !== rules.type) {
    throw new Error(`Invalid type for ${field}`);
  }
  if (payload[field] && rules.max && payload[field].length > rules.max) {
    throw new Error(`Field ${field} exceeds max length`);
  }
}

return { json: { valid: true, payload } };
```

**Результат:** Better security, prevent injection

#### 5.3. Implement rate limiting для Telegram

**Current:** Potentially unlimited sending
**Proposed:** Rate limiting queue

```javascript
// Code node: Rate Limiter
const RATE_LIMIT = 30; // messages per minute
const WINDOW = 60000; // 1 minute

const now = Date.now();
const recentMessages = $workflow.staticData.sentMessages || [];
const recentInWindow = recentMessages.filter(t => now - t < WINDOW);

if (recentInWindow.length >= RATE_LIMIT) {
  // Queue for later
  return { json: { queued: true, retry_after: WINDOW - (now - recentInWindow[0]) } };
}

// Send and record
recentInWindow.push(now);
$workflow.staticData.sentMessages = recentInWindow;

return { json: { queued: false, can_send: true } };
```

**Результат:** Prevent Telegram API bans

---

## Фаза 6: Documentation (1-2 дня)

### Задачи

#### 6.1. Создать README для каждого workflow

**Template:**
```markdown
# Workflow: [Name]

## Description
[Brief description]

## Trigger
[Type, configuration]

## Inputs
| Field | Type | Required | Description |
|-------|------|----------|-------------|

## Outputs
| Field | Type | Description |
|-------|------|-------------|

## Dependencies
- [List of dependencies]

## Error Handling
[How errors are handled]

## Usage Example
[Example usage]
```

#### 6.2. Обновить PROJECT_DOCS.md

- Актуализировать статистику
- Добавить новые workflows
- Обновить диаграммы

#### 6.3. Создать CHANGELOG.md

```markdown
# Changelog

## [Unreleased]

### Added
- [Master] Translation Pipeline workflow
- [Utils] Shared utility workflows
- Health Check workflow
- Automated backups

### Changed
- Consolidated task_* workflows
- Optimized SQL queries
- Added retry logic

### Deprecated
- Individual task_* workflows (use task_format_message)

### Removed
- Archived 11 deprecated workflows
```

---

# Детальные задачи

## Sprint 1 (Дни 1-2): Cleanup

- [ ] 1.1.1. Создать backup всех workflows
- [ ] 1.1.2. Архивировать 11 deprecated workflows
- [ ] 1.1.3. Проверить что активные workflows работают
- [ ] 1.2.1. Добавить descriptions к workflows без описания
- [ ] 1.2.2. Проверить accuracy описаний
- [ ] 1.3.1. Создать директорию /backups
- [ ] 1.3.2. Экспорт workflows в /backups
- [ ] 1.3.3. Backup БД в /backups

## Sprint 2 (Дни 3-5): Consolidation

- [ ] 2.1.1. Создать task_format_message workflow
- [ ] 2.1.2. Протестировать task_format_message
- [ ] 2.1.3. Обновить Send Message для использования нового workflow
- [ ] 2.1.4. Deactivate старые task_* workflows
- [ ] 2.2.1. Спроектировать [Master] Translation Pipeline
- [ ] 2.2.2. Создать [Master] Translation Pipeline
- [ ] 2.2.3. Протестировать pipeline на тестовом документе
- [ ] 2.3.1. Создать [Utils] SQL Executor
- [ ] 2.3.2. Создать [Utils] Telegram Sender
- [ ] 2.3.3. Создать [Utils] Error Logger
- [ ] 2.3.4. Создать [Utils] Retry Handler

## Sprint 3 (Дни 6-8): Optimization

- [ ] 3.1.1. Создать индексы в БД
- [ ] 3.1.2. Проверить query plans
- [ ] 3.1.3. Оптимизировать медленные запросы
- [ ] 3.2.1. Реализовать caching в sub_get_context
- [ ] 3.2.2. Протестировать caching
- [ ] 3.3.1. Настроить connection pooling в n8n
- [ ] 3.3.2. Load testing для проверки

## Sprint 4 (Дни 9-11): Reliability

- [ ] 4.1.1. Настроить Crontab UI
- [ ] 4.1.2. Создать backup jobs
- [ ] 4.1.3. Протестировать restore из backup
- [ ] 4.2.1. Создать Health Check workflow
- [ ] 4.2.2. Настроить schedule (5 min)
- [ ] 4.2.3. Протестировать alerting
- [ ] 4.3.1. Добавить retry logic к API calls
- [ ] 4.3.2. Протестировать retry при сбоях
- [ ] 4.4.1. Настроить alert conditions
- [ ] 4.4.2. Протестировать alerts

## Sprint 5 (Дни 12-13): Security

- [ ] 5.1.1. Audit workflows на hardcoded credentials
- [ ] 5.1.2. Создать credentials в n8n
- [ ] 5.1.3. Обновить workflows
- [ ] 5.2.1. Добавить validation к webhook endpoints
- [ ] 5.2.2. Протестировать validation
- [ ] 5.3.1. Реализовать rate limiting
- [ ] 5.3.2. Протестировать rate limiting

## Sprint 6 (Дни 14-15): Documentation

- [ ] 6.1.1. Создать README для каждого workflow
- [ ] 6.1.2. Обновить WORKFLOW_MAP.md
- [ ] 6.2.1. Актуализировать PROJECT_DOCS.md
- [ ] 6.2.2. Обновить ARCHITECTURE.md
- [ ] 6.3.1. Создать CHANGELOG.md
- [ ] 6.3.2. Обновить всю документацию

---

# Оценка рисков

## Высокий риск

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Потеря данных при рефакторинге | LOW | HIGH | Full backup перед изменениями |
| Breaking changes в workflows | MEDIUM | HIGH | Test на staging environment |
| Downtime при деплое | MEDIUM | MEDIUM | Deploy в off-peak hours |
| Ошибки в consolidation | MEDIUM | MEDIUM | Unit tests для новых workflows |

## Средний риск

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Performance regression | LOW | MEDIUM | Load testing после изменений |
| Credential migration issues | MEDIUM | MEDIUM | Тестировать на 1 workflow сначала |
| User confusion from changes | LOW | LOW | Документация и changelog |

## Низкий риск

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Documentation outdated | MEDIUM | LOW | Regular review process |
| New bugs introduced | MEDIUM | LOW | Testing protocol |

---

# Метрики успеха

## Количественные метрики

| Метрика | Before | After | Измерение |
|---------|--------|-------|-----------|
| Workflows total | 55 | 40 | `SELECT COUNT(*) FROM workflow_entity` |
| Workflows active | 33 | 35 | `SELECT COUNT(*) FROM workflow_entity WHERE active=true` |
| Workflows archived | 0 | 15 | `SELECT COUNT(*) FROM workflow_entity WHERE "isArchived"=true` |
| Nodes in task_* | 36 | 12 | Count nodes in workflows |
| SQL queries per translation | ~15 | ~10 | Count in workflow execution |
| Backup frequency | Manual | Every 6h | Crontab schedule |
| Health check interval | None | Every 5m | Workflow schedule |
| Workflows with error handling | ~15 | 100% | Audit workflows |
| Workflows with documentation | ~20 | 100% | Audit workflows |

## Качественные метрики

- [ ] Все workflows имеют descriptions
- [ ] Все API calls имеют retry logic
- [ ] Все webhook endpoints имеют validation
- [ ] Все credentials в Credentials Manager
- [ ] Автоматические backups работают
- [ ] Health check alerting работает
- [ ] Rate limiting предотвращает bans
- [ ] Documentation актуальна и полна

## Performance метрики

- [ ] -30% SQL query time
- [ ] -50% DB queries for cached data
- [ ] < 5 min error detection time
- [ ] < 15 min MTTR
- [ ] 99.9% uptime (после рефакторинга)

---

# Timeline

```
Week 1: [████████░░░░░░░░] Cleanup + Consolidation (Days 1-5)
Week 2: [░░░░████████░░░░] Optimization + Reliability (Days 6-11)
Week 3: [░░░░░░░░████░░░░] Security + Documentation (Days 12-15)
```

**Total estimated time:** 15 working days
**Start date:** TBD
**End date:** TBD + 15 days

---

# Approval

| Роль | Имя | Дата | Подпись |
|------|-----|------|---------|
| Project Owner | Алексей (bigalex) | | |
| Lead Developer | TBD | | |
| QA Engineer | TBD | | |

---

**Документ создан:** 9 апреля 2026 г.
**Статус:** На утверждении
**Следующая проверка:** После approval
