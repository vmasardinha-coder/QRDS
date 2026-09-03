import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import gate_btc_2_v2a_exact_spot_qualification_runner as q


class ExactSpotQualifierTests(unittest.TestCase):
    def test_parse_mexc_identity_exact(self):
        raw=json.dumps({"symbols":[{"symbol":"REALUSDT","baseAsset":"REAL","quoteAsset":"USDT"}]}).encode()
        hit=q.parse_mexc_identity(raw,"REALUSDT","REAL","USDT")
        self.assertEqual(hit["symbol"],"REALUSDT")
        with self.assertRaises(ValueError): q.parse_mexc_identity(raw,"REALUSDT","WRONG","USDT")

    def test_parse_gate_identity_exact(self):
        raw=json.dumps({"id":"PONS_USDT","base":"PONS","quote":"USDT"}).encode()
        self.assertEqual(q.parse_gate_identity(raw,"PONS_USDT","PONS","USDT")["id"],"PONS_USDT")
        with self.assertRaises(ValueError): q.parse_gate_identity(raw,"OTHER_USDT","PONS","USDT")

    def test_mexc_candle_invariants(self):
        raw=json.dumps([[1000,"1","2","0.5","1.5","3",0,"4"]]).encode()
        rows=q.parse_mexc_candles(raw)
        self.assertEqual(rows[0]["close"],1.5)
        bad=json.dumps([[1000,"1","0.9","1.1","1.0","3",0,"4"]]).encode()
        with self.assertRaises(ValueError): q.parse_mexc_candles(bad)

    def test_gate_candle_invariants(self):
        raw=json.dumps([[1000,"4","1.5","2","0.5","1","3"]]).encode()
        rows=q.parse_gate_candles(raw)
        self.assertEqual(rows[0]["base_volume"],3)
        bad=json.dumps([[1000,"4","1.5","1.2","0.5","1","3"]]).encode()
        with self.assertRaises(ValueError): q.parse_gate_candles(bad)

    def test_collect_mexc_preserves_raw_and_qa(self):
        identity=json.dumps({"symbols":[{"symbol":"REALUSDT","baseAsset":"REAL","quoteAsset":"USDT"}]}).encode()
        candles=json.dumps([
            [1756684800000,"1","2","0.5","1.5","3",0,"4"],
            [1756771200000,"1.5","2.5","1","2","4",0,"5"],
        ]).encode()
        with tempfile.TemporaryDirectory() as td, patch.object(q,"request_bytes",side_effect=[identity,candles]):
            out=Path(td)
            r=q.collect("MEXC","REALUSDT","REAL","USDT",q.date.fromisoformat("2025-09-02"),out,1)
            self.assertTrue(r["qa_pass"])
            self.assertTrue((out/"RAW_IDENTITY.json").is_file())
            self.assertTrue((out/"RAW_000.json").is_file())
            self.assertEqual(r["duplicate_rows"],0)

    def test_safety_boundary_is_static_in_source(self):
        source=Path(q.__file__).read_text(encoding="utf-8")
        for token in ("no_backfill", "no_counter_reset", "no_silent_source_substitution", "engine_feed", "scientific_credit", "prospective_credit"):
            self.assertIn(token,source)


if __name__=="__main__": unittest.main()
