# Local n8n Setup (Docker)

## Environment Overview
- **Path**: `/home/user/n8n-docker`
- **n8n Container**: `n8n-docker-n8n-1` (v1.x, latest image)
- **Database**: `n8n-docker-db-1` (PostgreSQL 16-alpine)
- **Reverse Proxy**: Caddy (`n8n-docker-caddy-1`)
- **Admin Tools**: pgAdmin (`n8n-docker-pgadmin-1`)

## Custom Database Schema
Workflows rely on several custom tables in the `public` schema of `n8n_database`:
- `document_jobs`: Main tracking for document processing tasks.
- `document_chunks`: Segments of documents being processed.
- `telegram_send_message`: Outgoing Telegram notifications.
- `telegram_chats`: List of authorized chats.

## Connectivity & Proxy
- **Proxy**: Uses a local `xray` forwarder for outgoing Telegram/API calls.
- **Environment Variables**: `HTTP_PROXY`, `HTTPS_PROXY` point to `host.docker.internal:10820`.

## Key Scripts
- `import_workflows_to_db.py`: Bulk import from `workflows_migration.json`.
- `create_error_handler.py`: Injects a global error handler directly into SQL.
- `setup_telegram_webhook.sh`: Configures webhooks for the Telegram bot.
