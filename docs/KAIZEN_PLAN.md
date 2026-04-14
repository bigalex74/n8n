# Кайдзен-план улучшений n8n Translation System

**Принципы кайдзен:**
1. 🔵 **Маленькие шаги** — каждое изменение атомарное, ≤30 минут
2. 🔵 **Без downtime** — переводы НЕ останавливаются ни на минуту
3. 🔵 **Откат за 1 клик** — каждое изменение можно отменить мгновенно
4. 🔵 **Проверка после каждого шага** — тест + ручной запуск
5. 🔵 **Ollama для тестов** — бесплатные модели, платные токены НЕ тратятся
6. 🔵 **Одно изменение за раз** — завершили → проверили → закоммитили → следующее

---

## Переключение моделей: Production ↔ Test

### Механизм переключения

Все AI workflow используют **n8n Credentials** для моделей:
- `Neuroapi` (BsGSDSjRdNfiWliT) — GPT-4o, Claude через Neuro API
- `polza.ai` (oyDHju4LEcPX94u4) — GPT-4o-mini, Claude через Polza
- `Ollama` (JD2Nq8h0kULY7Ly3) — openAiApi на http://127.0.0.1:11434/v1

**Стратегия:** Создать копии workflow с Ollama credential вместо платных.
- Production workflow → Neuroapi/Polza (платные)
- Test workflow → Ollama (бесплатные)
- Переключение через n8n API: `n8n_update_partial_workflow`

**Альтернатива (лучше):** Environment variable `AI_MODEL_MODE=production|test`
- В Code node перед AI-узлом: выбирать credential по env var
- Один workflow, два режима

---

## ФАЗА 0: Подготовка инфраструктуры тестирования

### Шаг 0.1: Проверить Ollama модель для тестов
**Время:** 5 минут | **Риск:** Нет | **Откат:** Не нужен

```bash
# Проверить что Ollama работает
curl http://localhost:11434/api/tags

# Если нет нужной модели — pull
ollama pull qwen2.5:7b  # или llama3.2:3b (быстрее)
```

**Проверка:** `curl http://localhost:11434/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"qwen2.5:7b","messages":[{"role":"user","content":"Привет"}]}'`

---

### Шаг 0.2: Создать test-credential для Ollama
**Время:** 10 минут | **Риск:** Нет | **Откат:** Удалить credential

Через n8n MCP:
```
n8n_manage_credentials(
  action="create",
  name="Ollama Test",
  type="openAiApi",
  data={
    "apiKey": "ollama",
    "baseUrl": "http://127.0.0.1:11434/v1"
  }
)
```

**Проверка:** Credential создан, виден в n8n UI

---

### Шаг 0.3: Создать тестовый workflow "Test Translate Chunk"
**Время:** 20 минут | **Риск:** Нет | **Отклад:** Удалить workflow

Создать копию `[Перевод] Перевод чанка` (GPARI8V4RBSPL1h39_kHW):
- Заменить все 4 AI credential на `Ollama Test`
- Отключить LightRAG запрос (не нужен для теста структуры)
- Отключить Postproduction
- Добавить node в конце: "Test Passed" если result_text не пустой
- Имя: `[TEST] Перевод чанка — Ollama`

**Через n8n MCP:**
1. `n8n_get_workflow(id="GPARI8V4RBSPL1h39_kHW", mode="full")`
2. Скопировать JSON, заменить credential ID на Ollama Test
3. `n8n_create_workflow(name="[TEST] Перевод чанка — Ollama", nodes=..., connections=...)`

**Проверка:** Workflow создан, inactive, 34 узла

---

### Шаг 0.4: Создать E2E Test Workflow
**Время:** 25 минут | **Риск:** Нет | **Откат:** Удалить workflow

Workflow который тестирует весь путь:
1. **Start**: Execute Workflow Trigger с `test_text` = "안녕하세요"
2. **Ollama Translate**: AI Agent с Ollama credential
3. **Validate**: Code node — проверить что output не пустой
4. **Result**: Pass/Fail

```
[Trigger] → [AI Agent Ollama] → [Validate: output.length > 0] → [Result: PASS/FAIL]
```

Имя: `[E2E] Translation Test`

**Проверка:** Запустить вручную → получить PASS

---

### Шаг 0.5: Создать Unit Test Framework для workflow
**Время:** 30 минут | **Риск:** Нет | **Откат:** Удалить файл

Создать `/home/user/n8n-docker/tests/test_workflows.py`:

```python
"""
Unit Test Framework для n8n workflow
Запускает workflow через n8n API с тестовыми данными
Все AI запросы идут через Ollama (бесплатно)
"""
import requests
import json
import time

N8N_API = "http://127.0.0.1:5678/rest"
N8N_API_KEY = "YOUR_API_KEY"

class N8nTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers = {
            "X-N8N-API-KEY": N8N_API_KEY,
            "Content-Type": "application/json"
        }

    def trigger_workflow(self, workflow_id, data, wait=True):
        """Запустить workflow через n8n API"""
        resp = self.session.post(
            f"{N8N_API}/workflows/{workflow_id}/execute",
            json={"data": data, "wait": wait}
        )
        return resp.json()

    def check_workflow_active(self, workflow_id):
        """Проверить что workflow активен"""
        resp = self.session.get(f"{N8N_API}/workflows/{workflow_id}")
        return resp.json()["data"]["active"]

    def test_translate_chunk(self, korean_text="안녕하세요"):
        """Тест перевода одного чанка через Ollama"""
        # Запустить test workflow
        result = self.trigger_workflow(
            workflow_id="[TEST-TRANSLATE-ID]",
            data={"chunk_text": korean_text}
        )
        # Проверить результат
        assert "output" in result
        assert len(result["output"]) > 0
        return result

    def test_all_workflows_connections(self):
        """Проверить что все workflow имеют валидные связи"""
        resp = self.session.get(f"{N8N_API}/workflows")
        workflows = resp.json()["data"]
        for wf in workflows:
            if wf["isArchived"]:
                continue
            # Проверить что connections валидны
            nodes = {n["name"] for n in wf["nodes"]}
            for source, targets in wf["connections"].items():
                assert source in nodes, f"Missing node: {source}"
                for target_list in targets:
                    for target in target_list:
                        assert target["node"] in nodes

    def test_database_consistency(self):
        """Проверить БД на целостность"""
        import psycopg2
        conn = psycopg2.connect("host=127.0.0.1 user=n8n_user password=n8n_db_password dbname=n8n_database")
        cur = conn.cursor()

        # Проверить застрявшие задачи
        cur.execute("SELECT id, status FROM document_jobs WHERE status NOT IN ('done', 'error')")
        stuck = cur.fetchall()
        assert len(stuck) == 0, f"Stuck jobs: {stuck}"

        # Проверить чанки без результата
        cur.execute("SELECT id FROM document_chunks WHERE chunk_text IS NOT NULL AND result_text IS NULL AND status != 'error'")
        orphan_chunks = cur.fetchall()
        assert len(orphan_chunks) == 0, f"Orphan chunks: {orphan_chunks}"

        conn.close()
```

**Проверка:** `python3 tests/test_workflows.py` запускается без ошибок

---

### Шаг 0.6: Создать CI-скрипт для запуска тестов
**Время:** 15 минут | **Риск:** Нет | **Откат:** Удалить файл

`/home/user/n8n-docker/tests/run_tests.sh`:
```bash
#!/bin/bash
echo "🧪 Запуск тестов n8n Translation System"
echo "========================================"

# 1. Проверить что n8n работает
echo -n "📡 n8n API: "
curl -sf http://127.0.0.1:5678/healthz > /dev/null && echo "✅ OK" || echo "❌ DOWN"

# 2. Проверить Ollama
echo -n "🤖 Ollama: "
curl -sf http://localhost:11434/api/tags > /dev/null && echo "✅ OK" || echo "❌ DOWN"

# 3. Проверить PostgreSQL
echo -n "🐘 PostgreSQL: "
psql -h 127.0.0.1 -U n8n_user -d n8n_database -c "SELECT 1" > /dev/null 2>&1 && echo "✅ OK" || echo "❌ DOWN"

# 4. Запустить unit-тесты
echo "🔬 Unit Tests:"
python3 tests/test_workflows.py

# 5. Запустить E2E тест
echo "🔄 E2E Test:"
python3 tests/test_e2e.py

echo "========================================"
echo "✅ Все тесты завершены"
```

**Проверка:** `bash tests/run_tests.sh` → все зелёные

---

## ФАЗА 1: Безопасность — Quick Wins (атомарные, без downtime)

### Шаг 1.1: Перенести Telegram API ключ в Credential Manager
**Время:** 10 минут | **Риск:** Низкий | **Откат:** Вернуть хардкод

Найти все workflow с хардкод `8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0`:
-billing HTTP-запросы в Start, [Send] finish, [Send] processing

**Действие:** Заменить хардкод на использование `Telegram account` credential (V4jPr27PQcfRRYRO)

**Через n8n MCP:** Для каждого workflow:
```
n8n_update_partial_workflow(
  id="workflow_id",
  operations=[{
    "type": "patchNodeField",
    "nodeName": "Billing HTTP",
    "field": "headerParameters.parameters[0].value",
    "value": "={{ $credentials.telegramBotToken }}"
  }]
)
```

**Проверка:** `grep -r "8591497428" /home/user/n8n-backups/workflows/` → 0 совпадений

---

### Шаг 1.2: Перенести Polza API ключ
**Время:** 10 минут | **Риск:** Низкий | **Откат:** Вернуть хардкод

Найти `pza_PV5t0y6PTuE8GLcZ-jgvlpNDLlZm0mUT` в Start workflow → заменить на credential `polza.ai` (oyDHju4LEcPX94u4)

**Проверка:** `grep -r "pza_PV5t" /home/user/n8n-backups/workflows/` → 0 совпадений

---

### Шаг 1.3: Перенести Neuro API ключ
**Время:** 10 минут | **Риск:** Низкий | **Откат:** Вернуть хардкод

Найти `sk-JPPv8NvhqimYVBabJvm6fB5mlv80WnLV673tfVzFm6IYq67V` в Start workflow → заменить на credential `Neuroapi` (BsGSDSjRdNfiWliT)

**Проверка:** `grep -r "sk-JPPv8N" /home/user/n8n-backups/workflows/` → 0 совпадений

---

### Шаг 1.4: Закрыть PostgreSQL порт (0.0.0.0 → 127.0.0.1)
**Время:** 5 минут | **Риск:** Низкий | **Откат:** Вернуть 5432:5432

В `docker-compose.yml`:
```yaml
# БЫЛО:
ports:
  - 5432:5432

# СТАЛО:
ports:
  - 127.0.0.1:5432:5432
```

**Примечание:** Все сервисы используют host networking → порт уже на 127.0.0.1. Проверить:
```bash
ss -tlnp | grep 5432
# Должно быть: 127.0.0.1:5432, НЕ 0.0.0.0:5432
```

Если 0.0.0.0 → `docker compose restart db`

**Проверка:** `curl -s telnet://$(hostname -I | awk '{print $1}'):5432` → connection refused

---

### Шаг 1.5: Portainer Docker socket → read-only
**Время:** 5 минут | **Риск:** Низкий | **Отклад:** Вернуть :rw

В docker-compose Portainer:
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro  # было без :ro
```

**Перезапуск:** `docker compose up -d portainer`

**Проверка:** `docker inspect portainer | grep docker.sock` → должно содержать `"Mode": "ro"`

---

### Шаг 1.6: chmod 600 на .env и секретные файлы
**Время:** 5 минут | **Риск:** Нет | **Откат:** chmod 644

```bash
chmod 600 /home/user/n8n-docker/.env
chmod 600 /home/user/.env
chmod 600 /home/user/n8n-docker/prometheus/prometheus.yml
```

**Проверка:** `ls -la /home/user/n8n-docker/.env` → `-rw-------`

---

### Шаг 1.7: Закоммитить все security-фиксы
**Время:** 5 минут | **Риск:** Нет

```bash
cd /home/user/n8n-docker
git add -A
git commit -m "security: remove hardcoded keys, restrict ports, fix permissions"
git push
```

**Результат Фазы 1:** ✅ Нет хардкод ключей, порты закрыты, permissions correct
**Тесты:** `bash tests/run_tests.sh` → все проходят

---

## ФАЗА 2: Надёжность — error handling

### Шаг 2.1: Очистить застрявшие данные
**Время:** 10 минут | **Риск:** Средний | **Откат:** Не нужен (данные мёртвые)

```sql
-- Проверить что застряло
SELECT id, file_name, status, created_at FROM document_jobs WHERE status != 'done' ORDER BY created_at;
SELECT id, job_id, status FROM document_chunks WHERE status NOT IN ('done', 'pending') LIMIT 10;

-- Пометить мёртвые задачи как error
UPDATE document_jobs SET status = 'error' WHERE status = 'pending' AND created_at < NOW() - INTERVAL '7 days';
UPDATE document_chunks SET status = 'error' WHERE status = 'processing' AND created_at < NOW() - INTERVAL '7 days';

-- Очистить telegram_send_message старше 30 дней
DELETE FROM telegram_send_message WHERE created_at < NOW() - INTERVAL '30 days';
```

**Проверка:** `SELECT COUNT(*) FROM document_jobs WHERE status = 'pending'` → 0

---

### Шаг 2.2: Добавить errorWorkflow к "Start"
**Время:** 15 минут | **Риск:** Низкий | **Откат:** Убрать errorWorkflow

В workflow "Start" (9cjeUNeTZX3YnO1W57YTP):
```
settings.errorWorkflow = "global-error-handler-36id"
```

Через n8n MCP:
```
n8n_update_partial_workflow(
  id="9cjeUNeTZX3YnO1W57YTP",
  operations=[{
    "type": "updateSettings",
    "settings": {"errorWorkflow": "global-error-handler-36id"}
  }]
)
```

**Проверка:** Settings workflow → Error → Global Error Handler установлен

---

### Шаг 2.3: Добавить errorWorkflow к workflow без него
**Время:** 20 минут (по 2 мин на workflow) | **Риск:** Низкий

Workflow БЕЗ errorWorkflow (проверить через n8n_get_workflow):
- Translate Chunk
- [Перевод] Глава
- [Перевод] Арка
- Finish
- [GET] Document
- [GET] /select_files
- ...и остальные

Для каждого:
```
n8n_update_partial_workflow(id=WF_ID, operations=[{"type": "updateSettings", "settings": {"errorWorkflow": "global-error-handler-36id"}}])
```

**Проверка:** Все workflow имеют settings.errorWorkflow = "global-error-handler-36id"

---

### Шаг 2.4: Retry on Fail для критических узлов
**Время:** 20 минут | **Риск:** Низкий

Для каждого AI-узла (Перевод чанка, Резервный перевод, Rolling Summary):
```json
{
  "retryOnFail": true,
  "maxTries": 3,
  "waitBetweenTries": 5000,
  "onError": "continueErrorOutput"
}
```

Через `patchNodeField` для каждого AI node.

**Проверка:** При сбое Ollama → автоматический retry 3 раза

---

### Шаг 2.5: Параметризовать SQL запросы
**Время:** 30 минут | **Риск:** Средний | **Откат:** Вернуть template strings

Заменить SQL-инъекции:
```sql
-- БЫЛО (инъекция!):
WHERE id = {{ $('Start Workflow').first().json.job_id }}

# СТАЛО (через Code node):
-- В Code node перед Postgres:
return {
  json: {
    job_id: $('Start Workflow').first().json.job_id,
    // валидация
    safe_job_id: Number($('Start Workflow').first().json.job_id)
  }
}

-- В Postgres:
WHERE id = {{ $json.safe_job_id }}
```

Или использовать n8n Postgres node с `values` параметром.

**Проверка:** Нет `{{ $json.xxx }}` прямо в SQL WHERE без Number() конвертации

---

### Шаг 2.6: Тест Фазы 2
```bash
# Проверить что все workflow имеют error handler
python3 tests/test_error_handling.py

# Проверить SQL injection fix
python3 tests/test_sql_injection.py

# E2E тест с заведомо плохими данными
python3 tests/test_e2e_error_cases.py
```

**Результат Фазы 2:** ✅ Все workflow имеют error handling, SQL безопасен, retry работает

---

## ФАЗА 3: Мониторинг

### Шаг 3.1: Translation Pipeline Dashboard
**Время:** 20 минут | **Риск:** Нет

Добавить в Grafana дашборд бэкапов панели:
- Текущие активные переводы (document_jobs WHERE status='processing')
- Среднее время перевода чанка
- Error rate по workflow
- Токены/стоимость за последний час

Через Grafana MCP:
```
update_dashboard(uid="n8n-backup-dashboard", operations=[...])
```

---

### Шаг 3.2: Telegram Alert на ошибки
**Время:** 15 минут | **Риск:** Низкий

В Global Error Handler добавить:
- Telegram сообщение с текстом ошибки
- Workflow name, node name, error message

**Проверка:** Вызвать ошибку вручную → получить Telegram уведомление

---

### Шаг 3.3: Alert on stuck jobs
**Время:** 10 минут | **Риск:** Нет

Добавить в Prometheus alert rule:
```yaml
- alert: StuckTranslationJob
  expr: count(backup_files_count{category="stuck_jobs"}) > 0
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "Есть застрявшие задачи перевода"
```

---

## ФАЗА 4: Рефакторинг (маленькими шагами)

### Шаг 4.1: Разделить /select_files на sub-workflows
**Время:** 3 шага по 20 минут | **Риск:** Средний

Текущий: 72 узла в одном workflow.

**Шаг 4.1a:** Вынести "Подготовка inline keyboard" в sub-workflow (15 узлов)
**Шаг 4.1b:** Вынести "Обработка callback" в sub-workflow (20 узлов)
**Шаг 4.1c:** Вынести "Запись файлов в БД" в sub-workflow (15 узлов)

Каждый шаг:
1. Создать sub-workflow через n8n_create_workflow
2. В основном заменить узлы на Execute Workflow node
3. Тестировать через E2E
4. Закоммитить

---

### Шаг 4.2: Billing в sub-workflow
**Время:** 15 минут | **Риск:** Низкий

Создать `[Sub] Billing Check` workflow:
- Billing Polza.ai
- Billing Neuro
- Сохранение в БД

Заменить во всех workflow вызов на Execute Workflow.

---

### Шаг 4.3: Удалить мёртвые узлы
**Время:** 10 минут | **Риск:** Низкий

Найти и удалить:
- Replace Me (NoOp) узлы
- Закомментированные узлы
- Неиспользуемые connections

---

## ФАЗА 5: Оптимизация

### Шаг 5.1: Polling → Webhook для Telegram
**Время:** 20 минут | **Риск:** Средний

Текущий: `[Send] wait` опрашивает Telegram каждые 1 сек через HTTP.
Заменить на: Webhook node → ждёт входящий callback.

**Проверка:** Пользователь нажимает "Продолжить" → мгновенный ответ

---

### Шаг 5.2: Индексы БД
**Время:** 10 минут | **Риск:** Низкий

```sql
CREATE INDEX IF NOT EXISTS idx_chunks_job_status ON document_chunks(job_id, status);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON document_jobs(status);
CREATE INDEX IF NOT EXISTS idx_messages_created ON telegram_send_message(created_at);
CREATE INDEX IF NOT EXISTS idx_chunks_index ON document_chunks(job_id, chunk_index);
```

**Проверка:** `EXPLAIN ANALYZE` для типичных запросов → быстрее

---

### Шаг 5.3: Очистка anonymous volumes
**Время:** 5 минут | **Риск:** Низкий

```bash
docker volume prune -f
docker image prune -f
```

---

## План тестирования

### Unit-тесты (каждый workflow отдельно)

| Тест | Что проверяет | Данные | Ожидаемый результат |
|------|--------------|--------|-------------------|
| test_translate_chunk_success | Перевод работает | "안녕하세요" | result_text не пустой |
| test_translate_chunk_empty | Пустой ввод | "" | error=False, пустой результат |
| test_translate_chunk_long | Длинный текст | 500 символов | result_text создан |
| test_chapter_update | Обновление главы | valid chunk_id | chapter updated |
| test_arc_update | Обновление арки | valid chunk_id | arc updated |
| test_error_handler | Ошибка обрабатывается | invalid data | error logged |
| test_glossary_create | Создание глоссария | korean text | glossary entries created |
| test_document_parse | Парсинг файла | text content | chunks created |
| test_send_message | Отправка сообщения | template="create_job" | message sent |
| test_select_files | Выбор файлов | valid callback | files selected |

### E2E-тесты (полный путь)

| Тест | Что проверяет | Поток |
|------|--------------|-------|
| e2e_full_translation | KO→RU перевод | Start → Translate Chunk → Finish |
| e2e_glossary_workflow | Создание + применение глоссария | Glossary Create → Translate → Verify |
| e2e_error_recovery | Ошибка → retry → успех | Fail → Retry → Success |
| e2e_parallel_jobs | Два перевода параллельно | Job1 + Job2 → both done |
| e2e_telegram_interaction | Telegram → n8n → ответ | Webhook → Process → Reply |

### Тестовые данные

```python
TEST_KOREAN_TEXTS = [
    "안녕하세요",  # Приветствие
    "그는 문을 열고 들어갔다.",  # Простое предложение
    "빛이 어둠을 가르며 동쪽 하늘에서 떠오르기 시작했다.",  # Литературный текст
    "프롤로그" * 100,  # Длинный текст
    "",  # Пустой
    "   ",  # Пробелы
    "12345",  # Цифры
    "한글English混合",  # Смешанный
]
```

---

## Сводная таблица всех шагов

| Фаза | Шаг | Описание | Время | Риск | Зависит от |
|------|-----|----------|-------|------|------------|
| 0 | 0.1 | Проверить Ollama | 5 мин | Нет | — |
| 0 | 0.2 | Создать test-credential | 10 мин | Нет | 0.1 |
| 0 | 0.3 | Test Translate Chunk workflow | 20 мин | Нет | 0.2 |
| 0 | 0.4 | E2E Test workflow | 25 мин | Нет | 0.3 |
| 0 | 0.5 | Unit Test Framework | 30 мин | Нет | 0.2 |
| 0 | 0.6 | CI-скрипт | 15 мин | Нет | 0.5 |
| **0 Итого** | | | **105 мин** | | |
| 1 | 1.1 | Telegram ключ → Credential | 10 мин | Низкий | 0.5 |
| 1 | 1.2 | Polza ключ → Credential | 10 мин | Низкий | 0.5 |
| 1 | 1.3 | Neuro ключ → Credential | 10 мин | Низкий | 0.5 |
| 1 | 1.4 | Закрыть PostgreSQL порт | 5 мин | Низкий | — |
| 1 | 1.5 | Portainer socket :ro | 5 мин | Низкий | — |
| 1 | 1.6 | chmod 600 секреты | 5 мин | Нет | — |
| 1 | 1.7 | Git commit | 5 мин | Нет | 1.1-1.6 |
| **1 Итого** | | | **50 мин** | | |
| 2 | 2.1 | Очистить застрявшие данные | 10 мин | Средний | 0.5 |
| 2 | 2.2 | errorWorkflow в Start | 15 мин | Низкий | 0.5 |
| 2 | 2.3 | errorWorkflow во все WF | 20 мин | Низкий | 2.2 |
| 2 | 2.4 | Retry on Fail AI-узлы | 20 мин | Низкий | 0.5 |
| 2 | 2.5 | Параметризовать SQL | 30 мин | Средний | 0.5 |
| 2 | 2.6 | Тест Фазы 2 | 10 мин | Нет | 2.1-2.5 |
| **2 Итого** | | | **105 мин** | | |
| 3 | 3.1 | Translation Dashboard | 20 мин | Нет | 0.5 |
| 3 | 3.2 | Telegram Alert на ошибки | 15 мин | Низкий | 2.2 |
| 3 | 3.3 | Alert on stuck jobs | 10 мин | Нет | 3.1 |
| **3 Итого** | | | **45 мин** | | |
| 4 | 4.1 | Разделить /select_files | 60 мин | Средний | 2.5 |
| 4 | 4.2 | Billing sub-workflow | 15 мин | Низкий | 2.5 |
| 4 | 4.3 | Удалить мёртвые узлы | 10 мин | Низкий | 0.5 |
| **4 Итого** | | | **85 мин** | | |
| 5 | 5.1 | Polling → Webhook | 20 мин | Средний | 2.5 |
| 5 | 5.2 | Индексы БД | 10 мин | Низкий | 0.5 |
| 5 | 5.3 | Очистка volumes | 5 мин | Низкий | — |
| **5 Итого** | | | **35 мин** | | |

**ИТОГО: ~425 минут (7 часов)** — разбито на 25 атомарных шагов

---

## Правила выполнения каждого шага

1. **Перед началом:** Запустить `bash tests/run_tests.sh` → убедиться что всё зелёное
2. **Во время:** Вносить минимальные изменения
3. **После:** 
   - Запустить `bash tests/run_tests.sh` → всё зелёное
   - Запустить ручной перевод → работает
   - Закоммитить: `git commit -m "kaizen step N: описание"`
   - Залить в git
4. **Если сломалось:** `git revert HEAD` → откат → разобраться → повторить

---

## Переключение Production/Test моделей

### Через Environment Variable (рекомендуемый способ)

В n8n settings → Environment Variables:
```bash
AI_MODEL_MODE=production   # или test
```

В каждом AI workflow добавить Code node перед AI-узлом:
```javascript
// Node: "Выбор модели"
const mode = process.env.AI_MODEL_MODE || 'production';

if (mode === 'test') {
  return { json: { use_ollama: true } };
} else {
  return { json: { use_ollama: false } };
}
```

Но n8n не поддерживает динамический выбор credential. **Альтернатива:**

### Через дублирование workflow (реализуемый способ)

- `[Перевод] Перевод чанка` → production (Neuroapi/Polza)
- `[TEST] Перевод чанка — Ollama` → test (Ollama)

Translate Chunk workflow выбирает какой sub-workflow вызывать:
```javascript
const mode = process.env.AI_MODEL_MODE || 'production';
return {
  json: {
    workflow_id: mode === 'test' 
      ? 'TEST-TRANSLATE-CHUNK-ID' 
      : 'GPARI8V4RBSPL1h39_kHW'
  }
}
```

### Быстрое переключение (1 команда)

```bash
# Production mode
docker exec n8n-docker-n8n-1 sh -c 'echo "production" > /tmp/ai_mode'

# Test mode (Ollama)
docker exec n8n-docker-n8n-1 sh -c 'echo "test" > /tmp/ai_mode'
```
