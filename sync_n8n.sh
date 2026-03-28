#!/bin/bash
# 🚀 n8n Git Sync Script

REPO_DIR="/home/user/n8n-backups"
N8N_CONTAINER="n8n-docker-n8n-1"
DATE=$(date +"%Y-%m-%d %H:%M:%S")

echo "--- Starting n8n Sync: $DATE ---"

# 1. Переход в папку репозитория
cd "$REPO_DIR" || exit 1

# 2. Очистка старых JSON перед новым экспортом (чтобы ловить удаления)
rm -rf workflows/*.json
rm -rf credentials/*.json
mkdir -p workflows credentials

# 3. Полный экспорт всех воркфлоу одним файлом
echo "📦 Exporting all workflows to full_backup.json..."
docker exec "$N8N_CONTAINER" n8n export:workflow --all > full_backup.json

# 4. Экспорт по отдельности для отслеживания истории изменений (diff)
echo "📁 Exporting individual workflows..."
# Получаем список ID и имен: ID|NAME
# n8n list:workflow выводит строки вида: ID|NAME
docker exec "$N8N_CONTAINER" n8n list:workflow | while read -r line; do
    WF_ID=$(echo "$line" | cut -d'|' -f1)
    WF_NAME=$(echo "$line" | cut -d'|' -f2 | tr ' /' '__') # заменяем пробелы и слеши для имени файла
    
    if [ -n "$WF_ID" ] && [ -n "$WF_NAME" ]; then
        echo "   - Exporting: $WF_NAME ($WF_ID)"
        docker exec "$N8N_CONTAINER" n8n export:workflow --id="$WF_ID" > "workflows/${WF_NAME}.json"
    fi
done

# 5. Экспорт структуры учетных данных (без самих секретов)
echo "🔑 Exporting credentials metadata..."
docker exec "$N8N_CONTAINER" n8n export:credentials --all --decrypted=false > credentials/all_credentials_meta.json

# 6. Git commit & push
echo "📤 Committing and pushing to Git..."
git add .
git commit -m "Auto-backup: $DATE" || echo "No changes to commit."
git push origin master

echo "✅ Sync completed successfully!"
