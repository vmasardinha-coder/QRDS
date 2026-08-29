import json
import unittest

from tools.gate_btc_2_stage9_hyperliquid_candidate_probe import inspect_perp, inspect_spot, run_probe


class HyperliquidStage9CandidateProbeTests(unittest.TestCase):
    def test_perp_fields_do_not_override_exact_instrument_identity(self):
        raw = json.dumps([
            {"universe": [{"name": "BTC"}]},
            [{"funding": "0.0001", "openInterest": "100", "dayNtlVlm": "200"}],
        ]).encode()
        result = inspect_perp(raw)
        self.assertEqual(result["status"], "FIELDS_PRESENT_IDENTITY_MISMATCH")
        self.assertEqual(result["venue_instrument"], "BTC")
        self.assertEqual(result["expected_instrument"], "BTCUSDT")

    def test_spot_btc_usdc_does_not_count_as_btcusdt(self):
        raw = json.dumps([
            {
                "tokens": [{"name": "BTC"}, {"name": "USDC"}],
                "universe": [{"tokens": [0, 1]}],
            },
            [{"dayNtlVlm": "123"}],
        ]).encode()
        result = inspect_spot(raw)
        self.assertEqual(result["status"], "EXACT_SPOT_INSTRUMENT_NOT_FOUND")
        self.assertIn("BTC/USDC", result["observed_btc_pairs"])

    def test_live_surface_availability_cannot_grant_credit(self):
        perp = json.dumps([
            {"universe": [{"name": "BTC"}]},
            [{"funding": "0.1", "openInterest": "1", "dayNtlVlm": "2"}],
        ]).encode()
        spot = json.dumps([
            {"tokens": [{"name": "BTC"}, {"name": "USDC"}], "universe": [{"tokens": [0, 1]}]},
            [{"dayNtlVlm": "3"}],
        ]).encode()

        def requester(info_type):
            return 200, perp if info_type == "metaAndAssetCtxs" else spot, "Sat, 29 Aug 2026 18:00:00 GMT"

        report = run_probe(requester)
        self.assertEqual(report["status"], "NO_COMPLETE_CANDIDATE_ROUTE")
        self.assertEqual(report["prospective_credit"], 0)
        self.assertFalse(report["source_admitted"])
        self.assertFalse(report["source_substitution_performed"])
        self.assertFalse(report["engine_feed"])
        self.assertEqual(report["orders_generated"], 0)
        self.assertEqual(report["real_capital_used"], 0)
        self.assertTrue(report["fail_closed"])

    def test_geo_block_remains_advisory_only(self):
        report = run_probe(lambda _: (451, b"", None))
        self.assertEqual(report["status"], "NO_COMPLETE_CANDIDATE_ROUTE")
        self.assertTrue(all(v["status"] == "GEO_BLOCKED" for v in report["surfaces"].values()))
        self.assertEqual(report["prospective_credit"], 0)


if __name__ == "__main__":
    unittest.main()
