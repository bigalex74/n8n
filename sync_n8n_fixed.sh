#!/bin/bash
# 🚀 Advanced bigalexn8n Git Sync Script (Updated for LightRAG & Infrastructure)
# Fixed: proper error handling, pull before merge, logging

REPO_DIR="/home/user/n8n-backups"
N8N_CONTAINER="n8n-docker-n8n-1"
DB_CONTAINER="n8n-docker-db-1"
DATE=$(date +"%Y-%m-%d %H:%M:%S")
LOG_FILE="$REPO_DIR/sync.log"

# Входные параметры для коммита
BRIEF_DESC=${1:-"Scheduled auto-backup"}
DETAILED_POINTS=${2:-"- Automatic synchronization of workflows, system data and infrastructure"}

# Функция логирования
log() {
    echo "$DATE - $1" | tee -a "$LOG_FILE"
}

# Функция обработки ошибок
handle_error() {
    log "❌ ERROR on line $1: $2"
    log "🔄 Attempting recovery..."
    
    # Отменяем изменения если нужно
    cd "$REPO_DIR"
    git merge --abort 2>/dev/null
    git checkout master 2>/dev/null
    git reset --hard origin/master 2>/dev/null
    
    log "📤 Sending error notification to Telegram..."
    curl -s -X POST "https://api.telegram.org/bot8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0/sendMessage" \
        -H "Content-Type: application/json" \
        -d "{\"chat_id\": 923741104, \"text\": \"❌ Backup failed: $2\\n\\nBranch: $BRANCH_NAME\\nTime: $DATE\"}" 2>/dev/null
    
    exit 1
}

trap 'handle_error $LINENO "$BASH_COMMAND"' ERR

cd "$REPO_DIR" || exit 1

# Инициализируем BRANCH_NAME до trap
BRANCH_NAME="unknown"

log "--- Starting Sync: Scheduled auto-backup ($DATE) ---"

# 0. Подготовка - сбрасываем на master и тянем актуальные данные
log "🔄 Syncing with remote..."
git checkout master 2>/dev/null
git fetch origin
git reset --hard origin/master

# 1. Инкремент номера ветки
LAST_NUM=$(cat .last_branch_number)
NEW_NUM=$((LAST_NUM + 1))
echo "$NEW_NUM" > .last_branch_number
BRANCH_NAME="bigalexn8n-$NEW_NUM"
log "📦 Branch: $BRANCH_NAME"

# 2. Экспорт n8n данных (Workflows & Credentials)
log "📦 Exporting workflows..."
rm -rf workflows/*.json
docker exec "$N8N_CONTAINER" n8n list:workflow | while read -r line; do
    WF_ID=$(echo "$line" | cut -d'|' -f1 | tr -d ' ')
    WF_NAME=$(echo "$line" | cut -d'|' -f2 | tr ' /' '__' | tr -d ' ')
    if [[ "$WF_ID" =~ ^[a-zA-Z0-9]+$ ]] && [ -n "$WF_NAME" ]; then
        docker exec "$N8N_CONTAINER" n8n export:workflow --id="$WF_ID" > "workflows/${WF_NAME}.json" 2>/dev/null
    fi
done
docker exec "$N8N_CONTAINER" n8n export:credentials --all --decrypted=false > credentials/all_credentials_meta.json 2>/dev/null

# 3. Бэкап критических системных таблиц БД
log "💾 Backing up critical system tables..."
TABLES=("workflow_entity" "credentials_entity" "user" "project" "tag_entity" "workflows_tags")
mkdir -p system_db_backups
for table in "${TABLES[@]}"; do
    docker exec "$DB_CONTAINER" pg_dump -U n8n_user -d n8n_database -t "$table" --data-only --inserts > "system_db_backups/${table}.sql" 2>/dev/null
done

# 4. Бэкап Инфраструктуры
log "🏗️ Backing up infrastructure..."
mkdir -p infrastructure
cp /home/user/n8n-docker/docker-compose.yml infrastructure/n8n-docker-compose.yml
cp /home/user/lightrag/docker-compose.yml infrastructure/lightrag-docker-compose.yml
cp /etc/caddy/Caddyfile infrastructure/Caddyfile 2>/dev/null || log "Warning: Could not copy Caddyfile"

# 5. Бэкап инструментов и скриптов
log "🛠️ Backing up tools..."
mkdir -p tools
cp /home/user/*.js tools/ 2>/dev/null || true
cp /home/user/*.sql tools/ 2>/dev/null || true

# 6. Бэкап AI Assets (Skills & Rules)
log "🧠 Backing up AI assets..."
mkdir -p ai_assets/skills
cp -r /home/user/.gemini/skills/* ai_assets/skills/ 2>/dev/null || true
cp /home/user/.gemini/GEMINI.md ai_assets/ 2>/dev/null || true
cp /home/user/n8n-docker/SCHEMA.md ai_assets/ 2>/dev/null || true

# 7. Git workflow
log "🌿 Committing to Git..."
git checkout -b "$BRANCH_NAME"
git add .

COMMIT_MSG="$BRANCH_NAME: $BRIEF_DESC

$DETAILED_POINTS"

if git diff --cached --quiet; then
    log "ℹ️ No changes to commit"
    git checkout master
    git branch -D "$BRANCH_NAME"
    log "✅ Sync $BRANCH_NAME completed (no changes)!"
    exit 0
fi

git commit -m "$COMMIT_MSG"
git push origin "$BRANCH_NAME"

# Слияние в мастер - ПРАВИЛЬНЫЙ ПОДХОД
log "🔀 Merging to master..."
git checkout master
git pull origin master --rebase  # Тянем актуальные изменения
git merge "$BRANCH_NAME" --no-ff -m "Merge branch '$BRANCH_NAME' into master"
git push origin master

# Cleanup
git branch -d "$BRANCH_NAME" 2>/dev/null

log "✅ Sync $BRANCH_NAME completed successfully!"
log "📤 Sending success notification..."
curl -s -X POST "https://api.telegram.org/bot8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\": 923741104, \"text\": \"✅ Backup $BRANCH_NAME completed\\n\\nTime: $DATE\\nChanges: $(git log --oneline -1)\"}" 2>/dev/null
