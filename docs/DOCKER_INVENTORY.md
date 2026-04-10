# Docker Inventory

## Активные контейнеры (на 31.03.2026)

### Новые контейнеры (LightRAG + Ollama)

#### **Ollama** (ollama/ollama:latest)
- **Container ID:** ddc0ce7211a0
- **Статус:** Up 16 minutes
- **Сеть:** host networking
- **Порт:** 11434/tcp (внутри контейнера)
- **Volume:** ollama_storage
- **Конфигурация:**
  - `OLLAMA_HOST=0.0.0.0:11434`
  - NVIDIA GPU support (compute,utility)
- **Назначение:** Локальная LLM inference для LightRAG
- **Compose проект:** /home/user/lightrag/docker-compose.yml

#### **LightRAG** (lightrag-lightrag)
- **Container ID:** 41011865ff90
- **Статус:** Up 16 minutes
- **Сеть:** host networking
- **Порт:** 9621/tcp (внутри контейнера)
- **Volumes:**
  - /home/user/lightrag/inputs:/app/inputs
  - /home/user/lightrag/outputs:/app/outputs
  - /home/user/lightrag/dict:/app/dict
- **Environment:**
  - `LLM_BINDING=openai`
  - `LLM_MODEL=openai/gpt-5.4-nano`
  - `LLM_BASE_URL=https://polza.ai/api/v1`
  - `LLM_API_KEY=pza_PV5t0y6PTuE8GLcZ-jgvlpNDLlZm0mUT`
  - `EMBEDDING_BINDING=ollama`
  - `EMBEDDING_MODEL=nomic-embed-text`
  - `EMBEDDING_DIM=768`
  - `CHUNK_SIZE=500`
  - `CHUNK_OVERLAP_SIZE=50`
- **Назначение:** RAG (Retrieval-Augmented Generation) система
- **Compose проект:** /home/user/lightrag/docker-compose.yml

---

### Существующие контейнеры (n8n экосистема)

#### **n8n** (docker.n8n.io/n8nio/n8n:latest)
- **Container ID:** 00d84ff9a0ef
- **Статус:** Up 8 hours
- **Размер образа:** 1.17GB
- **Назначение:** Workflow automation

#### **PostgreSQL** (postgres:16-alpine)
- **Container ID:** 3157770354cb
- **Статус:** Up 34 hours
- **Порт:** 5432/tcp
- **Volume:** n8n-docker_db_storage
- **Назначение:** База данных для n8n

#### **pgAdmin4** (dpage/pgadmin4:latest)
- **Container ID:** 21b6a54cd027
- **Статус:** Up 34 hours
- **Порт:** 127.0.0.1:5055->80/tcp
- **Volume:** n8n-docker_pgadmin_data
- **Назначение:** PostgreSQL администрирование

#### **Caddy** (caddy:2-alpine)
- **Статус:** Up 8 hours
- **Размер образа:** 62.1MB
- **Volumes:** n8n-docker_caddy_config, n8n-docker_caddy_data
- **Назначение:** Reverse proxy для n8n (bigalexn8n.ru)

#### **Grafana** (grafana/grafana:11.5.0)
- **Container ID:** 5e25bfa6cacc
- **Статус:** Up 8 hours
- **Порт:** 3000/tcp
- **Volume:** n8n-docker_grafana_storage
- **Назначение:** Мониторинг и визуализация

#### **Prometheus** (prom/prometheus:latest)
- **Container ID:** ae9a9bbba3cf
- **Статус:** Up 8 hours
- **Порт:** 9090/tcp
- **Volume:** n8n-docker_prometheus_data
- **Назначение:** Сбор метрик

#### **Node Exporter** (prom/node-exporter:latest)
- **Container ID:** 1b3c587b803b
- **Статус:** Up 8 hours
- **Порт:** 9100/tcp
- **Назначение:** Экспорт метрик хоста

#### **Postgres Exporter** (prometheuscommunity/postgres-exporter:latest)
- **Container ID:** 1103692c826c
- **Статус:** Up 8 hours
- **Порт:** 9187/tcp
- **Назначение:** Экспорт метрик PostgreSQL

---

## Docker Networks

| Network ID | Name | Driver |
|------------|------|--------|
| e825aa602110 | bridge | bridge |
| 452d851ac29c | host | host |
| 6207d2248fb9 | lightrag_default | bridge |
| bb515f7f2423 | n8n-docker_default | bridge |
| b8cddd954801 | n8n-docker_n8n-network | bridge |
| 9611e105ca90 | none | null |

---

## Docker Volumes

### LightRAG volumes:
- lightrag_ollama_storage

### n8n-docker volumes:
- n8n-docker_caddy_config
- n8n-docker_caddy_data
- n8n-docker_db_storage
- n8n-docker_grafana_storage
- n8n-docker_n8n_storage
- n8n-docker_pgadmin_data
- n8n-docker_prometheus_data

### Anonymous volumes (6):
- 0c48c728bf06...
- 6b319743f8bd...
- 7dbd19d058c1...
- 40d7065a5d7b...
- 75b074a8c4c0...
- 82b416443a60...
- 1040117b2326...
- a4c4bba109ff...
- fe9d8f9bec07...

---

## Сводка по проектам

### Проект 1: n8n-docker
- **Путь:** /home/user/n8n-docker
- **Сервисы:** db, n8n, pgadmin4, caddy, prometheus, grafana, node-exporter, postgres-exporter
- **Домен:** bigalexn8n.ru
- **Назначение:** Автоматизация workflow + мониторинг

### Проект 2: lightrag
- **Путь:** /home/user/lightrag
- **Сервисы:** ollama, lightrag
- **Назначение:** RAG система с локальной LLM (Ollama) + external LLM (polza.ai)
- **API Key:** pza_PV5t0y6PTuE8GLcZ-jgvlpNDLlZm0mUT (polza.ai)

---

## Примечания

- **Ollama** использует NVIDIA GPU (compute,utility capabilities)
- **LightRAG** использует host networking (без проброса портов)
- **n8n** использует Caddy как reverse proxy с Let's Encrypt
- **Grafana** доступна на порту 3000
- **Prometheus** доступен на порту 9090
- **pgAdmin** доступен только локально на 127.0.0.1:5055
