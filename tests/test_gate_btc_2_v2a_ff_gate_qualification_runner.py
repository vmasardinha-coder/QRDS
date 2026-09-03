import json
import unittest

from tools.gate_btc_2_v2a_ff_gate_qualification_runner import parse_pair, parse_candles


class TestFFGateQualificationRunner(unittest.TestCase):
    def test_exact_pair_identity(self):
        obj = {"id":"FF_USDT","base":"FF","quote":"USDT"}
        self.assertEqual(parse_pair(json.dumps(obj).encode())["id"], "FF_USDT")

    def test_pair_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_pair(json.dumps({"id":"FF_USDT","base":"FOO","quote":"USDT"}).encode())

    def test_known_candle_schema(self):
        rows = parse_candles(json.dumps([[1704067200,"15","1.5","2","0.5","1","10","true"]]).encode())
        self.assertEqual(rows[0]["day"], "2024-01-01")
        self.assertEqual(rows[0]["open"], 1.0)
        self.assertEqual(rows[0]["high"], 2.0)

    def test_error_envelope_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_candles(json.dumps({"label":"INVALID_PARAM_VALUE"}).encode())

    def test_negative_volume_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_candles(json.dumps([[1704067200,"15","1.5","2","0.5","1","-1"]]).encode())

    def test_bad_ohlc_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_candles(json.dumps([[1704067200,"15","1.5","0.8","0.5","1","10"]]).encode())


if __name__ == "__main__":
    unittest.main()
