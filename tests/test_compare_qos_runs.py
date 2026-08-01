import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.compare_qos_runs import compare


def _zip(path: Path, name: str, payload: dict) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(name, json.dumps(payload))


class QOSParityTests(unittest.TestCase):
    def test_fixture_can_pass_structure_but_never_value_parity(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            local = root / "local.zip"
            remote = root / "remote.zip"
            _zip(local, "RUN_STATUS.json", {
                "mode": "public_data_no_api_key_no_orders", "operational_status": "NOT_APPROVED",
                "real_orders": 0, "capital_used": 0,
                "component_status": {"delta": {"data_as_of": "2026-07-31"}},
            })
            _zip(remote, "QOS_ORCHESTRATION_MANIFEST_1.json", {
                "status": "PASS_WITH_GATEWAY_PENDING", "mode": "offline_fixture_no_network",
                "engines": [{"name": "V2A", "status": "PASS"}, {"name": "Delta", "status": "PASS"}],
                "gateway": {"state": "PENDING_SOURCE"},
                "locks": {"operational_status": "NOT_APPROVED", "orders_generated": 0,
                          "real_capital_used": 0},
            })
            result = compare(local, remote)
            self.assertEqual(result["status"], "STRUCTURAL_PASS_VALUE_PARITY_PENDING")
            self.assertFalse(result["equivalence_claim"])
            self.assertFalse(result["value_parity_ready"])

    def test_operational_payload_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root = Path(directory)
            local = root / "local.zip"
            remote = root / "remote.zip"
            _zip(local, "RUN_STATUS.json", {"mode": "x", "operational_status": "NOT_APPROVED",
                                             "real_orders": 0, "capital_used": 0})
            _zip(remote, "QOS_ORCHESTRATION_MANIFEST_1.json", {
                "status": "PASS", "mode": "x", "engines": [], "gateway": {"state": "EXECUTED_REMOTE"},
                "locks": {"operational_status": "APPROVED", "orders_generated": 1,
                          "real_capital_used": 100},
            })
            result = compare(local, remote)
            self.assertEqual(result["status"], "ERROR")
            self.assertFalse(result["equivalence_claim"])


if __name__ == "__main__":
    unittest.main()
