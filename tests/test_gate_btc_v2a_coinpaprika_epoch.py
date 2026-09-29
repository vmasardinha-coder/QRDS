from __future__ import annotations

import json
import unittest

from tools.gate_btc_v2a_coinpaprika_epoch import build_epoch


class ProspectiveEpochTests(unittest.TestCase):
    def test_partial_mapping_never_claims_candle_coverage_or_old_credit(self):
        rows = [{"id": f"cp-{i}", "symbol": f"C{i}", "name": f"Coin {i}",
                 "rank": i, "quotes": {"USD": {"market_cap": 1000 - i}}}
                for i in range(1, 251)]
        rows[1]["symbol"] = rows[0]["symbol"]
        baseline = [{"id": f"cg-{i}", "symbol": f"C{i}", "name": f"Coin {i}"}
                    for i in range(1, 251)]
        registry = {"complete_registry_claimed": True, "entries": [
            {"symbol": "C3", "coin_id": "cg-3", "source_identity": "BINANCE_SPOT",
             "source_symbol": "C3USDT", "source_admitted": True, "qa_pass": True,
             "qualification": "QUALIFIED_EXACT_SOURCE"}]}
        report, gaps = build_epoch(json.dumps(rows).encode(),
                                   {"source_data_as_of": "2026-09-27"}, baseline,
                                   registry, "2026-09-29T18:15:00Z")
        self.assertEqual(report["candidate_count"], 250)
        self.assertEqual(report["source_adjudicated_count"], 0)
        self.assertEqual(report["candle_coverage_count"], 0)
        self.assertEqual(report["scientific_credit"], 0)
        self.assertFalse(report["engine_feed"])
        self.assertEqual(gaps[0]["status"], "DUPLICATE_CANDIDATE_SYMBOL")
        self.assertEqual(gaps[2]["status"], "PROPOSED_IDENTITY_REQUIRES_SOURCE_ADJUDICATION")
        self.assertEqual(gaps[3]["status"], "NO_UNIQUE_QUALIFIED_CANDLE_SOURCE")

    def test_registry_identity_mismatch_cannot_be_proposed(self):
        rows = [{"id": f"cp-{i}", "symbol": f"C{i}", "name": f"Coin {i}",
                 "rank": i, "quotes": {"USD": {"market_cap": 1000 - i}}}
                for i in range(1, 251)]
        baseline = [{"id": f"cg-{i}", "symbol": f"C{i}", "name": f"Coin {i}"}
                    for i in range(1, 251)]
        registry = {"complete_registry_claimed": True, "entries": [
            {"symbol": "C1", "coin_id": "wrong-id", "source_admitted": True,
             "qa_pass": True, "qualification": "QUALIFIED_EXACT_SOURCE"}]}
        _, gaps = build_epoch(json.dumps(rows).encode(),
                              {"source_data_as_of": "2026-09-27"}, baseline,
                              registry, "2026-09-29T18:15:00Z")
        self.assertEqual(gaps[0]["status"], "REGISTRY_ID_DIFFERS_FROM_FROZEN_REFERENCE")


if __name__ == "__main__":
    unittest.main()
