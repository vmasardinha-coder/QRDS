from __future__ import annotations

import argparse
import json
import os
import tempfile
import unittest
from pathlib import Path

from tools import gate_btc_daily_research as daily


class DailyResearchTests(unittest.TestCase):
    def _write_fixture(self, root: Path, *, orders: int = 0) -> argparse.Namespace:
        qos = root / "qos"
        gateway = root / "gateway"
        downstream = root / "downstream"
        output = root / "output"
        for directory in (qos, gateway, downstream, output):
            directory.mkdir(parents=True, exist_ok=True)

        qos_manifest = {
            "status": "PASS_WITH_GATEWAY_PENDING",
            "errors": [],
            "matched_component_close": True,
            "requested_data_cutoff": "2026-08-01",
            "engines": [
                {
                    "name": "V2A",
                    "status": "PASS",
                    "output_zip": "qos_v2a_outputs.zip",
                    "manifest": {"version": "V2A", "data_as_of": "2026-08-01"},
                },
                {
                    "name": "Delta",
                    "status": "PASS",
                    "output_zip": "delta_walk_forward_outputs.zip",
                    "manifest": {"version": "DELTA", "data_as_of": "2026-08-01"},
                },
            ],
            "locks": {
                "research_only": True,
                "orders_generated": orders,
                "real_capital_used": 0,
                "operational_status": "NOT_APPROVED",
            },
        }
        (qos / "QOS_ORCHESTRATION_MANIFEST_20260802_000000.json").write_text(
            json.dumps(qos_manifest), encoding="utf-8"
        )

        gateway_manifest = {
            "version": "QOS_V2A1_GATEWAY_SCANNER_0.10",
            "technical_status": "PASS",
            "data_quality_status": "PASS_PARTIAL_REDUNDANCY_WARNING",
            "snapshot_status": "SNAPSHOT_USABLE_WITH_DATA_WARNINGS",
            "operational_status": "NOT_APPROVED",
            "retrospective_performance_status": "PROHIBITED_CURRENT_COMPOSITION",
            "errors": [],
            "data_as_of": "2026-08-02",
        }
        gateway_payload = {
            "status": "PASS",
            "public_source_acquisition_equivalence": "PASS_PUBLIC_CAPTURE_WITH_COMPLETE_RESPONSE_CASSETTE",
            "feature_construction_equivalence": "PASS_LINUX_OFFLINE_SAME_INPUT_REPLAY",
            "capture": {
                "status": "PASS",
                "http": {"capture_count": 835},
                "gateway": {"manifest": gateway_manifest},
            },
            "linux_replay": {
                "status": "PASS",
                "http": {"replay_total": 835, "replay_consumed": 835, "replay_remaining": 0},
            },
            "research_only": True,
            "orders_generated": 0,
            "real_capital_used": 0,
            "operational_status": "NOT_APPROVED",
            "methodology_changes": 0,
        }
        (gateway / "GATE_BTC_GATEWAY_UPSTREAM_EQUIVALENCE.json").write_text(
            json.dumps(gateway_payload), encoding="utf-8"
        )

        downstream_payload = {
            "status": "PASS",
            "source_canonicality": {"status": "PASS"},
            "reference_integrity": {"status": "PASS"},
            "frozen_replay": {"status": "PASS", "files": {}},
            "fixture_contract": {"status": "PASS"},
            "replay_scope": "DETERMINISTIC_DOWNSTREAM_REPLAY_FROM_ADMITTED_FEATURE_SNAPSHOT",
            "research_only": True,
            "orders_generated": 0,
            "real_capital_used": 0,
            "operational_status": "NOT_APPROVED",
            "methodology_changes": 0,
        }
        (downstream / "GATE_BTC_GATEWAY_V010_REPLAY.json").write_text(
            json.dumps(downstream_payload), encoding="utf-8"
        )
        return argparse.Namespace(
            qos_dir=qos,
            gateway_dir=gateway,
            gateway_reference_dir=downstream,
            data_cutoff="2026-08-01",
            output_dir=output,
        )

    def test_daily_handoff_accepts_documented_data_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            args = self._write_fixture(Path(temporary))
            original = os.environ.get("GATE_BTC_RESEARCH_ONLY")
            os.environ["GATE_BTC_RESEARCH_ONLY"] = "true"
            try:
                return_code = daily.run(args)
            finally:
                if original is None:
                    os.environ.pop("GATE_BTC_RESEARCH_ONLY", None)
                else:
                    os.environ["GATE_BTC_RESEARCH_ONLY"] = original
            self.assertEqual(return_code, 0)
            payload = json.loads(
                (args.output_dir / "GATE_BTC_DAILY_RESEARCH_MANIFEST.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["status"], "PASS_WITH_DATA_WARNINGS")
            self.assertEqual(payload["total_system_equivalence_baseline"], "PASS")
            self.assertTrue(payload["report_delivery"]["inputs_ready"])
            self.assertTrue((args.output_dir / "GATE_BTC_DAILY_RESEARCH_EVIDENCE.zip").is_file())

    def test_daily_handoff_fails_closed_on_order_count(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            args = self._write_fixture(Path(temporary), orders=1)
            return_code = daily.run(args)
            self.assertEqual(return_code, 1)
            payload = json.loads(
                (args.output_dir / "GATE_BTC_DAILY_RESEARCH_MANIFEST.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["status"], "FAIL")
            self.assertFalse(payload["report_delivery"]["inputs_ready"])
            self.assertIn("orders", payload["errors"][0]["message"].lower())


if __name__ == "__main__":
    unittest.main()
