import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools.qos_orchestrator import run


class QOSOrchestratorTests(unittest.TestCase):
    def test_fixture_orchestration_is_safe_and_packaged(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"GATE_BTC_RESEARCH_ONLY": "true"}, clear=False
        ):
            manifest, txt_path, json_path, zip_path = run(Path(directory), fixture_mode=True)
        self.assertEqual(manifest["status"], "PASS_WITH_GATEWAY_PENDING")
        self.assertEqual([item["status"] for item in manifest["engines"]], ["PASS", "PASS"])
        self.assertEqual(manifest["gateway"]["state"], "PENDING_SOURCE")
        self.assertFalse(manifest["equivalence_claim"])
        self.assertEqual(manifest["locks"]["orders_generated"], 0)
        self.assertTrue(txt_path.name.startswith("QOS_ORCHESTRATION_REPORT_"))
        self.assertTrue(json_path.name.startswith("QOS_ORCHESTRATION_MANIFEST_"))
        with zipfile.ZipFile(zip_path) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn("qos_v2a_outputs.zip", archive.namelist())
            self.assertIn("delta_walk_forward_outputs.zip", archive.namelist())

    def test_operational_mode_fails_closed_and_still_emits_evidence(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"GATE_BTC_RESEARCH_ONLY": "false"}, clear=False
        ):
            manifest, txt_path, json_path, zip_path = run(Path(directory), fixture_mode=True)
            persisted = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "ERROR")
        self.assertEqual(persisted["locks"]["operational_status"], "NOT_APPROVED")
        self.assertIn("must remain true", txt_path.read_text(encoding="utf-8"))
        self.assertTrue(zip_path.exists())


if __name__ == "__main__":
    unittest.main()
