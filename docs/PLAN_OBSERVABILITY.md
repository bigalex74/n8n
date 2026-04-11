# 📋 Plan: Observability & Resilience for Translation Pipeline

**Дата:** 10 апреля 2026 г.  
**Автор:** AI Architect Team (prime → architect → researcher)  
**Статус:** На утверждении

---

# Обзор

Система из 3 таблиц для полного observability + resilience:

```
pipeline_execution_log  ← каждая нода каждого workflow
pipeline_metrics        ← 5-минутные агрегаты для Grafana
circuit_breaker_state   ← состояние Ollama/LightRAG/Telegram
dead_letter_queue       ← проваленные задачи для ручного разбора
health_check_log        ← результаты health checks
```

---

# Что собираем

## n8n Execution Level
| Метрика | Источник | Частота |
|---------|----------|---------|
| Workflow execution | execution_entity (существует) | Каждый запуск |
| Node execution | pipeline_execution_log (новая) | Каждая нода |
| Latency (p50/p95/p99) | pipeline_metrics (новая) | 5 минут |
| Error rate | pipeline_metrics (новая) | 5 минут |

## Translation Pipeline Level
| Метрика | Источник | Частота |
|---------|----------|---------|
| Chapter translation time | document_chunks.updated_at + document_jobs | Каждый чанк |
| Words translated | document_chunks.character_count | Каждый чанк |
| Translation quality score | document_chunks.quality_score | Каждая глава |
| API call latency | pipeline_execution_log (metadata) | Каждый вызов |

## Infrastructure Level
| Метрика | Источник | Частота |
|---------|----------|---------|
| Ollama health | health_check_log | 1 минута |
| LightRAG health | health_check_log | 1 минута |
| Circuit breaker state | circuit_breaker_state | Real-time |
| DLQ size | dead_letter_queue | Real-time |

---

# Grafana Dashboard Plan

## Row 1: Overview (KPI Cards)
| Панель | Тип | SQL |
|--------|-----|-----|
| Total executions (24h) | Stat | `SELECT COUNT(*) FROM pipeline_execution_log WHERE started_at > NOW() - INTERVAL '24h'` |
| Success rate | Stat | `SELECT ROUND(AVG(CASE WHEN status='success' THEN 1 ELSE 0 END)*100, 1) FROM pipeline_execution_log WHERE started_at > NOW() - INTERVAL '24h'` |
| P95 latency | Stat | `SELECT p95_latency_ms FROM pipeline_metrics ORDER BY window_end DESC LIMIT 1` |
| Active DLQ | Stat | `SELECT COUNT(*) FROM dead_letter_queue WHERE status = 'pending'` |
| Circuit breaker status | Stat | `SELECT entity_name, state FROM circuit_breaker_state` |

## Row 2: Workflow Visualization (n8n-like UI)
| Панель | Тип | Описание |
|--------|-----|----------|
| Workflow Flow Diagram | Canvas/Nodes | Workflows как блоки, стрелки — вызовы через Execute Workflow |
| Node Execution Heatmap | Heatmap | Цвет = latency, размер = call count |
| Execution Timeline | State Timeline | Каждый execution = полоска, цвет = status, длина = duration |

## Row 3: Performance
| Панель | Тип | SQL |
|--------|-----|-----|
| Latency over time | Time series | `SELECT window_end as time, p50_latency_ms, p95_latency_ms, p99_latency_ms FROM pipeline_metrics` |
| Throughput | Time series | `SELECT window_end as time, executions_per_min FROM pipeline_metrics` |
| Top slow workflows | Bar chart | `SELECT workflow_name, AVG(duration_ms) FROM pipeline_execution_log WHERE started_at > NOW()-INTERVAL '24h' GROUP BY workflow_name ORDER BY AVG DESC LIMIT 10` |
| API call latency (Ollama/LightRAG) | Time series | `SELECT started_at as time, duration_ms FROM pipeline_execution_log WHERE node_type IN ('httpRequest') AND metadata->>'api' = 'ollama'` |

## Row 4: Errors & Dead Letter Queue
| Панель | Тип | SQL |
|--------|-----|-----|
| Errors over time | Time series | `SELECT started_at as time, COUNT(*) FROM pipeline_execution_log WHERE status='error' GROUP BY 1` |
| Errors by type | Pie chart | `SELECT error_type, COUNT(*) FROM pipeline_execution_log WHERE status='error' AND started_at > NOW()-INTERVAL '24h' GROUP BY error_type` |
| DLQ items | Table | `SELECT * FROM dead_letter_queue WHERE status='pending' ORDER BY created_at DESC` |
| Top failing workflows | Bar chart | `SELECT workflow_name, COUNT(*) FROM pipeline_execution_log WHERE status='error' GROUP BY workflow_name ORDER BY COUNT DESC LIMIT 10` |

## Row 5: Health & Circuit Breaker
| Панель | Тип | SQL |
|--------|-----|-----|
| Circuit breaker states | Table | `SELECT entity_name, state, failure_count, last_failure_at FROM circuit_breaker_state` |
| Health checks over time | State timeline | `SELECT checked_at as time, entity_name, status FROM health_check_log ORDER BY checked_at DESC` |
| Last failures | Table | `SELECT * FROM health_check_log WHERE status != 'ok' ORDER BY checked_at DESC LIMIT 20` |

---

# Alerting Plan

## Critical (Telegram + email)
| Алерт | Условие | Действие |
|-------|---------|----------|
| Ollama circuit breaker OPEN | Circuit breaker state = 'open' | Alert, fallback to polza.ai |
| Pipeline error rate > 20% | >20% executions fail в 5 мин | Alert, investigate |
| DLQ size > 50 | dead_letter_queue pending > 50 | Alert, manual triage |
| Any health check down | health_check status != 'ok' 3 раза подряд | Alert, restart service |

## Warning (Telegram)
| Алерт | Условие | Действие |
|-------|---------|----------|
| P95 latency > 10s | p95_latency_ms > 10000 | Monitor, check resources |
| Translation quality < 7.0 | avg_quality_score < 7.0 | Review prompts |
| Ollama call latency > 30s | ollama_avg_ms > 30000 | Check Ollama load |
| LightRAG errors > 5/5min | lightrag_errors > 5 | Check LightRAG health |
| Chapter translation fails | document_chunks error_text IS NOT NULL | Retry or investigate |

## Info (Log only)
| Алерт | Условие |
|-------|---------|
| Workflow executed | execution_entity INSERT |
| Job completed | document_jobs status = 'completed' |
| Circuit breaker half-open | state = 'half_open' |

---

# Resilience Plan

## Retry Strategy
```javascript
// Код для Code node: logStep() — вызывает до/после каждой ноды
async function logStep(executionId, workflowId, workflowName, nodeId, nodeName, nodeType, stepOrder, inputSummary, startTime) {
  // Выполняется ДО ноды
  const result = await $node['PostgreSQL'].run({
    operation: 'executeQuery',
    query: `INSERT INTO pipeline_execution_log 
      (execution_id, workflow_id, workflow_name, node_id, node_name, node_type, step_order, input_summary, status, started_at)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'running', NOW())`,
    additionalFields: { queryParams: [executionId, workflowId, workflowName, nodeId, nodeName, nodeType, stepOrder, JSON.stringify(inputSummary)] }
  });
  return result;
}

async function logStepComplete(executionId, nodeId, status, outputSummary, durationMs, error) {
  // Выполняется ПОСЛЕ ноды
  const result = await $node['PostgreSQL'].run({
    operation: 'executeQuery',
    query: `UPDATE pipeline_execution_log 
      SET status = $1, output_summary = $2, duration_ms = $3, 
          completed_at = NOW(), error_message = $4
      WHERE execution_id = $5 AND node_id = $6`,
    additionalFields: { queryParams: [status, JSON.stringify(outputSummary), durationMs, error?.message || null, executionId, nodeId] }
  });
  return result;
}
```

## Circuit Breaker
```sql
-- Функция обновления circuit breaker
CREATE OR REPLACE FUNCTION update_circuit_breaker(
    p_entity VARCHAR, p_success BOOLEAN
) RETURNS VARCHAR AS $$
DECLARE
    v_state VARCHAR;
    v_failures INTEGER;
BEGIN
    SELECT state, failure_count INTO v_state, v_failures
    FROM circuit_breaker_state WHERE entity_name = p_entity;

    IF p_success THEN
        UPDATE circuit_breaker_state SET 
            failure_count = 0,
            last_success_at = NOW(),
            state = CASE WHEN state = 'half_open' THEN 'closed' ELSE state END
        WHERE entity_name = p_entity;
        RETURN 'reset';
    ELSE
        v_failures := v_failures + 1;
        UPDATE circuit_breaker_state SET 
            failure_count = v_failures,
            last_failure_at = NOW(),
            state = CASE 
                WHEN v_failures >= failure_threshold THEN 'open'
                WHEN state = 'open' AND last_failure_at < NOW() - INTERVAL '60 seconds' THEN 'half_open'
                ELSE state
            END
        WHERE entity_name = p_entity;
        RETURN (SELECT state FROM circuit_breaker_state WHERE entity_name = p_entity);
    END IF;
END;
$$ LANGUAGE plpgsql;
```

## Dead Letter Queue Processor
```
[DLQ Processor Workflow]
├── Trigger: Schedule (every 5 minutes)
├── Query DLQ for pending items
├── For each item:
│   ├── Retry if retry_count < max_retries
│   ├── If success → remove from DLQ
│   └── If fail → increment retry_count, update next_retry_at
├── If retry_count >= max_retries → mark as 'exhausted'
└── Send Telegram alert for exhausted items
```

---

# План внедрения

## Phase 1: Миграция БД (1-2 часа)
- [ ] Создать 5 таблиц (001_observability_schema.sql)
- [ ] Создать индексы
- [ ] Создать функции (update_circuit_breaker, retry_failed_chunks)
- [ ] Verify: `SELECT * FROM pipeline_execution_log LIMIT 1;`

## Phase 2: Логирование в workflows (2-3 дня)
- [ ] Добавить logStep() в 5 критичных workflows:
  - [Перевод] Перевод чанка
  - [Перевод] Глава
  - [Перевод] Арка
  - Send Message
  - sub_lightrag_api
- [ ] Verify: данные пишутся в pipeline_execution_log

## Phase 3: Grafana (2-3 дня)
- [ ] Создать datasource PostgreSQL в Grafana
- [ ] Создать dashboard с 5 row-ами
- [ ] Настроить автообновление (30 сек)
- [ ] Verify: данные отображаются

## Phase 4: Alerting (1 день)
- [ ] Настроить Prometheus alerts (alerts.yml)
- [ ] Настроить Telegram notifications
- [ ] Протестировать алерты
- [ ] Verify: Telegram alert при simulated failure

## Phase 5: Resilience (2-3 дня)
- [ ] Добавить circuit breaker в API calls
- [ ] Создать DLQ Processor workflow
- [ ] Добавить retry logic с exponential backoff
- [ ] Протестировать: simulated failures → auto-recovery
- [ ] Verify: circuit breaker работает, DLQ processor работает

---

# Итог

**Что будет:**
- ✅ Полное observability (каждая нода, каждый вызов)
- ✅ Grafana dashboard с визуализацией pipeline
- ✅ Alerting в Telegram при проблемах
- ✅ Circuit breaker для Ollama/LightRAG/Telegram
- ✅ Dead letter queue для проваленных задач
- ✅ Auto-retry с exponential backoff

**Не трогает:**
- ❌ Качество перевода (не изменяется)
- ❌ Промпты для перевода (не изменяются)
- ❌ LightRAG/Ollama конфигурация (не изменяется)

**Файлы для внедрения:**
- `/home/user/n8n-docker/ADR_002_LOGGING_MONITORING_RESILIENCE.md` — полный ADR
- `/home/user/n8n-docker/migrations/001_observability_schema.sql` — SQL миграции
- `/home/user/n8n-docker/prometheus/rules/alerts.yml` — Prometheus alerts
