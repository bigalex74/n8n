# [Book Translation] Activate Translation Workflows

**Workflow ID:** `activate-translation-workflows`
**Статус:** ✅ ACTIVE и протестирован (E2E)
**Дата:** 10 апреля 2026 г.

---

## Что делает

Активирует **ВСЕ** workflow проекта **кроме**:
- ❌ `Ручной выбор файлов`
- ❌ `[Book Translation] Activate Translation Workflows` (сам себя)
- ❌ `Test Webhook Trigger`
- ❌ Архивированные workflow

## Результат теста

| Workflow | До | После |
|----------|-----|-------|
| [Перевод] Перевод чанка | false | ✅ true |
| [Перевод] Глава | false | ✅ true |
| Send Message | false | ✅ true |
| Translate Chunk | false | ✅ true |
| sub_lightrag_api | false | ✅ true |
| **Ручной выбор файлов** | false | ❌ false (исключен) |

## Как использовать

### Webhook
```bash
curl -X POST https://bigalexn8n.ru/webhook/activate-translation-workflows
```

### n8n UI
Открыть https://bigalexn8n.ru → Найти workflow → Execute

## Архитектура

```
Webhook / Manual Trigger
    ↓
Get All Workflows (n8n API)
    ↓
Filter Inactive (Code node) — исключает "Ручной выбор файлов"
    ↓
Activate Workflow (n8n API — automatic iteration over items)
```

---

**Файл:** `ACTIVATE_TRANSLATION_WORKFLOWS.json` — рабочая копия
