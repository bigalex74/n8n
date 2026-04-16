# Rollback plan for step 0.3

## 1) Откат файлов
```bash
cd /home/user/n8n-backups
git restore .
# или точечно:
# git restore <path>
```

## 2) Восстановление workflow snapshot
```bash
cd /home/user/n8n-backups
tar -xzf /home/user/n8n-backups/.kaizen/steps/20260416_223622_0.3/workflows_before.tar.gz
```

## 3) Восстановление данных проектных таблиц (при необходимости)
```bash
docker exec -i n8n-docker-db-1 psql -U n8n_user -d postgres < /home/user/n8n-backups/.kaizen/steps/20260416_223622_0.3/postgres_project_tables_before.sql
```
