from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.gate_btc_factory import continuation_guard as c


class ContinuationGuardTests(unittest.TestCase):
    def _with_temp_repo(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        old = os.getcwd()
        os.chdir(temp.name)
        self.addCleanup(os.chdir, old)
        Path('tools').mkdir(parents=True, exist_ok=True)
        return Path(temp.name)

    def _write_result(self, start: int, end: int, status: str, survivors=None, **extra):
        payload = {
            'status': status,
            'survivors': [] if survivors is None else survivors,
            'h1_economics_read': False,
            'survivor_partial_economics_read': False,
            'orders': 0,
            'capital': 0,
            'engine_feed': False,
            **extra,
        }
        path = Path(f'tools/gate_btc_b3_h{start}_h{end}_result.json')
        path.write_text(json.dumps(payload), encoding='utf-8')
        return path

    def test_h159_waits_until_canonical_close_exists(self):
        self._with_temp_repo()
        state, dispatch, path = c.classify_frontier(150, 159)
        self.assertEqual(state, 'WAITING_FOR_CANONICAL_TERMINAL_RESULT')
        self.assertFalse(dispatch)
        self.assertTrue(path.endswith('gate_btc_b3_h150_h159_result.json'))

    def test_h159_closed_no_survivor_dispatches_h160_path(self):
        self._with_temp_repo()
        self._write_result(150, 159, 'CLOSED_NO_H150_H159_SURVIVOR')
        state, dispatch, _ = c.classify_frontier(150, 159)
        self.assertEqual(state, 'TERMINAL_NO_SURVIVOR')
        self.assertTrue(dispatch)
        self.assertEqual((159 + 1, 159 + 10), (160, 169))

    def test_h169_closed_no_survivor_generalizes_without_hardcoding(self):
        self._with_temp_repo()
        self._write_result(160, 169, 'CLOSED_NO_H160_H169_SURVIVOR')
        state, dispatch, _ = c.classify_frontier(160, 169)
        self.assertEqual(state, 'TERMINAL_NO_SURVIVOR')
        self.assertTrue(dispatch)
        self.assertEqual((169 + 1, 169 + 10), (170, 179))

    def test_survivor_close_does_not_autoinvent_next_science(self):
        self._with_temp_repo()
        self._write_result(150, 159, 'SURVIVORS_READY_FOR_SEPARATE_PROSPECTIVE', ['H157'])
        state, dispatch, _ = c.classify_frontier(150, 159)
        self.assertEqual(state, 'TERMINAL_SURVIVOR_PRESENT')
        self.assertFalse(dispatch)

    def test_data_gap_fails_closed(self):
        self._with_temp_repo()
        self._write_result(150, 159, 'DATA_GAP_H150_H159_COVERAGE')
        state, dispatch, _ = c.classify_frontier(150, 159)
        self.assertEqual(state, 'FAIL_CLOSED_NON_SCIENTIFIC_CONTINUATION')
        self.assertFalse(dispatch)

    def test_unsafe_close_is_rejected(self):
        self._with_temp_repo()
        self._write_result(150, 159, 'CLOSED_NO_H150_H159_SURVIVOR', orders=1)
        with self.assertRaisesRegex(RuntimeError, 'UNSAFE_CLOSE_RESULT'):
            c.classify_frontier(150, 159)

    def test_legacy_h149_bootstrap_remains_supported(self):
        self._with_temp_repo()
        state, dispatch, _ = c.classify_frontier(140, 149)
        self.assertEqual(state, 'LEGACY_H149_BOOTSTRAP_REQUIRED')
        self.assertTrue(dispatch)

    def test_malformed_legacy_filename_does_not_poison_frontier(self):
        self._with_temp_repo()
        Path('.github/workflows').mkdir(parents=True, exist_ok=True)
        Path('.github/workflows/gate-btc-b3-h95-h10-economics.yml').write_text('legacy', encoding='utf-8')
        Path('.github/workflows/gate-btc-b3-h150-h159-focus.yml').write_text('canonical', encoding='utf-8')
        start, end, path = c.canonical_frontier_block()
        self.assertEqual((start, end), (150, 159))
        self.assertTrue(path.endswith('h150-h159-focus.yml'))

    def test_main_emits_frontier_key_and_target(self):
        self._with_temp_repo()
        self._write_result(150, 159, 'CLOSED_NO_H150_H159_SURVIVOR')
        out = Path('github_output.txt')
        with patch.object(c, 'canonical_frontier_block', return_value=(150, 159, 'synthetic')):
            with patch.dict(os.environ, {'GITHUB_OUTPUT': str(out)}):
                self.assertEqual(c.main(), 0)
        text = out.read_text(encoding='utf-8')
        self.assertIn('frontier_key=H159-TO-H160-H169', text)
        self.assertIn('next_start=160', text)
        self.assertIn('next_end=169', text)
        self.assertIn('should_dispatch=true', text)


if __name__ == '__main__':
    unittest.main()
