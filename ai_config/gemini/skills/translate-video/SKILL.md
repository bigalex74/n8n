---
name: translate-video
description: Специализированный скилл для разработки AI Video Translator. Используй при работе с проектом translateVideo — бэкенд (FastAPI, Python), фронтенд (React/TypeScript/Vite), пайплайн перевода видео, TTS-провайдеры, тесты, деплой Docker.
---

# AI Video Translator — Skill

Движок ИИ-перевода видео. Транскрипция (Whisper) → Перевод (DeepSeek/Qwen/Gemini) → TTS (OpenAI/ElevenLabs/YandexSpeechKit) → Рендеринг (FFmpeg).

---

## Окружение

| Параметр | Значение |
|----------|----------|
| Путь | `/home/user/translateVideo` |
| Стек | Python 3.11+, FastAPI, React 18, TypeScript, Vite, FFmpeg |
| Docker | `docker compose up -d` → контейнер `video-translator` |
| Порт | `:8002` (network_mode: host) |
| Версия | v1.97.0 |
| Основная ветка | `develop` |

---

## Архитектура

```
translateVideo/
├── src/translate_video/
│   ├── api/
│   │   ├── main.py           # FastAPI app, middleware, static
│   │   ├── middleware/auth.py # X-API-Key (env API_KEY)
│   │   └── routes/
│   │       ├── projects.py   # CRUD проектов
│   │       └── pipeline.py   # run/cancel/batch/tts-preview
│   ├── core/
│   │   ├── schemas.py        # VideoProject, Segment, StageRun
│   │   ├── config.py         # PipelineConfig
│   │   ├── preflight.py      # preflight + cost estimate
│   │   └── store.py          # ProjectStore (JSON на диске)
│   └── pipeline/
│       ├── runner.py         # PipelineRunner, on_stage_done callback
│       └── stages/           # extract_audio, transcribe, translate, tts, render...
├── ui/src/
│   ├── components/           # Dashboard, Workspace, NewProject, Settings...
│   ├── api/client.ts         # fetch-клиент
│   ├── types/schemas.ts      # TypeScript типы
│   ├── i18n.ts               # ru/en локализация
│   └── store/settings.ts     # localStorage персистенция
├── tests/
│   ├── unit/                 # 925 Python тестов + 223 Vitest (актуально: v1.97.0)
│   └── e2e/                  # e2e gate
├── runs/                     # рабочие директории проектов
├── Dockerfile
├── docker-compose.yml
├── Makefile                  # make deploy, make test
└── VERSION                   # текущая версия (sync с pyproject.toml + __init__.py)
```

---

## Ключевые схемы данных

**VideoProject** (core/schemas.py):
- `project_id`, `status` (created/running/completed/failed)
- `input_video`, `work_dir`, `config: PipelineConfig`
- `segments: list[Segment]`
- `stage_runs: list[StageRun]`
- `progress_percent`, `eta_seconds`, `started_at`
- `artifacts: dict[str, str]`
- `billing_snapshots: dict[str, float]` — стоимость по этапам (R10-И5)
- TypeScript тип: `billing_snapshots?: Record<string, number>` в `ui/src/types/schemas.ts`

**PipelineConfig** (core/config.py):
- `source_language`, `target_language`
- `tts_provider` (legacy/openai/elevenlabs/speechkit/polza)
- `translate_provider` (deepseek/qwen/gemini/neuroapi)
- `professional_tts_voice`, `tts_speed`

---

## Команды

| Задача | Команда |
|--------|---------|
| Деплой | `make deploy` (в `/home/user/translateVideo`) |
| Python тесты | `PYTHONPATH=src python -m unittest discover -s tests -q` |
| Python coverage | `PYTHONPATH=src python -m coverage run --source=translate_video -m unittest discover -s tests -q && python -m coverage report` |
| TS тесты | `cd ui && npm test` |
| TS build | `cd ui && npm run build` |
| Health check | `curl http://localhost:8002/api/health` |
| Swagger | `http://localhost:8002/docs` |
| Логи | `docker logs video-translator -f --tail=50` |
| Войти | `docker exec -it video-translator bash` |
| **Чистка Docker** | `docker builder prune -f && docker image prune -f` |

---

## Git Flow (СТРОГО)

1. `git checkout develop` — всегда от develop
2. `git checkout -b TVIDEO-XXX`
3. Перед push: все тесты + build
4. Push только в `develop`
5. Changelog заполнять ДО bump version
6. Версия синхронно в **5 файлах**: `VERSION`, `pyproject.toml`, `src/translate_video/__init__.py`, `ui/public/sw.js`, `PUBLIC_ROADMAP.md`

---

## Правила разработки

1. **Coverage ≥ 80% Python / ≥ 82% backend** — не снижать
2. **Coverage branch ≥ 75% TypeScript** — не снижать (Vitest branch coverage)
3. **Каждое изменение = тест** — новый код без теста не принимается
4. **Changelog до bump** — заполнить `change.log` перед изменением VERSION
5. **Идемпотентность** — пайплайн безопасен при повторном запуске
6. **Ticket в имени ветки** — `TVIDEO-XXX`
7. **Docker Hygiene (ОБЯЗАТЕЛЬНО)** — после каждого `make deploy` выполнять чистку (см. ниже)
8. **Retry/Backoff** — каждый HTTP-вызов к внешнему API обернуть в `with_retry()` немедленно при добавлении (utils/retry.py)
9. **Notification permission** — запрашивать контекстуально (при запуске действия), НЕ при старте приложения
10. **Mobile CSS** — при добавлении новых панелей добавлять `@media (max-width: 768px)` и `@media (pointer: coarse)` блоки
11. **Destructive actions** — кнопки сброса/удаления/очистки обязательно оборачивать в `window.confirm()` или custom modal
12. **Quality thresholds** — метрики качества отображать с 3-4 tier coloring (ok/warn/danger/critical), не бинарно

---

## 🐳 Docker Hygiene — ОБЯЗАТЕЛЬНО после каждого деплоя

> ⚠️ ИСТОРИЯ: В мае 2026 Docker build cache накопил **106 GB**, что привело к 100% заполнению диска и остановке работы. Правило введено как BLOCKER.

### После каждого `make deploy` выполнять:
```bash
# Чистка build cache (главный пожиратель — до 100+ GB)
docker builder prune -f

# Чистка dangling images (устаревшие слои)
docker image prune -f
```

### Еженедельная проверка дискового пространства:
```bash
# Статус Docker
docker system df

# Должно быть:
# - Build Cache: < 5 GB
# - Reclaimable Images: < 10 GB
# - Диск: < 70% (df -h /)
```

### Пороги тревоги:
| Метрика | Предупреждение | КРИТИЧНО (блок деплоя) |
|---------|---------------|------------------------|
| Диск `/` | > 70% | > 85% |
| Docker build cache | > 5 GB | > 20 GB |
| Docker images reclaimable | > 10 GB | > 30 GB |

### Полная ядерная очистка (только если диск > 85%):
```bash
# ОСТОРОЖНО: удаляет ВСЕ неиспользуемые образы
docker system prune -a -f --volumes
# После — пересобрать нужные: make deploy
```

---

## TTS-провайдеры

| Провайдер | ID | Особенности |
|-----------|-----|-------------|
| OpenAI | `openai` | gpt-4o-mini-tts, параметр `speed` |
| ElevenLabs | `elevenlabs` | voice_id, stability, speed |
| Yandex SpeechKit | `speechkit` | SSML, русский язык |
| Polza | `polza` | дешевле, rate-limit |
| Legacy | `legacy` | стандартный |

---

## Типичные проблемы

### Версии не синхронизированы
`test_version_files_are_aligned` падает → обновить все три файла: `VERSION`, `pyproject.toml`, `__init__.py`

### Batch endpoint 404
Маршрут `/batch/run` должен быть зарегистрирован ДО `/{project_id}/*` в FastAPI.

### Порт 8080 — это Open WebUI, не наш сервис
Наш сервис на **`:8002`**.

### Coverage падает
`--omit="*/legacy.py"` — legacy адаптер исключён из покрытия.

### Changelog формат (test_release_metadata падает)
Тест ищет `## X.Y.Z` (без скобок). **Не использовать** формат `## [X.Y.Z]`.
Правильно: `## 1.95.9 — 2026-05-08 — описание`

### PUBLIC_ROADMAP версия не обновлена
`test_public_roadmap_current_version_matches_version_file` — искать строку `**Текущая версия:**` в `PUBLIC_ROADMAP.md` и синхронизировать с `VERSION`.

### Agent Gate: `make deploy` обходит pre-push hook!
Хук `.git/hooks/pre-push` запускается только при `git push`. Если деплоить через `make deploy` без push — агенты не проверяются.
**Правило:** всегда делать `git push origin develop` отдельно от `make deploy`.

### DOCX без python-docx (нативный zipfile+OpenXML)
В Docker образе нет `python-docx`. Генерировать DOCX через `import zipfile; import io`.
Обязательно экранировать XML: `.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")`.

### TSV/DOCX блок: следить за отступами при вставке новых if-веток
При добавлении нового `if format == "docx":` ПЕРЕД TSV блоком — проверить что TSV код не попал внутрь docx-ветки.
Симптом: тест `test_tsv_export` возвращает TXT вместо TSV.

### billing_snapshots в export/script endpoint
Endpoint `/export/script?format=docx|tsv|txt` — новый в v1.95.8. Поддерживает `include_source` и `include_timecodes` query params.

### Паттерны R12 (v1.97.0)
- **WebSocket hook:** `useProjectWebSocket.ts` — заменяет polling. Backend endpoint `/api/v1/projects/{id}/ws` должен существовать.
- **ProjectStatus:** `created | queued | running | completed | failed | cancelled` — sync backend (`StrEnum`) ↔ frontend (`types/schemas.ts`) ↔ i18n (`i18n.ts`).
- **Email уведомления:** `EmailNotifier` в `api/notifications/__init__.py` — daemon thread, non-blocking. Конфиг только через env vars.
- **ZIP export filename:** `{video_stem}_translated.zip` (не project_id). Шаблон: `os.path.splitext(os.path.basename(project.input_video))[0]`.
- **AP-WS-AUTH:** WS endpoint `/{project_id}/ws` без auth — P1 для R13.
- **AP-DYNIMPORT:** `await import(...)` в компонентах — запрещён, заменить на static import.

## Уроки R11 (2026-05-08)
- **datetime.utcnow() deprecated**: всегда использовать `datetime.now(datetime.timezone.utc)`
- **docker-compose.yml**: убрать строку `version:` (deprecated в Compose V2+)
- **TSX декомпозиция**: после вынесения компонента — немедленно чистить unused imports
- **PUBLIC_ROADMAP.md**: обновлять версию синхронно с VERSION файлом (тест это проверяет)
