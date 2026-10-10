import copy
import tempfile
import unittest
from pathlib import Path
from tools.gate_btc_momentum_cost_diagnostic import rebalance, project, prices_for


class MomentumCostDiagnosticTest(unittest.TestCase):
    def fixture(self):
        targets = [f'A{i}' for i in range(10)]
        prices = {a:1.0 for a in targets}; prices['BTC']=1.0
        rows=[]
        for i in range(9):
            rows.append({'cutoff':f'2026-10-{i+1:02}', 'return_observations':i,
                         'event':'ACTIVATION' if i==0 else 'REBALANCE' if i==7 else 'HOLD',
                         'nav':{'M1_TOP10':1.0}, 'holdings_after_close':{'M1_TOP10':targets},
                         'quantities_after_close':{'M1_TOP10':{a:0.1 for a in targets}}})
        return {'rows':rows},[prices.copy() for _ in rows]

    def test_entry_cost_is_self_financing_and_no_charge_on_holds(self):
        ledger, prices = self.fixture()
        before=copy.deepcopy(ledger)
        out=project(ledger,prices,100)
        self.assertAlmostEqual(out['summary']['M1_TOP10']['nav_model_net'],1/1.01,places=12)
        self.assertAlmostEqual(out['summary']['BTC_HOLD']['nav_model_net'],1/1.01,places=12)
        self.assertTrue(all(r['portfolios']['M1_TOP10']['cost_nav_units']==0 for r in out['rows'][1:]))
        self.assertEqual(ledger,before)

    def test_full_rotation_charges_both_sells_and_buys(self):
        nav,cost,traded=rebalance({'A':1.0},['B'],0.0,0.01)
        self.assertAlmostEqual(nav,0.99/1.01,places=12)
        self.assertAlmostEqual(nav+cost,1.0,places=12)
        self.assertAlmostEqual(traded,1+nav,places=12)

    def test_zero_cost_matches_gross_and_gap_is_rejected(self):
        ledger,prices=self.fixture()
        out=project(ledger,prices,0)
        self.assertAlmostEqual(out['summary']['M1_TOP10']['nav_model_net'],1.0)
        ledger['rows'][3]['cutoff']='2026-10-05'
        with self.assertRaises(ValueError):project(ledger,prices,5)

    def test_changed_price_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            epoch=Path(td); p=epoch/'source_prices/2026-10-01/MANIFEST.json'
            p.parent.mkdir(parents=True);p.write_text('{}')
            row={'cutoff':'2026-10-01','evidence':{'price_manifest_sha256':'wrong'}}
            with self.assertRaises(ValueError):prices_for(row,epoch)

