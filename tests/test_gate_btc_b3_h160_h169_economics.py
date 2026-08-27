import unittest
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,'tools')
import gate_btc_b3_h160_h169_economics as h


class H160H169EconomicsContract(unittest.TestCase):
    def test_frozen_family_and_windows(self):
        self.assertEqual(h.FAMS, tuple(f'H{i}' for i in range(160,170)))
        self.assertEqual(h.HOLDS,(60,120))
        self.assertEqual(h.LEVEL_WINDOW,60)
        self.assertEqual(h.CHANGE_WINDOW,20)
        self.assertEqual(h.COVERAGE_MIN,0.90)
        self.assertEqual(h.CUTOFF,'2026-08-10')

    def test_family_inputs_frozen(self):
        self.assertEqual(h.FAMILY_INPUTS['H168'],('z_h160','z_h161','z_h162'))
        self.assertEqual(h.FAMILY_INPUTS['H169'],('z_h160','z_h161','z_h162','z_h163','z_h164'))

    def test_robust_level_uses_prior_60_only(self):
        s=pd.Series(list(range(1,62)),dtype=float)
        z=h.robust_level_z(s)
        self.assertTrue(pd.isna(z.iloc[59]))
        prior=np.arange(1,61,dtype=float)
        med=np.median(prior); mad=np.median(np.abs(prior-med))
        self.assertAlmostEqual(float(z.iloc[60]),(61.0-med)/mad)

    def test_change_scale_uses_prior_20_changes(self):
        s=pd.Series(np.arange(0,23,dtype=float)**2)
        z=h.abs_change_z(s)
        self.assertTrue(pd.isna(z.iloc[20]))
        change=s.diff()
        scale=change.abs().iloc[1:21].median()
        self.assertAlmostEqual(float(z.iloc[21]),float(change.iloc[21]/scale))

    def test_no_h1_or_partial_economics_dependency_in_source(self):
        text=open('tools/gate_btc_b3_h160_h169_economics.py',encoding='utf-8').read()
        self.assertIn('h1_economics_read',text)
        self.assertIn('survivor_partial_economics_read',text)
        self.assertNotIn('synthetic_backfill',text.lower())


if __name__=='__main__': unittest.main()
