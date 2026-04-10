#!/bin/bash
# Скрипт резервного копирования n8n

BACKUP_DIR=~/n8n-docker/backups
DATE=$(date +%Y-%m-%d_%H-%M-%S)
mkdir -p $BACKUP_DIR

echo "--- Создание резервной копии ($DATE) ---"

# Дамп базы данных PostgreSQL
echo "Backup Database..."
cd ~/n8n-docker
# Получаем имя контейнера с базой данных
DB_CONTAINER=$(docker compose ps -q db)
# Выполняем дамп внутри контейнера
docker exec -t $DB_CONTAINER pg_dumpall -c -U n8n_user > $BACKUP_DIR/db_dump_$DATE.sql

# Архивируем вместе с конфигурацией
echo "Archiving..."
tar -czf $BACKUP_DIR/n8n_backup_$DATE.tar.gz -C $BACKUP_DIR db_dump_$DATE.sql -C ~/n8n-docker .env docker-compose.yml Caddyfile

# Удаляем временный дамп SQL (он уже в архиве)
rm $BACKUP_DIR/db_dump_$DATE.sql

# Оставляем только последние 7 бэкапов
echo "Cleaning old backups..."
find $BACKUP_DIR -type f -name "*.tar.gz" -mtime +7 -delete

echo "--- Бэкап завершен: $BACKUP_DIR/n8n_backup_$DATE.tar.gz ---"
