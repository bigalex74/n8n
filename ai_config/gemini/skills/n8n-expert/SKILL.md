---
name: n8n-expert
description: Specialized expert for n8n workflow development, Docker management, and MCP integration. Use when building or managing n8n workflows, handling PostgreSQL integrations for n8n, or configuring n8n-related environment and proxies.
---

# n8n Expert

Expert guidance for managing the local n8n-docker environment and professional workflow development.

## Core Workflows

### 1. Workflow Development
- **Best Practices**: Reference [best-practices.md](references/best-practices.md).
- **Modularity**: Prioritize sub-workflows and clean naming.
- **Error Handling**: Always ensure the "Global Error Handler" is connected.

### 2. Environment Management
- **Stack Ops**: Use `docker-compose` at `/home/user/n8n-docker`.
- **Initialization**: Run `import_workflows_to_db.py` to sync migrations.
- **Database**: Manage custom tables like `document_jobs` and `telegram_send_message`. Reference [local-setup.md](references/local-setup.md).

### 3. MCP Integration
- **Capabilities**: Enable n8n as an MCP Server or Client.
- **Guide**: Reference [mcp-guide.md](references/mcp-guide.md).
- **Tools**: Use community MCP servers to extend Gemini's capabilities over n8n.

## Domain Knowledge
- **n8n version**: v1.x (latest image).
- **PostgreSQL**: Version 16-alpine with custom schema for book translation/processing.
- **Proxy**: xray-core based forwarder at port 10820.
