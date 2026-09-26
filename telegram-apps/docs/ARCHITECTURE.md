# Telegram Apps Hub — архитектура и спецификация

> Канонический документ по приложению. Обновлять при любом значимом изменении
> архитектуры. Составлен 2026-09-26 после полного аудита кода.

## 1. Что это за приложение

Набор **Telegram Mini Apps** («Apps Hub») — внутренний инструмент команды Алексея
и **Юли** для конвейера **перевода книг с корейского языка**, плюс сопутствующие
мелкие приложения (инвестиции, стикеры, промпты и т.п.).

Разрабатывается ~полгода. Основной пользователь-оператор — Юля.

- **Прод-домен:** `apps.bigalexn8n.ru` (наружу через Caddy → контейнер `apps-hub:8000`).
- **Точки входа:** каждый мини-апп открывается как отдельный раздел (`/ocr`, `/glossary`, …).

## 2. Где расположено (важно для будущих сессий)

| Что | Где |
|---|---|
| Исходный код | `/home/user/telegram-apps` (репозиторий git, ветка `master`) |
| Запуск | Docker-контейнер `apps-hub`, образ `lightrag-apps-hub` |
| Bind-mount | `/home/user/telegram-apps:/app:rw` — **контейнер отдаёт живые файлы** |
| Порт | 8000 (uvicorn, `network`/host через Caddy) |
| БД | PostgreSQL (контейнер `n8n-docker-db-1`, postgres:16), база `postgres`, пользователь `n8n_user` |
| Секреты | Infisical (env `dev`): `YANDEX_OAUTH_TOKEN`, `TELEGRAM_BOT_TOKEN`, `OCR_BATCH_TRIGGER_TOKEN`, `DB_PASSWORD` |
| Файловое хранилище | **Яндекс.Диск**, корень `/Yulia/+ Test/` |
| Документация | этот каталог `docs/` (`ARCHITECTURE.md`, `SCHEMA.md`, `DEVELOPMENT_PROCESS.md`, `CHANGELOG.md`) |
| Worklog OCR | `~/.openclaw/workspace/projects/ocr-miniapp/WORKLOG.md` |
| Worklog TGS | `~/.openclaw/workspace/projects/svg2tgs-test/WORKLOG.md` |

## 3. Стек

- **Backend:** один FastAPI-монолит `main.py` (~3300 строк), Python 3.10, uvicorn.
- **Frontend:** ванильный HTML/JS, по одному `static/<app>/index.html` на раздел.
  Никакого React/сборки — статика отдаётся тем же FastAPI.
- **БД:** PostgreSQL через `psycopg2` (сырые SQL, без ORM).
- **Внешние интеграции:** Яндекс.Диск REST API, n8n webhooks, локальные OCR-сервисы
  (PaddleOCR :8765, AI-OCR :8766), Telegram Bot API (через прокси `127.0.0.1:10809`).
- **Тесты:** `pytest` (API, `tests/test_*.py`) + Playwright (E2E, `tests/*.spec.js`).

## 4. Разделы (Mini Apps)

Каждый раздел = HTML-страница (`GET /<name>`) + свой набор `/api/*`-эндпоинтов.

| Раздел | Route | Назначение |
|---|---|---|
| Хаб | `/` | стартовая страница-меню |
| OCR | `/ocr` | запуск/статус пакетного OCR корейских сканов, ревью распознанного текста |
| Originals | `/originals` | обработка исходных .docx (merge, чистка мусора/пустых абзацев, конвертация) |
| Glossary | `/glossary` | глоссарий терминов KO/RU/Пол (см. §7) |
| TGS | `/tgs` | конвертация SVG → .tgs (Telegram animated stickers) для Юли |
| Prompts | `/prompts` | CRUD промптов + история версий |
| Invest | `/invest` | инвест-портфель/офферы (личный инструмент Алексея) |
| Trade | `/trade` | «лига» трейдинга |
| Files/Manage/Batya | `/files`,`/manage`,`/batya` | служебные/вспомогательные |

## 5. Архитектурные паттерны (зафиксировано)

1. **Монолит-роутер.** Весь backend в `main.py`; вспомогательная логика вынесена в
   `ocr_review.py`, `invest_logic.py`, `telegram_webapp_auth.py`, `telegram_polling.py`.
   68 эндпоинтов, сгруппированы по префиксу `/api/<domain>/`.
2. **Статика рядом с API.** Frontend не отделён от backend; каждый мини-апп —
   самодостаточный `index.html` с инлайн-JS. Общего фронт-фреймворка нет.
3. **Аутентификация = Telegram initData + allowlist.** `telegram_webapp_auth.py`
   проверяет подпись `initData` (HMAC по `TELEGRAM_BOT_TOKEN`, TTL
   `TELEGRAM_INIT_DATA_MAX_AGE`=86400с). Доступ к операциям — по allowlist
   `OCR_OPERATOR_IDS` + владелец `OCR_OWNER_ID`/`OCR_OWNER_USERNAME`.
   Анонимный web-запрос отклоняется.
4. **Двойное хранение.** Структурированные данные (термины глоссария, ревью) — в
   PostgreSQL; артефакты-файлы (.xlsx, .txt, .docx, .tgs) — на Яндекс.Диске.
5. **Единый слой Яндекс.Диска.** OAuth-токен `YANDEX_OAUTH_TOKEN` → запрос
   upload/download href → PUT/GET. Один и тот же механизм у OCR, originals, tgs,
   glossary. Пути параметризованы (`*_FOLDER_PATH`), базовый корень `/Yulia/+ Test/`.
6. **Тяжёлая работа — через n8n.** OCR не выполняется в приложении: `/api/ocr/start`
   дёргает защищённый n8n webhook (`ocr-yandex-korean-batch`), очередь и
   single-active-batch lock живут в Postgres, результат PaddleOCR кладётся на
   Я.Диск, финальный отчёт шлёт n8n. Приложение — тонкий безопасный триггер+статус.
7. **Схема БД самоприменяется.** Таблицы и миграции создаются на лету через
   `CREATE TABLE IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` при первом обращении —
   отдельного migration-раннера нет.
8. **Идемпотентность загрузки.** «Открыть глоссарий» = `DELETE + INSERT` рабочей
   области (одна область на оператора), а не мультидокументная модель.

## 6. Модель данных (PostgreSQL)

```
glossary_workspaces(owner_id PK, name, source_filename, dirty bool, updated_at)
glossary_entries(id PK, owner_id FK→workspaces ON DELETE CASCADE,
                 ko, ru, gender, position, active bool)
  idx: (owner_id, ko), (owner_id, ru), (owner_id, position, id)
```
- **Одна рабочая область на оператора** (`owner_id`). Нет понятия «много глоссариев»
  одновременно — переключение перезаливает область.
- `active=false` = «удалённый» термин (soft-delete, вкладка «Удалённые»).
- `dirty` = есть несохранённые правки (гвард при переключении/создании).
- OCR-ревью хранятся в своих таблицах (см. `ocr_review.py`).

## 7. Раздел Glossary (текущий фокус, спец Юли от 2026-09-26)

- Frontend: `static/glossary/index.html` (ванильный JS).
- Backend: эндпоинты `/api/glossary*` в `main.py` (строки ~2110–2480).
- Парсер xlsx: `parse_glossary_xlsx` (~1186–1241) — читает `sharedStrings` и
  `inlineStr`, ожидает шапку `KO / RU / Пол`.
- Ключевые эндпоинты: `load`, `name`, `new`, `entries` (CRUD),
  `entries/{id}/resolve|remove|restore`, `deleted/clear`, `export`.

## 8. Деплой

- Файлы **bind-mount** в контейнер (`:rw`), uvicorn запущен **без `--reload`**.
- **Выкатка правок = `docker restart apps-hub`** (пересборка образа не нужна,
  пока меняются только смонтированные `main.py`/`static`/helpers).
- Проверка живости: `GET /api/health`, `docker logs apps-hub`.
- Прод-проверка OCR НЕ должна запускать новый batch (только auth/health/status).

## 9. Технический долг и риски

1. **Git remote не настроен** (`git remote -v` пуст) — код только локальный,
   бэкапа в облаке нет. Реальный риск потери. → настроить приватный remote.
2. **Монолит 3300 строк** — `main.py` смешивает роутинг, бизнес-логику, SQL,
   интеграции. Тяжело тестировать и менять; растёт связанность.
3. **Сырой SQL без слоя доступа** — строки запросов разбросаны по эндпоинтам,
   легко расходятся (напр. набор колонок в SELECT).
4. **Парсер xlsx хрупкий** — жёстко ждёт шапку `KO/RU/Пол` и атрибут `r` у ячеек;
   реальные файлы Юли из Excel/Sheets часто не проходят (укреплён в `fix/glossary`,
   но остаётся зоной риска). SheetJS/openpyxl не используется — ручной разбор XML.
5. **Нет staging** — несмотря на декларацию в `DEVELOPMENT_PROCESS.md`, отдельной
   тестовой среды нет; проверка = pytest в образе + ручная после рестарта прода.
6. **Интеграционные тесты требуют живой Postgres** — часть тестов (`ai_start`,
   glossary-эндпоинты с БД) не гоняются в песочнице.
7. **Секреты в env контейнера** — корректно (Infisical), но много доменов делят
   один процесс; компрометация процесса = доступ ко всем токенам.
8. **Frontend без сборки/тестов компонентов** — вся логика инлайн в HTML,
   регрессии ловятся только Playwright-ом по критическим сценариям.

## 10. Как проверять изменения (DoD)

- `docker exec apps-hub python -m unittest tests.test_ocr_api` (или pytest) — зелёные.
- Для багов — добавить регрессионный тест (TDD, см. `DEVELOPMENT_PROCESS.md`).
- Синтаксис `main.py` и затронутого JS — чисто.
- Playwright по затронутому сценарию, если UI.
- Деплой (`docker restart apps-hub`) — только после зелёных тестов и «ок» Алексея.
- Работать в ветке `fix/*` или `feature/*`, `master` не трогать без явного слияния.
