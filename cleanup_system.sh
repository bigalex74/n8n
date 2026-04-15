#!/bin/bash
# 🧹 System Cleanup Script
# Removes Docker junk, old logs and temp files

# Load environment if present
ENV_FILE="/home/user/n8n-backups/.env"
if [ -f "$ENV_FILE" ]; then
    set -o allexport
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +o allexport
fi

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-${TELEGRAM_BOT:-}}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-${TELEGRAM_CHAT:-}}"
LOG_DIR="${LOG_DIR:-/home/user/n8n-backups}"

# Ensure proxy variables are set (use local proxy by default)
export HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:10808}"
export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:10808}"
export NO_PROXY="${NO_PROXY:-localhost,127.0.0.1,::1,bigalexn8n.ru}"

# Curl options
CURL_OPTS="--connect-timeout 10 --max-time 30 -sS"
if [ -n "$HTTPS_PROXY" ]; then
    CURL_OPTS="$CURL_OPTS -x $HTTPS_PROXY"
fi

log() { echo "$(date) - $1"; }

notify() {
    BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}" 
    CHAT_ID="${TELEGRAM_CHAT_ID:-}"
    if [ -z "$BOT_TOKEN" ] || [ -z "$CHAT_ID" ]; then
        log "⚠️ Telegram credentials missing, skipping notify"
        return
    fi

    RESP=$(curl $CURL_OPTS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" --data "chat_id=${CHAT_ID}" --data-urlencode "text=$1" 2>&1) || true

    if echo "$RESP" | grep -q '"ok":true'; then
        log "✅ Telegram notification sent"
    else
        log "❌ Telegram notification failed: $RESP"
        if command -v docker >/dev/null 2>&1; then
            docker exec -i "${DB_CONTAINER:-n8n-docker-db-1}" psql -U n8n_user -d n8n_database -c "INSERT INTO telegram_send_message (message, chat_id) VALUES ('Weekly Cleanup Completed: Free space before ${BEFORE}, after ${AFTER}', '${CHAT_ID}');" 2>/dev/null || true
            log "ℹ️ Queued notification in telegram_send_message"
        fi
    fi
}

log "--- Starting System Cleanup ---"

# 1. Get Disk Space before
BEFORE=$(df -h / | awk 'NR==2 {print $4}')

# 2. Docker Cleanup
log "Pruning Docker system..."
docker system prune -f > /dev/null

# 3. Clean old logs (older than 14 days)
log "Cleaning old log files..."
find "$LOG_DIR" -name "*.log" -mtime +14 -delete

# 4. Clean tmp files
log "Cleaning /tmp directory..."
find /tmp -atime +2 -type f -delete 2>/dev/null

# 5. Get Disk Space after
AFTER=$(df -h / | awk 'NR==2 {print $4}')

log "✅ Cleanup completed!"
notify "🧹 Weekly Cleanup Completed!

💾 Free space before: $BEFORE
💾 Free space after: $AFTER
✅ Status: System optimized"
