import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import gate_btc_xagent_decision_fallback as g


def clock(h, m, s=0):
    return datetime(2026, 10, 26, h, m, s, tzinfo=timezone.utc)


def run(status="completed", conclusion="success", created="2026-10-26T02:04:00Z", updated="2026-10-26T02:05:00Z"):
    return dict(id=1, status=status, conclusion=conclusion, created_at=created, updated_at=updated)


class DecisionFallbackTests(unittest.TestCase):
    def setUp(self):
        self.contract = g.load_contract()

    def test_bounded_runway_and_setup_reserve(self):
        for now, expected in [(clock(1, 44, 59), False), (clock(1, 45), True),
                              (clock(2, 0), True), (clock(2, 40), True),
                              (clock(2, 40, 1), False), (clock(3, 0), False)]:
            with self.subTest(now=now):
                self.assertEqual(g.window_gate(now, self.contract)[0], expected)

    def test_naive_clock_rejected(self):
        with self.assertRaisesRegex(ValueError, "TIMEZONE"):
            g.window_gate(datetime(2026, 10, 26, 2), self.contract)

    def test_before_preregistered_start_never_dispatches(self):
        self.assertFalse(g.window_gate(datetime(2026, 10, 22, 2, tzinfo=timezone.utc), self.contract)[0])

    def test_active_worker_blocks_duplicate(self):
        self.assertFalse(g.recovery_decision([run(status="queued", conclusion=None)], clock(2, 10), self.contract)[0])

    def test_off_window_success_does_not_mask_missed_decision(self):
        old = run(created="2026-10-26T01:30:00Z", updated="2026-10-26T01:59:00Z")
        self.assertTrue(g.recovery_decision([old], clock(2, 0), self.contract)[0])

    def test_recent_window_success_throttles_then_retries(self):
        self.assertFalse(g.recovery_decision([run()], clock(2, 9, 59), self.contract)[0])
        self.assertTrue(g.recovery_decision([run()], clock(2, 10), self.contract)[0])

    def test_failed_window_run_can_retry(self):
        self.assertTrue(g.recovery_decision([run(conclusion="failure")], clock(2, 6), self.contract)[0])

    def test_outside_window_has_no_network_or_dispatch(self):
        with patch.object(g, "github_json") as fetch, patch.object(g, "dispatch") as send:
            g.main(lambda: clock(12, 0))
            fetch.assert_not_called()
            send.assert_not_called()

    def test_network_delay_past_cutoff_blocks_dispatch(self):
        times = iter([clock(2, 39), clock(2, 41)])
        with patch.dict(os.environ, GH_TOKEN="fixture", REPOSITORY="owner/repo"), \
                patch.object(g, "github_json", return_value={"workflow_runs": []}), \
                patch.object(g, "dispatch") as send:
            g.main(lambda: next(times))
            send.assert_not_called()

    def test_dispatches_actual_decisor_without_date_override(self):
        with patch.dict(os.environ, GH_TOKEN="fixture", REPOSITORY="owner/repo"), \
                patch.object(g, "github_json", return_value={"workflow_runs": []}), \
                patch.object(g, "dispatch") as send:
            g.main(lambda: clock(1, 52))
            send.assert_called_once_with("owner/repo", "gate-btc-xagent-spot-decision-window.yml", "fixture")

    def test_workflow_wires_guard_without_removing_transform(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/gate-btc-xagent-schedule-fallback.yml").read_text()
        self.assertIn("python tools/gate_btc_xagent_decision_fallback.py", workflow)
        self.assertIn("TARGET_WORKFLOW: gate-btc-xagent-disagree-transform.yml", workflow)
        self.assertIn("python -m unittest discover -s tests -p test_gate_btc_xagent_decision_fallback.py -v", workflow)


if __name__ == "__main__":
    unittest.main()
