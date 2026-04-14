# n8n MCP Skill

## Capabilities
- **Manage Workflows**: Direct DB access to `public.workflow_entity` to list, read, and manage workflows.
- **Track Jobs**: Query `document_jobs` and `document_chunks` for status.
- **Manage Alerts**: Direct insertion into `telegram_send_message` for Telegram notifications.
- **Logs**: Read execution logs from `document_log`.

## Usage
- Always check `n8n-docker` environment first.
- Use `psql` via Docker to perform DB operations if MCP is unavailable.
- For AI-driven automation, rely on LightRAG KB for workflow logic.

## Commands
- Use `mcp_postgres` to interact with n8n database.
- Use `docker logs` for real-time monitoring.
