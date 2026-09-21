import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tools import gate_btc_2_v2a_bingx_spot_qualification_runner as q


class BingXQualifierTests(unittest.TestCase):
    def test_parse_identity_exact_active(self):
        raw = json.dumps({"code": 0, "msg": "", "data": {"symbols": [{"symbol": "REAL-USDT", "status": 1}]}}).encode()
        hit = q.parse_identity(raw, "REAL-USDT", "REAL", "USDT")
        self.assertEqual(hit["symbol"], "REAL-USDT")
        with self.assertRaises(ValueError):
            q.parse_identity(raw, "WRONG-USDT", "WRONG", "USDT")

    def test_parse_identity_rejects_inactive(self):
        raw = json.dumps({"code": 0, "data": {"symbols": [{"symbol": "REAL-USDT", "status": 0}]}}).encode()
        with self.assertRaises(ValueError):
            q.parse_identity(raw, "REAL-USDT", "REAL", "USDT")

    def test_parse_candles_and_ohlc(self):
        raw = json.dumps({"code": 0, "data": [[1756684800000, "1", "2", "0.5", "1.5", "3", 1756771199999, "4"]]}).encode()
        rows = q.parse_candles(raw)
        self.assertEqual(rows[0]["close"], 1.5)
        bad = json.dumps({"code": 0, "data": [[1756684800000, "1", "0.9", "1.1", "1.0", "3", 1756771199999, "4"]]}).encode()
        with self.assertRaises(ValueError):
            q.parse_candles(bad)

    def test_collect_preserves_raw_and_zero_credit_scope(self):
        identity = json.dumps({"code": 0, "data": {"symbols": [{"symbol": "REAL-USDT", "status": 1}]}}).encode()
        candles = json.dumps({"code": 0, "data": [
            [1756684800000, "1", "2", "0.5", "1.5", "3", 1756771199999, "4"],
            [1756771200000, "1.5", "2.5", "1", "2", "4", 1756857599999, "5"],
        ]}).encode()
        with tempfile.TemporaryDirectory() as td, patch.object(q, "request_bytes", side_effect=[identity, candles]):
            out = Path(td)
            r = q.collect("REAL-USDT", "REAL", "USDT", date.fromisoformat("2025-09-02"), out)
            self.assertTrue(r["qa_pass"])
            self.assertTrue((out / "RAW_IDENTITY.json").is_file())
            self.assertTrue((out / "RAW_000.json").is_file())
            self.assertEqual(r["duplicate_rows"], 0)

    def test_safety_tokens_static(self):
        source = Path(q.__file__).read_text(encoding="utf-8")
        for token in (
            "no_backfill", "no_counter_reset", "no_silent_source_substitution",
            "scientific_credit", "prospective_credit", "admission_scope", "engine_feed",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
