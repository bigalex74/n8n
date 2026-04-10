# ⚠️ Проблемы и рекомендации - n8n Translation System

**Дата:** 9 апреля 2026 г.
**Версия:** 1.0
**Приоритет:** HIGH
**Статус:** На рассмотрении

---

# Содержание

1. [Критичные проблемы (P0)](#критичные-проблемы-p0)
2. [Важные проблемы (P1)](#важные-проблемы-p1)
3. [Улучшения (P2)](#улучшения-p2)
4. [Технический долг](#технический-долг)
5. [Рекомендации по развитию](#рекомендации-по-развитию)
6. [Best Practices](#best-practices)
7. [Чек-лист для immediate actions](#чек-лист-для-immediate-actions)

---

# Критичные проблемы (P0)

## P0-1: Отсутствие автоматических бэкапов

**Статус:** 🔴 КРИТИЧНО
**Влияние:** Риск полной потери данных
**Текущее состояние:**
- Есть только ручной скрипт `backup_n8n.sh`
- Нет автоматического расписания
- Нет external storage для бэкапов
- Нет тестирования restore procedure

**Риск:**
- При сбое диска/сервера → полная потеря данных
- Workflow конфигурации, credentials, execution history
- База данных с документами, пользователями, настройками

**Рекомендация:**
```bash
# 1. Создать автоматический backup cron
# Использовать Crontab UI (http://localhost:8001)

# Backup БД каждые 6 часов
0 */6 * * * docker exec n8n-docker-db-1 pg_dump -U n8n_user n8n_database | gzip > /backups/db_$(date +\%Y\%m\%d_\%H\%M).sql.gz

# Экспорт workflows ежедневно в полночь
0 0 * * * docker exec n8n-docker-n8n-1 n8n export:workflow --all --output=/backups/workflows_$(date +\%Y\%m\%d).json

# Очистка старых бэкапов (хранить 30 дней)
0 1 * * * find /backups -type f -mtime +30 -delete
```

**Дополнительно:**
- Настроить offsite backup (rsync на другой сервер / cloud storage)
- Еженедельно тестировать restore procedure
- Мониторить размер бэкапов (alert если 0 bytes)

**Время реализации:** 2-3 часа
**Сложность:** LOW

---

## P0-2: Нет error handling в критичных workflows

**Статус:** 🔴 КРИТИЧНО
**Влияние:** Тихие failures, потеря данных, ручное вмешательство
**Текущее состояние:**
- Только 1 Global Error Handler активен
- Многие workflows без error nodes
- API calls без retry logic
- Нет alerting при ошибках

**Примеры проблем:**
```
[Перевод] Перевод чанка
├── Вызов LightRAG API → если fail → chunk остается pending
├── Вызов Ollama API → если timeout → no retry
└── Save to DB → если error → data lost
```

**Рекомендация:**

1. **Добавить Error Trigger к каждому workflow:**
```javascript
// Error Handler node
const error = $input.first().json.error;
const workflowName = $workflow.name;

// Log error
await logError({
  workflow: workflowName,
  error: error.message,
  timestamp: new Date().toISOString(),
  severity: 'critical'
});

// Send alert
await sendTelegramAlert(`❌ Error in ${workflowName}: ${error.message}`);

// Retry if retryable
if (isRetryable(error)) {
  return { retry: true, delay: calculateBackoff() };
}

return { retry: false, action: 'manual_intervention' };
```

2. **Реализовать retry с exponential backoff:**
```javascript
async function withRetry(fn, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (e) {
      if (i === maxRetries - 1) throw e;
      const delay = 1000 * Math.pow(2, i); // 1s, 2s, 4s
      await sleep(delay);
    }
  }
}
```

3. **Создать Dead Letter Queue таблицу:**
```sql
CREATE TABLE failed_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operation_type VARCHAR(100),
    payload JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    next_retry_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(100)
);

CREATE INDEX idx_failed_operations_retry 
ON failed_operations(next_retry_at) 
WHERE resolved_at IS NULL;
```

**Время реализации:** 1-2 дня
**Сложность:** MEDIUM

---

## P0-3: Hardcoded credentials в workflows

**Статус:** 🔴 КРИТИЧНО (Security)
**Влияние:** Утечка secrets при экспорте workflow
**Текущее состояние:**
- Potentially hardcoded tokens (Telegram, API keys)
- Encryption key в `.env` файле
- Нет ротации credentials

**Найденные credentials:**
```
Telegram Bot Token: 8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0
n8n Encryption Key: InqHY6REAuKYfnqDgmmcZGuSnLZJFl90
polza.ai API Key: pza_PV5t0y6PTuE8GLcZ-jgvlpNDLlZm0mUT
DB Password: n8n_db_password (в .env)
```

**Риск:**
- При экспорте workflow → tokens в JSON файле
- При commit в Git → утечка в repository
- При доступе к серверу → все credentials

**Рекомендация:**

1. **Использовать n8n Credentials Manager:**
```javascript
// НЕПРАВИЛЬНО:
const token = '8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0';

// ПРАВИЛЬНО:
const credentials = await $credentials.get('telegramApi');
const token = credentials.token;
```

2. **Создать credentials в n8n UI:**
- Telegram Bot API
- polza.ai API
- PostgreSQL (для custom queries)
- Google Drive (для backup)

3. **Обновить все workflows:**
```bash
# Audit workflows на hardcoded credentials
docker exec n8n-docker-db-1 psql -U n8n_user -d n8n_database -c \
  "SELECT name, nodes FROM workflow_entity WHERE nodes::text ~ '[0-9]{8,}:[A-Za-z0-9_-]{20,}'";
```

4. **Ротация credentials:**
- Сгенерировать новый Telegram Bot Token через BotFather
- Создать новый API key на polza.ai
- Обновить пароль БД

**Время реализации:** 4-6 часов
**Сложность:** MEDIUM

---

## P0-4: Отсутствие health monitoring

**Статус:** 🔴 КРИТИЧНО
**Вляние:** Позднее обнаружение проблем, downtime
**Текущее состояние:**
- Grafana dashboard есть, но нет alerting
- Prometheus собирает метрики, но нет alert rules
- Нет health checks для сервисов
- Нет автоматического restart при сбоях

**Рекомендация:**

1. **Создать Health Check workflow:**
```yaml
Workflow: [System] Health Check
Trigger: Schedule (every 5 minutes)
Checks:
  - PostgreSQL: SELECT 1
  - LightRAG: GET /health
  - Ollama: POST /api/generate (test prompt)
  - Telegram: GET /botTOKEN/getMe
  - Disk space: df -h / (alert if < 20%)
  - Memory: free -m (alert if > 90%)
  - n8n: HTTP GET localhost:5678/healthz
```

2. **Настроить Grafana alerts:**
```yaml
Alert Rules:
  - High error rate: > 10 errors in 5 minutes → Telegram alert
  - Workflow failures: > 5 failed executions in 10 minutes → Telegram
  - Disk space: < 20% → Telegram + email
  - Memory: > 90% → Telegram + email
  - Backup failed: if backup file not created → Telegram
  - Service down: health check failed → Telegram + auto-restart
```

3. **Создать auto-restart скрипт:**
```bash
#!/bin/bash
# /scripts/auto_restart.sh

SERVICES=("n8n-docker-n8n-1" "n8n-docker-db-1" "ollama" "lightrag")

for service in "${SERVICES[@]}"; do
  if ! docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
    echo "$(date): $service is down, restarting..." >> /var/log/auto_restart.log
    docker restart $service
    echo "$(date): $service restarted" >> /var/log/auto_restart.log
    
    # Send alert
    curl -s "https://api.telegram.org/botTOKEN/sendMessage" \
      -d "chat_id=923741104" \
      -d "text=⚠️ Service $service was restarted automatically"
  fi
done
```

**Время реализации:** 1 день
**Сложность:** MEDIUM

---

# Важные проблемы (P1)

## P1-1: Дублирование task_* workflows

**Статус:** 🟠 ВАЖНО
**Влияние:** Сложность поддержки, баги в нескольких местах
**Текущее состояние:**
- 6 отдельных workflows: task_create, task_start, task_process, task_error, task_finish, task_stop
- Одинаковая структура (6 nodes each)
- Total: 36 nodes для поддержки
- При изменении формата → править во всех 6 местах

**Рекомендация:**
- Консолидировать в 1 параметризированный workflow
- См. REFACTORING_PLAN.md section 2.1
- Экономия: 36 → 12 nodes (67% reduction)

**Время реализации:** 4-6 часов
**Сложность:** LOW

---

## P1-2: Неактивные критичные workflows

**Статус:** 🟠 ВАЖНО
**Влияние:** Путаница, потенциальные ошибки
**Текущее состояние:**
- `sub_get_context` - inactive, но вызывается через Execute Workflow node
- `sub_notify` - inactive, но вызывается через Execute Workflow node
- 6 task_* workflows - inactive, но вызываются через Execute Workflow nodes

**Проблема:**
- Непонятно active ли workflow или нет
- При попытке активации → потенциальные конфликты
- Новый разработчик может подумать что workflow deprecated

**Рекомендация:**

1. **Активировать workflows которые используются:**
```sql
UPDATE workflow_entity 
SET active = true 
WHERE name IN ('sub_get_context', 'sub_notify');
```

2. **Добавить description что workflow вызывается через Execute node:**
```
Description: "Context provider workflow. Called via Execute Workflow node from Send Message orchestrator. Do not deactivate."
```

3. **Создать документацию с dependency map:**
- См. WORKFLOW_MAP.md

**Время реализации:** 1-2 часа
**Сложность:** LOW

---

## P1-3: Отсутствие documentation для workflows

**Статус:** 🟠 ВАЖНО
**Влияние:** Сложно onboard, трудно debug
**Текущее состояние:**
- Многие workflows без description поля
- Нет документации по inputs/outputs
- Неясны зависимости между workflows

**Рекомендация:**

1. **Добавить descriptions через SQL:**
```sql
-- Batch update descriptions
UPDATE workflow_entity SET description = '[Pipeline] Processes document arcs (groups of chapters). Calls chapter translation in parallel.' WHERE name = '[Перевод] Арка';
UPDATE workflow_entity SET description = '[Pipeline] Translates individual chapter. Uses LightRAG for context, Ollama for translation.' WHERE name = '[Перевод] Глава';
UPDATE workflow_entity SET description = '[Pipeline] Translates single text chunk. Core translation unit with retry logic.' WHERE name = '[Перевод] Перевод чанка';
-- ... для всех 55 workflows
```

2. **Создать README для каждого workflow:**
- См. шаблон в REFACTORING_PLAN.md section 6.1

3. **Создать workflow catalog:**
```markdown
# Workflow Catalog

## Pipeline Workflows
| Name | Description | Trigger | Inputs | Outputs | Dependencies |
|------|-------------|---------|--------|---------|--------------|
| [Перевод] Арка | Processes document arcs | Execute | arc_id, job_id | arc_status | document_arcs |
| ... | ... | ... | ... | ... | ... |
```

**Время реализации:** 1-2 дня
**Сложность:** LOW (but tedious)

---

## P1-4: Неоптимизированные SQL запросы

**Статус:** 🟠 ВАЖНО
**Влияние:** Медленная performance при масштабировании
**Текущее состояние:**
- Potential N+1 queries (fetch job, then fetch chunks one by one)
- Отсутствуют индексы на часто используемых columns
- sub_get_context уже оптимизирован (1 query вместо 3) ✅

**Рекомендация:**

1. **Добавить индексы:**
```sql
-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_document_jobs_status ON document_jobs(status);
CREATE INDEX IF NOT EXISTS idx_document_jobs_created ON document_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_document_jobs_updated ON document_jobs(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_document_chunks_job_status ON document_chunks(job_id, status);
CREATE INDEX IF NOT EXISTS idx_document_chunks_status ON document_chunks(status);
CREATE INDEX IF NOT EXISTS idx_document_chunks_job_index ON document_chunks(job_id, chunk_index);

CREATE INDEX IF NOT EXISTS idx_document_log_job_date ON document_log(job_id, date_time DESC);
CREATE INDEX IF NOT EXISTS idx_document_log_type ON document_log(type, date_time DESC);

CREATE INDEX IF NOT EXISTS idx_telegram_send_message_chat ON telegram_send_message(chat_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_telegram_send_message_status ON telegram_send_message(status);

-- Analyze tables
ANALYZE document_jobs;
ANALYZE document_chunks;
ANALYZE document_log;
ANALYZE telegram_send_message;
```

2. **Использовать EXPLAIN ANALYZE для медленных запросов:**
```sql
EXPLAIN ANALYZE
SELECT j.*, 
       (SELECT COUNT(*) FROM document_chunks WHERE job_id = j.id) as chunks_total,
       (SELECT COUNT(*) FROM document_chunks WHERE job_id = j.id AND status = 'done') as chunks_done
FROM document_jobs j
WHERE j.id = 1;
```

3. **Добавить caching для повторяющихся данных:**
```javascript
// Cache glossary terms per job
const cache = $workflow.staticData.cache || {};
const key = `glossary_${job_id}`;

if (cache[key] && (Date.now() - cache[key].timestamp < 3600000)) {
  return { json: { cached: true, data: cache[key].data } };
}

// Fetch and cache
const glossary = await fetchGlossary(job_id);
cache[key] = { data: glossary, timestamp: Date.now() };
$workflow.staticData.cache = cache;
```

**Время реализации:** 4-6 часов
**Сложность:** MEDIUM

---

## P1-5: Отсутствие rate limiting для Telegram

**Статус:** 🟠 ВАЖНО
**Влияние:** Potential ban от Telegram API
**Текущее состояние:**
- Нет ограничения на отправку сообщений
- Telegram limits: 30 messages/second per bot, 20 messages/minute to same chat
- При интенсивной обработке → риск rate limit exceeded

**Рекомендация:**

1. **Добавить rate limiting queue:**
```javascript
// Rate limiter utility
const RATE_LIMITS = {
  per_second: 30,
  per_minute_per_chat: 20,
  retry_after: 60000 // 1 minute
};

async function sendWithRateLimit(chatId, message) {
  const now = Date.now();
  const key = `rate_${chatId}`;
  
  const sent = $workflow.staticData.sentMessages || {};
  const recent = (sent[key] || []).filter(t => now - t < 60000);
  
  if (recent.length >= RATE_LIMITS.per_minute_per_chat) {
    // Queue for later
    return { 
      queued: true, 
      retry_after: 60000 - (now - recent[0]),
      message 
    };
  }
  
  // Send message
  const result = await telegram.sendMessage(chatId, message);
  
  // Record
  recent.push(now);
  sent[key] = recent;
  $workflow.staticData.sentMessages = sent;
  
  return { queued: false, result };
}
```

2. **Использовать editMessageText вместо send для updates:**
- Уже реализовано в sub_notify ✅
- Убедиться что используется везде

**Время реализации:** 2-3 часа
**Сложность:** LOW

---

# Улучшения (P2)

## P2-1: Добавить workflow tags

**Статус:** 🟡 УЛУЧШЕНИЕ
**Влияние:** Упрощение навигации и фильтрации
**Текущее состояние:**
- 55 workflows без категоризации
- Сложно найти workflows по типу

**Рекомендация:**
```sql
-- Add tags (when n8n supports)
-- Pipeline: [Перевод] workflows
-- Notification: Send Message, task_*, sub_*
-- Telegram: Telegram Trigger, Перезапуск, Получение
-- System: Health Check, Proxy Check, Error Handler
-- Utility: Translate Chunk, Select From List
-- File: [GET] endpoints, export workflows
-- Resource: Glossary, Prompts, DB setup
```

**Время реализации:** 1-2 часа
**Сложность:** LOW

---

## P2-2: Создать workflow для DB maintenance

**Статус:** 🟡 УЛУЧШЕНИЕ
**Влияние:** Better DB performance over time
**Текущее состояние:**
- Нет автоматического VACUUM/ANALYZE
- Нет очистки старых logs
- Нет архивации completed jobs

**Рекомендация:**

```yaml
Workflow: [System] DB Maintenance
Trigger: Schedule (weekly)
Tasks:
  - VACUUM ANALYZE document_jobs
  - VACUUM ANALYZE document_chunks
  - VACUUM ANALYZE document_log
  - Archive old completed jobs (> 90 days)
  - Delete old logs (> 180 days)
  - Update table statistics
  - Send report
```

**SQL:**
```sql
-- Weekly maintenance
VACUUM ANALYZE document_jobs;
VACUUM ANALYZE document_chunks;
VACUUM ANALYZE document_log;

-- Archive old jobs
INSERT INTO document_jobs_archive 
SELECT * FROM document_jobs 
WHERE status = 'completed' AND finished_at < NOW() - INTERVAL '90 days';

DELETE FROM document_jobs 
WHERE status = 'completed' AND finished_at < NOW() - INTERVAL '90 days';

-- Clean old logs
DELETE FROM document_log 
WHERE date_time < NOW() - INTERVAL '180 days';
```

**Время реализации:** 3-4 часа
**Сложность:** LOW

---

## P2-3: Добавить audit logging

**Статус:** 🟡 УЛУЧШЕНИЕ
**Влияние:** Better traceability, security
**Текущее состояние:**
- Нет записи кто/что изменил
- Нет истории изменений workflows
- Нет audit trail для critical operations

**Рекомендация:**

1. **Создать audit log таблицу:**
```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    user_id VARCHAR(100),
    action VARCHAR(100),
    entity_type VARCHAR(100),
    entity_id VARCHAR(100),
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
```

2. **Создать triggers для audit:**
```sql
CREATE OR REPLACE FUNCTION audit_document_jobs()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO audit_log (action, entity_type, entity_id, old_value, new_value)
  VALUES (
    TG_OP,
    'document_jobs',
    COALESCE(NEW.id, OLD.id)::VARCHAR,
    row_to_json(OLD)::JSONB,
    row_to_json(NEW)::JSONB
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_document_jobs
AFTER INSERT OR UPDATE OR DELETE ON document_jobs
FOR EACH ROW EXECUTE FUNCTION audit_document_jobs();
```

**Время реализации:** 4-6 часов
**Сложность:** MEDIUM

---

## P2-4: Реализовать graceful degradation

**Статус:** 🟡 УЛУЧШЕНИЕ
**Влияние:** Better resilience during partial failures
**Текущее состояние:**
- Если LightRAG down → translation fails
- Если Ollama down → quality check fails
- Нет fallback mechanisms

**Рекомендация:**

1. **Add fallback для LightRAG:**
```javascript
// Translation with fallback
try {
  const context = await queryLightRAG(query);
  return translateWithOllama(text, context);
} catch (e) {
  // Fallback: translate without RAG context
  console.warn('LightRAG unavailable, using fallback');
  return translateWithOllama(text, null);
}
```

2. **Add fallback для Ollama:**
```javascript
// Use external API if Ollama down
try {
  return await ollama.generate(model, prompt);
} catch (e) {
  // Fallback to external LLM
  console.warn('Ollama unavailable, using fallback');
  return await externalLLM.generate(model, prompt);
}
```

3. **Circuit breaker pattern:**
```javascript
class CircuitBreaker {
  constructor(failureThreshold = 5, resetTimeout = 60000) {
    this.failures = 0;
    this.threshold = failureThreshold;
    this.timeout = resetTimeout;
    this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
  }
  
  async execute(fn) {
    if (this.state === 'OPEN') {
      throw new Error('Circuit breaker OPEN');
    }
    
    try {
      const result = await fn();
      this.failures = 0;
      this.state = 'CLOSED';
      return result;
    } catch (e) {
      this.failures++;
      if (this.failures >= this.threshold) {
        this.state = 'OPEN';
        setTimeout(() => this.state = 'HALF_OPEN', this.timeout);
      }
      throw e;
    }
  }
}
```

**Время реализации:** 1-2 дня
**Сложность:** HIGH

---

# Технический долг

## TD-1: Смешанные версии workflows

**Описание:** Есть старые и новые версии одних и тех же workflows
**Пример:** `[depricated] Send Message (RESTORED)` vs `Send Message`
**Рекомендация:** Удалить старые версии после тестирования новых

---

## TD-2: Отсутствие тестов для workflows

**Описание:** Нет unit/integration tests
**Рекомендация:** Создать test workflows с Pin Data для mocking

---

## TD-3: Hardcoded IDs в workflows

**Описание:** Workflow IDs, chat IDs hardcoded
**Рекомендация:** Вынести в environment variables или settings table

---

## TD-4: Отсутствие API versioning

**Описание:** Webhook endpoints без версионирования
**Рекомендация:** `/webhook/v1/telegram`, `/webhook/v2/translation`

---

# Рекомендации по развитию

## R-1: Масштабирование

### Горизонтальное масштабирование
- Multiple n8n instances за load balancer
- Separate workers для translation jobs
- Queue-based processing (RabbitMQ/Redis)

### Вертикальное масштабирование
- Увеличить RAM для Ollama (большие модели)
- GPU upgrade для faster inference
- SSD для БД (если еще не используется)

---

## R-2: Multi-language support

### Текущее: KO → RU
### Будущее: Any → Any
- Добавить поддержку EN, JA, ZH, и др.
- Language detection из файла
- Model selection based on language pair

---

## R-3: Web UI для управления

### Features:
- Upload documents
- Monitor progress
- Review glossary
- Download translations
- Manage settings

### Tech stack:
- Frontend: React/Next.js
- Backend: n8n webhooks
- Auth: n8n credentials

---

## R-4: Analytics dashboard

### Metrics to track:
- Translation quality over time
- Most common errors
- User activity
- Cost per document
- Processing time trends

---

# Best Practices

## Разработка workflows

1. **Naming Convention:**
   ```
   [Category] Description - Environment
   Examples:
   - [Pipeline] File Parsing - Production
   - [Notification] Telegram Sender - Production
   - [Utils] Retry Handler - Production
   ```

2. **Error Handling:**
   - Every workflow должен иметь error handler
   - Log errors в БД
   - Alert на critical errors
   - Retry на transient failures

3. **Documentation:**
   - Description поле всегда заполнено
   - Inputs/outputs документированы
   - Dependencies указаны

4. **Testing:**
   - Test с Pin Data перед deploy
   - Integration tests для pipelines
   - Load tests для critical paths

---

## Операционные best practices

1. **Backups:**
   - Автоматические каждые 6 часов
   - Offsite storage
   - Еженедельное тестирование restore

2. **Monitoring:**
   - Health checks every 5 minutes
   - Alerts в Telegram
   - Grafana dashboards

3. **Security:**
   - Credentials в n8n Credentials Manager
   - Input validation на всех endpoints
   - Rate limiting для external APIs
   - Regular credential rotation

4. **Performance:**
   - DB indexes на часто используемых columns
   - Caching для повторяющихся данных
   - Connection pooling
   - Query optimization

---

# Чек-лист для immediate actions

## Сегодня (1-2 часа)

- [ ] Создать backup БД и workflows
- [ ] Проверить что backups работают
- [ ] Активировать sub_get_context и sub_notify (если используются)
- [ ] Добавить descriptions к workflows без них

## Эта неделя (1-2 дня)

- [ ] Настроить автоматические бэкапы (Crontab UI)
- [ ] Создать Health Check workflow
- [ ] Настроить alerting в Telegram
- [ ] Архивировать deprecated workflows
- [ ] Добавить индексы в БД

## Этот месяц (1-2 недели)

- [ ] Consolidate task_* workflows
- [ ] Создать [Master] Translation Pipeline
- [ ] Добавить retry logic к API calls
- [ ] Реализовать rate limiting
- [ ] Migrate credentials to n8n Credentials Manager
- [ ] Создать полную документацию

---

# Summary

## Приоритеты

| Приоритет | Проблем | Время | Влияние |
|-----------|---------|-------|---------|
| P0 (Critical) | 4 | 2-3 дня | HIGH |
| P1 (Important) | 5 | 3-4 дня | MEDIUM |
| P2 (Nice to have) | 4 | 2-3 дня | LOW |
| Technical Debt | 4 | Ongoing | MEDIUM |

## Общий effort

- **Minimum (P0 only):** 2-3 дня
- **Recommended (P0 + P1):** 5-7 дней
- **Full (All priorities):** 2-3 недели

## ROI

После выполнения всех рекомендаций:
- ✅ 99.9% uptime (vs current unknown)
- ✅ < 5 min error detection (vs manual)
- ✅ < 15 min MTTR (vs hours)
- ✅ 67% меньше nodes для поддержки
- ✅ 100% workflows с документацией
- ✅ Automated backups (vs manual)
- ✅ Zero hardcoded credentials

---

**Документ создан:** 9 апреля 2026 г.
**Автор:** AI Architecture Team
**Статус:** На рассмотрении
**Следующая проверка:** После approval и планирования спринтов
