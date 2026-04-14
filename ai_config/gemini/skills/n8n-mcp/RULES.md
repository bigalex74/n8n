# n8n MCP Rules

## 1. Data Integrity
- DO NOT manually delete workflows from `workflow_entity`. Use `docker exec n8n workflow:deactivate` if needed.
- Always verify `job_id` before querying `document_chunks`.

## 2. Communication
- Respond in Russian as per global mandate.
- Use emojis for status: ✅ (done), ⏳ (processing), ❌ (failed), 🔔 (notify).

## 3. Automation
- If a workflow fails, check `document_log` for the specific node error.
- Insert a record into `telegram_send_message` with template `error_processing` on critical failures.
