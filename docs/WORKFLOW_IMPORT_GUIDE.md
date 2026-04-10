# 📘 Как импортировать воркфлоу в n8n через базу данных PostgreSQL

## ⚠️ Важно

Этот метод используется **только когда стандартный импорт через UI не работает** или требуется автоматизация.

**Стандартный способ:** n8n UI → Settings → Import/Export → Import

---

## 📋 Предварительные требования

1. **Доступ к БД PostgreSQL**
   - Контейнер: `n8n-docker-db-1`
   - Пользователь: `n8n_user`
   - Пароль: из `/home/user/n8n-docker/.env`
   - База: `n8n_database`

2. **JSON файлы воркфлоу** в формате n8n:
   ```json
   {
     "name": "Workflow Name",
     "nodes": [...],
     "connections": {...},
     "active": true,
     "settings": {...}
   }
   ```

---

## 🔧 Шаг 1: Подготовка JSON файлов

### 1.1. Исправьте escape-символы

Проблема: В Code Node jsCode содержит специальные символы которые нужно экранировать.

**Решение:** Используйте `json.dumps()` с `ensure_ascii=False`:

```python
import json

with open('workflow.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Проверка валидности JSON
json.dumps(data, ensure_ascii=False)
```

### 1.2. Сгенерируйте UUID для каждого воркфлоу

```python
import uuid

with open('workflow.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Генерация UUID
data[0]['id'] = str(uuid.uuid4())

with open('workflow_fixed.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
```

---

## 🗄️ Шаг 2: Структура базы данных

### 2.1. Таблицы

| Таблица | Описание |
|---------|----------|
| `workflow_entity` | Основные данные воркфлоу |
| `workflow_history` | История версий (обязательно для v1.x+) |
| `shared_workflow` | Связь воркфлоу с проектами/пользователями |
| `project` | Проекты (personal/team) |
| `user` | Пользователи |

### 2.2. Связи

```
workflow_entity (id) 
    ↓ 1:1
workflow_history (workflowId → workflow_entity.id)
    ↓ 1:N
shared_workflow (workflowId → workflow_entity.id)
    ↓ N:1
project (id)
```

---

## 📝 Шаг 3: SQL последовательность импорта

### 3.1. Получение данных

```sql
-- Получить ID проекта (обычно personal проект пользователя)
SELECT id, name, type FROM project LIMIT 1;

-- Получить ID владельца (первый активный пользователь)
SELECT id FROM "user" WHERE email IS NOT NULL LIMIT 1;
```

### 3.2. Генерация UUID

```python
import uuid
version_id = str(uuid.uuid4())  # Для workflow_history
workflow_id = str(uuid.uuid4()) # Для workflow_entity (если новый)
```

### 3.3. Вставка в workflow_entity (СНАЧАЛА!)

```sql
INSERT INTO workflow_entity (
  id, name, nodes, connections, settings,
  active, "createdAt", "updatedAt", "versionCounter",
  "versionId", "activeVersionId", "isArchived", "triggerCount"
) VALUES (
  '{workflow_id}',
  '{name}',
  '{nodes_json}',
  '{connections_json}',
  '{settings_json}',
  true,  -- active
  NOW(), -- createdAt
  NOW(), -- updatedAt
  1,     -- versionCounter
  '{version_id}', -- versionId
  NULL,  -- activeVersionId (NULL сначала!)
  false, -- isArchived
  0      -- triggerCount
);
```

**⚠️ Важно:** `activeVersionId` должен быть `NULL` на этом этапе!

### 3.4. Вставка в workflow_history

```sql
INSERT INTO workflow_history (
  "versionId", "workflowId", authors, "createdAt", "updatedAt",
  nodes, connections, name, autosaved, description
) VALUES (
  '{version_id}',
  '{workflow_id}',
  '{owner_id}',
  NOW(),
  NOW(),
  '{nodes_json}',
  '{connections_json}',
  '{name}',
  false,
  NULL
);
```

### 3.5. Обновление activeVersionId

```sql
UPDATE workflow_entity 
SET "activeVersionId" = '{version_id}'
WHERE id = '{workflow_id}';
```

**Теперь FK constraint выполнится** потому что `version_id` существует в `workflow_history`.

### 3.6. Добавление в shared_workflow

```sql
INSERT INTO shared_workflow ("workflowId", "projectId", role, "createdAt", "updatedAt")
VALUES (
  '{workflow_id}',
  '{project_id}',
  'workflow:owner',
  NOW(),
  NOW()
);
```

**⚠️ Без этой записи воркфлоу не активируется!** Ошибка: `Could not find any entity of type "SharedWorkflow"`

---

## 🚀 Автоматизация: Python скрипт

Создайте файл `import_workflow.py`:

```python
#!/usr/bin/env python3
"""
n8n Workflow Importer via PostgreSQL
Использование: python3 import_workflow.py workflow.json
"""

import json
import sys
import subprocess
import uuid
from datetime import datetime

# Конфигурация
DB_CONTAINER = 'n8n-docker-db-1'
DB_USER = 'n8n_user'
DB_NAME = 'n8n_database'
PROJECT_ID = 'laKLUPkuQseBWQhm'  # Получить из БД
OWNER_ID = '72a067d6-c26f-4653-90ff-323299f21ddd'  # Получить из БД

def run_sql(sql):
    """Выполнить SQL через docker exec"""
    cmd = ['docker', 'exec', DB_CONTAINER, 'psql', '-U', DB_USER, '-d', DB_NAME, '-c', sql]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ SQL Error: {result.stderr}")
        return False
    return True

def import_workflow(file_path):
    """Импортировать воркфлоу"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    workflow = data[0] if isinstance(data, list) else data
    name = workflow.get('name', 'Unknown')
    
    # Генерация UUID
    workflow_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    # Подготовка JSON
    nodes_json = json.dumps(workflow.get('nodes', []), ensure_ascii=False).replace("'", "''")
    connections_json = json.dumps(workflow.get('connections', {}), ensure_ascii=False).replace("'", "''")
    settings_json = json.dumps(workflow.get('settings', {}), ensure_ascii=False).replace("'", "''")
    active = 'true' if workflow.get('active', False) else 'false'
    
    print(f"📝 Импорт воркфлоу: {name}")
    
    # 1. workflow_entity (activeVersionId = NULL)
    sql1 = f"""
    INSERT INTO workflow_entity (
      id, name, nodes, connections, settings, active,
      "createdAt", "updatedAt", "versionCounter", "versionId",
      "activeVersionId", "isArchived", "triggerCount"
    ) VALUES (
      '{workflow_id}', '{name.replace("'", "''")}',
      '{nodes_json}', '{connections_json}', '{settings_json}',
      {active}, '{now}', '{now}', 1, '{version_id}', NULL, false, 0
    );
    """
    if not run_sql(sql1):
        return False
    print(f"   ✅ workflow_entity создан")
    
    # 2. workflow_history
    sql2 = f"""
    INSERT INTO workflow_history (
      "versionId", "workflowId", authors, "createdAt", "updatedAt",
      nodes, connections, name, autosaved, description
    ) VALUES (
      '{version_id}', '{workflow_id}', '{OWNER_ID}',
      '{now}', '{now}', '{nodes_json}', '{connections_json}',
      '{name.replace("'", "''")}', false, NULL
    );
    """
    if not run_sql(sql2):
        return False
    print(f"   ✅ workflow_history создан")
    
    # 3. Обновление activeVersionId
    sql3 = f"""
    UPDATE workflow_entity SET "activeVersionId" = '{version_id}'
    WHERE id = '{workflow_id}';
    """
    run_sql(sql3)
    print(f"   ✅ activeVersionId установлен")
    
    # 4. shared_workflow
    sql4 = f"""
    INSERT INTO shared_workflow ("workflowId", "projectId", role, "createdAt", "updatedAt")
    VALUES ('{workflow_id}', '{PROJECT_ID}', 'workflow:owner', '{now}', '{now}');
    """
    if not run_sql(sql4):
        return False
    print(f"   ✅ shared_workflow создан")
    
    print(f"✅ Воркфлоу импортирован: {workflow_id}")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python3 import_workflow.py <workflow.json>")
        sys.exit(1)
    
    if import_workflow(sys.argv[1]):
        print("\n📋 Следующие шаги:")
        print("   1. Перезапустите n8n: docker restart n8n-docker-n8n-1")
        print("   2. Проверьте воркфлоу в UI")
    else:
        print("\n❌ Ошибка импорта")
        sys.exit(1)
```

---

## 🧪 Проверка импорта

### SQL запросы для проверки

```sql
-- Проверка воркфлоу
SELECT id, name, active, "versionId", "activeVersionId" 
FROM workflow_entity 
WHERE name = 'Your Workflow Name';

-- Проверка истории версий
SELECT "versionId", "workflowId", name, "createdAt" 
FROM workflow_history 
WHERE "workflowId" = '<workflow_id>';

-- Проверка доступа
SELECT "workflowId", "projectId", role 
FROM shared_workflow 
WHERE "workflowId" = '<workflow_id>';

-- Полная проверка
SELECT 
  we.id,
  we.name,
  we.active,
  wh."versionId" IS NOT NULL as has_history,
  sw."workflowId" IS NOT NULL as has_shared
FROM workflow_entity we
LEFT JOIN workflow_history wh ON we."versionId" = wh."versionId"
LEFT JOIN shared_workflow sw ON we.id = sw."workflowId"
WHERE we.name = 'Your Workflow Name';
```

---

## 🔄 Перезапуск n8n

После импорта **обязательно** перезапустите n8n:

```bash
docker restart n8n-docker-n8n-1
```

Проверьте логи:

```bash
docker logs n8n-docker-n8n-1 2>&1 | grep -E "Activated|Error" | tail -20
```

Ожидаемый результат:
```
Activated workflow "Your Workflow Name" (ID: xxx-xxx-xxx)
```

---

## ⚠️ Troubleshooting

### Ошибка: `violates foreign key constraint "FK_..."`

**Проблема:** `activeVersionId` ссылается на несуществующий `versionId` в `workflow_history`.

**Решение:**
1. Вставляйте в `workflow_entity` с `activeVersionId = NULL`
2. Создавайте запись в `workflow_history`
3. Обновляйте `activeVersionId`

### Ошибка: `Could not find any entity of type "SharedWorkflow"`

**Проблема:** Нет записи в `shared_workflow`.

**Решение:**
```sql
INSERT INTO shared_workflow ("workflowId", "projectId", role)
VALUES ('<workflow_id>', '<project_id>', 'workflow:owner');
```

### Ошибка: `duplicate key value violates unique constraint`

**Проблема:** Воркфлоу с таким именем или ID уже существует.

**Решение:**
```sql
-- Удалить старый воркфлоу
DELETE FROM shared_workflow WHERE "workflowId" = '<old_id>';
DELETE FROM workflow_history WHERE "workflowId" = '<old_id>';
DELETE FROM workflow_entity WHERE id = '<old_id>';
```

### Воркфлоу не отображается в UI

**Возможные причины:**
1. Нет записи в `shared_workflow` → добавьте
2. `active = false` → обновите на `true`
3. Кэш браузера → очистите или откройте в инкогнито
4. Не тот пользователь → проверьте email в UI

---

## 📊 Пример полного импорта

```bash
# 1. Получить ID проекта
docker exec n8n-docker-db-1 psql -U n8n_user -d n8n_database -c \
  "SELECT id FROM project WHERE type = 'personal' LIMIT 1;"

# 2. Импортировать воркфлоу
python3 import_workflow.py /path/to/workflow.json

# 3. Перезапустить n8n
docker restart n8n-docker-n8n-1

# 4. Проверить активацию
docker logs n8n-docker-n8n-1 2>&1 | grep "Activated workflow"
```

---

## 🔐 Безопасность

- **Никогда не храните пароли в скриптах** → используйте переменные окружения
- **Ограничьте доступ к БД** → только localhost
- **Делайте бэкап перед импортом**:
  ```bash
  docker exec n8n-docker-db-1 pg_dump -U n8n_user n8n_database > backup.sql
  ```

---

## 📚 Дополнительные ресурсы

- [n8n Database Schema](https://github.com/n8n-io/n8n/tree/master/packages/@n8n/db)
- [n8n Workflow Repository](https://github.com/n8n-io/n8n/blob/master/packages/@n8n/db/src/repositories/workflow.repository.ts)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Сохранено:** 2026-03-28  
**Версия n8n:** 1.x (latest)  
**PostgreSQL:** 16-alpine
