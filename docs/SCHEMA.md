# 🧠 n8n Project Knowledge Base

## 📂 Databases & Schemas
- **n8n_database**: System tables for n8n (executions, workflows, credentials).
- **postgres (public)**: Application database for Novel Translation.
  - `document_jobs`: Registry of all translation tasks.
  - `document_chunks`: Atomic text fragments for translation.
  - `document_glossary`: Extracted names and terms.
  - `telegram_send_message`: Queue for notifications (Trigger for n8n).
  - `v_novel_dashboard`: Analytical view for stats.

## 🏗️ Architecture
- **Host Networking**: n8n runs on host network to access local proxy.
- **Proxy**: `http://127.0.0.1:10808` (Xray/Hiddify).
- **Git Sync**: Auto-backups every 4 hours to `bigalex74/n8n`.

## 🛠️ Workflows
- `System - Stats Dashboard`: Manual/Webhook trigger for global analytics.
- `System - Proxy Check`: Connectivity monitor.
- `System - Novel Pipeline Test`: Integrity validator.
- `Main Orchestrator`: `J62UViXZMD5o6qoU` (Send Message).

## 📜 Development Rules
1. Use `postgres` database for custom logic.
2. Idempotency: Use `message_id` for Telegram edits.
3. Modular: Sub-workflows for common tasks (Notify, Context).
4. Git: New branch -> Push -> Merge to master.
