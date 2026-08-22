import tempfile
import unittest
from pathlib import Path

from tools import gate_btc_v16b_rehearsal as r


class V16BRehearsalIsolationTests(unittest.TestCase):
    def test_mark_forces_noncanonical_zero_count(self):
        row = {"status": "OK", "ORDERS": 99, "REAL_CAPITAL": 99}
        out = r._mark(row)
        self.assertTrue(out["REHEARSAL"])
        self.assertEqual(out["PROSPECTIVE_COUNT"], 0)
        self.assertFalse(out["CANONICAL_LEDGER"])
        self.assertTrue(out["RESEARCH_ONLY"])
        self.assertTrue(out["SHADOW_ONLY"])
        self.assertTrue(out["NOT_APPROVED"])
        self.assertFalse(out["ENGINE_FEED"])
        self.assertEqual(out["ORDERS"], 0)
        self.assertEqual(out["REAL_CAPITAL"], 0)

    def test_rehearsal_ledger_name_required(self):
        with self.assertRaises(ValueError):
            r._assert_rehearsal_ledger(Path("runtime/ledgers/v16b/prospective.jsonl"))
        r._assert_rehearsal_ledger(Path("artifacts/gate_btc/v16b/rehearsal/V16B_REHEARSAL.jsonl"))

    def test_protocol_version_is_frozen(self):
        self.assertEqual(r.REHEARSAL_PROTOCOL_VERSION, "V16B_REHEARSAL_1D_V1_20260822")
        self.assertEqual(r.REHEARSAL_FIELDS["PROSPECTIVE_COUNT"], 0)
        self.assertIs(r.REHEARSAL_FIELDS["CANONICAL_LEDGER"], False)


if __name__ == "__main__":
    unittest.main()
