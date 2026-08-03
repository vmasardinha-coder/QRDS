import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_bull_replay import ContractError, load_contract, run_synthetic


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "migration" / "reporting" / "bull_replay_contract.json"


class BullReplayContractTests(unittest.TestCase):
    def test_frozen_contract_loads(self):
        contract = load_contract(CONTRACT)
        self.assertTrue(contract["research_only"])
        self.assertEqual(contract["operational_status"], "NOT_APPROVED")
        self.assertEqual(contract["benchmarks_required"], ["Victor_proxy", "BTC_puro", "BTC_ETH_70_30"])

    def test_contract_fails_open_if_safety_lock_changes(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        contract["orders_allowed"] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contract.json"
            path.write_text(json.dumps(contract), encoding="utf-8")
            with self.assertRaises(ContractError):
                load_contract(path)

    def test_contract_rejects_invalid_allocation(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        contract["allocation_splits"] = [[70, 20]]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contract.json"
            path.write_text(json.dumps(contract), encoding="utf-8")
            with self.assertRaises(ContractError):
                load_contract(path)

    def test_synthetic_runner_emits_research_only_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = run_synthetic(CONTRACT, Path(tmp))
            self.assertEqual(manifest["status"], "PASS_SYNTHETIC_INFRASTRUCTURE_ONLY")
            self.assertEqual(manifest["orders_generated"], 0)
            self.assertEqual(manifest["real_capital_used"], 0)
            self.assertFalse(manifest["real_market_data_loaded"])
            self.assertFalse(manifest["holdout_opened"])
            self.assertGreater(manifest["rows"], 0)
            self.assertTrue((Path(tmp) / "GATE_BTC_BULL_REPLAY_SYNTHETIC_METRICS.csv").exists())
            self.assertTrue((Path(tmp) / "GATE_BTC_BULL_REPLAY_SYNTHETIC_MANIFEST.json").exists())


if __name__ == "__main__":
    unittest.main()
