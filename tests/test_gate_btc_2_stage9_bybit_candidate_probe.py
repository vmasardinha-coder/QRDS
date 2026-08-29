import json
import unittest

from tools.gate_btc_2_stage9_bybit_candidate_probe import REQUIRED_ROLES, run_probe


def payload(category: str, complete: bool = True) -> bytes:
    if category == "linear":
        row = {
            "symbol": "BTCUSDT",
            "fundingRate": "0.0001",
            "openInterest": "123.45",
            "volume24h": "678.90",
        }
        if not complete:
            row.pop("fundingRate")
    else:
        row = {"symbol": "BTCUSDT", "volume24h": "42.0"}
    return json.dumps({"retCode": 0, "result": {"list": [row]}, "time": 1788000000000}).encode()


class Stage9BybitCandidateProbeTests(unittest.TestCase):
    def test_complete_route_is_qualification_only(self):
        def requester(base, category):
            return (200, payload(category))

        report = run_probe(requester)
        self.assertEqual(report["status"], "CANDIDATE_READY_FOR_PREREGISTRATION")
        self.assertGreater(report["complete_candidate_base_count"], 0)
        self.assertEqual(report["required_source_roles"], list(REQUIRED_ROLES))
        self.assertTrue(report["qualification_only"])
        self.assertEqual(report["prospective_credit"], 0)
        self.assertFalse(report["source_admitted"])
        self.assertFalse(report["source_substitution_performed"])
        self.assertFalse(report["contract_changed"])
        self.assertFalse(report["engine_feed"])
        self.assertEqual(report["orders_generated"], 0)
        self.assertEqual(report["real_capital_used"], 0)

    def test_missing_role_field_does_not_qualify(self):
        def requester(base, category):
            return (200, payload(category, complete=False) if category == "linear" else payload(category))

        report = run_probe(requester)
        self.assertEqual(report["status"], "NO_COMPLETE_CANDIDATE_ROUTE")
        self.assertEqual(report["complete_candidate_base_count"], 0)
        self.assertEqual(report["prospective_credit"], 0)

    def test_geo_block_does_not_bypass(self):
        def requester(base, category):
            return (451, b"blocked")

        report = run_probe(requester)
        self.assertEqual(report["status"], "NO_COMPLETE_CANDIDATE_ROUTE")
        self.assertFalse(report["proxy_or_geo_bypass_used"])
        self.assertFalse(report["source_substitution_performed"])


if __name__ == "__main__":
    unittest.main()
