#!/usr/bin/env python3
"""Quality-тесты каркаса (не блокируют по историческим данным)."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workflow_test_helpers import db_connect, db_connect_n8n_system, load_workflow, n8n_health_ok


class WorkflowQualityTests(unittest.TestCase):
    def test_n8n_health_endpoint(self):
        self.assertTrue(n8n_health_ok(), "n8n /healthz недоступен")

    def test_global_errors_table_is_queryable(self):
        conn = db_connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM public.global_errors")
                count = cur.fetchone()[0]
        finally:
            conn.close()
        self.assertGreaterEqual(count, 0)

    def test_system_credentials_table_is_queryable(self):
        conn = db_connect_n8n_system()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM public.credentials_entity")
                count = cur.fetchone()[0]
        finally:
            conn.close()
        self.assertGreater(count, 0)

    def test_core_workflows_are_active_in_export(self):
        for filename in ("Start.json", "Translate_Chunk.json", "Finish.json"):
            wf = load_workflow(filename)
            with self.subTest(workflow=wf["name"]):
                self.assertTrue(wf.get("active"), f"{wf['name']} должен быть active в экспортe")


if __name__ == "__main__":
    unittest.main(verbosity=2)
