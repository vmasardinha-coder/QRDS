import importlib.util
import json
import unittest
from pathlib import Path

M = Path('tools/gate_btc_factory/grammar_008_industrial_gap_safe.py')
spec = importlib.util.spec_from_file_location('g008gap', M)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
PR = json.loads(Path('tools/gate_btc_factory/GRAMMAR_008_FREQTRADE_INDUSTRIAL_PREREG_20260921.json').read_text())
SE = json.loads(Path('tools/gate_btc_factory/GRAMMAR_008_INDICATOR_SEMANTICS_20260921.json').read_text())


class Grammar008GapSafeTests(unittest.TestCase):
    def test_contiguous_segments_break_on_missing_hour(self):
        h = m.HOUR
        bars = [
            {'time': 0}, {'time': h}, {'time': 2*h},
            {'time': 6*h}, {'time': 7*h},
        ]
        segments = m.contiguous_segments(bars)
        self.assertEqual([[b['time'] for b in s] for s in segments], [[0, h, 2*h], [6*h, 7*h]])

    def test_gap_safe_backtest_never_crosses_missing_hours(self):
        h = m.HOUR
        bars = []
        for t in list(range(0, 40*h, h)) + list(range(43*h, 90*h, h)):
            bars.append({'time': t, 'open': 100.0, 'high': 101.0, 'low': 99.0, 'close': 100.0, 'volume': 1.0})
        spec = next(x for x in m.base.candidate_specs(PR, SE) if x['candidate_id'] == 'G008_BAND_MEAN_REVERSION::BB20_W2_0::BTC-USD')
        result = m.gap_safe_backtest_partition(bars, spec, PR, 0, 89*h)
        self.assertEqual(result['gap_policy'], 'INELIGIBLE_NO_IMPUTATION')
        self.assertEqual(result['physical_contiguous_segments'], 2)
        for trade in result['trades']:
            self.assertFalse(trade['entry_time'] < 43*h <= trade['exit_time'])

    def test_execute_records_zero_imputation(self):
        calls = []
        def fetcher(product, start, end):
            calls.append((product, start, end))
            bars = []
            skipped = start + 30*m.HOUR
            for t in range(start, end, m.HOUR):
                if t == skipped:
                    continue
                bars.append({'time': t, 'open': 100.0, 'high': 101.0, 'low': 99.0, 'close': 100.0, 'volume': 1.0})
            return bars
        result = m.execute(PR, SE, fetcher=fetcher)
        self.assertEqual(result['imputed_bar_count'], 0)
        self.assertEqual(result['missing_bar_policy_applied'], 'INELIGIBLE_NO_IMPUTATION')
        self.assertEqual(len(calls), 2)
        self.assertFalse(result['validation_source_opened'])
        self.assertFalse(result['holdout_source_opened'])


if __name__ == '__main__':
    unittest.main()
