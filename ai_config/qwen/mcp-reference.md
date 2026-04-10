# MCP Servers Reference List

## Установленные MCP серверы

| # | MCP Server | Команда установки | Статус |
|---|-----------|------------------|--------|
| 1 | **Context7** | `npx -y @upstash/context7-mcp` | ✅ Установлен |
| 2 | **GitHub** | `npx -y @modelcontextprotocol/server-github` | ⏳ В settings.json |
| 3 | **Filesystem** | `npx -y @modelcontextprotocol/server-filesystem /home/user` | ⏳ В settings.json |
| 4 | **Brave Search** | `npx -y @modelcontextprotocol/server-brave-search` | ⏳ В settings.json |
| 5 | **PostgreSQL** | `npx -y @modelcontextprotocol/server-postgres` | ⏳ В settings.json |
| 6 | **Memory** | `npx -y @modelcontextprotocol/server-memory` | ⏳ В settings.json |
| 7 | **Sentry** | `npx -y @modelcontextprotocol/server-sentry` | ⏳ В settings.json |
| 8 | **Docker** | `npx -y @modelcontextprotocol/server-docker` | ⏳ В settings.json |
| 9 | **SQLite** | `npx -y @modelcontextprotocol/server-sqlite` | ⏳ В settings.json |
| 10 | **Playwright** | `npx -y @executeautomation/playwright-mcp-server` | ⏳ В settings.json |
| 11 | **Firecrawl** | `npx -y @mendable/firecrawl-mcp` | ⏳ В settings.json |
| 12 | **Puppeteer** | `npx -y @modelcontextprotocol/server-puppeteer` | ⏳ В settings.json |
| 13 | **Linear** | `npx -y @linear/mcp` | ⏳ В settings.json |
| 14 | **Google Workspace** | `npx -y @modelcontextprotocol/server-google-workspace` | ⏳ В settings.json |
| 15 | **E2B Sandbox** | `npx -y @e2b/mcp` | ⏳ В settings.json |

## НЕ установлены (исключены по запросу)
- ❌ Slack
- ❌ Jira
- ❌ Notion
- ❌ Figma
- ❌ Stripe

## Настройка

MCP серверы конфигурируются в `~/.qwen/settings.json` в секции `mcpServers`.

---

**Создано:** 10 апреля 2026 г.
