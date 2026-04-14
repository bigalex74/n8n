#!/bin/bash
# 🚀 bigalexn8n Git Sync Script - FULL BACKUP
# Backs up: workflows, DB, infra, AI agents/skills/rules, docs, apps

# Ensure git is available (when running inside Alpine container)
if ! command -v git &> /dev/null; then
    apk add --no-cache git bash openssh 2>/dev/null || true
    git config --global --add safe.directory /home/user/n8n-backups 2>/dev/null || true
    git config --global --add safe.directory /home/user/n8n-docker 2>/dev/null || true
    git config --global user.email "bigalex@backup" 2>/dev/null || true
    git config --global user.name "backup-bot" 2>/dev/null || true
fi

# SSH config workaround (owned by user, run as root in container)
export GIT_SSH_COMMAND="ssh -i /home/user/.ssh/id_ed25519_n8n -F /dev/null -o StrictHostKeyChecking=no"

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
echo "Running as: $(whoami)"; echo "Current dir: $(pwd)"; log "--- Starting Sync ($DATE) ---"

# 0. Sync with remote first
log "🔄 Syncing with remote..."
git checkout master 2>/dev/null
# Abort any in-progress rebase/merge
git rebase --abort 2>/dev/null || true
git merge --abort 2>/dev/null || true
# Ensure sync.log is tracked but not stashed (it's in .gitignore now but may be cached)
git rm --cached sync.log 2>/dev/null || true
# Stash tracked files that might have local changes (exclude sync.log)
git stash push -m "auto-stash before sync" -- $(git ls-files | grep -v sync.log) 2>/dev/null || true
git pull origin master || {
    log "❌ Cannot pull from remote"; exit 1
}
# Restore sync.log as empty if it doesn't exist
touch "$LOG_FILE"

# 1. Branch number
LAST_NUM=$(cat .last_branch_number 2>/dev/null || echo "0")
NEW_NUM=$((LAST_NUM + 1))
echo "$NEW_NUM" > .last_branch_number
BRANCH_NAME="bigalexn8n-$NEW_NUM"
log "📦 Branch: $BRANCH_NAME"

# 2. Export workflows
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
cp /home/user/n8n-docker/prometheus/prometheus.yml infrastructure/prometheus.yml 2>/dev/null || true
cp /home/user/n8n-docker/.env infrastructure/n8n-env 2>/dev/null || true

# 5. Tools & scripts
log "🛠️ Backing up tools..."
mkdir -p tools
cp /home/user/*.js tools/ 2>/dev/null || true
cp /home/user/*.sql tools/ 2>/dev/null || true
cp /home/user/n8n-docker/*.sh tools/ 2>/dev/null || true
cp /home/user/n8n-docker/*.py tools/ 2>/dev/null || true
cp /home/user/n8n-docker/import_activate_translation_fixed.py tools/ 2>/dev/null || true
cp /home/user/n8n-docker/e2e_test_activate.py tools/ 2>/dev/null || true
cp /home/user/n8n-docker/e2e_test_v6.py tools/ 2>/dev/null || true
cp /home/user/n8n-docker/import_v3.py tools/ 2>/dev/null || true
cp /home/user/n8n-docker/import_v4.py tools/ 2>/dev/null || true
cp /home/user/n8n-docker/import_activate_translation.py tools/ 2>/dev/null || true

# 6. AI Agent Configuration (PROMPTS, RULES, SKILLS, SETTINGS)
log "🤖 Backing up AI Agent configuration..."
mkdir -p ai_config

# Qwen settings & rules
mkdir -p ai_config/qwen
cp /home/user/.qwen/settings.json ai_config/qwen/ 2>/dev/null || true
cp /home/user/.qwen/output-language.md ai_config/qwen/ 2>/dev/null || true
cp /home/user/.qwen/QWEN.md ai_config/qwen/ 2>/dev/null || true

# Agent prompts (9 prompts)
mkdir -p ai_config/qwen/prompts
cp /home/user/.qwen/prompts/*.md ai_config/qwen/prompts/ 2>/dev/null || true

# Development rules
mkdir -p ai_config/qwen/rules
cp /home/user/.qwen/rules/*.md ai_config/qwen/rules/ 2>/dev/null || true

# Skills
mkdir -p ai_config/qwen/skills
cp /home/user/.qwen/skills/*.json ai_config/qwen/skills/ 2>/dev/null || true
cp /home/user/.qwen/CONTEXT7_GUIDE.md ai_config/qwen/ 2>/dev/null || true
cp /home/user/.qwen/TELEGRAM_DEVELOPER_GUIDE.md ai_config/qwen/ 2>/dev/null || true
cp /home/user/.qwen/TELEGRAM_RESOURCES.md ai_config/qwen/ 2>/dev/null || true

# Gemini skills (legacy)
mkdir -p ai_config/gemini
cp -r /home/user/.gemini/skills ai_config/gemini/ 2>/dev/null || true
cp /home/user/.gemini/GEMINI.md ai_config/gemini/ 2>/dev/null || true
cp /home/user/n8n-expert.skill ai_config/gemini/ 2>/dev/null || true

# 7. Documentation
log "📚 Backing up documentation..."
mkdir -p docs

# n8n-docker documentation (25+ files)
cp /home/user/n8n-docker/*.md docs/ 2>/dev/null || true

# Root level documentation
cp /home/user/LIGHTRAG_INTEGRATION_DOC.md docs/ 2>/dev/null || true
cp /home/user/REFACTORING_SUMMARY.md docs/ 2>/dev/null || true
cp /home/user/SEND_MESSAGE_WORKFLOW.md docs/ 2>/dev/null || true
cp /home/user/TESTING_GUIDE.md docs/ 2>/dev/null || true
cp /home/user/ACTIVATE_TRANSLATION_WORKFLOWS.json docs/ 2>/dev/null || true

# Workflow JSON files (working copies)
mkdir -p docs/workflow_jsons
cp /home/user/*.json docs/workflow_jsons/ 2>/dev/null || true
cp /home/user/main_workflow_*.json docs/workflow_jsons/ 2>/dev/null || true
cp /home/user/sub_workflow_*.json docs/workflow_jsons/ 2>/dev/null || true
cp /home/user/Send_Message_*.json docs/workflow_jsons/ 2>/dev/null || true
cp /home/user/Translate_Chunk_*.json docs/workflow_jsons/ 2>/dev/null || true
cp /home/user/sm_task_*.json docs/workflow_jsons/ 2>/dev/null || true

# 8. Telegram Apps source code
log "📱 Backing up telegram-apps..."
mkdir -p telegram-apps
cp /home/user/telegram-apps/*.py telegram-apps/ 2>/dev/null || true
cp /home/user/telegram-apps/Dockerfile telegram-apps/ 2>/dev/null || true
cp /home/user/telegram-apps/main.py telegram-apps/ 2>/dev/null || true
cp /home/user/telegram-apps/telegram_polling.py telegram-apps/ 2>/dev/null || true
cp /home/user/telegram-apps/test_api.py telegram-apps/ 2>/dev/null || true
cp /home/user/telegram-apps/Caddyfile_tmp telegram-apps/ 2>/dev/null || true
cp -r /home/user/telegram-apps/static telegram-apps/ 2>/dev/null || true
cp -r /home/user/telegram-apps/tests telegram-apps/ 2>/dev/null || true
cp -r /home/user/telegram-apps/docs telegram-apps/ 2>/dev/null || true

# 9. LightRAG configuration
log "🧠 Backing up lightrag config..."
mkdir -p lightrag-config
cp /home/user/lightrag/src/Dockerfile lightrag-config/ 2>/dev/null || true
cp /home/user/lightrag/src/pyproject.toml lightrag-config/ 2>/dev/null || true

# 10. n8n expert skill references
log "📖 Backing up n8n expert skill..."
mkdir -p n8n-expert-skill
cp -r /home/user/.gemini/skills/n8n-expert n8n-expert-skill/ 2>/dev/null || true

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

- Workflows, credentials, system tables
- Infrastructure (docker-compose, Caddy, prometheus)
- AI Agent config (prompts, rules, skills, settings)
- Full documentation
- Telegram apps source
- Tools and scripts"

git push origin "$BRANCH_NAME"

# 8. Merge to master - PULL FIRST!
log "🔀 Merging to master..."

# Stash local changes (exclude sync.log)
git stash push -m "auto-stash before merge" -- $(git ls-files | grep -v sync.log) 2>/dev/null || true

git checkout master
# Abort any in-progress rebase/merge
git rebase --abort 2>/dev/null || true
git merge --abort 2>/dev/null || true
git pull origin master || { log "❌ Cannot pull master"; exit 1; }

# Resolve conflicts by taking ours (latest backup data)
git merge "$BRANCH_NAME" --no-ff -m "Merge branch '$BRANCH_NAME'" --strategy-option ours 2>/dev/null
if [ $? -ne 0 ]; then
    log "⚠️ Merge conflicts detected, resolving..."
    git checkout --ours .
    git add -A
    git commit -m "Merge branch '$BRANCH_NAME' (resolved conflicts)" 2>/dev/null || true
fi

git push origin master

# Pop stashed changes
git stash pop 2>/dev/null || true

# Cleanup
git branch -d "$BRANCH_NAME" 2>/dev/null
rm -f /tmp/wf_list.txt

# Summary
WF_COUNT=$(ls workflows/*.json 2>/dev/null | wc -l)
DOC_COUNT=$(ls docs/*.md 2>/dev/null | wc -l)
AI_FILES=$(find ai_config -type f 2>/dev/null | wc -l)
APP_FILES=$(find telegram-apps -type f 2>/dev/null | wc -l)

log "✅ Sync $BRANCH_NAME completed!"
log "📊 Summary: $WF_COUNT workflows, $DOC_COUNT docs, $AI_FILES AI config files, $APP_FILES app files"
notify "✅ Backup $BRANCH_NAME completed

📦 Workflows: $WF_COUNT
📚 Docs: $DOC_COUNT
🤖 AI config: $AI_FILES files
📱 Apps: $APP_FILES files
⏰ Time: $DATE"
