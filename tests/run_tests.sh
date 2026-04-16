#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

echo "🧪 n8n-backups workflow test gate"
echo "========================================"

echo -n "📡 n8n /healthz: "
if curl -sf http://127.0.0.1:5678/healthz >/dev/null; then
  echo "OK"
else
  echo "DOWN"
fi

echo -n "🤖 Ollama /api/tags: "
if curl -sf http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "OK"
else
  echo "DOWN"
fi

echo -n "🐘 Postgres (project DB): "
if docker exec n8n-docker-db-1 psql -U n8n_user -d postgres -c "SELECT 1" >/dev/null 2>&1; then
  echo "OK"
else
  echo "DOWN"
fi

echo "----------------------------------------"
python3 tests/run_tests.py
echo "========================================"
echo "✅ Test gate passed"
