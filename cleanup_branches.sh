#!/bin/bash
# 🧹 Monthly cleanup of old branches

REPO_DIR="/home/user/n8n-backups"
cd "$REPO_DIR" || exit 1

echo "--- Starting Monthly Cleanup: $(date) ---"

# Получаем список веток, мержнутых в master, которые старше 30 дней
# Для простоты: удаляем все локальные ветки bigalexn8n-*, кроме текущих/мастера
git branch --merged master | grep "bigalexn8n-" | while read -r branch; do
    # Проверка даты последнего коммита в ветке
    LAST_COMMIT_DATE=$(git log -1 --format=%ct "$branch")
    NOW=$(date +%s)
    DIFF=$(( (NOW - LAST_COMMIT_DATE) / 86400 ))
    
    if [ "$DIFF" -gt 30 ]; then
        echo "Deleting old branch: $branch (age: $DIFF days)"
        git branch -d "$branch"
        # Удаляем также на удаленном репозитории
        git push origin --delete "$branch" 2>/dev/null || true
    fi
done

echo "✅ Cleanup completed!"
