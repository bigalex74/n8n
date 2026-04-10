-- ============================================================
-- ADR-002: Observability Schema Migration
-- Дата: 2026-04-10
-- Назначение: Таблицы логирования, мониторинга и отказоустойчивости
-- ============================================================

BEGIN;

-- ============================================================
-- 1. pipeline_execution_log — детальное логирование каждой ноды
-- ============================================================
CREATE TABLE IF NOT EXISTS pipeline_execution_log (
    id              BIGSERIAL PRIMARY KEY,
    execution_id    UUID NOT NULL,
    workflow_id     INTEGER REFERENCES workflow_entity(id),
    workflow_name   VARCHAR(200),
    node_id         VARCHAR(100),
    node_name       VARCHAR(200),
    node_type       VARCHAR(100),
    step_order      INTEGER,

    input_summary   JSONB,
    input_bytes     INTEGER,

    output_summary  JSONB,
    output_bytes    INTEGER,
    output_items    INTEGER,

    status          VARCHAR(20) NOT NULL,
    duration_ms     INTEGER,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,

    error_type      VARCHAR(100),
    error_message   TEXT,
    retry_count     INTEGER DEFAULT 0,

    metadata        JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipel_exec_workflow ON pipeline_execution_log(workflow_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipel_exec_node     ON pipeline_execution_log(node_name, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipel_exec_status   ON pipeline_execution_log(status, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipel_exec_error    ON pipeline_execution_log(error_type, started_at DESC)
    WHERE status = 'error';
CREATE INDEX IF NOT EXISTS idx_pipel_exec_job      ON pipeline_execution_log((metadata->>'job_id'))
    WHERE metadata ? 'job_id';
CREATE INDEX IF NOT EXISTS idx_pipel_exec_duration ON pipeline_execution_log(duration_ms DESC);

-- ============================================================
-- 2. pipeline_metrics — агрегированные метрики (5-min windows)
-- ============================================================
CREATE TABLE IF NOT EXISTS pipeline_metrics (
    id                      BIGSERIAL PRIMARY KEY,
    window_start            TIMESTAMPTZ NOT NULL,
    window_end              TIMESTAMPTZ NOT NULL,

    total_executions        INTEGER DEFAULT 0,
    successful_executions   INTEGER DEFAULT 0,
    failed_executions       INTEGER DEFAULT 0,
    total_nodes_executed    INTEGER DEFAULT 0,

    p50_latency_ms          INTEGER,
    p95_latency_ms          INTEGER,
    p99_latency_ms          INTEGER,
    avg_latency_ms          NUMERIC(10,2),
    max_latency_ms          INTEGER,

    executions_per_min      NUMERIC(8,2),
    nodes_per_min           NUMERIC(8,2),

    ollama_calls            INTEGER DEFAULT 0,
    ollama_errors           INTEGER DEFAULT 0,
    ollama_avg_ms           NUMERIC(10,2),
    lightrag_calls          INTEGER DEFAULT 0,
    lightrag_errors         INTEGER DEFAULT 0,
    lightrag_avg_ms         NUMERIC(10,2),

    chapters_translated     INTEGER DEFAULT 0,
    words_translated        INTEGER DEFAULT 0,
    avg_quality_score       NUMERIC(4,2),

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(window_start)
);

CREATE INDEX IF NOT EXISTS idx_pipel_metrics_window ON pipeline_metrics(window_start DESC);

-- ============================================================
-- 3. circuit_breaker_state — состояние circuit breaker
-- ============================================================
CREATE TABLE IF NOT EXISTS circuit_breaker_state (
    id                      SERIAL PRIMARY KEY,
    service_name            VARCHAR(50) NOT NULL,
    state                   VARCHAR(20) NOT NULL DEFAULT 'closed',
    failure_count           INTEGER DEFAULT 0,
    success_count           INTEGER DEFAULT 0,
    last_failure_at         TIMESTAMPTZ,
    last_success_at         TIMESTAMPTZ,
    opened_at               TIMESTAMPTZ,
    half_open_at            TIMESTAMPTZ,
    failure_threshold       INTEGER DEFAULT 5,
    recovery_timeout_sec    INTEGER DEFAULT 60,
    half_open_max_calls     INTEGER DEFAULT 1,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(service_name)
);

-- Начальные записи
INSERT INTO circuit_breaker_state (service_name, failure_threshold, recovery_timeout_sec)
VALUES
    ('ollama', 5, 60),
    ('lightrag', 3, 30),
    ('telegram_api', 3, 120)
ON CONFLICT (service_name) DO NOTHING;

-- ============================================================
-- 4. dead_letter_queue — необработанные задачи
-- ============================================================
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id              BIGSERIAL PRIMARY KEY,
    source_table    VARCHAR(100) NOT NULL,
    source_id       INTEGER,
    workflow_id     INTEGER,
    payload         JSONB NOT NULL,
    error_type      VARCHAR(100),
    error_message   TEXT,
    retry_count     INTEGER DEFAULT 0,
    max_retries     INTEGER DEFAULT 3,
    status          VARCHAR(20) DEFAULT 'pending',
    next_retry_at   TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    resolved_by     VARCHAR(100),
    resolution_note TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dlq_status ON dead_letter_queue(status, next_retry_at);
CREATE INDEX IF NOT EXISTS idx_dlq_created ON dead_letter_queue(created_at DESC);

-- ============================================================
-- 5. health_check_log — результаты health checks
-- ============================================================
CREATE TABLE IF NOT EXISTS health_check_log (
    id              BIGSERIAL PRIMARY KEY,
    service_name    VARCHAR(50) NOT NULL,
    status          VARCHAR(20) NOT NULL,
    response_time_ms INTEGER,
    details         JSONB DEFAULT '{}'::jsonb,
    checked_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_health_service ON health_check_log(service_name, checked_at DESC);

-- ============================================================
-- 6. Вспомогательные функции
-- ============================================================

-- Retry failed chunks
CREATE OR REPLACE FUNCTION retry_failed_chunks()
RETURNS TABLE(chunk_id INT, job_id INT) AS $$
BEGIN
  RETURN QUERY
  UPDATE document_chunks
  SET status = 'pending',
      retry_count = retry_count + 1,
      error_text = NULL,
      updated_at = NOW()
  WHERE status = 'error'
    AND retry_count < 3
    AND updated_at < NOW() - INTERVAL '5 minutes'
  RETURNING id, job_id;
END;
$$ LANGUAGE plpgsql;

-- Update circuit breaker after request
CREATE OR REPLACE FUNCTION update_circuit_breaker(
    p_service   VARCHAR,
    p_success   BOOLEAN,
    p_error_type VARCHAR DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_state       VARCHAR;
    v_failures    INTEGER;
    v_threshold   INTEGER;
BEGIN
    SELECT state, failure_count, failure_threshold
    INTO v_state, v_failures, v_threshold
    FROM circuit_breaker_state
    WHERE service_name = p_service;

    IF p_success THEN
        IF v_state = 'half_open' THEN
            UPDATE circuit_breaker_state
            SET state = 'closed',
                failure_count = 0,
                last_success_at = NOW(),
                updated_at = NOW()
            WHERE service_name = p_service;
        ELSE
            UPDATE circuit_breaker_state
            SET success_count = success_count + 1,
                last_success_at = NOW(),
                updated_at = NOW()
            WHERE service_name = p_service;
        END IF;
    ELSE
        UPDATE circuit_breaker_state
        SET failure_count = failure_count + 1,
            last_failure_at = NOW(),
            state = CASE WHEN failure_count + 1 >= failure_threshold
                         THEN 'open' ELSE state END,
            opened_at = CASE WHEN failure_count + 1 >= failure_threshold
                             THEN NOW() ELSE opened_at END,
            updated_at = NOW()
        WHERE service_name = p_service;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Get circuit breaker state (for Code Node)
CREATE OR REPLACE FUNCTION get_circuit_breaker_state(p_service VARCHAR)
RETURNS TABLE(
    state VARCHAR,
    failure_count INTEGER,
    failure_threshold INTEGER,
    recovery_timeout_sec INTEGER,
    opened_at TIMESTAMPTZ,
    half_open_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT cs.state, cs.failure_count, cs.failure_threshold,
           cs.recovery_timeout_sec, cs.opened_at, cs.half_open_at
    FROM circuit_breaker_state cs
    WHERE cs.service_name = p_service;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 7. Partitioning для pipeline_execution_log (опционально, для больших объёмов)
-- ============================================================
-- Если > 1M записей/день, раскомментировать:
-- ALTER TABLE pipeline_execution_log DROP CONSTRAINT IF EXISTS pipeline_execution_log_pkey;
-- CREATE TABLE pipeline_execution_log (
--     id BIGSERIAL,
--     ...
-- ) PARTITION BY RANGE (started_at);
-- CREATE TABLE pipeline_execution_log_2026_04 PARTITION OF pipeline_execution_log
--     FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');

-- ============================================================
-- 8. Retention policy (авто-очистка старых логов)
-- ============================================================
-- pipeline_execution_log: храним 30 дней
-- health_check_log: храним 7 дней
-- pipeline_metrics: храним 90 дней

CREATE OR REPLACE FUNCTION cleanup_old_logs()
RETURNS VOID AS $$
BEGIN
    -- Удаляем логи старше 30 дней
    DELETE FROM pipeline_execution_log
    WHERE started_at < NOW() - INTERVAL '30 days';

    -- Удаляем health checks старше 7 дней
    DELETE FROM health_check_log
    WHERE checked_at < NOW() - INTERVAL '7 days';

    -- Удаляем метрики старше 90 дней
    DELETE FROM pipeline_metrics
    WHERE window_start < NOW() - INTERVAL '90 days';

    -- Архивируем resolved DLQ записи старше 14 дней
    DELETE FROM dead_letter_queue
    WHERE status IN ('resolved', 'discarded')
      AND resolved_at < NOW() - INTERVAL '14 days';
END;
$$ LANGUAGE plpgsql;

COMMIT;

-- ============================================================
-- Проверка:
-- SELECT tablename FROM pg_tables WHERE schemaname = 'public'
--   AND tablename LIKE 'pipeline_%' OR tablename LIKE 'circuit_%'
--   OR tablename LIKE 'dead_letter%' OR tablename LIKE 'health_%';
-- ============================================================
