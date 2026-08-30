import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_2_stage9_bitget_admission_review import review_capture


class BitgetAdmissionReviewTests(unittest.TestCase):
    def _fixture(self, root: Path):
        perp = b'{"code":"00000","data":[{"symbol":"BTCUSDT","fundingRate":"0.0001","holdingAmount":"5","baseVolume":"10"}]}'
        spot = b'{"code":"00000","data":[{"symbol":"BTCUSDT","baseVolume":"8"}]}'
        (root / "bitget_perp.json").write_bytes(perp)
        (root / "bitget_spot.json").write_bytes(spot)
        decision = {
            "status":"CAPTURED_AWAITING_ADMISSION_REVIEW",
            "captured_at_utc":"2026-08-30T02:12:08Z",
            "provider":"BITGET_PUBLIC_V2","venue":"BITGET","instrument":"BTCUSDT",
            "forward_only":True,"historical_rows_backfilled":0,
            "source_admitted":False,"prospective_credit":0,
            "roles":{"FUNDING":{},"OPEN_INTEREST":{},"PERP_VOLUME":{},"SPOT_VOLUME":{}},
            "raw_sha256":{"perp":hashlib.sha256(perp).hexdigest(),"spot":hashlib.sha256(spot).hexdigest()},
            "research_only":True,"shadow_only":True,"not_approved":True,
            "engine_feed":False,"orders_generated":0,"real_capital_used":0,
            "no_retune":True,"no_backfill":True,"fail_closed":True,
            "stage_9_complete":False,"promotion_allowed":False,
            "methodology_changes":0,"clock_changes":0,"economics_changes":0,
        }
        (root / "capture_decision.json").write_text(json.dumps(decision))

    def test_valid_capture_admits_only_shadow_observation(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); self._fixture(p)
            review, admission = review_capture(p)
            self.assertEqual(review["status"], "ADMITTED_FORWARD_ONLY_CAPTURE")
            self.assertEqual(admission["decision"], "ADMITTED_FORWARD_ONLY")
            self.assertTrue(admission["source_admitted_for_shadow_collection"])
            self.assertEqual(admission["prospective_observations_admitted"], 1)
            self.assertFalse(admission["stage_9_complete"])
            self.assertFalse(admission["economics_allowed"])
            self.assertFalse(admission["engine_feed"])
            self.assertEqual(admission["orders_generated"], 0)
            self.assertEqual(admission["real_capital_used"], 0)

    def test_tampered_raw_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); self._fixture(p)
            (p / "bitget_spot.json").write_bytes(b'{}')
            with self.assertRaises(RuntimeError):
                review_capture(p)

    def test_premerge_capture_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); self._fixture(p)
            d=json.loads((p / "capture_decision.json").read_text())
            d["captured_at_utc"]="2026-08-30T01:00:00Z"
            (p / "capture_decision.json").write_text(json.dumps(d))
            with self.assertRaises(RuntimeError):
                review_capture(p)

    def test_economics_change_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); self._fixture(p)
            d=json.loads((p / "capture_decision.json").read_text())
            d["economics_changes"]=1
            (p / "capture_decision.json").write_text(json.dumps(d))
            with self.assertRaises(RuntimeError):
                review_capture(p)


if __name__ == "__main__":
    unittest.main()
