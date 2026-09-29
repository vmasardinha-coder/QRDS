import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from tools.gate_btc_factory.calendar_gate_preflight import check


def write(root, rel, value):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


class CalendarEpochTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        write(self.root, "runtime/GATE_BTC_MEASUREMENT_STATUS.json",
              {"qos_monthly": {"expected_closes": ["2026-08-31"]}})
        write(self.root, "runtime/ledgers/v16b/STATUS.json",
              {"canonical_cycle_count": 0, "next_canonical_event": None})
        for name, folder in (("prl50", "prl50_position"), ("alt_trail", "alt_trail40_10")):
            self.make_epoch(name, folder)

    def make_epoch(self, name, folder):
        base = f"runtime/ledgers/{folder}"
        clocks = {"first_eligible_signal_date": "2026-09-30"}
        if name == "alt_trail":
            clocks["first_eligible_execution_date"] = "2026-10-01"
        write(self.root, base + "/STATUS.json", {"current_epoch": "monthly_20260930", **clocks})
        write(self.root, base + "/epochs/monthly_20260930/ANCHOR.json",
              {"contract_sha256": "frozen", **clocks})
        write(self.root, base + "/epochs/monthly_20260930/STATUS.json",
              {"contract_sha256": "frozen", **clocks})

    def test_active_epoch_passes_at_its_actual_frozen_clock(self):
        result = check(self.root, date(2026, 9, 29))
        self.assertEqual(result["overall_status"], "PASS")
        rows = {r["track"]: r for r in result["rows"]}
        self.assertEqual(rows["prl50"]["days_to_first_clock"], 1)
        self.assertEqual(rows["alt_trail"]["first_eligible_signal_date"], "2026-09-30")

    def test_status_date_divergence_fails_closed(self):
        p = self.root / "runtime/ledgers/prl50_position/STATUS.json"
        value = json.loads(p.read_text())
        value["first_eligible_signal_date"] = "2026-09-29"
        p.write_text(json.dumps(value))
        result = check(self.root, date(2026, 9, 29))
        self.assertEqual(result["overall_status"], "RED_FAIL_CLOSED")
        self.assertIn("diverges", next(r for r in result["rows"] if r["track"] == "prl50")["error"])

    def test_missing_epoch_anchor_fails_closed(self):
        (self.root / "runtime/ledgers/alt_trail40_10/epochs/monthly_20260930/ANCHOR.json").unlink()
        result = check(self.root, date(2026, 9, 29))
        self.assertEqual(result["overall_status"], "RED_FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
