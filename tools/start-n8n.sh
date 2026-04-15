#!/bin/bash
# Запуск n8n через Infisical Secrets Manager
# Все секреты (DB, Encryption, Proxy) теперь управляются в UI Infisical

cd /home/user/n8n-docker

# Инъекция секретов из Infisical и запуск n8n
infisical run --domain https://secrets.bigalexn8n.ru --env dev -- n8n start
