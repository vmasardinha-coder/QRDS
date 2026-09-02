import json
import unittest

from tools.gate_btc_2_v2a_usyc_deribit_qualification_runner import parse_payload


class TestUSYCDeribitQualificationRunner(unittest.TestCase):
    def test_parse_payload_known_schema(self):
        raw = json.dumps({
            "jsonrpc": "2.0",
            "result": {
                "status": "ok",
                "ticks": [1704067200000],
                "open": [1.0],
                "high": [2.0],
                "low": [0.5],
                "close": [1.5],
                "volume": [10.0],
                "cost": [15.0],
            },
        }).encode()
        rows = parse_payload(raw)
        self.assertEqual(rows[0]["day"], "2024-01-01")
        self.assertEqual(rows[0]["base_volume"], 10.0)
        self.assertEqual(rows[0]["quote_volume"], 15.0)

    def test_no_data_is_empty(self):
        raw = json.dumps({"jsonrpc": "2.0", "result": {"status": "no_data"}}).encode()
        self.assertEqual(parse_payload(raw), [])

    def test_error_envelope_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_payload(json.dumps({"error": {"code": 1}}).encode())

    def test_mismatched_arrays_fail_closed(self):
        raw = json.dumps({
            "result": {
                "status": "ok",
                "ticks": [1704067200000],
                "open": [1.0],
                "high": [2.0],
                "low": [0.5],
                "close": [1.5],
                "volume": [10.0],
                "cost": [],
            }
        }).encode()
        with self.assertRaises(ValueError):
            parse_payload(raw)

    def test_bad_ohlc_fails_closed(self):
        raw = json.dumps({
            "result": {
                "status": "ok",
                "ticks": [1704067200000],
                "open": [1.0],
                "high": [0.8],
                "low": [0.5],
                "close": [1.5],
                "volume": [10.0],
                "cost": [15.0],
            }
        }).encode()
        with self.assertRaises(ValueError):
            parse_payload(raw)


if __name__ == "__main__":
    unittest.main()
