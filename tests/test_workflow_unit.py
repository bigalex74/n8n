#!/usr/bin/env python3
"""Unit-тесты структуры критичных workflow."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workflow_test_helpers import GLOBAL_ERROR_WORKFLOW_ID, load_workflow


class WorkflowUnitTests(unittest.TestCase):
    def test_start_translate_finish_have_global_error_workflow(self):
        critical = ["Start.json", "Translate_Chunk.json", "Finish.json"]
        for filename in critical:
            wf = load_workflow(filename)
            with self.subTest(workflow=wf["name"]):
                settings = wf.get("settings", {})
                self.assertEqual(settings.get("errorWorkflow"), GLOBAL_ERROR_WORKFLOW_ID)

    def test_global_error_handler_has_expected_minimal_chain(self):
        wf = load_workflow("__Global_Error_Handler.json")
        self.assertEqual(wf["id"], GLOBAL_ERROR_WORKFLOW_ID)

        nodes = wf.get("nodes", [])
        node_names = {n["name"] for n in nodes}
        self.assertIn("Error Trigger", node_names)
        self.assertIn("Insert rows in a table", node_names)

        pg_node = next(n for n in nodes if n["name"] == "Insert rows in a table")
        params = pg_node.get("parameters", {})

        table_cfg = params.get("table", {})
        self.assertEqual(table_cfg.get("value"), "global_errors")

        mapped = params.get("columns", {}).get("value", {})
        required_fields = {
            "workflow_id": "={{ $json.workflow.id }}",
            "workflow_name": "={{ $json.workflow.name }}",
            "execution_id": "={{ $json.execution.id }}",
            "error_message": "={{ $json.execution.error.message }}",
            "error_stack": "={{ $json.execution.error.stack }}",
        }
        for field, expr in required_fields.items():
            with self.subTest(field=field):
                self.assertEqual(mapped.get(field), expr)

    def test_translate_chunk_contains_local_error_branches(self):
        wf = load_workflow("Translate_Chunk.json")
        node_names = {n["name"] for n in wf.get("nodes", [])}
        expected = {
            "Обработка ошибки - Чанк",
            "Обработка ошибки - Глава",
            "Обработка ошибки - Арка",
            "Переход на следующий чанк",
        }
        self.assertTrue(expected.issubset(node_names))

    def test_finish_has_core_delivery_nodes(self):
        wf = load_workflow("Finish.json")
        node_names = {n["name"] for n in wf.get("nodes", [])}
        self.assertIn("Переведенный файл в Telegram", node_names)
        self.assertIn("Переведенный файл в Google Drive", node_names)
        self.assertIn("Сообщение о финише перевода", node_names)

    def test_test_translate_workflow_uses_ollama_test_credential(self):
        wf = load_workflow("_TEST__________________Ollama.json")
        self.assertEqual(wf["name"], "[TEST] Перевод чанка — Ollama")
        self.assertGreaterEqual(len(wf.get("nodes", [])), 3)

        credential_names = set()
        for node in wf.get("nodes", []):
            creds = node.get("credentials", {})
            for val in creds.values():
                name = val.get("name")
                if name:
                    credential_names.add(name)
        self.assertIn("Ollama Test", credential_names)

    def test_e2e_translation_test_suite_exists(self):
        wf = load_workflow("_E2E__Translation_Test_Suite.json")
        self.assertEqual(wf["name"], "[E2E] Translation Test Suite")
        self.assertTrue(wf.get("active"))
        self.assertGreaterEqual(len(wf.get("nodes", [])), 3)

    def test_no_hardcoded_telegram_bot_token_in_workflows(self):
        targets = [
            "Select_From_List.json",
            "_Send__wait.json",
            "_GET___select_files.json",
        ]
        for filename in targets:
            wf = load_workflow(filename)
            with self.subTest(workflow=wf["name"]):
                all_urls = [
                    node.get("parameters", {}).get("url", "")
                    for node in wf.get("nodes", [])
                    if node.get("parameters", {}).get("url")
                ]
                joined = "\n".join(all_urls)
                self.assertNotIn("8591497428", joined)
                self.assertNotIn("AAEbVnPaXYe2E-WI2ni2cCuSGnmgS5sckR0", joined)

    def test_telegram_http_nodes_use_credential_expression(self):
        targets = [
            "Select_From_List.json",
            "_Send__wait.json",
            "_GET___select_files.json",
        ]
        for filename in targets:
            wf = load_workflow(filename)
            for node in wf.get("nodes", []):
                url = node.get("parameters", {}).get("url", "")
                if "api.telegram.org/bot" not in url:
                    continue
                with self.subTest(workflow=wf["name"], node=node["name"]):
                    self.assertIn("{{$credentials.telegramApi.accessToken}}", url)
                    creds = node.get("credentials", {}).get("telegramApi", {})
                    self.assertEqual(creds.get("name"), "Telegram account")


if __name__ == "__main__":
    unittest.main(verbosity=2)
