import json
import unittest

from tools.gate_btc_2_stage9_bitget_candidate_probe import inspect_perp, inspect_spot, run_probe


class BitgetStage9CandidateProbeTests(unittest.TestCase):
    def test_exact_btcusdt_perp_can_cover_three_roles(self):
        raw = json.dumps({
            "code": "00000",
            "requestTime": 1788030000000,
            "data": [{
                "symbol": "BTCUSDT",
                "fundingRate": "0.0001",
                "holdingAmount": "100",
                "baseVolume": "200",
                "ts": "1788030000100",
            }],
        }).encode()
        result = inspect_perp(raw)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["venue_instrument"], "BTCUSDT")
        self.assertEqual(set(result["role_field_map"]), {"FUNDING", "OPEN_INTEREST", "PERP_VOLUME"})

    def test_exact_btcusdt_spot_can_cover_volume(self):
        raw = json.dumps({
            "code": "00000",
            "requestTime": 1788030000000,
            "data": [{"symbol": "BTCUSDT", "baseVolume": "12", "ts": "1788030000100"}],
        }).encode()
        result = inspect_spot(raw)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["role_field_map"], {"SPOT_VOLUME": "baseVolume"})

    def test_missing_role_field_fails_closed(self):
        raw = json.dumps({
            "code": "00000",
            "data": [{"symbol": "BTCUSDT", "fundingRate": "0.1", "holdingAmount": "1"}],
        }).encode()
        result = inspect_perp(raw)
        self.assertEqual(result["status"], "ROLE_FIELDS_MISSING")
        self.assertIn("baseVolume", result["missing_fields"])

    def test_ready_candidate_still_cannot_grant_credit(self):
        perp = json.dumps({
            "code": "00000", "requestTime": 1,
            "data": [{"symbol": "BTCUSDT", "fundingRate": "0.1", "holdingAmount": "1", "baseVolume": "2", "ts": "1"}],
        }).encode()
        spot = json.dumps({
            "code": "00000", "requestTime": 1,
            "data": [{"symbol": "BTCUSDT", "baseVolume": "3", "ts": "1"}],
        }).encode()

        def requester(path, params):
            return 200, perp if "/mix/" in path else spot, "Sat, 29 Aug 2026 21:00:00 GMT"

        report = run_probe(requester)
        self.assertEqual(report["status"], "CANDIDATE_READY_FOR_PREREGISTRATION")
        self.assertEqual(report["prospective_credit"], 0)
        self.assertFalse(report["source_admitted"])
        self.assertFalse(report["source_substitution_performed"])
        self.assertFalse(report["engine_feed"])
        self.assertEqual(report["orders_generated"], 0)
        self.assertEqual(report["real_capital_used"], 0)
        self.assertTrue(report["no_backfill"])
        self.assertTrue(report["no_retune"])
        self.assertTrue(report["fail_closed"])

    def test_geo_block_remains_advisory_only(self):
        report = run_probe(lambda _path, _params: (451, b"", None))
        self.assertEqual(report["status"], "NO_COMPLETE_CANDIDATE_ROUTE")
        self.assertTrue(all(v["status"] == "GEO_BLOCKED" for v in report["surfaces"].values()))
        self.assertEqual(report["prospective_credit"], 0)


if __name__ == "__main__":
    unittest.main()
