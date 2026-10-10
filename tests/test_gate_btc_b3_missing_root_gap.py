import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools.gate_btc_b3_gap_classifier import classify, h1


class MissingRootGapTests(unittest.TestCase):
    def test_captured_official_file_missing_frozen_wdo_is_zero_credit_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = root / "H1_STRUCTURAL_STATUS.json"
            gap = root / "H1_OPERATIONAL_GAP.json"
            status.write_text(
                '{"date":"2026-10-09","status":"STRUCTURAL_FAIL_CLOSED",'
                '"qualified":false,"error":"RuntimeError(\'M1_WDO_MISSING\')",'
                '"source":{"state":"SOURCE_CAPTURED","sha256":"sample"}}',
                encoding="utf-8",
            )
            self.assertEqual(h1(SimpleNamespace(status=str(status), out=str(gap))), 0)
            import json
            payload = json.loads(gap.read_text(encoding="utf-8"))
            self.assertEqual(payload["reason"], "M1_WDO_MISSING")
            self.assertEqual(payload["eligible_observation_increment"], 0)
            self.assertFalse(payload["scientifically_qualified"])
            self.assertFalse(payload["engine_feed"])

    def test_other_processing_failures_stay_hard_failures(self):
        for error in ("RuntimeError('WDO_CONTRACT_MISMATCH')",
                      "RuntimeError('M1_WDO_CLOSE_OFF_TICK')",
                      "ValueError('parser crashed')"):
            with self.subTest(error=error):
                self.assertEqual(classify(error), (False, None))


if __name__ == "__main__":
    unittest.main()
