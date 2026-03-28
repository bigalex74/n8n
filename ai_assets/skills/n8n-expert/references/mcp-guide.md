# n8n & MCP Guide

## Core Concepts
- **n8n as Server**: Exposes n8n workflows as tools for AI assistants (Claude, Cursor, etc.). Uses the *MCP Server Trigger* node.
- **n8n as Client**: AI Agents in n8n can use external MCP servers for specialized tasks. Uses the *MCP Client Tool* node.

## Setup Requirements
- **Version**: Requires n8n v1.88.0+.
- **Env**: Set `N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true` for community tools.
- **SSE**: Current built-in support is via SSE (HTTP).

## Recommended Tools
- **n8n-mcp**: Community MCP server to manage workflows from natural language.
- **n8n-nodes-mcp**: Community node to extend MCP capabilities within n8n.

## How to use in this Workspace
1. **Enable MCP**: Update `n8n-docker/.env` with required variables.
2. **Expose Tools**: Create a workflow with *MCP Server Trigger* and connect the desired nodes.
3. **Register in Client**: Point the client to `https://bigalexn8n.ru:5678/rest/mcp/sse`.
