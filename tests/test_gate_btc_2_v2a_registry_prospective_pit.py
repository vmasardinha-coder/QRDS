import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "tools" / "gate_btc_2_v2a_registry_prospective_pit.py"
SPEC = importlib.util.spec_from_file_location("registry_pit", MOD_PATH)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


class RegistryProspectivePitTests(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / "tools" / "gate_btc_2_v2a_complete_qualified_source_registry_v1.json"
        self.source = json.loads(self.path.read_text(encoding="utf-8"))

    def test_runtime_registry_is_exact_137_and_cutover_schema(self):
        runtime = mod._runtime_registry(self.source)
        self.assertEqual(runtime["schema"], "gate_btc.v2a_prospective_qualified_source_registry.v1")
        self.assertEqual(runtime["epoch_id"], "GATE_BTC_2_V2A_PROSPECTIVE_EPOCH_2026_09_03")
        self.assertEqual(len(runtime["entries"]), 137)
        self.assertEqual(len({x["symbol"] for x in runtime["entries"]}), 137)
        for entry in runtime["entries"]:
            self.assertEqual(entry["qualification"], "QUALIFIED_EXACT_SOURCE")
            self.assertTrue(entry["qa_pass"])
            self.assertEqual(entry["observed_vs_derived"], "OBSERVED")
            self.assertEqual(len(entry["provenance_sha256"]), 64)
            self.assertTrue(entry["source_identity"])
            self.assertTrue(entry["source_symbol"])
            self.assertEqual(entry["timezone"], "UTC")
            self.assertTrue(entry["cutoff_semantics"])

    def test_every_frozen_provider_has_explicit_fail_closed_adapter(self):
        allowed = (
            "BINANCE_SPOT",
            "OKX_SPOT",
            "OKX_PUBLIC_SPOT",
            "GATE_SPOT",
            "MEXC_SPOT",
            "BITGET_SPOT",
            "BYBIT_SPOT",
            "COINBASE_EXCHANGE_SPOT",
            "KRAKEN",
            "GECKOTERMINAL_PUBLIC_ONCHAIN",
            "DERIBIT_SPOT",
            "FIGURE_MARKETS",
        )
        unsupported = []
        for entry in self.source["entries"]:
            identity = str(entry["source_identity"]).upper()
            if not any(identity.startswith(prefix) for prefix in allowed):
                unsupported.append((entry["symbol"], entry["source_identity"]))
        self.assertEqual(unsupported, [])

    def test_no_scientific_or_economic_credit_in_runtime_registry(self):
        runtime = mod._runtime_registry(self.source)
        self.assertEqual(runtime["historical_credit"], 0)
        self.assertEqual(runtime["prospective_credit_before_d0"], 0)
        self.assertFalse(runtime["backfill_performed"])
        self.assertFalse(runtime["counter_reset_performed"])
        self.assertFalse(runtime["engine_feed"])
        self.assertEqual(runtime["orders"], 0)
        self.assertEqual(runtime["real_capital_brl"], 0)
        self.assertFalse(runtime["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
