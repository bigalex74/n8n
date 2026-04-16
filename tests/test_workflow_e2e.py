#!/usr/bin/env python3
"""E2E/интеграционные тесты для контура обработки ошибок и инфраструктуры workflow."""

from __future__ import annotations

from pathlib import Path
import uuid
import sys
import unittest

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workflow_test_helpers import PG_DB, db_connect, db_connect_n8n_system, load_workflow, n8n_health_ok


class WorkflowE2ETests(unittest.TestCase):
    def test_project_db_is_postgres(self):
        self.assertEqual(PG_DB, "postgres")

    def test_required_tables_exist(self):
        expected_tables = {
            "global_errors",
            "document_jobs",
            "document_chunks",
            "telegram_send_message",
        }
        conn = db_connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname='public'
                    AND tablename = ANY(%s)
                    """,
                    (list(expected_tables),),
                )
                found = {row[0] for row in cur.fetchall()}
        finally:
            conn.close()
        self.assertEqual(found, expected_tables)

    def test_global_errors_insert_roundtrip(self):
        marker = f"wf-test-{uuid.uuid4().hex[:10]}"
        conn = db_connect()
        inserted_id = None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.global_errors
                    (workflow_id, workflow_name, execution_id, error_message, error_stack)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        "unit-test-workflow",
                        "WF Test Global Error Handler",
                        marker,
                        "Synthetic failure for workflow e2e test",
                        "stack: wf-test",
                    ),
                )
                inserted_id = cur.fetchone()[0]
                conn.commit()

                cur.execute(
                    "SELECT workflow_id, execution_id, error_message FROM public.global_errors WHERE id = %s",
                    (inserted_id,),
                )
                row = cur.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], "unit-test-workflow")
                self.assertEqual(row[1], marker)
                self.assertIn("Synthetic failure", row[2])
        finally:
            if inserted_id is not None:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM public.global_errors WHERE id = %s", (inserted_id,))
                    conn.commit()
            conn.close()

    def test_global_error_workflow_pin_payload_matches_mapping(self):
        wf = load_workflow("__Global_Error_Handler.json")
        sample = wf.get("pinData", {}).get("Error Trigger", [{}])[0].get("json", {})

        # Это фактические поля, которые workflow использует в expressions.
        self.assertIn("workflow", sample)
        self.assertIn("execution", sample)
        self.assertIn("id", sample["workflow"])
        self.assertIn("name", sample["workflow"])
        self.assertIn("id", sample["execution"])
        self.assertIn("error", sample["execution"])
        self.assertIn("message", sample["execution"]["error"])
        self.assertIn("stack", sample["execution"]["error"])

    def test_optional_webhook_smoke_for_test_suites(self):
        if not n8n_health_ok():
            self.skipTest("n8n недоступен по /healthz")

        # Webhook может отсутствовать/быть неактивным, это не должно падать как hard fail.
        paths = [
            "test-translate-ollama",
            "e2e-translation-test",
        ]
        failures = []
        for path in paths:
            try:
                resp = requests.post(
                    f"http://127.0.0.1:5678/webhook/{path}",
                    json={"chunk_text": "테스트", "test_name": "workflow-smoke"},
                    timeout=20,
                )
                if resp.status_code not in (200, 404, 410):
                    failures.append((path, resp.status_code, resp.text[:200]))
            except Exception as exc:
                failures.append((path, "exception", str(exc)))

        if failures:
            self.fail(f"Webhook smoke failures: {failures}")

    def test_test_translate_webhook_returns_pass(self):
        if not n8n_health_ok():
            self.skipTest("n8n недоступен по /healthz")

        resp = requests.post(
            "http://127.0.0.1:5678/webhook/test-translate-ollama",
            json={"chunk_text": "안녕하세요"},
            timeout=25,
        )
        self.assertEqual(resp.status_code, 200, resp.text[:300])
        payload = resp.json()
        self.assertTrue(payload.get("passed"))
        self.assertTrue(payload.get("output"))
        self.assertGreater(int(payload.get("length", 0)), 0)

    def test_e2e_translation_webhook_returns_pass(self):
        if not n8n_health_ok():
            self.skipTest("n8n недоступен по /healthz")

        resp = requests.post(
            "http://127.0.0.1:5678/webhook/e2e-translation-test",
            json={"chunk_text": "그는 문을 열고 들어갔다.", "test_name": "suite-e2e-smoke"},
            timeout=30,
        )
        self.assertEqual(resp.status_code, 200, resp.text[:300])
        payload = resp.json()
        self.assertTrue(payload.get("passed"))
        self.assertTrue(payload.get("output"))
        self.assertGreater(int(payload.get("length", 0)), 0)

    def test_ollama_chat_completion_smoke(self):
        tags_resp = requests.get("http://127.0.0.1:11434/api/tags", timeout=10)
        self.assertEqual(tags_resp.status_code, 200)
        models = tags_resp.json().get("models", [])
        self.assertTrue(models, "В Ollama не найдено ни одной модели")

        model_name = models[0]["name"]
        completion_resp = requests.post(
            "http://127.0.0.1:11434/v1/chat/completions",
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": "Ответь одним словом: OK"}],
                "temperature": 0,
            },
            timeout=30,
        )
        self.assertEqual(completion_resp.status_code, 200)
        content = (
            completion_resp.json()
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        self.assertTrue(content, "Пустой ответ от Ollama chat/completions")

    def test_ollama_test_credential_exists_in_n8n_system_db(self):
        conn = db_connect_n8n_system()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, type
                    FROM public.credentials_entity
                    WHERE name = %s
                    """,
                    ("Ollama Test",),
                )
                row = cur.fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(row, "Credential 'Ollama Test' не найден в n8n_database")
        self.assertEqual(row[1], "Ollama Test")
        self.assertIn(row[2], ("openAiApi", "ollamaApi"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
