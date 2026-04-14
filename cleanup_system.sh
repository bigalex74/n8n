#!/bin/bash
# 🧹 System Cleanup Script
# Removes Docker junk, old logs and temp files

TELEGRAM_BOT_TOKEN="8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0"
TELEGRAM_CHAT_ID="923741104"
LOG_DIR="/home/user/n8n-backups"

log() { echo "$(date) - $1"; }

notify() {
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        -H "Content-Type: application/json" \
        -d "{\"chat_id\": \"$TELEGRAM_CHAT_ID\", \"text\": \"$1\"}" > /dev/null
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
