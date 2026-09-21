import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path

PATH = Path('tools/gate_btc_factory/crypto_forward_schedule_guard.py')
spec = importlib.util.spec_from_file_location('crypto_forward_schedule_guard', PATH)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
NOW = datetime(2026, 9, 21, 13, 0, tzinfo=timezone.utc)


def run(run_id, status, conclusion=None, updated='2026-09-21T12:00:00Z'):
    return {
        'id': run_id,
        'status': status,
        'conclusion': conclusion,
        'created_at': updated,
        'updated_at': updated,
    }


class CryptoForwardScheduleGuardTests(unittest.TestCase):
    def test_active_run_blocks_dispatch(self):
        should, reason = g.dispatch_decision([run(1, 'in_progress')], NOW, 900)
        self.assertFalse(should)
        self.assertIn('ACTIVE', reason)

    def test_recent_success_blocks_dispatch(self):
        should, reason = g.dispatch_decision(
            [run(2, 'completed', 'success', '2026-09-21T12:50:01Z')], NOW, 900
        )
        self.assertFalse(should)
        self.assertIn('FRESH_SUCCESS', reason)

    def test_stale_success_dispatches(self):
        should, reason = g.dispatch_decision(
            [run(3, 'completed', 'success', '2026-09-21T12:44:59Z')], NOW, 900
        )
        self.assertTrue(should)
        self.assertEqual(reason, 'STALE_OR_NO_SUCCESS')

    def test_recent_failure_dispatches(self):
        should, reason = g.dispatch_decision(
            [run(4, 'completed', 'failure', '2026-09-21T12:59:00Z')], NOW, 900
        )
        self.assertTrue(should)
        self.assertEqual(reason, 'STALE_OR_NO_SUCCESS')

    def test_no_runs_dispatches(self):
        should, reason = g.dispatch_decision([], NOW, 900)
        self.assertTrue(should)
        self.assertEqual(reason, 'STALE_OR_NO_SUCCESS')


if __name__ == '__main__':
    unittest.main()
