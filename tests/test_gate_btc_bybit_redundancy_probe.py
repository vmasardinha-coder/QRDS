import json
import unittest

from tools.gate_btc_bybit_redundancy_probe import BASE_URLS, run_probe
from tools.gate_btc_2_stage9_bybit_candidate_probe import REQUIRED_ROLES, run_probe as run_stage9_candidate_probe


class BybitRedundancyProbeTests(unittest.TestCase):
    def test_any_usable_endpoint_is_pass(self):
        def requester(base):
            if base == BASE_URLS[2]:
                return 200, json.dumps({"retCode": 0, "result": {"list": [{"symbol": "BTCUSDT"}]}}).encode()
            return 403, b""

        report = run_probe(requester)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["status_counts"]["PASS"], 1)
        self.assertFalse(report["feeds_frozen_engine"])
        self.assertFalse(report["source_substitution_performed"])
        self.assertEqual(report["methodology_changes"], 0)

    def test_all_403_is_explicit_geo_block_warning(self):
        report = run_probe(lambda base: (403, b""))
        self.assertEqual(report["status"], "WARN_GEO_BLOCKED")
        self.assertEqual(report["status_counts"]["GEO_BLOCKED"], len(BASE_URLS))
        self.assertEqual(report["orders_generated"], 0)
        self.assertEqual(report["real_capital_used"], 0)

    def test_http_200_bad_payload_is_not_fake_pass(self):
        report = run_probe(lambda base: (200, b'{"retCode":10001,"result":{"list":[]}}'))
        self.assertEqual(report["status"], "WARN_UNAVAILABLE")
        self.assertEqual(report["status_counts"]["INVALID_PAYLOAD"], len(BASE_URLS))

    def test_stage9_complete_role_route_is_qualification_only(self):
        def requester(base, category):
            if category == "linear":
                row = {
                    "symbol": "BTCUSDT",
                    "fundingRate": "0.0001",
                    "openInterest": "123.45",
                    "volume24h": "678.90",
                }
            else:
                row = {"symbol": "BTCUSDT", "volume24h": "42.0"}
            return 200, json.dumps({"retCode": 0, "result": {"list": [row]}, "time": 1788000000000}).encode()

        report = run_stage9_candidate_probe(requester)
        self.assertEqual(report["status"], "CANDIDATE_READY_FOR_PREREGISTRATION")
        self.assertEqual(report["required_source_roles"], list(REQUIRED_ROLES))
        self.assertGreater(report["complete_candidate_base_count"], 0)
        self.assertTrue(report["qualification_only"])
        self.assertEqual(report["prospective_credit"], 0)
        self.assertFalse(report["source_admitted"])
        self.assertFalse(report["source_substitution_performed"])
        self.assertFalse(report["contract_changed"])
        self.assertFalse(report["engine_feed"])
        self.assertEqual(report["orders_generated"], 0)
        self.assertEqual(report["real_capital_used"], 0)

    def test_stage9_missing_role_does_not_qualify(self):
        def requester(base, category):
            if category == "linear":
                row = {"symbol": "BTCUSDT", "openInterest": "123.45", "volume24h": "678.90"}
            else:
                row = {"symbol": "BTCUSDT", "volume24h": "42.0"}
            return 200, json.dumps({"retCode": 0, "result": {"list": [row]}, "time": 1788000000000}).encode()

        report = run_stage9_candidate_probe(requester)
        self.assertEqual(report["status"], "NO_COMPLETE_CANDIDATE_ROUTE")
        self.assertEqual(report["complete_candidate_base_count"], 0)
        self.assertEqual(report["prospective_credit"], 0)


if __name__ == "__main__":
    unittest.main()
