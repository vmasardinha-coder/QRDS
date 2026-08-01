import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.gate_btc_migration_runner import run


class MigrationRunnerTests(unittest.TestCase):
    def test_runner_generates_fail_closed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"GATE_BTC_RESEARCH_ONLY": "true"}, clear=False
        ):
            manifest, txt_path, json_path, zip_path = run(Path(directory))
            self.assertEqual(manifest["status"], "PASS")
            self.assertEqual(manifest["locks"]["orders_generated"], 0)
            self.assertEqual(manifest["locks"]["real_capital_used"], 0)
            self.assertTrue(txt_path.exists() and json_path.exists() and zip_path.exists())

    def test_runner_rejects_operational_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"GATE_BTC_RESEARCH_ONLY": "false"}, clear=False
        ):
            manifest, txt_path, _, zip_path = run(Path(directory))
            self.assertEqual(manifest["status"], "ERROR")
            self.assertIn("must remain true", txt_path.read_text(encoding="utf-8"))
            self.assertTrue(zip_path.exists())
