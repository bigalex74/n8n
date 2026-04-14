#!/bin/bash
# ☁️ Yandex Disk Cloud Backup Script for n8n
# Backs up local git repo data to Yandex Disk

TOKEN="y0__xCc_sOPARjKqkAgi6v2iRcwv7fckghPleeJFShDdjbcZbr6LOLRdyb5ug"
BACKUP_DIR="/home/user/n8n-backups"
CLOUD_ARCHIVE_DIR="$BACKUP_DIR/cloud_archives"
DATE=$(date +"%Y-%m-%d_%H-%M-%S")
FILENAME="n8n_full_backup_$DATE.zip"
ARCHIVE_PATH="$CLOUD_ARCHIVE_DIR/$FILENAME"
TELEGRAM_BOT_TOKEN="8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0"
TELEGRAM_CHAT_ID="923741104"

log() { echo "$(date) - $1"; }

notify() {
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        -H "Content-Type: application/json" \
        -d "{\"chat_id\": \"$TELEGRAM_CHAT_ID\", \"text\": \"$1\"}" > /dev/null
}

# 1. Create Archive
log "Creating ZIP archive..."
cd "$BACKUP_DIR" || exit 1
zip -r "$ARCHIVE_PATH" workflows system_db_backups infrastructure ai_config tools docs -x "*.log" > /dev/null

# 2. Ensure Folder exists on Yandex Disk
log "Ensuring Cloud folder exists..."
curl -s -X PUT "https://cloud-api.yandex.net/v1/disk/resources?path=Backups" -H "Authorization: OAuth $TOKEN" > /dev/null
curl -s -X PUT "https://cloud-api.yandex.net/v1/disk/resources?path=Backups/n8n" -H "Authorization: OAuth $TOKEN" > /dev/null

# 3. Get Upload URL
log "Getting upload URL..."
UPLOAD_URL_JSON=$(curl -s -X GET "https://cloud-api.yandex.net/v1/disk/resources/upload?path=Backups/n8n/$FILENAME&overwrite=true" -H "Authorization: OAuth $TOKEN")
UPLOAD_URL=$(echo "$UPLOAD_URL_JSON" | grep -oP '"href":"\K[^"]+')

if [ -z "$UPLOAD_URL" ]; then
    log "❌ Failed to get upload URL: $UPLOAD_URL_JSON"
    notify "❌ Cloud Backup Failed: Could not get Yandex Disk upload URL"
    exit 1
fi

# 4. Upload file
log "Uploading to Yandex Disk..."
UPLOAD_STATUS=$(curl -s -X PUT -T "$ARCHIVE_PATH" "$UPLOAD_URL")

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
