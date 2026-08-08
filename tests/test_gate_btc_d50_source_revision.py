import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from tools.gate_btc_measurement_status import audit_d50
from tools.gate_btc_measurement_common import load_json


class D50SourceRevisionTests(unittest.TestCase):
    def _run(self, frozen_payload, candidate_payload):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        frozen = root / "frozen.json"
        candidate = root / "candidate.json"
        output = root / "report.json"
        frozen.write_text(json.dumps(frozen_payload), encoding="utf-8")
        candidate.write_text(json.dumps(candidate_payload), encoding="utf-8")
        rc = audit_d50(Namespace(
            frozen_row=frozen,
            candidate_row=candidate,
            ignore_field=None,
            output=output,
        ))
        return temp, rc, load_json(output), load_json(frozen)

    def test_source_hash_revision_passes_without_mutating_frozen_row(self):
        frozen = {
            "date": "2026-08-01",
            "strategy": "D50_CONTROL",
            "net_return": -0.0010251858188263,
            "turnover": 0.5,
            "source_bar_sha256": "7db607-old",
            "replay_row_sha256": "a0f200-old",
        }
        candidate = {
            **frozen,
            "source_bar_sha256": "e5478c-new",
            "replay_row_sha256": "918811-new",
        }
        temp, rc, report, preserved = self._run(frozen, candidate)
        try:
            self.assertEqual(rc, 0)
            self.assertEqual(report["status"], "PASS_PROVENANCE_ONLY_SOURCE_REVISION")
            self.assertTrue(report["economic_fields_identical"])
            self.assertTrue(report["source_revision_only"])
            self.assertFalse(report["mutation_performed"])
            self.assertEqual(report["economic_difference_count"], 0)
            self.assertEqual(report["provenance_difference_count"], 2)
            self.assertEqual(preserved, frozen)
        finally:
            temp.cleanup()

    def test_economic_revision_remains_fail_closed(self):
        frozen = {
            "date": "2026-08-01",
            "strategy": "D50_CONTROL",
            "net_return": -0.0010251858188263,
            "source_bar_sha256": "old",
            "replay_row_sha256": "old-row",
        }
        candidate = {
            **frozen,
            "net_return": -0.0011,
            "source_bar_sha256": "new",
            "replay_row_sha256": "new-row",
        }
        temp, rc, report, preserved = self._run(frozen, candidate)
        try:
            self.assertEqual(rc, 2)
            self.assertEqual(report["status"], "FAIL_IMMUTABLE_ECONOMIC_ROW_CHANGED")
            self.assertFalse(report["economic_fields_identical"])
            self.assertGreater(report["economic_difference_count"], 0)
            self.assertFalse(report["mutation_performed"])
            self.assertEqual(preserved, frozen)
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
