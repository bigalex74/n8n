#!/usr/bin/env python3
"""Единая точка запуска unit + e2e тестов workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import unittest


def main() -> int:
    parser = argparse.ArgumentParser(description="Workflow test runner")
    parser.add_argument(
        "--suite",
        choices=["all", "unit", "e2e", "quality"],
        default="all",
        help="Какой набор тестов запускать",
    )
    args = parser.parse_args()

    tests_dir = Path(__file__).resolve().parent
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    if args.suite in ("all", "unit"):
        suite.addTests(loader.discover(str(tests_dir), pattern="test_workflow_unit.py"))
    if args.suite in ("all", "e2e"):
        suite.addTests(loader.discover(str(tests_dir), pattern="test_workflow_e2e.py"))
    if args.suite in ("all", "quality"):
        suite.addTests(loader.discover(str(tests_dir), pattern="test_workflow_quality.py"))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
