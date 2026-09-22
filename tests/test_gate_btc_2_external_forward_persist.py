import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_2_external_forward_persist import build_record, append_record


class ExternalForwardPersistTests(unittest.TestCase):
    def test_xvol_eligible_append_is_idempotent_and_zero_credit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "src"
            runtime = root / "runtime"
            src.mkdir()
            (src / "SUMMARY.json").write_text(json.dumps({
                "observation_ms": 123456,
                "feature_snapshot_eligible": True,
                "feature_disposition": "FAMILY_FEATURE_SNAPSHOT_READY",
            }), encoding="utf-8")
            (src / "FAMILY_FEATURES.json").write_text(json.dumps({
                "eligible": True,
                "features": {
                    "atm_iv_near": 31.0,
                    "atm_iv_far": 35.0,
                    "term_slope": 4.0,
                    "put_25d_iv_near": 32.0,
                    "call_25d_iv_near": 33.0,
                    "risk_reversal_25d": 1.0,
                    "butterfly_25d": 1.5,
                    "surface_dispersion_near": 7.0,
                },
            }), encoding="utf-8")
            rec = build_record("F-XVOL-SURFACE", src, 0, "99", "abc", "2026-09-23T00:00:00Z")
            self.assertTrue(rec["available"])
            self.assertEqual(rec["scientific_credit"], 0)
            self.assertEqual(rec["survivor_credit"], 0)
            self.assertFalse(rec["engine_feed"])
            self.assertEqual(rec["orders"], 0)
            self.assertTrue(append_record(runtime, rec))
            self.assertFalse(append_record(runtime, rec))
            lines = (runtime / "F-XVOL-SURFACE" / "HISTORY.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            status = json.loads((runtime / "F-XVOL-SURFACE" / "STATUS.json").read_text(encoding="utf-8"))
            self.assertEqual(status["record_count"], 1)
            self.assertEqual(status["status"], "PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING")

    def test_missing_capture_is_explicit_unavailable_not_zero_filled(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "missing"
            src.mkdir()
            rec = build_record("F-XMM-INVENTORY", src, 1, "100", "def", "2026-09-23T04:00:00Z")
            self.assertFalse(rec["available"])
            self.assertIsNone(rec["features"])
            self.assertEqual(rec["source_quality"], "UNAVAILABLE")
            self.assertEqual(rec["unavailable_reason"], "CAPTURE_MISSING_OR_INELIGIBLE")
            self.assertTrue(append_record(root / "runtime", rec))

    def test_xmm_quality_pass_preserves_venue_feature_maps(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "src"
            src.mkdir()
            med = {
                "BINANCE": {"imbalance_l1": 0.2, "spread_bps": 0.01},
                "OKX": {"imbalance_l1": -0.1, "spread_bps": 0.02},
            }
            (src / "SUMMARY.json").write_text(json.dumps({
                "quality_pass": True,
                "median_features": med,
                "disposition": "FAMILY_FEATURE_CAPTURE_READY",
            }), encoding="utf-8")
            rec = build_record("F-XMM-INVENTORY", src, 0, "101", "ghi", "2026-09-23T08:00:00Z")
            self.assertTrue(rec["available"])
            self.assertEqual(rec["features"], med)
            self.assertFalse(rec["economic_claim_authorized"])
            self.assertFalse(rec["promotion_authority"])


if __name__ == "__main__":
    unittest.main()
