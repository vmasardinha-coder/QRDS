import math
import unittest

from tools.gate_btc_2_quantlib_deribit_options_runner import capability_metrics, quantile, sample_gate


class QuantLibDeribitOptionsTests(unittest.TestCase):
    def test_quantile_linear(self):
        self.assertEqual(quantile([1.0], 0.9), 1.0)
        self.assertAlmostEqual(quantile([0.0, 1.0], 0.5), 0.5)
        self.assertAlmostEqual(quantile([0.0, 1.0, 2.0], 0.9), 1.8)

    def _row(self, i, option_type, expiry, err=0.0001, mark=0.01):
        return {
            'instrument_name': f'BTC-X-{i}',
            'option_type': option_type,
            'expiration_timestamp': expiry,
            'reconstructed_btc': mark + err,
            'mark_price_btc': mark,
            'abs_error_btc': abs(err),
            'relative_error': abs(err) / mark,
        }

    def test_sample_gate(self):
        rows=[]
        for i in range(15):
            rows.append(self._row(i, 'call', 1000 if i < 8 else 2000))
        for i in range(15, 30):
            rows.append(self._row(i, 'put', 1000 if i < 23 else 2000))
        passed, d = sample_gate(rows)
        self.assertTrue(passed)
        self.assertEqual(d['calls'], 15)
        self.assertEqual(d['puts'], 15)
        self.assertEqual(d['distinct_expiries'], 2)
        self.assertEqual(d['duplicate_instruments'], 0)

    def test_sample_gate_rejects_duplicate(self):
        rows=[]
        for i in range(15):
            rows.append(self._row(i, 'call', 1000 if i < 8 else 2000))
        for i in range(15, 30):
            rows.append(self._row(i, 'put', 1000 if i < 23 else 2000))
        rows[-1]['instrument_name'] = rows[0]['instrument_name']
        self.assertFalse(sample_gate(rows)[0])

    def test_capability_pass_and_fail(self):
        rows=[]
        for i in range(40):
            rows.append(self._row(i, 'call' if i % 2 == 0 else 'put', 1000 if i < 20 else 2000, err=0.0001, mark=0.01))
        self.assertTrue(capability_metrics(rows)['capability_pass'])
        bad=[dict(r, abs_error_btc=0.003, relative_error=0.3) for r in rows]
        self.assertFalse(capability_metrics(bad)['capability_pass'])


if __name__ == '__main__':
    unittest.main()
