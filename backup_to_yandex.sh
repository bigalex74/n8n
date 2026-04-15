#!/bin/bash
# ☁️ Yandex Disk Cloud Backup Script for n8n
# Backs up local git repo data to Yandex Disk

# Load configuration from .env if present
ENV_FILE="/home/user/n8n-backups/.env"
if [ -f "$ENV_FILE" ]; then
    set -o allexport
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +o allexport
fi

# Cloud token (from env or fallback)
TOKEN="${YANDEX_OAUTH_TOKEN:-${TOKEN:-}}"
BACKUP_DIR="${BACKUP_DIR:-/home/user/n8n-backups}"
CLOUD_ARCHIVE_DIR="${CLOUD_ARCHIVE_DIR:-$BACKUP_DIR/cloud_archives}"
DATE=$(date +"%Y-%m-%d_%H-%M-%S")
FILENAME="n8n_full_backup_$DATE.zip"
ARCHIVE_PATH="$CLOUD_ARCHIVE_DIR/$FILENAME"

# Telegram settings (prefer env)
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-${TELEGRAM_BOT:-}}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-${TELEGRAM_CHAT:-}}"

# Ensure proxy variables are set (use local proxy by default)
export HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:10808}"
export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:10808}"
export NO_PROXY="${NO_PROXY:-localhost,127.0.0.1,::1,bigalexn8n.ru}"

# Curl options
CURL_OPTS="--connect-timeout 10 --max-time 120 -sS"
if [ -n "$HTTPS_PROXY" ]; then
    CURL_OPTS="$CURL_OPTS -x $HTTPS_PROXY"
fi


log() { echo "$(date) - $1"; }

notify() {
    # Prefer env-provided bot token/chat; build curl options
    BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-${TELEGRAM_BOT:-}}"
    CHAT_ID="${TELEGRAM_CHAT_ID:-${TELEGRAM_CHAT:-}}"
    if [ -z "$BOT_TOKEN" ] || [ -z "$CHAT_ID" ]; then
        log "⚠️ Telegram credentials missing, skipping notify"
        return
    fi

    # Send as form data (url-encoded) to avoid JSON quoting issues
    RESP=$(curl $CURL_OPTS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" --data "chat_id=${CHAT_ID}" --data-urlencode "text=$1" 2>&1) || true

    if echo "$RESP" | grep -q '"ok":true'; then
        log "✅ Telegram notification sent"
    else
        log "❌ Telegram notification failed: $RESP"
        # Fallback: queue message in telegram_send_message table so n8n can send it later
        if command -v docker >/dev/null 2>&1; then
            docker exec -i "${DB_CONTAINER:-n8n-docker-db-1}" psql -U n8n_user -d n8n_database -c "INSERT INTO telegram_send_message (message, chat_id) VALUES ('Cloud Backup Failed: Could not get Yandex Disk upload URL', '${CHAT_ID}');" 2>/dev/null || true
            log "ℹ️ Queued notification in telegram_send_message"
        fi
    fi
}

# 1. Create Archive
log "Creating ZIP archive..."
cd "$BACKUP_DIR" || exit 1
zip -r "$ARCHIVE_PATH" workflows system_db_backups infrastructure ai_config tools docs -x "*.log" > /dev/null

# 2. Ensure Folder exists on Yandex Disk
log "Ensuring Cloud folder exists..."
curl $CURL_OPTS -X PUT "https://cloud-api.yandex.net/v1/disk/resources?path=Backups" -H "Authorization: OAuth $TOKEN" > /dev/null
curl $CURL_OPTS -X PUT "https://cloud-api.yandex.net/v1/disk/resources?path=Backups/n8n" -H "Authorization: OAuth $TOKEN" > /dev/null

# 3. Get Upload URL
log "Getting upload URL..."
UPLOAD_URL_JSON=$(curl $CURL_OPTS -X GET "https://cloud-api.yandex.net/v1/disk/resources/upload?path=Backups/n8n/$FILENAME&overwrite=true" -H "Authorization: OAuth $TOKEN")
UPLOAD_URL=$(echo "$UPLOAD_URL_JSON" | grep -oP '"href":"\K[^\"]+')

if [ -z "$UPLOAD_URL" ]; then
    log "❌ Failed to get upload URL: $UPLOAD_URL_JSON"
    notify "❌ Cloud Backup Failed: Could not get Yandex Disk upload URL"
    exit 1
fi

# 4. Upload file
log "Uploading to Yandex Disk..."
UPLOAD_STATUS=$(curl $CURL_OPTS -X PUT -T "$ARCHIVE_PATH" "$UPLOAD_URL" 2>&1) || true

# 5. Verify and Cleanup
if [ $? -eq 0 ]; then
    log "✅ Successfully uploaded to Yandex Disk!"
    FILE_SIZE=$(du -h "$ARCHIVE_PATH" | cut -f1)
    notify "☁️ Yandex Disk Backup Completed!
    
📄 File: $FILENAME
📦 Size: $FILE_SIZE
✅ Status: Success"
    
    # Keep only last 7 local cloud archives
    ls -t "$CLOUD_ARCHIVE_DIR"/*.zip | tail -n +8 | xargs rm -f 2>/dev/null
else
    log "❌ Upload failed"
    notify "❌ Cloud Backup Failed during upload"
fi

rm -f "$ARCHIVE_PATH"
