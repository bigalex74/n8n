# Cron Backup Fix Report - 2026-04-14

## Проблемы (3 root causes)

### 1. Git dubious ownership (root vs user)
Cron запускался от root, но репозиторий принадлежал user. Git блокировал операции.
**Решение:** Добавлен safe.directory на уровне system (root) и global (user)

### 2. sync.log конфликты слияния
sync.log был в .gitignore, но отслеживался в git — вызывал конфликты при каждом pull/merge.
**Решение:** Убран из индекса через `git rm --cached sync.log`, добавлен в .gitignore

### 3. Секрет Grafana в settings.json
Grafana service account token попал в коммит — GitHub заблокировал push.
**Решение:** settings.json добавлен в .gitignore, удалён из индекса

### 4. Некорректный stash handling
`git stash; git pull; git stash pop` в одну строку через `;` — ошибки игнорировались
**Решение:** Разделено на отдельные команды с обработкой ошибок

### 5. Дублирование cron задач
Одна и та же задача была и в root и в user crontab — два параллельных запуска конфликтовали
**Решение:** Удалено из root crontab, осталось только от user

## Изменения в sync_n8n.sh
- Abort rebase/merge перед каждой операцией
- .last_branch_number сохраняется/восстанавливается вокруг stash
- sync.log исключён из stash и merge
- `--strategy-option ours` для автоматического разрешения конфликтов
- `git rm --cached sync.log` перед pull для гарантии

## Итог
✅ Бэкап работает каждые 4 часа от user
✅ Репозиторий всегда в чистом состоянии
✅ Конфликтов больше нет
