import json
import unittest

from tools.gate_btc_2_v2a_xdc_mexc_qualification_runner import parse_payload


class TestXDCMexcQualificationRunner(unittest.TestCase):
    def test_parse_payload_known_schema(self):
        raw = json.dumps([
            [1704067200000, "1", "2", "0.5", "1.5", "10", 1704153599999, "15"]
        ]).encode()
        rows = parse_payload(raw)
        self.assertEqual(rows[0]["day"], "2024-01-01")
        self.assertEqual(rows[0]["open"], 1.0)
        self.assertEqual(rows[0]["high"], 2.0)
        self.assertEqual(rows[0]["base_volume"], 10.0)
        self.assertEqual(rows[0]["quote_volume"], 15.0)

    def test_error_envelope_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_payload(json.dumps({"code": 400, "msg": "error"}).encode())

    def test_unknown_row_schema_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_payload(json.dumps([[1, 2]]).encode())

    def test_negative_volume_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_payload(json.dumps([
                [1704067200000, "1", "2", "0.5", "1.5", "-1", 1704153599999, "15"]
            ]).encode())

    def test_bad_ohlc_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_payload(json.dumps([
                [1704067200000, "1", "0.8", "0.5", "1.5", "10", 1704153599999, "15"]
            ]).encode())


if __name__ == "__main__":
    unittest.main()
