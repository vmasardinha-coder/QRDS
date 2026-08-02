from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class GatewayFrozenReplayTests(unittest.TestCase):
    def test_frozen_reference_replay_passes_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "evidence"
            environment = os.environ.copy()
            environment["GATE_BTC_RESEARCH_ONLY"] = "true"
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "gateway_frozen_replay.py"),
                    "--skip-fixture",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
                timeout=120,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            payload = json.loads(
                (output_dir / "GATE_BTC_GATEWAY_V010_REPLAY.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(payload["source_canonicality"]["status"], "PASS")
            self.assertEqual(payload["reference_integrity"]["status"], "PASS")
            self.assertEqual(payload["frozen_replay"]["status"], "PASS")
            expected_rows = {
                "all_strategy_selections.csv": 118,
                "strategy_compositions.csv": 132,
                "strategy_execution_profiles.csv": 8,
                "delta_stop_trade_rules.csv": 80,
                "gateway_decision_log.csv": 80,
            }
            for filename, rows in expected_rows.items():
                self.assertEqual(
                    payload["frozen_replay"]["files"][filename]["rows"], rows
                )
                self.assertEqual(
                    payload["frozen_replay"]["files"][filename]["status"], "PASS"
                )
            self.assertFalse(payload["public_source_acquisition_reconstructed"])
            self.assertFalse(payload["feature_construction_reconstructed"])
            self.assertEqual(payload["orders_generated"], 0)
            self.assertEqual(payload["real_capital_used"], 0)
            self.assertEqual(payload["operational_status"], "NOT_APPROVED")
            self.assertEqual(payload["methodology_changes"], 0)
            self.assertTrue(
                (output_dir / "GATE_BTC_GATEWAY_V010_REPLAY_EVIDENCE.zip").is_file()
            )

    def test_research_only_cannot_be_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "evidence"
            environment = os.environ.copy()
            environment["GATE_BTC_RESEARCH_ONLY"] = "false"
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "gateway_frozen_replay.py"),
                    "--skip-fixture",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
                timeout=120,
            )
            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(
                (output_dir / "GATE_BTC_GATEWAY_V010_REPLAY.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(payload["status"], "FAIL")
            self.assertIn(
                "GATE_BTC_RESEARCH_ONLY", payload["errors"][0]["message"]
            )
            self.assertEqual(payload["orders_generated"], 0)
            self.assertEqual(payload["real_capital_used"], 0)
            self.assertEqual(payload["operational_status"], "NOT_APPROVED")


if __name__ == "__main__":
    unittest.main()
