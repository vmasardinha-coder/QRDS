import copy
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from tools.gate_btc_reporting_operational_overlay import enrich, v16b_terminal_closed


def terminal():
    return dict(schema="gate_btc.v16b.status.v1", status="TERMINAL_BLOCKED_NOT_PROMOTABLE",
        data_as_of="2026-09-09", terminal_disposition="CLOSED_FAIL_CLOSED_EXTERNAL_ENTRY_INFRASTRUCTURE_BLOCK",
        parent_reopened=False, canonical_cycle_count=0, next_canonical_event=None,
        promotion_allowed=False, economic_claim_allowed=False, prospective_credit=0,
        engine_feed=False, research_only=True, shadow_only=True, not_approved=True,
        orders_generated=0, real_capital_used=0)


class TerminalParentTests(unittest.TestCase):
    def test_incomplete_or_reopened_record_cannot_hide_staleness(self):
        for key, value in (("schema", "other"), ("status", "BLOCKED_ACTIVE"),
                ("terminal_disposition", "unknown"), ("parent_reopened", True),
                ("canonical_cycle_count", 1), ("next_canonical_event", "SIGNAL_2026-10-15"),
                ("promotion_allowed", True), ("economic_claim_allowed", True),
                ("prospective_credit", 1), ("engine_feed", True), ("data_as_of", "2026-10-20")):
            obj = terminal(); obj[key] = value
            with self.subTest(key=key):
                self.assertFalse(v16b_terminal_closed(obj, date(2026, 10, 11)))
        for key in terminal():
            if key in {"research_only", "shadow_only", "not_approved", "orders_generated", "real_capital_used"}:
                continue
            obj = terminal(); obj.pop(key)
            with self.subTest(missing=key):
                self.assertFalse(v16b_terminal_closed(obj, date(2026, 10, 11)))

    def run_overlay(self, obj):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); path = root / "ledgers/v16b/STATUS.json"
            path.parent.mkdir(parents=True); path.write_text(json.dumps(obj))
            raw = path.read_bytes()
            state = dict(reference_data_date="2026-10-11", components={},
                warnings=dict(stale_components=["v16b", "other_front"],
                    missing_or_undated_components=[], failed_delivery_components=[],
                    blocked_dependency_components=["v16b", "v16b1"]))
            result = enrich(root, copy.deepcopy(state), datetime(2026, 10, 12, tzinfo=timezone.utc))
            self.assertEqual(raw, path.read_bytes())
            return result

    def test_closed_parent_is_removed_but_other_blockers_and_zero_cycles_remain(self):
        result = self.run_overlay(terminal())
        self.assertEqual(result["components"]["v16b"]["freshness"], "CLOSED_NOT_APPLICABLE")
        self.assertEqual(result["components"]["v16b"]["canonical_cycle_count"], 0)
        self.assertIn("other_front", result["warnings"]["stale_components"])
        self.assertIn("v16b1", result["warnings"]["blocked_dependency_components"])
        for names in ("stale_components", "missing_or_undated_components", "failed_delivery_components", "blocked_dependency_components"):
            self.assertNotIn("v16b", result["warnings"][names])
        self.assertFalse(result["delivery_complete"])
        self.assertEqual(result["status"], "BLOCKED_INCOMPLETE_DELIVERY")

    def test_reopened_parent_keeps_stale_warning(self):
        obj = terminal(); obj["parent_reopened"] = True
        result = self.run_overlay(obj)
        self.assertEqual(result["components"]["v16b"]["freshness"], "STALE")
        self.assertIn("v16b", result["warnings"]["stale_components"])

    def test_unsafe_record_still_aborts(self):
        obj = terminal(); obj["orders_generated"] = 1
        with self.assertRaises(SystemExit):
            self.run_overlay(obj)


if __name__ == "__main__":
    unittest.main()
