# Context7 MCP — Правила использования

## Что это

Context7 — инструмент получения **актуальной документации** любой библиотеки прямо в контексте.
Решает проблему устаревших знаний модели: API меняются, выходят новые версии, добавляются breaking changes.

**Два инструмента:**
1. `resolve-library-id` — найти ID библиотеки по названию
2. `query-docs` — получить документацию по конкретному вопросу

---

## Обязательный рабочий процесс

```
1. resolve-library-id(libraryName, query)   → получить libraryId + выбрать лучший результат
2. query-docs(libraryId, query)             → получить релевантные фрагменты документации
3. Адаптировать пример под локальный стек  → НЕ копировать слепо
```

> **ПРАВИЛО:** Никогда не вызывать `query-docs` без предварительного `resolve-library-id`,
> если ID библиотеки не известен точно (формат `/org/project` или `/org/project/version`).

> **ЛИМИТ:** Не более 3 вызовов Context7 на один вопрос пользователя.

---

## Когда ИСПОЛЬЗОВАТЬ (обязательно)

- ✅ Любой вопрос про конкретную библиотеку/фреймворк/API
- ✅ Настройка, конфигурация, setup инструментов
- ✅ Миграция между версиями (breaking changes)
- ✅ Отладка специфичных для библиотеки ошибок
- ✅ Генерация кода с использованием API библиотеки
- ✅ Даже для «известных» библиотек — обучающие данные могут быть устаревшими

## Когда НЕ использовать

- ❌ Общие вопросы про алгоритмы или архитектуру (нет библиотеки)
- ❌ Bash/shell команды (не нужна документация)
- ❌ Уже получена документация в этом же диалоге — не дублировать

---

## Выбор лучшего результата из resolve-library-id

При выборе из нескольких результатов:

| Критерий | Приоритет |
|---|---|
| Точное совпадение имени | 1 |
| Source Reputation = High | 2 |
| Benchmark Score (выше = лучше) | 3 |
| Code Snippets (больше = лучше) | 4 |

**Пример:** FastAPI → выбрать `/websites/fastapi_tiangolo` (Score: 89.97, High, 8895 snippets)
а не `/fastapi/fastapi` (Score: 84.29, 1102 snippets).

---

## Версии — указывать когда важно

Если у пользователя конкретная версия → добавить в libraryId:
```
/vercel/next.js/v14.3.0-canary.87
/fastapi/fastapi/0.115.13
```

Если версия не критична → использовать без суффикса (последняя).

---

## Стек проекта translateVideo — готовые libraryId

| Библиотека | libraryId | Score | Когда использовать |
|---|---|---|---|
| FastAPI | `/websites/fastapi_tiangolo` | 89.97 | Middleware, роуты, зависимости |
| React 19 | `/facebook/react` | — | Hooks, Portal, Suspense |
| TypeScript | `/microsoft/typescript` | — | Типы, дженерики, utility types |
| Vite | `/vitejs/vite` | — | Config, плагины, env vars |
| Playwright | `/microsoft/playwright` | — | E2E тесты, config, API |
| Vitest | `/vitest-dev/vitest` | — | Unit тесты, моки |
| Zustand | `/pmndrs/zustand` | — | State management |
| Starlette | `/encode/starlette` | — | Middleware, StaticFiles |
| Python | `/python/cpython` | — | stdlib вопросы |

> Перед использованием libraryId из таблицы — проверить через `resolve-library-id`
> (версии могут измениться).

---

## Антипаттерны

- ❌ **Слепое копирование** — пример из документации может не подходить под стек. Всегда адаптировать.
- ❌ **Игнорирование версии** — `query-docs` без версии вернёт latest, а проект может использовать другую.
- ❌ **Перегрузка контекста** — не делать `query-docs` с расплывчатым запросом типа «как работает FastAPI». Запрос должен быть конкретным.
- ❌ **Дублирование** — если документация уже получена в этом диалоге — не запрашивать снова.
- ❌ **Больше 3 вызовов** на один вопрос — нарушает лимит.

---

## Формат хорошего query

**Плохо:** `"fastapi middleware"`
**Хорошо:** `"how to add custom Cache-Control response headers in FastAPI middleware for specific routes"`

**Плохо:** `"react hooks"`
**Хорошо:** `"React 19 createPortal render outside parent DOM node"`

**Принцип:** запрос = конкретная задача, не тема.

---

## Примеры использования

### Пример 1: Новый middleware в FastAPI
```python
# Задача: добавить Cache-Control заголовки

# 1. resolve-library-id("FastAPI", "custom middleware response headers Cache-Control")
#    → /websites/fastapi_tiangolo

# 2. query-docs("/websites/fastapi_tiangolo", "BaseHTTPMiddleware add custom response headers Cache-Control")
#    → получаем актуальный пример middleware

# 3. Адаптируем под наш стек (src/translate_video/api/main.py)
```

### Пример 2: Playwright config для системного Chrome
```python
# 1. resolve-library-id("Playwright", "use system Chrome browser channel")
#    → /microsoft/playwright

# 2. query-docs("/microsoft/playwright", "channel chrome use system browser instead of downloaded chromium")
#    → получаем channel:'chrome' документацию
```

### Пример 3: React Portal
```python
# 1. resolve-library-id("React", "createPortal render modal outside DOM")
#    → /facebook/react

# 2. query-docs("/facebook/react", "createPortal render children into different DOM node modal overlay")
#    → получаем актуальный API createPortal
```
