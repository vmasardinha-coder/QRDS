import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.gate_btc_2_family_feature_cadence import append


NOW = datetime(2026, 9, 29, 12, 21, tzinfo=timezone.utc)
MS = int(datetime(2026, 9, 29, 12, 20, tzinfo=timezone.utc).timestamp() * 1000)
SAFETY = dict(research_only=True, shadow_only=True, no_backfill=True,
              factory_runtime_untouched=True, economic_claim_authorized=False,
              factory_migration_authorized=False, orders=0, real_capital_brl=0)


class FamilyCadenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.capture = self.root / "capture"
        self.capture.mkdir()
        self.ledger = self.root / "ledger"

    def put(self, name, value):
        p = self.capture / name
        p.write_text(json.dumps(value) if not isinstance(value, str) else value)

    def xmm(self):
        self.put("SUMMARY.json", dict(SAFETY, family_id="F-XMM-INVENTORY",
                                      quality_pass=True, accepted_events=2,
                                      median_features={"BINANCE": {"spread_bps": 1}, "OKX": {"spread_bps": 2}}))
        self.put("FEATURE_EVENTS.jsonl", "\n".join(json.dumps(
            {"venue": venue, "receipt_ms": MS, "features": {"spread_bps": 1}})
            for venue in ("BINANCE", "OKX")) + "\n")

    def test_prospective_xmm_capture_seals_raw_and_rejects_duplicate(self):
        self.xmm()
        row = append("F-XMM-INVENTORY", self.capture, self.ledger, 123, NOW)
        self.assertEqual(row["utc_day"], "2026-09-29")
        self.assertEqual(row["economic_credit"], 0)
        self.assertTrue((self.ledger / "sources/2026-09-29.zip").exists())
        with self.assertRaisesRegex(RuntimeError, "duplicate"):
            append("F-XMM-INVENTORY", self.capture, self.ledger, 124, NOW)

    def test_old_capture_cannot_gain_prospective_credit(self):
        self.xmm()
        with self.assertRaisesRegex(RuntimeError, "retrospective"):
            append("F-XMM-INVENTORY", self.capture, self.ledger, 123,
                   datetime(2026, 9, 30, 12, 21, tzinfo=timezone.utc))
        self.assertFalse(self.ledger.exists())

    def test_xvol_requires_eligible_snapshot(self):
        self.put("SUMMARY.json", dict(SAFETY, family_id="F-XVOL-SURFACE",
                                      feature_snapshot_eligible=True, observation_ms=MS))
        self.put("FAMILY_FEATURES.json", {"eligible": True, "features": {"atm_iv_near": 30}})
        for name in ("RAW_INSTRUMENTS.json", "RAW_SUMMARY.json", "ROWS.jsonl"):
            self.put(name, "{}")
        row = append("F-XVOL-SURFACE", self.capture, self.ledger, 125, NOW)
        self.assertEqual(row["features"]["atm_iv_near"], 30)
        self.assertEqual(row["historical_credit"], 0)


if __name__ == "__main__":
    unittest.main()
