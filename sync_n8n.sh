#!/bin/bash
# 🚀 bigalexn8n Git Sync Script - FIXED VERSION
# Fixes: proper error handling, read from file not pipe, pull before merge

REPO_DIR="/home/user/n8n-backups"
N8N_CONTAINER="n8n-docker-n8n-1"
DB_CONTAINER="n8n-docker-db-1"
DATE=$(date +"%Y-%m-%d %H:%M:%S")
LOG_FILE="$REPO_DIR/sync.log"
BRANCH_NAME="pending"

log() { echo "$DATE - $1" | tee -a "$LOG_FILE"; }

cleanup() {
    cd "$REPO_DIR" 2>/dev/null
    git merge --abort 2>/dev/null
    git checkout master 2>/dev/null
    git reset --hard origin/master 2>/dev/null
}

notify() {
    curl -s -X POST "https://api.telegram.org/bot8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0/sendMessage" \
        -H "Content-Type: application/json" \
        -d "{\"chat_id\": 923741104, \"text\": \"$1\"}" 2>/dev/null
}

cd "$REPO_DIR" || exit 1
log "--- Starting Sync ($DATE) ---"

# 0. Sync with remote first
log "🔄 Syncing with remote..."
git checkout master 2>/dev/null
git pull origin master || {
    log "❌ Cannot pull from remote"; exit 1
}

# 1. Branch number
LAST_NUM=$(cat .last_branch_number 2>/dev/null || echo "0")
NEW_NUM=$((LAST_NUM + 1))
echo "$NEW_NUM" > .last_branch_number
BRANCH_NAME="bigalexn8n-$NEW_NUM"
log "📦 Branch: $BRANCH_NAME"

# 2. Export workflows - READ FROM FILE not pipe
log "📦 Exporting workflows..."
rm -rf workflows/*.json
docker exec "$N8N_CONTAINER" n8n list:workflow > /tmp/wf_list.txt 2>/dev/null

if [ -s /tmp/wf_list.txt ]; then
    while IFS='|' read -r WF_ID WF_NAME || [ -n "$WF_ID" ]; do
        WF_ID=$(echo "$WF_ID" | tr -d ' \r\n')
        WF_NAME=$(echo "$WF_NAME" | tr -d '\r\n' | sed 's/[ /]/_/g')
        if [ -n "$WF_ID" ] && [ -n "$WF_NAME" ]; then
            docker exec "$N8N_CONTAINER" n8n export:workflow --id="$WF_ID" > "workflows/${WF_NAME}.json" 2>/dev/null || true
        fi
    done < /tmp/wf_list.txt
    log "✅ Exported $(ls workflows/*.json 2>/dev/null | wc -l) workflows"
else
    log "⚠️ Failed to list workflows"
fi

docker exec "$N8N_CONTAINER" n8n export:credentials --all --decrypted=false > credentials/all_credentials_meta.json 2>/dev/null || true

# 3. DB backup
log "💾 Backing up system tables..."
TABLES=("workflow_entity" "credentials_entity" "user" "project" "tag_entity" "workflows_tags")
mkdir -p system_db_backups
for table in "${TABLES[@]}"; do
    docker exec "$DB_CONTAINER" pg_dump -U n8n_user -d n8n_database -t "$table" --data-only --inserts > "system_db_backups/${table}.sql" 2>/dev/null || true
done

# 4. Infrastructure
log "🏗️ Backing up infrastructure..."
mkdir -p infrastructure
cp /home/user/n8n-docker/docker-compose.yml infrastructure/n8n-docker-compose.yml
cp /home/user/lightrag/docker-compose.yml infrastructure/lightrag-docker-compose.yml
cp /etc/caddy/Caddyfile infrastructure/Caddyfile 2>/dev/null || true

# 5. Tools
log "🛠️ Backing up tools..."
mkdir -p tools
cp /home/user/*.js tools/ 2>/dev/null || true
cp /home/user/*.sql tools/ 2>/dev/null || true

# 6. AI assets
log "🧠 Backing up AI assets..."
mkdir -p ai_assets/skills
cp -r /home/user/.gemini/skills/* ai_assets/skills/ 2>/dev/null || true
cp /home/user/.gemini/GEMINI.md ai_assets/ 2>/dev/null || true
cp /home/user/n8n-docker/SCHEMA.md ai_assets/ 2>/dev/null || true

# 7. Git commit
log "🌿 Committing..."
git checkout -b "$BRANCH_NAME"
git add .

if git diff --cached --quiet; then
    log "ℹ️ No changes to commit"
    git checkout master
    git branch -D "$BRANCH_NAME" 2>/dev/null
    log "✅ Completed (no changes)"
    rm -f /tmp/wf_list.txt
    exit 0
fi

git commit -m "$BRANCH_NAME: Scheduled auto-backup

- Automatic synchronization of workflows, system data and infrastructure"

git push origin "$BRANCH_NAME"

# 8. Merge to master - PULL FIRST!
log "🔀 Merging to master..."
git checkout master
git pull origin master

# Resolve conflicts by taking ours (latest backup data)
git merge "$BRANCH_NAME" --no-ff -m "Merge branch '$BRANCH_NAME'" 2>/dev/null
if [ $? -ne 0 ]; then
    log "⚠️ Merge conflicts detected, resolving..."
    git checkout --ours .
    git add .
    git commit -m "Merge branch '$BRANCH_NAME' (resolved conflicts)" 2>/dev/null || true
fi

git push origin master

# Cleanup
git branch -d "$BRANCH_NAME" 2>/dev/null
rm -f /tmp/wf_list.txt

log "✅ Sync $BRANCH_NAME completed successfully!"
notify "✅ Backup $BRANCH_NAME completed
Time: $DATE"
