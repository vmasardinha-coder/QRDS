import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools.gate_btc_b3_gap_classifier import classify, log_mode


class SourceGapClassificationTest(unittest.TestCase):
    def test_exhausted_unavailable_warmup_source_is_zero_credit_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / "collect.log"
            gap = root / "gap.json"
            log.write_text("RuntimeError: SOURCE_NOT_READY 2026-08-12 SOURCE_RETRY_EXHAUSTED\n")
            rc = log_mode(SimpleNamespace(log=str(log), stream="H31",
                                          date="2026-10-01", out=str(gap)))
            self.assertEqual(rc, 0)
            row = json.loads(gap.read_text())
            self.assertEqual(row["date"], "2026-10-01")
            self.assertIn("2026-08-12", row["reason"])
            self.assertFalse(row["scientifically_qualified"])
            self.assertEqual(row["eligible_observation_increment"], 0)
            self.assertFalse(row["synthetic_backfill"])

    def test_processing_and_other_source_errors_remain_hard_failures(self):
        self.assertEqual(classify("SCHEMA_MISMATCH"), (False, None))
        self.assertEqual(
            classify("RuntimeError: SOURCE_NOT_READY 2026-08-12 UNEXPECTED_IDENTITY"),
            (False, None))


if __name__ == "__main__":
    unittest.main()
