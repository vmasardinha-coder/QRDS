import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_v2a_failure_diagnostic import build_diagnostic


class V2AFailureDiagnosticTests(unittest.TestCase):
    def manifest(self):
        return {"data_as_of": "2026-08-06", "attempted_symbols": 4, "loaded_symbols": 1, "failed_symbols": 3}

    def test_classifies_without_changing_engine(self):
        universe = [
            {"symbol": "TAO", "id": "bittensor", "name": "Bittensor", "market_cap_rank": "42"},
            {"symbol": "BUIDL", "id": "blackrock-usd-institutional-digital-liquidity-fund", "name": "BlackRock USD Institutional Digital Liquidity Fund", "market_cap_rank": "33"},
            {"symbol": "KAS", "id": "kaspa", "name": "Kaspa", "market_cap_rank": "80"},
        ]
        failures = [
            {"symbol": "TAO", "reason": "okx: only 39 rows"},
            {"symbol": "BUIDL", "reason": "okx: RuntimeError: OKX returned no candles"},
            {"symbol": "KAS", "reason": "okx: RuntimeError: OKX returned no candles"},
        ]
        report = build_diagnostic(universe, failures, self.manifest())
        by_symbol = {row["symbol"]: row for row in report["rows"]}
        self.assertEqual(by_symbol["TAO"]["action_class"], "WAIT_FOR_HISTORY")
        self.assertEqual(by_symbol["TAO"]["observed_history_rows"], 39)
        self.assertEqual(by_symbol["BUIDL"]["action_class"], "SEMANTIC_SCOPE_REVIEW")
        self.assertIn("RWA_OR_TOKENIZED_NAME_PATTERN", by_symbol["BUIDL"]["semantic_flags"])
        self.assertEqual(by_symbol["KAS"]["action_class"], "SOURCE_RECOVERY_CANDIDATE")
        self.assertTrue(report["advisory_only"])
        self.assertFalse(report["denominator_changed"])
        self.assertFalse(report["universe_changed"])
        self.assertFalse(report["source_order_changed"])
        self.assertFalse(report["source_substitution_performed"])
        self.assertFalse(report["feeds_frozen_engine"])
        self.assertEqual(report["methodology_changes"], 0)
        self.assertEqual(report["orders_generated"], 0)
        self.assertEqual(report["real_capital_used"], 0)

    def test_cashlike_symbol_is_review_only_not_excluded(self):
        universe = [{"symbol": "CRVUSD", "id": "crvusd", "name": "crvUSD", "market_cap_rank": "153"}]
        failures = [{"symbol": "CRVUSD", "reason": "okx: RuntimeError: OKX returned no candles"}]
        manifest = {"data_as_of": "2026-08-06", "attempted_symbols": 1, "loaded_symbols": 0, "failed_symbols": 1}
        report = build_diagnostic(universe, failures, manifest)
        row = report["rows"][0]
        self.assertEqual(row["action_class"], "SEMANTIC_SCOPE_REVIEW")
        self.assertIn("CASHLIKE_OR_STABLE_SYMBOL_PATTERN", row["semantic_flags"])
        self.assertFalse(report["universe_changed"])

    def test_manifest_count_mismatch_fails_closed(self):
        universe = [{"symbol": "KAS", "id": "kaspa", "name": "Kaspa", "market_cap_rank": "80"}]
        failures = [{"symbol": "KAS", "reason": "okx: RuntimeError: OKX returned no candles"}]
        bad_manifest = {"data_as_of": "2026-08-06", "attempted_symbols": 3, "loaded_symbols": 1, "failed_symbols": 1}
        with self.assertRaisesRegex(RuntimeError, "attempted != loaded \\+ failed"):
            build_diagnostic(universe, failures, bad_manifest)


if __name__ == "__main__":
    unittest.main()
