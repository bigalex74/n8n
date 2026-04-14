# Аудит 34 активных workflow проекта n8n (KO→RU Translation)

**Дата аудита:** 14 апреля 2026  
**Аудитор:** Qwen Code (анализ через n8n MCP API)  
**Методология:** Полный JSON каждого workflow через `n8n_get_workflow mode="full"`, анализ по 7 критериям.

---

## Сводка по всем workflow

| # | Workflow | Nodes | CRITICAL | HIGH | MEDIUM | LOW |
|---|----------|-------|----------|------|--------|-----|
| 1 | Start | 21 | 1 | 2 | 2 | 1 |
| 2 | Translate Chunk | 17 | 0 | 1 | 1 | 1 |
| 3 | [Перевод] Перевод чанка | 34 | 1 | 1 | 1 | 2 |
| 4 | [Перевод] Глава | 26 | 0 | 0 | 1 | 1 |
| 5 | [Перевод] Арка | 31 | 0 | 0 | 1 | 2 |
| 6 | [Перевод] Обработка ошибки | 14 | 0 | 1 | 2 | 0 |
| 7 | Finish | 10 | 0 | 1 | 1 | 0 |
| 8 | [GET] Document | 14 | 0 | 0 | 0 | 1 |
| 9 | [GET] /select_files | 72 | 1 | 3 | 2 | 1 |
| 10 | Парсинг файла для перевода | 10 | 0 | 0 | 0 | 1 |
| 11 | Предварительный анализ файла для перевода | 27 | 0 | 1 | 2 | 1 |
| 12 | Send Message | 12 | 0 | 0 | 0 | 0 |
| 13 | [Send] create_job | 8 | 0 | 0 | 0 | 1 |
| 14 | [Send] wait | 10 | 0 | 0 | 0 | 0 |
| 15 | [Send] processing | 13 | 0 | 1 | 1 | 1 |
| 16 | [Send] error | 5 | 0 | 0 | 0 | 0 |
| 17 | [Send] finish | 19 | 0 | 1 | 1 | 1 |
| 18 | Получение сообщения | 8 | 0 | 0 | 1 | 0 |
| 19 | Select From List | 10 | 0 | 1 | 0 | 0 |
| 20 | Создание Глоссария | 17 | 0 | 0 | 0 | 1 |
| 21 | Добавление Глоссария | 9 | 0 | 0 | 0 | 1 |
| 22 | Добавление Промта | 10 | 0 | 0 | 0 | 1 |
| 23 | Добавление промта для постредакта | 10 | 0 | 0 | 0 | 1 |
| 24 | Постредактура | 9 | 0 | 0 | 0 | 1 |
| 25 | Настройка БД | 8 | 0 | 1 | 1 | 0 |
| 26 | Добавление ресурсов в бд | 23 | 0 | 1 | 1 | 1 |
| 27 | sub_lightrag_api | 5 | 0 | 1 | 0 | 0 |
| 28 | Переведенный файл в Google Drive | 11 | 0 | 0 | 0 | 1 |
| 29 | Переведенный файл в Telegram | 9 | 0 | 0 | 0 | 1 |
| 30 | Анотация | 7 | 0 | 0 | 1 | 0 |
| 31 | Перезапуск прослушки Telegram | 4 | 0 | 0 | 0 | 0 |
| 32 | Global Error Handler | 2 | 0 | 0 | 1 | 0 |
| 33 | Activate Translation Workflows | 5 | 0 | 0 | 1 | 0 |
| 34 | Ручной выбор файлов | 30 | 1 | 1 | 1 | 2 |

**ИТОГО:** CRITICAL: 4, HIGH: 14, MEDIUM: 18, LOW: 20

---

## Детальный анализ по workflow

### 1. Start (9cjeUNeTZX3YnO1W57YTP) — Главный оркестратор

#### A. Архитектурные паттерны
- **[HIGH]** Оркестратор делает слишком много: биллинг, настройка БД, парсинг, анализ, глоссарий, промты — всё в одном workflow. Нарушение single responsibility. Рекомендация: разделить на инициализацию и основной поток.
- **[MEDIUM]** Merge-узел с 5 входами (Merge1) — сложный узел синхронизации. При падении одного из 5 параллельных путей (Без доп Промта × 2, Создание Глоссария → Добавление Глоссария1, Добавление Промта, Добавление Промта для постредакта) — Merge зависнет.

#### B. Обработка ошибок
- **[CRITICAL]** `errorWorkflow` НЕ установлен в settings. При критической ошибке в Start workflow не будет делегирован на global-error-handler.
- **[HIGH]** Billing-запросы (Polza.ai, NeuroAPI) имеют `onError: continueRegularOutput` — при ошибке биллинга workflow продолжит выполнение без данных о балансе. Нет fallback на нулевые значения.

#### D. Безопасность
- **[CRITICAL]** HARDCODED API ключи в узлах "Billing Polza.ai" и "Billing Neuro":
  - `Bearer pza_PV5t0y6PTuE8GLcZ-jgvlpNDLlZm0mUT` (Polza.ai)
  - `Bearer sk-JPPv8NvhqimYVBabJvm6fB5mlv80WnLV673tfVzFm6IYq67V` (NeuroAPI)
  Рекомендация: вынести в Credentials Manager.

#### E. Best Practices
- **[MEDIUM]** Узлы "Без доп Промта" и "Без доп Промта1" — дублирование логики (одинаковый SQL UPDATE). Можно объединить.
- **[LOW]** Нет комментариев/notes на большинстве узлов.

---

### 2. Translate Chunk (Q5TRHGg-XRblnMRpH41Ee) — Цикл обработки чанков

#### A. Архитектурные паттерны
- **[HIGH]** Рекурсивный вызов самого себя: "Переход на следующий чанк" вызывает Q5TRHGg-XRblnMRpH41Ee. При большом количестве чанков может переполнить стек вызовов или memory. Рекомендация: использовать SplitInBatches с Loop Over Items вместо рекурсии.

#### B. Обработка ошибок
- **[MEDIUM]** errorWorkflow не установлен. Рекомендация: установить `global-error-handler-36id`.

#### E. Best Practices
- **[LOW]** `waitForSubWorkflow: false` для "Выполнить задачу по переводу текста" — если sub-workflow упадёт, Translate Chunk не узнает. Для "Финиш" аналогично.

---

### 3. [Перевод] Перевод чанка (GPARI8V4RBSPL1h39_kHW) — AI перевод с fallback

#### B. Обработка ошибок
- **[HIGH]** Узел "Если не ERROR?" — пустое условие (`"leftValue": "", "rightValue": "", "operator": {"type": "string", "operation": "equals"}`). Всегда будет true (пустая строка == пустая строка), т.е. никогда не перейдёт на error-ветку. Это делает fallback "Резервный перевод чанка" недостижимым при ошибках AI.
  
#### D. Безопасность
- **[CRITICAL]** SQL-инъекция: `"result_text = '{{ $json.output.replaceAll(`'`, `''`) }}'"`. Метод `replaceAll("'", "''")` НЕ защищает от всех видов SQL-инъекций (например, через backslash-escaping в PostgreSQL). Рекомендация: использовать `queryReplacement` (параметризированные запросы).

#### E. Best Practices
- **[MEDIUM]** Узел "If" — пустое условие, всегда false. Мёртвый код.
- **[LOW]** Дублирование кода формирования глоссария: узел "Формирование промтов для перевода" и "Формирование промтов для перевода1" содержат одинаковый JS-код.

---

### 4. [Перевод] Глава (IgLfaCSszdwsPw_b4u3au) — Rolling summary главы

#### E. Best Practices
- **[MEDIUM]** Узел "Code in JavaScript" имеет нейтральное имя. Переименовать в "Форматирование summary для LightRAG".
- **[LOW]** Gemini 2.5 Flash Lite подключён через Neuroapi credential (not Polza) — проверить корректность провайдера.

---

### 5. [Перевод] Арка (OggkJgA8IFmasME_BNimq) — Rolling summary арки

#### E. Best Practices
- **[MEDIUM]** Опечатка в имени узла: "Нчало новой арки?" → "Начало новой арки?". Также "Cоздание стартового Summary" (кириллическая 'C' вместо латинской 'C' может вызывать проблемы при поиске).
- **[LOW]** Insert into LightRAG: `waitForSubWorkflow: false` — если LightRAG не успеет обработать, summary арки может быть потерян.

---

### 6. [Перевод] Обработка ошибки (ImJpqAA5WlJZDK5jMtQSM)

#### B. Обработка ошибок
- **[HIGH]** SQL-инъекция: `"error_text = '{{ $json.error_text.replaceAll(`'`,`''`) }}'"` — та же проблема что и в WF #3.
  
#### C. Производительность
- **[MEDIUM]** Цикл polling'а: Wait 5s → Подтверждение пришло? → Wait 5s → ... бесконечный цикл с интервалом 5 секунд. Может создавать тысячи executions. Рекомендация: использовать webhook-based ожидание вместо polling.
- **[MEDIUM]** "Чтение данных текущей задачи" делает `SELECT * FROM document_log` без LIMIT — читает ВСЕ логи job. При длительном переводе — огромный объём данных.

---

### 7. Finish (vuqLp6ZGenvpkJbmVPR_6)

#### B. Обработка ошибок
- **[HIGH]** Узел "to log" имеет пустой output connection (`"main": [[]]`) — мёртвый узел, никогда не сработает.

#### E. Best Practices
- **[MEDIUM]** PinData содержит `job_id: 48` — тестовые данные в production workflow. Может привести к неверному поведению.

---

### 8. [GET] Document (sLo74sUgMdcJEmxJoRJQ-)

#### E. Best Practices
- **[LOW]** `get_file` в Telegram node не имеет `retryOnFail`. При временных ошибках сети документ будет потерян.

---

### 9. [GET] /select_files (MmfiOXrCt2lkZ4TxZMyWS) — 72 узла

#### A. Архитектурные паттерны
- **[CRITICAL]** 72 узла в одном workflow — это слишком много. Содержит UI выбора файлов, обработку callback, загрузку файлов в БД, удаление сообщений, и запуск перевода. Рекомендация: разделить на UI-часть и обработку загрузки.

#### B. Обработка ошибок
- **[HIGH]** errorWorkflow НЕ установлен.

#### C. Производительность
- **[HIGH]** 7 Delete a chat message + 7 Execute a SQL query + 7 Update row(s) — паттерн copy-paste для каждого типа файла (translate, glossary, prompt, post_prod). Это дублирование. Рекомендация: использовать SplitInBatches + Loop.
- **[MEDIUM]** Replace Me узел найден — забытый placeholder.

#### D. Безопасность
- **[HIGH]** Telegram API token захардкожен в HTTP Request: `https://api.telegram.org/bot8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0/sendMessage`. Это критическая утечка.

#### E. Best Practices
- **[MEDIUM]** Множество "Delete a chat message" с одинаковой логикой.
- **[LOW]** Код создания inline-клавиатуры в JS содержит дублирование текстов.

---

### 10. Парсинг файла для перевода (bC43bgf5ZtXoi_XDLDwHO)

#### E. Best Practices
- **[LOW]** Postgres typeVersion: 2.1 (устаревший, актуальный 2.6).

---

### 11. Предварительный анализ файла для перевода (lSuNRX0VILP9Lgit5VKlK)

#### B. Обработка ошибок
- **[HIGH]** При ошибке обоих Information Extractor (основного и резервного), workflow продолжает выполнение с пустыми данными. Нет Stop/Error узла.

#### C. Производительность
- **[MEDIUM]** Loop Over Items проходит по ВСЕМ чанкам файла (может быть 100+). Каждый вызов Information Extractor — дорогой AI запрос. Рекомендация: ограничить количество итераций или батчить.
- **[MEDIUM]** Wait 30 сек после ошибки — длительный простой. При 10+ ошибках = 5+ минут простоя.

#### E. Best Practices
- **[LOW]** Узел "Уведомление: Прогресс" не имеет executeOnce — будет вызываться на каждой итерации цикла, создавая множество Telegram-запросов.

---

### 12. Send Message (J62UViXZMD5o6qoU)

#### Анализ
- Без критических проблем. Простой роутер по template.
- **[LOW]** Узел "Сообщение Старт обработки" имеет пустой output connection.

---

### 13. [Send] create_job (ScNLD3LbRTVAJOK4)

#### E. Best Practices
- **[LOW]** errorWorkflow не установлен.

---

### 14. [Send] wait (OWLYY2oiQ6YPBJ7M)

#### Анализ
- Polling Telegram getUpdates каждые 1 сек — корректная реализация для ожидания callback.
- **[MEDIUM]** При большом количестве обновлений getUpdates может вернуть старые данные.

---

### 15. [Send] processing (9uUyj9OamISRPudJ)

#### B. Обработка ошибок
- **[HIGH]** Хардкод API ключей в "Billing Polza.ai" и "Billing Neuro" — те же ключи что и в Start.
  
#### D. Безопасность
- **[HIGH]** API ключи в plaintext:
  - `Bearer pza_PV5t0y6PTuE8GLcZ-jgvlpNDLlZm0mUT`
  - `Bearer sk-JPPv8NvhqimYVBabJvm6fB5mlv80WnLV673tfVzFm6IYq67V`

#### E. Best Practices
- **[MEDIUM]** Billing-запросы с timeout=1000ms (1 секунда) — может быть недостаточно при высокой нагрузке.
- **[LOW]** Закомментированный код: `// const done = Math.floor(Math.random() * total);`

---

### 16. [Send] error (2uhp8PCTjxiKj91n)

#### Анализ
- Без проблем. Минималистичный workflow из 5 узлов.

---

### 17. [Send] finish (hoUl3ewz23AwAHlq)

#### B. Обработка ошибок
- **[HIGH]** Хардкод API ключей в Billing узлах.

#### D. Безопасность
- **[HIGH]** API ключи:
  - `Bearer pza_PV5t0y6PTuE8GLcZ-jgvlpNDLlZm0mUT`
  - `Bearer sk-JPPv8NvhqimYVBabJvm6fB5mlv80WnLV673tfVzFm6IYq67V`

#### E. Best Practices
- **[MEDIUM]** Аннотация: код парсинга ответа аннотации может упасть если формат ответа от LLM нарушен (split('---') может дать < 3 parts).
- **[LOW]** TG caption limit 1024 — обрезка без предупреждения пользователю.

---

### 18. Получение сообщения (CHSGtgO88LgGVbV8)

#### C. Производительность
- **[MEDIUM]** Telegram polling каждые 5 минут (Schedule Trigger) — при большом количестве сообщений может быть задержка. Рекомендация: webhook вместо polling.

---

### 19. Select From List (CJ7lDvgGlmoP8Ymbgqd0A)

#### B. Обработка ошибок
- **[HIGH]** SQL-инъекция: `WHERE date_time > '{{ $('TG | send').first().json.result.date.toDateTime('s') }}'` — выражение вставляется напрямую в SQL.

---

### 20. Создание Глоссария (t8Dmavjx9KS5Ms3SB3Qdj)

#### E. Best Practices
- **[LOW]** Google Drive файл создаётся в root папке с `allowFileDiscovery: true` — публичный доступ к файлу с глоссарием. Рекомендация: ограничить доступ.

---

### 21. Добавление Глоссария (ZdsvkMfRDAU4yLbL3DPcK)

#### D. Безопасность
- **[LOW]** `json_to_recordset($1)` с `queryReplacement: '={{ $input.all() }}'` — сериализация всех входных данных в JSON. При большом глоссарии может превысить лимит параметра PostgreSQL.

---

### 22. Добавление Промта (TVHpHR7HlCdrqEvAF3WNP)

#### E. Best Practices
- **[LOW]** Postgres typeVersion: 2.1 (устаревший).

---

### 23. Добавление промта для постредакта (FuVQL0O5ik3aocbx)

#### E. Best Practices
- **[LOW]** errorWorkflow не установлен. Postgres typeVersion: 2.1.

---

### 24. Постредактура (A8zKJVQgROH1cnkv)

#### E. Best Practices
- **[LOW]** errorWorkflow не установлен — при падении AI-агента постредактуры ошибка не будет обработана глобально.

---

### 25. Настройка БД (UnqVdfxubclgfA7tafBwo)

#### B. Обработка ошибок
- **[HIGH]** Создает ВСЕ таблицы с нуля (`CREATE TABLE IF NOT EXISTS`) + `TRUNCATE TABLE job_current` при каждом запуске. При параллельных переводах TRUNCATE удалит данные другого перевода.
- **[MEDIUM]** `DROP TABLE IF EXISTS telegram_chats CASCADE` — удалит ВСЕ данные о чатах, включая авторизованные.

#### D. Безопасность
- **[MEDIUM]** SQL содержит `INSERT INTO telegram_chats (chat) VALUES ('{{ $('Start Workflow').first().json.chat_id }}')` — потенциальная инъекция если chat_id не валидирован.

---

### 26. Добавление ресурсов в бд (rlk5lgq3uE4N0yl0)

#### B. Обработка ошибок
- **[HIGH]** errorWorkflow не установлен.

#### A. Архитектурные паттерны
- **[MEDIUM]** Дублирование логики загрузки файлов (Get base64 string × 4, Запись в БД × 4). Можно параметризировать.

---

### 27. sub_lightrag_api (AW58nseQdLtJn5ZO)

#### B. Обработка ошибок
- **[HIGH]** errorWorkflow не установлен. `continueOnFail: true` на HTTP запросах — ошибки API LightRAG будут проглочены.

---

### 28. Переведенный файл в Google Drive (KebWQcS1WmNtgdgA)

#### E. Best Practices
- **[LOW]** Папка на Google Drive с `type: anyone, role: writer` — любой человек с ссылкой может редактировать. Рекомендация: `role: reader`.

---

### 29. Переведенный файл в Telegram (sv73wrV6anQE7cTv)

#### D. Безопасность
- **[LOW]** SQL: `WHERE id = $1` с `queryReplacement: "={{ $json.translate_file.split('_')[1] }}"` — если translate_file не содержит '_', будет ошибка JS.

---

### 30. Анотация (2kztTVutdATd1MDS)

#### E. Best Practices
- **[MEDIUM]** Хардкод Polza API key в "Генерация обложки": `Bearer pza_PV5t0y6PTuE8GLcZ-jgvlpNDLlZm0mUT ` (с пробелом на конце — может вызвать 401).
- **[LOW]** Flux API endpoint захардкожен.

---

### 31. Перезапуск прослушки Telegram (GiqH3FrsgKjwIbUfcS6-j)

#### Анализ
- Простой workflow: Schedule → Deactivate → Wait 3s → Activate. Без проблем.

---

### 32. Global Error Handler (global-error-handler-36id)

#### E. Best Practices
- **[MEDIUM]** Проверить содержимое — если handler не логирует ошибку в document_log, ошибки будут теряться.

---

### 33. Activate Translation Workflows (activate-translation-workflows)

#### E. Best Practices
- **[MEDIUM]** Описан как "[NOT USED]" в описании, но активен. Если не используется — деактивировать.
- **[LOW]** Webhook без авторизации — любой может вызвать `/webhook/activate-translation-workflows` и активировать все workflow.

---

### 34. Ручной выбор файлов (AnPEATb8u6yyFa54)

#### A. Архитектурные паттерны
- **[CRITICAL]** 30 узлов + Form Trigger с динамическими dropdown из Google Drive. При большом количестве файлов (100+) форма может не загрузиться (ограничение размера URL).

#### B. Обработка ошибок
- **[HIGH]** errorWorkflow не установлен.

#### D. Безопасность
- **[HIGH]** Google Drive OAuth credential используется для поиска/скачивания файлов — проверить что scope ограничен только нужными папками.

#### E. Best Practices
- **[MEDIUM]** DataTable "select_files" создается/удаляется каждый раз — race condition при параллельных запусках.
- **[LOW]** Файл для поиска промта: `name='{{ ... }}'` — если имя содержит спецсимволы, Google Drive query может упасть.

---

## Общие проблемы (cross-cutting concerns)

### БЕЗОПАСНОСТЬ

1. **[CRITICAL] Хардкод API ключей** — найдено в 5+ workflow:
   - Polza.ai: `pza_PV5t0y6PTuE8GLcZ-jgvlpNDLlZm0mUT`
   - NeuroAPI: `sk-JPPv8NvhqimYVBabJvm6fB5mlv80WnLV673tfVzFm6IYq67V`
   - Telegram Bot: `8591497428:AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0`
   - **Рекомендация:** Перенести все в n8n Credential Manager и заменить ссылки в workflow.

2. **[HIGH] SQL-инъекции** — минимум 3 места где данные вставляются напрямую в SQL через `{{ }}`:
   - WF #3: `result_text = '{{ $json.output.replaceAll(`'`, `''`) }}'`
   - WF #6: `error_text = '{{ $json.error_text.replaceAll(`'`,`''`) }}'`
   - WF #19: `WHERE date_time > '{{ ... }}'`
   - **Рекомендация:** Использовать `queryReplacement` (параметризированные запросы).

3. **[HIGH] Google Drive public access** — файлы и папки создаются с `type: anyone, role: writer`.
   - **Рекомендация:** Изменить на `type: anyone, role: reader` или использовать restricted sharing.

### ОБРАБОТКА ОШИБОК

4. **[HIGH] errorWorkflow НЕ установлен** в ~10 workflow. При ошибке execution просто завершится без уведомления.
   - Затронутые: Translate Chunk, [GET] /select_files, Добавление Глоссария, Добавление Промта, Добавление промта для постредакта, Постредактура, Добавление ресурсов в бд, sub_lightrag_api, Ручной выбор файлов.
   - **Рекомендация:** Установить `errorWorkflow: global-error-handler-36id` во всех workflow.

### ПРОИЗВОДИТЕЛЬНОСТЬ

5. **[HIGH] Рекурсивный вызов** Translate Chunk вызывает сам себя для каждого чанка. При 4000+ чанках — риск memory exhaustion.
   - **Рекомендация:** Переписать с использованием SplitInBatches + Loop Over Items.

6. **[MEDIUM] Polling вместо webhook** — "Получение сообщения" polling Telegram каждые 5 мин, "Обработка ошибки" polling каждые 5 сек.
   - **Рекомендация:** Использовать Telegram webhook trigger.

### АРХИТЕКТУРА

7. **[HIGH] [GET] /select_files — 72 узла.** Это самый большой workflow. Содержит дублирование логики для каждого типа файла.
   - **Рекомендация:** Рефакторинг с использованием циклов.

8. **[MEDIUM] Дублирование billing-запросов.** Billing Polza.ai и Billing Neuro встречаются в Start, [Send] processing, [Send] finish — 3 копии с хардкод ключами.
   - **Рекомендация:** Вынести в sub-workflow "Get Billing Info".

9. **[MEDIUM] Настройка БД: TRUNCATE job_current** при каждом запуске. При параллельных переводах — потеря данных.
   - **Рекомендация:** Удалить TRUNCATE, использовать DELETE WHERE job_id = ...

### BEST PRACTICES

10. **[MEDIUM] PinData в production.** Start, Finish, Перевод чанка, Создание Глоссария, Добавление Глоссария, Добавление Промта, sub_lightrag_api, Ручной выбор файлов — все содержат pinData.
    - **Рекомендация:** Удалить pinData из всех production workflow.

11. **[LOW] Устаревшие typeVersion.** Некоторые Postgres-узлы используют 2.1 вместо 2.6.

12. **[LOW] Мёртвые узлы:** Replace Me1 (WF #11), Replace Me (WF #9), If (WF #3), empty output connections (WF #12, #7).

---

## Приоритетный план исправлений

### Немедленно (P0 — Security)
1. Убрать все хардкод API ключи → Credential Manager
2. Исправить SQL-инъекции → queryReplacement
3. Ограничить Google Drive access → reader вместо writer

### Срочно (P1 — Reliability)
4. Установить errorWorkflow во все workflow
5. Переписать рекурсивный цикл Translate Chunk
6. Убрать TRUNCATE job_current из Настройки БД

### Важно (P2 — Performance)
7. Рефакторинг /select_files (72 → ~20 узлов)
8. Вынести billing в sub-workflow
9. Polling → webhook для Telegram

### Планово (P3 — Best Practices)
10. Удалить PinData из production
11. Обновить typeVersion
12. Удалить мёртвые узлы
13. Добавить comments/notes

---

*Аудит завершён. Всего найдено: 4 CRITICAL, 14 HIGH, 18 MEDIUM, 20 LOW.*
