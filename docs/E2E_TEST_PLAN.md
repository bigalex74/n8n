# E2E Test Plan: Translation Pipeline with Zero Token Cost

**Дата:** 11 апреля 2026 г.
**Цель:** Запустить полный цикл перевода на тестовых данных без расходов токенов

---

# 1. Анализ текущей конфигурации

## Текущие модели Ollama
| Модель | Размер | Скорость | Стоимость | Текущее использование |
|--------|--------|----------|-----------|----------------------|
| qwen2.5:32b | 20GB | ~медленно | Бесплатно (локально) | Основной LLM для LightRAG |
| llama3.2:3b | 2GB | **~быстро** | Бесплатно (локально) | Уже скачана, не используется для перевода |
| nomic-embed-text | 0.3GB | быстро | Бесплатно | Embeddings для LightRAG |

## Текущий LLM для LightRAG
- **polza.ai** (gpt-5.4-nano) → **платный API**
- LightRAG env vars запечены в docker-compose (нужно переопределить)

## Pipeline перевода
```
File → Парсинг → Анализ → Глоссарий → Перевод чанков → Постредактура → Экспорт
```

---

# 2. Стратегия Zero-Cost Testing

## Подход: Переключение на Ollama llama3.2:3b

| Компонент | Production | Test Mode |
|-----------|-----------|-----------|
| LightRAG LLM | polza.ai (gpt-5.4-nano) | **Ollama llama3.2:3b** |
| LightRAG Embeddings | Ollama nomic-embed-text | Ollama nomic-embed-text (без изменений) |
| n8n Translation Code nodes | polza.ai API | **Ollama llama3.2:3b** |
| Ollama direct calls | qwen2.5:32b | **llama3.2:3b** |

## Почему llama3.2:3b?
- ✅ Уже скачана (2GB, не нужно качать)
- ✅ Быстрая на CPU (3B параметров)
- ✅ Бесплатная (локальная)
- ⚠️ Качество ниже чем у qwen2.5:32b, но для тестирования логирования — достаточно

## Механизм переключения

### Вариант A: Environment Variable (рекомендую)
```bash
# В .env или docker-compose
TRANSLATION_MODE=test
TEST_LLM_MODEL=llama3.2:3b
```

n8n Code nodes проверяют переменную:
```javascript
const model = $env["TRANSLATION_MODE"] === "test" 
  ? $env["TEST_LLM_MODEL"]  // llama3.2:3b
  : "qwen2.5:32b";           // production
```

### Вариант B: LightRAG config override
```bash
# Переопределить env для lightrag контейнера
docker exec lightrag env LLM_BINDING=ollama
docker exec lightrag env LLM_MODEL=llama3.2:3b  
docker exec lightrag env LLM_BINDING_HOST=http://127.0.0.1:11434
```

### Вариант C: Отдельный test docker-compose
```yaml
# docker-compose.test.yml
lightrag-test:
  extends: lightrag
  environment:
    - LLM_BINDING=ollama
    - LLM_MODEL=llama3.2:3b
    - LLM_BINDING_HOST=http://127.0.0.1:11434
```

---

# 3. Тестовые данные

## 3.1. Тестовый файл перевода (создам автоматически)
```
Текст: ~500 слов (1-2 страницы)
Язык: корейский → русский (или английский → русский для простоты)
Сложность: простая (нет сложных терминов)
```

## 3.2. Тестовый глоссарий
| Термин | Перевод |
|--------|---------|
| 김철수 | Ким Чхольсу |
| 서울 | Сеул |
| 마법사 | волшебник |

## 3.3. Тестовые промпты
- Упрощённый промпт для llama3.2:3b (короче контекст = быстрее)

## 3.4. Тестовый документ_jobs entry
```sql
INSERT INTO document_jobs (file_name, status) 
VALUES ('test_e2e_short.txt', 'pending');
```

---

# 4. Автоматизация E2E теста

## Workflow: [Test] E2E Translation Pipeline

```
[Trigger: Manual/Webhook]
    ↓
[1] Create Test Job
    ├── INSERT INTO document_jobs
    ├── Create test file
    ├── Create test glossary
    └── Set TRANSLATION_MODE=test
    ↓
[2] Switch to Test Mode
    ├── Update LightRAG env → ollama
    ├── Update n8n env → llama3.2:3b
    └── Verify: call Ollama API, confirm model
    ↓
[3] Run Full Pipeline
    ├── Парсинг файла
    ├── Анализ структуры
    ├── Создание глоссария
    ├── Перевод чанков (5-10 чанков)
    └── Постредактура
    ↓
[4] Verify Logging
    ├── Check pipeline_execution_log populated
    ├── Check pipeline_metrics populated
    ├── Check execution_entity has entries
    └── Count: nodes logged, errors, durations
    ↓
[5] Verify Grafana
    ├── Query Grafana API for dashboard data
    ├── Verify metrics panels show data
    └── Verify workflow visualization
    ↓
[6] Cleanup
    ├── DELETE test document_jobs
    ├── DELETE test pipeline_execution_log entries
    ├── Switch back to production mode
    └── Report results
    ↓
[7] Send Report (Telegram)
    ├── Success/failure
    ├── Metrics summary
    └── Links to Grafana
```

---

# 5. Что нужно от тебя

### Обязательно:
| Что | Зачем | Формат |
|-----|-------|--------|
| **Тестовый текстовый файл** | Входные данные для перевода | .txt файл, 500-1000 слов |
| **polza.ai API ключ** | Чтобы знать что переключать | Текущее значение из docker-compose |
| **Доступ к n8n Credentials** | Чтобы обновить API endpoint для теста | n8n UI или БД |

### Опционально (могу создать сам):
- [ ] Тестовый глоссарий (создам)
- [ ] Тестовые промпты для llama3.2:3b (создам)
- [ ] Тестовый workflow (создам)
- [ ] Grafana API check (создам)

---

# 6. Ожидаемые результаты

## Метрики E2E теста
| Метрика | Ожидаемое |
|---------|-----------|
| Токены polza.ai | **0** (используется llama3.2:3b) |
| Время одного чанка | ~2-5 сек (llama3.2:3b vs ~30 сек qwen2.5:32b) |
| pipeline_execution_log записей | ~50-100 (5-10 чанков × ~10 нод) |
| pipeline_metrics записей | 1-2 (5-минутные окна) |
| Grafana панелей с данными | 15+ |
| Ошибок | 0 |

---

# 7. Риски и Mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| llama3.2:3b не справляется с переводом | Средняя | Достаточно для проверки логирования; качество не тестируем |
| LightRAG не переключается на Ollama | Низкая | Вариант B: запустить отдельный lightrag-test контейнер |
| n8n Code nodes игнорируют env var | Низкая | Проверить что env var передаётся в контейнер |
| Grafana не показывает данные | Низкая | Проверить datasource PostgreSQL |
