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
            "BINGX_SPOT",
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

    def test_real_bingx_is_explicit_prospective_replacement(self):
        real = next(x for x in self.source["entries"] if x["symbol"] == "REAL")
        self.assertEqual(real["source_identity"], "BINGX_SPOT")
        self.assertEqual(real["source_symbol"], "REAL-USDT")
        self.assertEqual(real["prior_source_identity"], "MEXC_SPOT")
        self.assertEqual(real["prior_source_symbol"], "REALUSDT")
        self.assertFalse(real["retroactive_repair_allowed"])
        self.assertEqual(real["admission_effective_rule"], "FIRST_POST_MERGE_PROSPECTIVE_COLLECTION_ONLY")
        self.assertEqual(real["historical_credit"], 0)
        self.assertEqual(real["d0_credit"], 0)

    def test_real_bingx_adjudication_is_prospective_only(self):
        adj = json.loads((ROOT / "tools" / "gate_btc_2_v2a_real_bingx_adjudication_2026_09_26.json").read_text(encoding="utf-8"))
        self.assertTrue(adj["source_substitution_authorized"])
        self.assertEqual(adj["replacement_source_identity"], "BINGX_SPOT")
        self.assertEqual(adj["prior_source_identity"], "MEXC_SPOT")
        self.assertEqual(adj["physical_qualification_run_id"], 36252251598)
        self.assertFalse(adj["retroactive_repair_allowed"])
        self.assertTrue(adj["NO_BACKFILL"])
        self.assertEqual(adj["historical_credit"], 0)
        self.assertEqual(adj["scientific_credit"], 0)
        self.assertEqual(adj["ORDERS"], 0)
        self.assertEqual(adj["REAL_CAPITAL_BRL"], 0)

    def test_bingx_probe_and_observation_contract(self):
        from datetime import datetime, timezone
        from unittest.mock import patch
        raw = b'{"code":0,"data":[[1790000000000,"1","2","0.5","1.5","100",0,"150"]]}'
        entry = {"source_identity":"BINGX_SPOT","source_symbol":"REAL-USDT"}
        with patch.object(mod, "_get", return_value=raw):
            url, got = mod._probe(entry, datetime(2026,9,26,12,0,tzinfo=timezone.utc))
        self.assertIn("open-api.bingx.com/openApi/market/his/v1/kline", url)
        self.assertIn("symbol=REAL-USDT", url)
        self.assertEqual(got, raw)
        self.assertTrue(mod._response_has_observation(entry, raw))

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
