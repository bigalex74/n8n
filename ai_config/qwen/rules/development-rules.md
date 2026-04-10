# Development Rules

## Общие правила

1. Все ответы на русском языке (кроме кода, путей, логов)
2. Не переводить: код, пути, stack traces, JSON keys, identifiers
3. Сначала анализировать, потом действовать
4. Всегда проверять существующий код перед изменениями

## Code Quality

1. Все функции должны иметь docstrings/comments
2. Максимальная длина функции: 50 строк
3. Cyclomatic complexity < 10
4. No dead code в PR
5. DRY принцип: не повторять код

## n8n Workflows

1. Sub-workflows при >10-15 узлов
2. Именование: `[Project] [Function] - [Env]`
3. Global Error Handler обязателен
4. Retry on Fail с Exponential Backoff
5. Credentials через Credential Manager (не хардкодить!)
6. Description поле должно быть заполнено
7. Environment variables: `{{ $env["VAR"] }}`
8. Filter early, SplitInBatches для >100 элементов

## JavaScript/Node.js

1. Использовать async/await (не callbacks)
2. const/let (не var)
3. Arrow functions для callback'ов
4. Template literals
5. JSDoc для сложных функций
6. ESLint + Pretter стиль

## Python

1. Type hints обязательны
2. Docstrings (Google style)
3. f-strings для форматирования
4. List comprehensions где уместно
5. Context managers (with statement)
6. Black + Ruff стиль

## SQL

1. UPPERCASE keywords (SELECT, FROM, WHERE)
2. Explicit JOINs (не implicit)
3. CTEs для сложных запросов
4. Миграции для schema changes
5. Индексы на foreign keys
6. SQLFluff стиль

## Security

1. **Никаких hardcoded secrets** — только .env или Credentials Manager
2. Input validation на всех endpoints
3. Rate limiting для external APIs
4. Валидация всех входных данных
5. Параметризованные SQL запросы (не конкатенация!)

## Testing

1. Unit tests: >80% coverage
2. Integration tests для critical paths
3. E2E tests для happy path
4. Все тесты должны проходить перед merge
5. Тестировать edge cases

## Documentation

1. README для каждого модуля
2. CHANGELOG для изменений
3. ADR для архитектурных решений
4. Комментарии для complex logic
5. Примеры использования

## Git

1. Коммиты атомарные (одна логическая Änderung = один коммит)
2. Понятные commit messages (что и зачем)
3. Не коммитить secrets, .env, credentials
4. Branch per feature
