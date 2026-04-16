# Kaizen Execution Protocol

Этот регламент обязателен для каждого шага из `docs/KAIZEN_PLAN.md`.

## Принципы выполнения
1. Один шаг за раз (без параллельных изменений).
2. Перед изменениями всегда делается технический бэкап и формируется план отката.
3. После изменений всегда прогоняются тесты.
4. Если тесты не зелёные — шаг не принимается, выполняется откат.
5. При добавлении функциональности — сразу добавляются/обновляются тесты.

## Обязательный pipeline шага
1. `tools/kaizen_step.sh backup <STEP_ID> "<краткое описание>"`
2. Внести изменения (код, workflow, SQL, конфиги).
3. Добавить/обновить тесты под новую логику.
4. `tools/kaizen_step.sh test <STEP_ID>`
5. Если тесты зелёные: `tools/kaizen_step.sh finalize <STEP_ID>`
6. Если тесты красные: `tools/kaizen_step.sh rollback-note <STEP_ID>` и откатить изменения.

## Что сохраняется в бэкапе шага
- Git-состояние до изменений (`status`, `diff`, commit hash).
- Снимок каталога `workflows/`.
- SQL-дамп проектных таблиц из БД `postgres`:
  - `global_errors`
  - `document_jobs`
  - `document_chunks`
  - `telegram_send_message`
  - `translate_prompts`
- Инструкция отката (`ROLLBACK.md`) в директории шага.

## Тестовый gate
- Базовая команда: `python3 tests/run_tests.py`
- Для быстрых проверок допускается:
  - `python3 tests/run_tests.py --suite unit`
  - затем полный прогон перед finalize.

## Расположение артефактов
- Все артефакты шага сохраняются в `.kaizen/steps/<timestamp>_<STEP_ID>/`.

