# MOEX Cron Setup

Этот fallback нужен, пока встроенный `Schedule Trigger` в `n8n` не подтвержден как надежный production-механизм для MOEX workflow.

## Что уже подготовлено

- cron manifest: `/home/user/n8n-docker/crontab/moex_research.cron`
- trigger script: `/home/user/n8n-docker/scripts/trigger_moex_workflow.sh`
- installer: `/home/user/n8n-docker/scripts/apply_moex_cron.sh`
- remover: `/home/user/n8n-docker/scripts/remove_moex_cron.sh`

## Что делает cron

- `news`: каждые 15 минут со сдвигом в 3 минуты
- `candle`: по сессионным окнам MOEX для weekday и weekend
- `digest`: ежедневно в `00:20 MSK`
- `backfill`: ежедневно в `03:07 MSK`

В cron manifest явно зафиксирован `Europe/Moscow`:

- `CRON_TZ=Europe/Moscow`
- `TZ=Europe/Moscow`

## Установка на хосте

Выполнить на хосте под тем пользователем, у которого должен жить cron:

```bash
cd /home/user/n8n-docker
./scripts/apply_moex_cron.sh
crontab -l
```

Скрипт не затирает чужие cron entries. Он обновляет только managed block между маркерами:

```text
# BEGIN MOEX RESEARCH
# END MOEX RESEARCH
```

## Снятие cron блока

```bash
cd /home/user/n8n-docker
./scripts/remove_moex_cron.sh
crontab -l
```

## Ручная проверка до ожидания расписания

Можно вручную дернуть каждый workflow:

```bash
/home/user/n8n-docker/scripts/trigger_moex_workflow.sh news
/home/user/n8n-docker/scripts/trigger_moex_workflow.sh candle
/home/user/n8n-docker/scripts/trigger_moex_workflow.sh digest
/home/user/n8n-docker/scripts/trigger_moex_workflow.sh backfill
```

## Проверка логов

```bash
tail -f /home/user/n8n-docker/logs/moex-news-cron.log
tail -f /home/user/n8n-docker/logs/moex-candle-cron.log
tail -f /home/user/n8n-docker/logs/moex-digest-cron.log
tail -f /home/user/n8n-docker/logs/moex-backfill-cron.log
```

## Что считать успешной проверкой

Нужно подтвердить:

1. cron реально вызывает webhook без сетевых ошибок
2. в `n8n` появляются новые execution от webhook path
3. `news` пишет новые записи в `raw.news_item` и матчи в `raw.news_instrument_match`
4. `candle` пишет очередную порцию свечей в trade DB
5. `digest` собирает summary и пушит материал в отдельный trade LightRAG

Только после этого имеет смысл переносить секреты в `Infisical`.
