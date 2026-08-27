import unittest

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, 'tools')
import gate_btc_b3_h150_h159_economics as h


class H150H159ContractTests(unittest.TestCase):
    def test_frozen_family_budget(self):
        self.assertEqual(h.FAMS, tuple(f'H{i}' for i in range(150, 160)))
        self.assertEqual(h.ASSETS, ('WIN', 'WDO'))
        self.assertEqual(h.HOLDS, (60, 120))
        self.assertEqual(h.ROLL, 20)
        self.assertEqual(h.PRIMARY_BASE, 0)

    def test_revision_never_crosses_annual_horizon(self):
        dates = pd.date_range('2025-01-01', periods=23, freq='D').strftime('%Y-%m-%d')
        df = pd.DataFrame({
            'date': dates,
            'ref': ['2025'] * 21 + ['2026'] * 2,
            'median': list(range(21)) + [100, 101],
        })
        out = h.add_revision_z(df, 'median', 'x')
        self.assertTrue(np.isnan(out.loc[21, 'rev_x']))
        self.assertEqual(out.loc[22, 'rev_x'], 1)

    def test_full_twenty_prior_revisions_required(self):
        dates = pd.date_range('2025-01-01', periods=23, freq='D').strftime('%Y-%m-%d')
        df = pd.DataFrame({'date': dates, 'ref': ['2025'] * 23, 'median': np.arange(23, dtype=float)})
        out = h.add_revision_z(df, 'median', 'x')
        # First revision has no predecessor; z remains unavailable until 20 completed prior revisions exist.
        self.assertTrue(out.loc[:20, 'z_x'].isna().all())
        self.assertTrue(np.isfinite(out.loc[21, 'z_x']))

    def test_safety_constants_do_not_expose_execution(self):
        self.assertEqual(h.GEN, 'H150_H159_V1')
        self.assertEqual(h.CUTOFF, '2026-08-10')


if __name__ == '__main__':
    unittest.main()
