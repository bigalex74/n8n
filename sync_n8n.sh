#!/bin/bash
# 🚀 Advanced bigalexn8n Git Sync Script

REPO_DIR="/home/user/n8n-backups"
N8N_CONTAINER="n8n-docker-n8n-1"
DB_CONTAINER="n8n-docker-db-1"
DATE=$(date +"%Y-%m-%d %H:%M:%S")

# Входные параметры для коммита
BRIEF_DESC=${1:-"Scheduled auto-backup"}
DETAILED_POINTS=${2:-"- Automatic synchronization of workflows and system data"}

cd "$REPO_DIR" || exit 1

# 1. Инкремент номера ветки
LAST_NUM=$(cat .last_branch_number)
NEW_NUM=$((LAST_NUM + 1))
echo "$NEW_NUM" > .last_branch_number
BRANCH_NAME="bigalexn8n-$NEW_NUM"

echo "--- Starting Sync: $BRANCH_NAME ($DATE) ---"

# 2. Экспорт n8n данных (Workflows & Credentials)
rm -rf workflows/*.json
docker exec "$N8N_CONTAINER" n8n list:workflow | while read -r line; do
    WF_ID=$(echo "$line" | cut -d'|' -f1)
    WF_NAME=$(echo "$line" | cut -d'|' -f2 | tr ' /' '__')
    if [ -n "$WF_ID" ] && [ -n "$WF_NAME" ]; then
        docker exec "$N8N_CONTAINER" n8n export:workflow --id="$WF_ID" > "workflows/${WF_NAME}.json"
    fi
done
docker exec "$N8N_CONTAINER" n8n export:credentials --all --decrypted=false > credentials/all_credentials_meta.json

# 3. Бэкап критических системных таблиц БД
echo "💾 Backing up critical system tables..."
TABLES=("workflow_entity" "credentials_entity" "user" "project" "tag" "workflow_tag_mapping")
for table in "${TABLES[@]}"; do
    docker exec "$DB_CONTAINER" pg_dump -U n8n_user -d n8n_database -t "$table" --data-only --inserts > "system_db_backups/${table}.sql"
done

# 4. Бэкап AI Assets (Skills & Rules)
echo "🧠 Backing up AI assets..."
cp -r /home/user/.gemini/skills/* ai_assets/skills/ 2>/dev/null || true
cp /home/user/.gemini/GEMINI.md ai_assets/ 2>/dev/null || true
cp /home/user/n8n-docker/SCHEMA.md ai_assets/ 2>/dev/null || true

# 5. Git workflow
git checkout -b "$BRANCH_NAME"
git add .

# Формирование сообщения коммита по стандарту
COMMIT_MSG="$BRANCH_NAME: $BRIEF_DESC

$DETAILED_POINTS"

git commit -m "$COMMIT_MSG"
git push origin "$BRANCH_NAME"

# Слияние в мастер
git checkout master
git merge "$BRANCH_NAME"
git push origin master

echo "✅ Sync $BRANCH_NAME completed!"
