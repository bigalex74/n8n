#!/usr/bin/env python3
"""
Скрипт создания Global Error Handler workflow
"""

import json
import subprocess
import uuid
from datetime import datetime

DB_USER = "n8n_user"
DB_NAME = "n8n_database"
ERROR_HANDLER_ID = "global-error-handler-0vh7sstt4fc1wugw"

def run_sql(sql):
    cmd = [
        "sudo", "docker", "exec", "-i", "n8n-docker-db-1",
        "psql", "-U", DB_USER, "-d", DB_NAME
    ]
    result = subprocess.run(cmd, input=sql.encode(), capture_output=True)
    return result.returncode == 0, result.stdout.decode(), result.stderr.decode()

def create_error_handler():
    version_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    nodes = [
        {
            "parameters": {},
            "type": "n8n-nodes-base.errorTrigger",
            "typeVersion": 1,
            "position": [0, 280],
            "id": "error-trigger",
            "name": "Error Trigger"
        },
        {
            "parameters": {
                "logLevel": "error",
                "message": "={{ $json.error }}"
            },
            "type": "n8n-nodes-base.debugHelper",
            "typeVersion": 1,
            "position": [200, 280],
            "id": "debug-error",
            "name": "Log Error"
        }
    ]
    
    connections = {
        "Error Trigger": [
            [{"node": "Log Error", "type": "main", "index": 0}]
        ]
    }
    
    settings = {
        "executionOrder": "v1",
        "binaryMode": "separate"
    }
    
    # Проверить существует ли
    check_sql = f"SELECT id FROM workflow_entity WHERE id = '{ERROR_HANDLER_ID}';"
    success, stdout, stderr = run_sql(check_sql)
    
    if stdout.strip() and 'global-error' in stdout:
        print("✅ Error Handler уже существует")
        return True
    
    # Удалить если есть (на всякий случай)
    delete_sql = f"DELETE FROM workflow_entity WHERE id = '{ERROR_HANDLER_ID}';"
    run_sql(delete_sql)
    
    # Вставить новый
    insert_sql = f"""
INSERT INTO workflow_entity 
    (id, name, active, "isArchived", "createdAt", "updatedAt", description, nodes, connections, settings, "pinData", "staticData", "versionId", "triggerCount", "versionCounter", "activeVersionId") 
VALUES 
    ('{ERROR_HANDLER_ID}', '🔴 Global Error Handler', true, false, 
     '{now}', '{now}', 'Глобальный обработчик ошибок для всех workflow',
     '{json.dumps(nodes)}', 
     '{json.dumps(connections)}', 
     '{json.dumps(settings)}', 
     '{{}}', '{{}}', '{version_id}', 0, 1, '{version_id}');
"""
    
    print("Создание Global Error Handler...", end=" ")
    success, stdout, stderr = run_sql(insert_sql)
    
    if not success:
        print(f"❌ {stderr[:200]}")
        return False
    
    print("✅")
    
    # Добавить в shared_workflow
    project_id = "laKLUPkuQseBWQhm"
    sql_shared = f"""
INSERT INTO shared_workflow ("workflowId", "projectId", "role", "createdAt", "updatedAt")
VALUES ('{ERROR_HANDLER_ID}', '{project_id}', 'workflow:owner', NOW(), NOW());
"""
    run_sql(sql_shared)
    print("✅ Добавлен в shared_workflow")
    
    # Добавить в workflow_history
    sql_history = f"""
INSERT INTO workflow_history ("versionId", "workflowId", authors, nodes, connections, name, description, "createdAt", "updatedAt", autosaved)
VALUES ('{version_id}', '{ERROR_HANDLER_ID}', '[]', 
        '{json.dumps(nodes)}', 
        '{json.dumps(connections)}', 
        '🔴 Global Error Handler', 'Глобальный обработчик ошибок', 
        '{now}', '{now}', false);
"""
    run_sql(sql_history)
    print("✅ Добавлен в workflow_history")
    
    return True

def update_all_workflows():
    """Обновить все workflow"""
    sql = f"""
UPDATE workflow_entity 
SET settings = jsonb_set(
    COALESCE(settings, '{{}}'::jsonb),
    '{{errorWorkflow}}',
    '"global-error-handler-0vh7sstt4fc1wugw"'::jsonb
)
WHERE id != 'global-error-handler-0vh7sstt4fc1wugw';
"""
    print("\nОбновление настроек workflow...", end=" ")
    success, stdout, stderr = run_sql(sql)
    
    if success:
        print("✅")
        return True
    else:
        print(f"❌ {stderr[:200]}")
        return False

if __name__ == "__main__":
    print("=== Создание Global Error Handler ===\n")
    
    if create_error_handler():
        update_all_workflows()
        print("\n✅ Готово! Перезапустите n8n")
    else:
        print("\n❌ Ошибка")
