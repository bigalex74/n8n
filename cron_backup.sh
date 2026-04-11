#!/bin/sh
# Wrapper: ensure git config is set before running backup
git config --global --add safe.directory /home/user/n8n-backups 2>/dev/null
git config --global --add safe.directory /home/user/n8n-docker 2>/dev/null
git config --global user.email "bigalex@backup" 2>/dev/null
git config --global user.name "backup-bot" 2>/dev/null
/bin/bash /home/user/n8n-backups/sync_n8n.sh >> /home/user/n8n-backups/sync.log 2>&1
