# Context7 MCP - Руководство по использованию

## Что такое Context7

Context7 - это MCP сервер, который предоставляет LLM актуальную, специфичную для версий документацию и примеры кода напрямую из источников. Устраняет проблемы устаревших данных, несуществующих API и обобщённых ответов.

## Установка

### npm пакет
```bash
npm install -g @upstash/context7-mcp
```

### Конфигурация в Qwen Code (settings.json)
```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

### С API ключом (повышенные лимиты)
Получите ключ на https://context7.com/dashboard
```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"],
      "env": {
        "CONTEXT7_API_KEY": "ваш_api_ключ"
      }
    }
  }
}
```

## Доступные инструменты

### 1. resolve-library-id
Преобразует общее имя библиотеки в Context7-ID.

**Параметры:**
- `libraryName` (required): имя библиотеки
- `query` (required): вопрос или задача пользователя (используется для ранжирования)

**Пример:**
```
libraryName: "Next.js"
query: "How to create middleware for authentication"
```
**Результат:** `/vercel/next.js`

### 2. query-docs
Извлекает документацию по точному ID.

**Параметры:**
- `libraryId` (required): точный Context7 ID (например, `/mongodb/docs`, `/vercel/next.js`)
- `query` (required): вопрос или задача для получения релевантных фрагментов

**Пример:**
```
libraryId: "/vercel/next.js"
query: "How to configure middleware in Next.js 15"
```

## Синтаксис использования

### Базовый синтаксис
Добавьте `use context7` в конец запроса:
```
Create a Next.js 15 middleware that handles authentication. use context7
```

### Прямое указание библиотеки
Используйте формат `/owner/repo` для пропуска этапа разрешения имени:
```
use library /supabase/supabase for API and docs
```

### Управление версиями
Просто указывайте нужную версию в запросе:
```
How do I configure Prisma 6 with PostgreSQL? use context7
```
Сервер автоматически подберёт документацию для версии 6.

## Лучшие практики

1. **Триггер использования**: Всегда добавляйте `use context7` когда требуется актуальная документация

2. **Оптимизация контекста**: Context7 загружается по требованию (on-demand), потребляя 0 токенов контекста в фоновом режиме

3. **Пропуск поиска библиотеки**: Используйте синтаксис `/owner/repo` прямо в промпте

4. **API ключ**: Получите бесплатный ключ на context7.com/dashboard для повышения лимитов

5. **Фоллбэк**: Если Context7 не индексирует библиотеку, используйте веб-поиск или сверьтесь с официальной документацией

## Правило для автоматического использования

Добавьте в правила ассистента:
```
Always use Context7 when I need library/API documentation, 
code generation, setup or configuration steps without me 
having to explicitly ask.
```

## Примеры использования

### Пример 1: React компонент
```
Create a React 19 Server Component that fetches user data. use context7
```

### Пример 2: Express.js маршруты
```
Set up Express.js routes with error handling. use library /expressjs/express
```

### Пример 3: TypeScript конфигурация
```
Configure TypeScript with strict mode for a Node.js project. use context7
```

## Логика работы AI

При распознавании `use context7`:
1. **resolve-library-id** → находит ID библиотеки
2. **query-docs** → загружает актуальную документацию
3. **Генерация кода** → создаёт ответ на основе актуального API

## Требования

- Node.js 18 или новее
- MCP-совместимый клиент (Qwen Code, Cursor, Claude Desktop, VS Code)
- Интернет-соединение

## Устранение неполадок

### ERR_MODULE_NOT_FOUND
Замените `npx` на `bunx` в конфигурации сервера

### Устаревшие данные
Если данные устарели (релиз вышел несколько дней назад), используйте MCP-серверы веб-поиска

## Лицензия
MIT

## Ссылки
- Официальный репозиторий: https://github.com/upstash/context7
- Получить API ключ: https://context7.com/dashboard
