# Infisical N8N Infra Cutover

## Update 2026-04-18 14:45 MSK

Cutover завершен.

Что подтверждено:

- infra-secrets загружены в `Infisical` environment `dev`
- `n8n-docker/docker-compose.yml` больше не содержит fallback literals для чувствительных значений
- для `docker compose` действий добавлен wrapper:
  - `/home/user/n8n-docker/scripts/compose_with_infisical.sh`
- `restart_n8n.sh` переведен на wrapper
- стек был пересоздан через `infisical run -- docker compose up -d`
- post-check:
  - `https://bigalexn8n.ru` отвечает `200`
  - `./scripts/compose_with_infisical.sh ps` показывает поднятые `db`, `n8n`, `pgadmin`, `prometheus`, `postgres-exporter`

Практический итог:

- staged режим больше не нужен как основной operational path
- обычные compose-действия для этого проекта нужно выполнять через `./scripts/compose_with_infisical.sh ...`
- временный plaintext-файл `.env.infisical.n8n.infra` после cutover удален

## Что уже сделано

- `docker-compose.yml` переведен в staged режим:
  - сначала пробует брать чувствительные значения из env
  - если env не передан, использует текущие fallback literals
- добавлен пример env-файла:
  - `/home/user/n8n-docker/.env.infisical.n8n.infra.example`
- добавлены host-side helper scripts:
  - `/home/user/n8n-docker/scripts/set_n8n_infra_secrets_in_infisical.sh`
  - `/home/user/n8n-docker/scripts/verify_n8n_infra_infisical.sh`

Изначально это было сделано как безопасный staged cutover:

1. сначала загружаем секреты в `Infisical`
2. потом перезапускаем стек
3. только после успешной проверки убираем fallback literals из `docker-compose.yml`

## Какие секреты переводятся

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `N8N_ENCRYPTION_KEY`
- `DB_POSTGRESDB_HOST`
- `DB_POSTGRESDB_PORT`
- `DB_POSTGRESDB_DATABASE`
- `DB_POSTGRESDB_USER`
- `DB_POSTGRESDB_PASSWORD`
- `PGADMIN_DEFAULT_EMAIL`
- `PGADMIN_DEFAULT_PASSWORD`
- `POSTGRES_EXPORTER_DATA_SOURCE_NAME`

## Почему cutover не был выполнен из текущей сессии

В этой песочнице `infisical` CLI не может взять credential из system keyring:

```text
failed to fetch credentials from keyring
dial unix /run/user/1000/bus: connect: operation not permitted
```

То есть проблема не в `Infisical` и не в конфиге проекта, а в ограничении среды выполнения.

## Что делать на хосте

### 1. Подготовить env-файл с реальными значениями

```bash
cd /home/user/n8n-docker
cp .env.infisical.n8n.infra.example .env.infisical.n8n.infra
```

Заполнить файл реальными значениями.

### 2. Загрузить секреты в Infisical

Если CLI уже залогинен:

```bash
cd /home/user/n8n-docker
./scripts/set_n8n_infra_secrets_in_infisical.sh
```

Если нужен service token:

```bash
cd /home/user/n8n-docker
INFISICAL_TOKEN='...'
export INFISICAL_TOKEN
./scripts/set_n8n_infra_secrets_in_infisical.sh
```

### 3. Проверить наличие всех секретов

```bash
cd /home/user/n8n-docker
./scripts/verify_n8n_infra_infisical.sh
```

### 4. Перезапустить стек

```bash
cd /home/user/n8n-docker
./scripts/compose_with_infisical.sh down
./scripts/compose_with_infisical.sh up -d
```

### 5. Проверить после перезапуска

- `n8n` открывается
- workflow MOEX остаются активными
- cron-triggered path продолжает писать в trade DB
- `tradekb` продолжает принимать `candle_snapshot` и `news_item`

## Что останется после успешной проверки

После host-side verification cleanup pass уже выполнен:

1. fallback literals удалены из `docker-compose.yml`
2. временная plaintext-копия `n8n` infra env удалена
3. `PGADMIN_DEFAULT_EMAIL` и `PGADMIN_DEFAULT_PASSWORD` остаются в `Infisical`
