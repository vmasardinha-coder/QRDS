import json
import unittest

from tools.gate_btc_bybit_redundancy_probe import BASE_URLS, run_probe


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


if __name__ == "__main__":
    unittest.main()
