import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_gateway_isolated_source import validate


class GatewayIsolatedSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.outputs = self.root / "extracted/outputs"
        self.outputs.mkdir(parents=True)
        qos = {
            "status": "PASS_WITH_GATEWAY_PENDING", "matched_component_close": True,
            "errors": [], "data_as_of": "2026-09-29",
            "engines": [
                {"name": n, "status": "PASS", "manifest": {"data_as_of": "2026-09-29"}}
                for n in ("V2A", "Delta")
            ],
            "locks": {"research_only": True, "orders_generated": 0,
                      "real_capital_used": 0, "operational_status": "NOT_APPROVED"},
        }
        gateway_manifest = {
            "data_as_of": "2026-09-30", "technical_status": "PASS",
            "operational_status": "NOT_APPROVED",
            "retrospective_performance_status": "PROHIBITED_CURRENT_COMPOSITION",
            "errors": [],
        }
        safety = {"research_only": True, "orders_generated": 0,
                  "real_capital_used": 0, "operational_status": "NOT_APPROVED",
                  "methodology_changes": 0}
        upstream = {
            **safety, "status": "PASS",
            "public_source_acquisition_equivalence": "PASS_PUBLIC_CAPTURE",
            "feature_construction_equivalence": "PASS_LINUX_REPLAY",
            "capture": {"status": "PASS", "http": {"capture_count": 1},
                        "gateway": {"manifest": gateway_manifest}},
            "linux_replay": {"status": "PASS", "http": {
                "replay_total": 1, "replay_consumed": 1, "replay_remaining": 0}},
        }
        downstream = {**safety, "status": "PASS", **{
            key: {"status": "PASS"} for key in
            ("source_canonicality", "reference_integrity", "frozen_replay", "fixture_contract")}}
        self.write("qos_daily/QOS_ORCHESTRATION_MANIFEST_1.json", qos)
        self.write("gateway_daily/GATE_BTC_GATEWAY_UPSTREAM_EQUIVALENCE.json", upstream)
        self.write("gateway_reference_check/GATE_BTC_GATEWAY_V010_REPLAY.json", downstream)
        for name in ("v2a1_run_manifest.json", "scanner_snapshot_status.json",
                     "strategy_compositions.csv", "strategy_execution_profiles.csv"):
            self.write_output(name, gateway_manifest if name.endswith(".json") else "header\n")

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def write_output(self, name, value):
        (self.outputs / name).write_text(
            json.dumps(value) if isinstance(value, dict) else value, encoding="utf-8")

    def test_valid_same_run_gateway_date_after_qos_close(self):
        self.assertEqual(validate(self.root, self.outputs), "2026-09-30")

    def test_rejects_missing_capture_and_replay_parity(self):
        path = self.root / "gateway_daily/GATE_BTC_GATEWAY_UPSTREAM_EQUIVALENCE.json"
        payload = json.loads(path.read_text())
        payload["linux_replay"]["http"]["replay_consumed"] = 0
        self.write("gateway_daily/GATE_BTC_GATEWAY_UPSTREAM_EQUIVALENCE.json", payload)
        with self.assertRaisesRegex(RuntimeError, "HTTP cassette incomplete"):
            validate(self.root, self.outputs)

    def test_rejects_stale_gateway_and_order_generation(self):
        self.write_output("v2a1_run_manifest.json", {
            "data_as_of": "2026-09-28", "technical_status": "PASS",
            "retrospective_performance_status": "PROHIBITED_CURRENT_COMPOSITION"})
        with self.assertRaisesRegex(RuntimeError, "replay close mismatch"):
            validate(self.root, self.outputs)
        path = self.root / "qos_daily/QOS_ORCHESTRATION_MANIFEST_1.json"
        payload = json.loads(path.read_text())
        payload["locks"]["orders_generated"] = 1
        self.write("qos_daily/QOS_ORCHESTRATION_MANIFEST_1.json", payload)
        with self.assertRaisesRegex(RuntimeError, "QOS safety lock invalid"):
            validate(self.root, self.outputs)


if __name__ == "__main__":
    unittest.main()
