import unittest

from tools.gate_btc_rwa_sidecar_manifest import build


class RWASidecarManifestTests(unittest.TestCase):
    def diagnostic(self):
        return {
            "schema": "gate_btc.v2a_failure_diagnostic.v1",
            "advisory_only": True,
            "feeds_frozen_engine": False,
            "source_substitution_performed": False,
            "denominator_changed": False,
            "universe_changed": False,
            "methodology_changes": 0,
            "data_as_of": "2026-08-06",
            "snapshot_id": "2026-08-06-run-1",
            "rows": [
                {"symbol": "BUIDL", "coin_id": "buidl", "name": "Institutional Digital Liquidity Fund", "market_cap_rank": 10, "semantic_flags": ["RWA_OR_TOKENIZED_NAME_PATTERN"], "failure_reason": "no candles", "action_class": "SEMANTIC_SCOPE_REVIEW"},
                {"symbol": "CRVUSD", "coin_id": "crvusd", "name": "crvUSD", "market_cap_rank": 100, "semantic_flags": ["CASHLIKE_OR_STABLE_SYMBOL_PATTERN"], "failure_reason": "no candles", "action_class": "SEMANTIC_SCOPE_REVIEW"},
                {"symbol": "KAS", "coin_id": "kaspa", "name": "Kaspa", "market_cap_rank": 30, "semantic_flags": [], "failure_reason": "no candles", "action_class": "SOURCE_RECOVERY_CANDIDATE"},
            ],
        }

    def test_sidecar_is_observation_only(self):
        report = build(self.diagnostic())
        self.assertEqual(report["status"], "PASS_OBSERVATION_SIDECAR_ONLY")
        self.assertEqual(report["candidate_count"], 2)
        self.assertEqual(report["rwa_or_tokenized_flag_count"], 1)
        self.assertEqual(report["cashlike_or_stable_flag_count"], 1)
        self.assertFalse(report["stock_bases_adapter_implemented"])
        self.assertFalse(report["rwa_strategy_universe_created"])
        self.assertFalse(report["automatic_exclusion_from_v2a"])
        self.assertFalse(report["engine_feed"])
        self.assertFalse(report["feeds_frozen_engine"])
        self.assertFalse(report["source_substitution_performed"])
        self.assertFalse(report["strategy_inputs_changed"])
        self.assertFalse(report["denominator_changed"])
        self.assertFalse(report["universe_changed"])
        self.assertEqual(report["methodology_changes"], 0)
        self.assertEqual(report["orders_generated"], 0)
        self.assertEqual(report["real_capital_used"], 0)
        self.assertEqual({row["symbol"] for row in report["rows"]}, {"BUIDL", "CRVUSD"})
        self.assertTrue(all(row["automatic_exclusion_from_v2a"] is False for row in report["rows"]))
        self.assertTrue(all(row["tradable_universe_member"] is False for row in report["rows"]))

    def test_empty_semantic_flags_fail_closed(self):
        bad = self.diagnostic()
        bad["rows"][0]["semantic_flags"] = []
        with self.assertRaisesRegex(RuntimeError, "semantic review row without flags"):
            build(bad)

    def test_boundary_change_fails_closed(self):
        bad = self.diagnostic()
        bad["universe_changed"] = True
        with self.assertRaisesRegex(RuntimeError, "universe boundary changed"):
            build(bad)


if __name__ == "__main__":
    unittest.main()
