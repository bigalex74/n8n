#!/usr/bin/env python3
"""E2E/интеграционные тесты для контура обработки ошибок и инфраструктуры workflow."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import time
import uuid
import sys
import unittest

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workflow_test_helpers import PG_DB, db_connect, db_connect_n8n_system, load_workflow, n8n_health_ok


class WorkflowE2ETests(unittest.TestCase):
    _credentials_cache = None
    _live_billing_nodes_cache = None
    _n8n_api_key_cache = None

    @classmethod
    def _load_n8n_credentials(cls):
        if cls._credentials_cache is not None:
            return cls._credentials_cache
        try:
            proc = subprocess.run(
                [
                    "docker",
                    "exec",
                    "n8n-docker-n8n-1",
                    "n8n",
                    "export:credentials",
                    "--all",
                    "--decrypted",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except Exception as exc:
            raise AssertionError(f"Не удалось получить credentials из n8n: {exc}") from exc

        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError(f"Некорректный JSON credentials export: {exc}") from exc

        cls._credentials_cache = payload
        return payload

    @classmethod
    def _n8n_api_key(cls) -> str:
        if cls._n8n_api_key_cache is not None:
            return cls._n8n_api_key_cache
        cred = cls._credential_by_name("n8n account")
        key = (cred.get("data") or {}).get("apiKey")
        if not key:
            raise AssertionError("Credential 'n8n account' не содержит apiKey")
        cls._n8n_api_key_cache = key
        return key

    @classmethod
    def _list_executions(cls, workflow_id: str, limit: int = 20):
        key = cls._n8n_api_key()
        resp = requests.get(
            "http://127.0.0.1:5678/api/v1/executions",
            params={"workflowId": workflow_id, "limit": limit},
            headers={"X-N8N-API-KEY": key},
            timeout=20,
        )
        if resp.status_code != 200:
            raise AssertionError(f"n8n API executions error: {resp.status_code} {resp.text[:200]}")
        return resp.json().get("data", [])

    @classmethod
    def _wait_new_execution(cls, workflow_id: str, before_ids: set[int], timeout_s: int = 20):
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            rows = cls._list_executions(workflow_id, limit=30)
            for item in rows:
                if item.get("id") not in before_ids:
                    return item
            time.sleep(1)
        return None

    @classmethod
    def _execution_details(cls, execution_id: int):
        key = cls._n8n_api_key()
        resp = requests.get(
            f"http://127.0.0.1:5678/api/v1/executions/{execution_id}",
            params={"includeData": "true"},
            headers={"X-N8N-API-KEY": key},
            timeout=20,
        )
        if resp.status_code != 200:
            raise AssertionError(f"n8n API execution details error: {resp.status_code} {resp.text[:200]}")
        return resp.json()

    @classmethod
    def _credential_by_name(cls, name: str):
        creds = cls._load_n8n_credentials()
        for item in creds:
            if item.get("name") == name:
                return item
        raise AssertionError(f"Credential '{name}' не найден в n8n export")

    @classmethod
    def _load_live_billing_nodes(cls):
        if cls._live_billing_nodes_cache is not None:
            return cls._live_billing_nodes_cache

        target_workflows = ["Start", "[Send] processing", "[Sub] Billing Check"]
        conn = db_connect_n8n_system()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      w.name AS workflow_name,
                      e->>'name' AS node_name,
                      e->'parameters'->>'url' AS url,
                      e->'parameters'->'headerParameters'->'parameters'->0->>'value' AS auth_value,
                      COALESCE(
                        e->'credentials'->'httpHeaderAuth'->>'name',
                        e->'credentials'->'openAiApi'->>'name'
                      ) AS credential_name
                    FROM public.workflow_entity w,
                         jsonb_array_elements(w.nodes::jsonb) e
                    WHERE w.name = ANY(%s)
                      AND e->>'name' IN ('Billing Polza.ai', 'Billing Neuro')
                    ORDER BY w.name, e->>'name'
                    """,
                    (target_workflows,),
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        cls._live_billing_nodes_cache = [
            {
                "workflow_name": row[0],
                "node_name": row[1],
                "url": row[2],
                "auth_value": row[3],
                "credential_name": row[4],
            }
            for row in rows
        ]
        return cls._live_billing_nodes_cache

    @classmethod
    def _live_credential_for_node(cls, node_name: str) -> str:
        rows = [r for r in cls._load_live_billing_nodes() if r["node_name"] == node_name]
        if not rows:
            raise AssertionError(f"Billing node '{node_name}' не найден в live workflow")
        cred_names = {r["credential_name"] for r in rows}
        if None in cred_names or "" in cred_names:
            raise AssertionError(f"У node '{node_name}' отсутствует credential в live workflow")
        if len(cred_names) != 1:
            raise AssertionError(f"У node '{node_name}' разные credentials в workflow: {sorted(cred_names)}")
        return next(iter(cred_names))

    @classmethod
    def _live_billing_node_rows(cls, node_name: str):
        rows = [r for r in cls._load_live_billing_nodes() if r["node_name"] == node_name]
        if not rows:
            raise AssertionError(f"Billing node '{node_name}' не найден в live workflow")
        return rows

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

    def test_polza_balance_api_returns_200_and_valid_payload(self):
        credential_name = self._live_credential_for_node("Billing Polza.ai")
        cred = self._credential_by_name(credential_name)
        data = cred.get("data", {})
        base_url = (data.get("url") or "https://polza.ai/api/v1").rstrip("/")
        auth_value = data.get("value")
        self.assertTrue(auth_value, f"У credential {credential_name} отсутствует value")
        self.assertTrue(str(auth_value).startswith("Bearer "), f"У credential {credential_name} value без Bearer")

        resp = requests.get(
            f"{base_url}/balance",
            headers={"Authorization": auth_value},
            timeout=20,
        )
        self.assertEqual(resp.status_code, 200, resp.text[:300])
        payload = resp.json()
        self.assertIn("amount", payload)
        try:
            float(payload["amount"])
        except (TypeError, ValueError) as exc:
            self.fail(f"Поле amount не является числом/числоподобной строкой: {payload.get('amount')!r} ({exc})")

    def test_neuroapi_billing_usage_returns_200_and_valid_payload(self):
        credential_name = self._live_credential_for_node("Billing Neuro")
        cred = self._credential_by_name(credential_name)
        data = cred.get("data", {})
        base_url = (data.get("url") or "https://neuroapi.host/v1").rstrip("/")
        auth_value = data.get("value")
        self.assertTrue(auth_value, f"У credential {credential_name} отсутствует value")
        self.assertTrue(str(auth_value).startswith("Bearer "), f"У credential {credential_name} value без Bearer")

        resp = requests.get(
            f"{base_url}/dashboard/billing/usage",
            headers={"Authorization": auth_value},
            timeout=20,
        )
        self.assertEqual(resp.status_code, 200, resp.text[:300])
        payload = resp.json()
        self.assertIn("total_usage", payload)
        self.assertIsInstance(payload["total_usage"], (int, float))

    def test_live_billing_nodes_use_http_header_auth_credentials(self):
        rows = self._load_live_billing_nodes()
        self.assertTrue(rows, "Billing nodes не найдены в live workflow")

        bad = []
        for row in rows:
            if row["credential_name"] not in ("Billing Polza Header", "Billing Neuro Header"):
                bad.append(
                    (
                        row["workflow_name"],
                        row["node_name"],
                        f"unexpected credential_name={row['credential_name']!r}",
                    )
                )
            if row["auth_value"] not in (None, "", "={{ 'Bearer ' + $credentials.apiKey }}"):
                bad.append(
                    (
                        row["workflow_name"],
                        row["node_name"],
                        f"unexpected inline auth_value={row['auth_value']!r}",
                    )
                )

        self.assertEqual(
            bad,
            [],
            f"Billing nodes сконфигурированы некорректно: {bad}",
        )

    def test_live_billing_credentials_have_authorization_bearer(self):
        for node_name in ("Billing Polza.ai", "Billing Neuro"):
            cred_name = self._live_credential_for_node(node_name)
            cred = self._credential_by_name(cred_name)
            self.assertEqual(cred.get("type"), "httpHeaderAuth", f"{node_name}: credential type должен быть httpHeaderAuth")
            data = cred.get("data", {})
            self.assertEqual(data.get("name"), "Authorization", f"{node_name}: header name должен быть Authorization")
            self.assertTrue(
                str(data.get("value", "")).startswith("Bearer "),
                f"{node_name}: header value должен начинаться с Bearer ",
            )

    def test_live_billing_nodes_do_not_use_broken_api_key_placeholders(self):
        conn = db_connect_n8n_system()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT name
                    FROM public.workflow_entity
                    WHERE name = ANY(%s)
                      AND (
                        nodes::text LIKE %s
                        OR nodes::text LIKE %s
                      )
                    ORDER BY name
                    """,
                    (
                        ["Start", "[Send] processing", "[Sub] Billing Check", "Анотация"],
                        "%{{.apiKey}}%",
                        "% + .apiKey %",
                    ),
                )
                bad = [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

        self.assertEqual(
            bad,
            [],
            f"Обнаружены нерабочие шаблоны apiKey в live workflow: {bad}",
        )

    def test_send_message_trigger_creates_real_executions(self):
        if not n8n_health_ok():
            self.skipTest("n8n недоступен по /healthz")

        send_message_wf = "J62UViXZMD5o6qoU"
        free_templates = ["create_job", "start_processing", "processing", "error_processing"]
        before_send = {row["id"] for row in self._list_executions(send_message_wf, limit=40)}

        conn = db_connect()
        try:
            for template in free_templates:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO telegram_send_message (template) VALUES (%s) RETURNING id",
                        (template,),
                    )
                    inserted_id = cur.fetchone()[0]
                    conn.commit()

                send_exec = self._wait_new_execution(send_message_wf, before_send, timeout_s=25)
                self.assertIsNotNone(
                    send_exec,
                    f"После INSERT template={template} id={inserted_id} не появился execution Send Message",
                )
                self.assertIn(
                    send_exec.get("status"),
                    ("running", "success"),
                    f"Send Message execution в неожиданном статусе: {send_exec}",
                )
                self.assertEqual(
                    send_exec.get("mode"),
                    "trigger",
                    f"Send Message execution должен быть trigger-mode: {send_exec}",
                )

                before_send.add(int(send_exec["id"]))
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
