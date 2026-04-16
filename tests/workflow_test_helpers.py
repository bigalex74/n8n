#!/usr/bin/env python3
"""Общие хелперы для unit/e2e тестов workflow."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import psycopg2
import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT_DIR / "workflows"

GLOBAL_ERROR_WORKFLOW_ID = "global-error-handler-36id"

# Проектная БД (не системная n8n_database)
PG_HOST = os.getenv("WF_TEST_PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("WF_TEST_PG_PORT", "5432"))
PG_DB = os.getenv("WF_TEST_PG_DB", "postgres")
N8N_SYSTEM_DB = os.getenv("WF_TEST_N8N_SYSTEM_DB", "n8n_database")
PG_USER = os.getenv("WF_TEST_PG_USER", "n8n_user")
PG_PASSWORD = os.getenv("WF_TEST_PG_PASSWORD", "n8n_db_password")

N8N_URL = os.getenv("WF_TEST_N8N_URL", "http://127.0.0.1:5678")


def load_workflow(filename: str) -> Dict[str, Any]:
    path = WORKFLOWS_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not payload or not isinstance(payload, list):
        raise ValueError(f"Некорректный формат workflow файла: {path}")
    return payload[0]


def db_connect():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )


def db_connect_n8n_system():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=N8N_SYSTEM_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )


def n8n_health_ok(timeout: int = 5) -> bool:
    try:
        resp = requests.get(f"{N8N_URL}/healthz", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False
