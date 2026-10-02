import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools.gate_btc_b3_gap_classifier import h1


class H1ScheduleClassificationTest(unittest.TestCase):
    def test_missing_frozen_schedule_has_no_gap_or_scientific_credit(self):
        with tempfile.TemporaryDirectory() as directory:
            status = Path(directory) / "H1_STRUCTURAL_STATUS.json"
            gap = Path(directory) / "H1_OPERATIONAL_GAP.json"
            status.write_text(json.dumps({
                "status": "NO_FROZEN_H1_SCHEDULE_FOR_DATE",
                "qualified": False,
                "date": "2026-10-01",
            }), encoding="utf-8")
            self.assertEqual(h1(SimpleNamespace(status=str(status), out=str(gap))), 0)
            self.assertFalse(gap.exists())

    def test_processing_error_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            status = Path(directory) / "H1_STRUCTURAL_STATUS.json"
            status.write_text(json.dumps({
                "status": "FAILED", "error": "SCHEMA_MISMATCH", "date": "2026-10-01"
            }), encoding="utf-8")
            self.assertEqual(h1(SimpleNamespace(status=str(status), out=None)), 2)


if __name__ == "__main__":
    unittest.main()
