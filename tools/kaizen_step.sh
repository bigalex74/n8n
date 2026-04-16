#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/user/n8n-backups"
STATE_DIR="${ROOT_DIR}/.kaizen/steps"
PG_CONTAINER="${KAIZEN_PG_CONTAINER:-n8n-docker-db-1}"
PG_USER="${KAIZEN_PG_USER:-n8n_user}"
PG_DB="${KAIZEN_PG_DB:-postgres}"

usage() {
  cat <<'EOF'
Usage:
  kaizen_step.sh backup <STEP_ID> "<description>"
  kaizen_step.sh test <STEP_ID>
  kaizen_step.sh finalize <STEP_ID>
  kaizen_step.sh rollback-note <STEP_ID>

Examples:
  ./tools/kaizen_step.sh backup 0.1 "Проверка Ollama модели"
  ./tools/kaizen_step.sh test 0.1
  ./tools/kaizen_step.sh finalize 0.1
EOF
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

latest_step_dir() {
  local step_id="$1"
  ls -1dt "${STATE_DIR}"/*_"${step_id}" 2>/dev/null | head -n 1
}

create_step_dir() {
  local step_id="$1"
  local ts
  ts="$(date +%Y%m%d_%H%M%S)"
  mkdir -p "${STATE_DIR}/${ts}_${step_id}"
  echo "${STATE_DIR}/${ts}_${step_id}"
}

backup_step() {
  local step_id="$1"
  local desc="$2"
  local step_dir
  step_dir="$(create_step_dir "$step_id")"

  require_cmd git
  require_cmd tar
  require_cmd docker

  echo "STEP_ID=${step_id}" > "${step_dir}/META.env"
  echo "DESCRIPTION=${desc}" >> "${step_dir}/META.env"
  echo "CREATED_AT=$(date -Is)" >> "${step_dir}/META.env"

  git -C "${ROOT_DIR}" rev-parse HEAD > "${step_dir}/git_head_before.txt" || true
  git -C "${ROOT_DIR}" status --short > "${step_dir}/git_status_before.txt" || true
  git -C "${ROOT_DIR}" diff > "${step_dir}/git_diff_before.patch" || true

  tar -czf "${step_dir}/workflows_before.tar.gz" -C "${ROOT_DIR}" workflows

  docker exec "${PG_CONTAINER}" pg_dump -U "${PG_USER}" -d "${PG_DB}" \
    --data-only --inserts \
    -t public.global_errors \
    -t public.document_jobs \
    -t public.document_chunks \
    -t public.telegram_send_message \
    -t public.translate_prompts \
    > "${step_dir}/postgres_project_tables_before.sql"

  cat > "${step_dir}/ROLLBACK.md" <<EOF
# Rollback plan for step ${step_id}

## 1) Откат файлов
\`\`\`bash
cd ${ROOT_DIR}
git restore .
# или точечно:
# git restore <path>
\`\`\`

## 2) Восстановление workflow snapshot
\`\`\`bash
cd ${ROOT_DIR}
tar -xzf ${step_dir}/workflows_before.tar.gz
\`\`\`

## 3) Восстановление данных проектных таблиц (при необходимости)
\`\`\`bash
docker exec -i ${PG_CONTAINER} psql -U ${PG_USER} -d ${PG_DB} < ${step_dir}/postgres_project_tables_before.sql
\`\`\`
EOF

  echo "Backup created: ${step_dir}"
}

test_step() {
  local step_id="$1"
  local step_dir
  step_dir="$(latest_step_dir "$step_id")"
  [[ -n "${step_dir}" ]] || {
    echo "No backup directory found for step ${step_id}" >&2
    exit 1
  }

  cd "${ROOT_DIR}"
  python3 tests/run_tests.py | tee "${step_dir}/tests_after.log"
}

finalize_step() {
  local step_id="$1"
  local step_dir
  step_dir="$(latest_step_dir "$step_id")"
  [[ -n "${step_dir}" ]] || {
    echo "No backup directory found for step ${step_id}" >&2
    exit 1
  }

  git -C "${ROOT_DIR}" status --short > "${step_dir}/git_status_after.txt" || true
  git -C "${ROOT_DIR}" diff > "${step_dir}/git_diff_after.patch" || true
  echo "FINALIZED_AT=$(date -Is)" >> "${step_dir}/META.env"
  echo "Step ${step_id} finalized: ${step_dir}"
}

rollback_note() {
  local step_id="$1"
  local step_dir
  step_dir="$(latest_step_dir "$step_id")"
  [[ -n "${step_dir}" ]] || {
    echo "No backup directory found for step ${step_id}" >&2
    exit 1
  }
  echo "ROLLBACK_REQUIRED_AT=$(date -Is)" >> "${step_dir}/META.env"
  echo "Rollback flagged for step ${step_id}. See ${step_dir}/ROLLBACK.md"
}

main() {
  [[ $# -ge 2 ]] || {
    usage
    exit 1
  }

  mkdir -p "${STATE_DIR}"

  local action="$1"
  local step_id="$2"
  local desc="${3:-}"

  case "${action}" in
    backup)
      [[ -n "${desc}" ]] || {
        echo "Description is required for backup action" >&2
        exit 1
      }
      backup_step "${step_id}" "${desc}"
      ;;
    test)
      test_step "${step_id}"
      ;;
    finalize)
      finalize_step "${step_id}"
      ;;
    rollback-note)
      rollback_note "${step_id}"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
