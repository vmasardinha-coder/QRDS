import json
import tempfile
import unittest
from pathlib import Path

from tests.test_gate_btc_delta_paper_monitor import CONTRACT, fixture
from tools.gate_btc_delta_isolated_source import preserve
from tools.gate_btc_delta_paper_monitor import MonitorError


class DeltaIsolatedSourceTests(unittest.TestCase):
    def test_preserves_same_close_without_changing_paper_nav(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.zip"
            fixture(source, "2026-10-01")
            runtime = root / "isolated"
            first = preserve(CONTRACT, source, runtime, 100, "2026-10-01")
            self.assertEqual(first["status"], "PRESERVED_UNCREDITED_SOURCE")
            self.assertEqual(first["scientific_credit"], 0)
            self.assertFalse(first["paper_nav_appended"])
            self.assertEqual((runtime / "snapshots/2026-10-01.zip").read_bytes(), source.read_bytes())
            self.assertEqual(preserve(CONTRACT, source, runtime, 100, "2026-10-01")["status"], "DUPLICATE_IDENTICAL")
            self.assertFalse((runtime / "STATUS.json").exists())
            self.assertFalse((runtime / "DAILY_NAV.csv").exists())
            receipt = json.loads((runtime / "snapshots/2026-10-01.json").read_text())
            self.assertEqual(receipt["source_run_id"], 100)

    def test_rejects_stale_wrong_close_unsafe_or_revised_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.zip"
            fixture(source, "2026-10-01")
            runtime = root / "isolated"
            with self.assertRaisesRegex(MonitorError, "exact prospective close"):
                preserve(CONTRACT, source, runtime, 100, "2026-10-02")
            preserve(CONTRACT, source, runtime, 100, "2026-10-01")
            revised = root / "revised.zip"
            fixture(revised, "2026-10-01", ret=.02)
            with self.assertRaisesRegex(MonitorError, "immutable Delta close conflicts"):
                preserve(CONTRACT, revised, runtime, 101, "2026-10-01")
            unsafe = root / "unsafe.zip"
            fixture(unsafe, "2026-10-02", unsafe=True)
            with self.assertRaisesRegex(MonitorError, "unsafe/failed"):
                preserve(CONTRACT, unsafe, runtime, 102, "2026-10-02")


if __name__ == "__main__":
    unittest.main()
