import json
import unittest

from tools.gate_btc_2_v2a_jasmy_coinbase_qualification_runner import parse_candles, parse_product


class TestJASMYCoinbaseQualificationRunner(unittest.TestCase):
    def test_parse_product_exact_pair(self):
        raw = json.dumps({"id": "JASMY-USD", "base_currency": "JASMY", "quote_currency": "USD"}).encode()
        product = parse_product(raw)
        self.assertEqual(product["id"], "JASMY-USD")

    def test_parse_product_identity_mismatch_fails_closed(self):
        raw = json.dumps({"id": "JASMY-USD", "base_currency": "OTHER", "quote_currency": "USD"}).encode()
        with self.assertRaises(ValueError):
            parse_product(raw)

    def test_parse_candles_known_schema(self):
        raw = json.dumps([[1704067200, 0.5, 2.0, 1.0, 1.5, 10.0]]).encode()
        rows = parse_candles(raw)
        self.assertEqual(rows[0]["day"], "2024-01-01")
        self.assertEqual(rows[0]["open"], 1.0)
        self.assertEqual(rows[0]["high"], 2.0)
        self.assertEqual(rows[0]["base_volume"], 10.0)

    def test_error_envelope_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_candles(json.dumps({"message": "NotFound"}).encode())

    def test_negative_volume_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_candles(json.dumps([[1704067200, 0.5, 2.0, 1.0, 1.5, -1.0]]).encode())

    def test_bad_ohlc_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_candles(json.dumps([[1704067200, 0.5, 0.8, 1.0, 1.5, 10.0]]).encode())


if __name__ == "__main__":
    unittest.main()
