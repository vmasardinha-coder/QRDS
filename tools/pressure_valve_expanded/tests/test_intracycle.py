import unittest,sys
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'code' if (BASE/'code').is_dir() else BASE))
from pressure_valve_intracycle import simulate,plus,prepare
START='2026-10-22T09:15:00-03:00'
def prices(values):return {plus(START,i*5):v for i,v in enumerate(values)}
def trade(fid='H1',i=0,ep=100,side=1,cost=0):return {'family_id':fid,'policy':'TEST','session':'2026-10-22','entry':plus(START,i*5),'ep':ep,'side':side,'point':1,'cost':cost,'scenario':'REF'}

class Intracycle(unittest.TestCase):
    def test_profit_before_negative_close(self):
        r=simulate([trade()],prices([100,110,105,90,90]),{'minutes':15})
        self.assertEqual(r['net_brl'],-10);self.assertEqual(r['positions'][0]['sampled_mfe_brl'],10);self.assertTrue(r['positions'][0]['ever_sampled_positive'])
    def test_target_executes_next_bar_not_at_target(self):
        r=simulate([trade()],prices([100,110,104,103,103]),{'minutes':15,'target':10})
        self.assertEqual(r['positions'][0]['exit'],plus(START,10));self.assertEqual(r['net_brl'],4)
    def test_stop_can_overshoot(self):
        r=simulate([trade()],prices([100,90,80,80,80]),{'minutes':15,'stop':10})
        self.assertEqual(r['net_brl'],-20);self.assertEqual(r['positions'][0]['reason'],'STOP')
    def test_trailing_uses_past_peak(self):
        r=simulate([trade()],prices([100,110,104,102,102]),{'minutes':15,'arm':10,'distance':5})
        self.assertEqual(r['net_brl'],2);self.assertEqual(r['positions'][0]['reason'],'TRAIL')
    def test_future_prices_do_not_change_exit(self):
        a=simulate([trade()],prices([100,110,104,1,1]),{'minutes':15,'target':10})
        b=simulate([trade()],prices([100,110,104,999,999]),{'minutes':15,'target':10})
        self.assertEqual(a['net_brl'],b['net_brl'])
    def test_cap_slot_reused_only_after_fill(self):
        r=simulate([trade('H1'),trade('H2',1,110),trade('H3',2,104)],prices([100,110,104,103,103,103]),{'minutes':10,'target':10},cap=1)
        self.assertEqual([p['family_id'] for p in r['positions']],['H1','H3']);self.assertEqual(r['max_contracts'],1);self.assertEqual(r['skipped_cap'],1)
    def test_fixed_exit_releases_before_new_batch(self):
        r=simulate([trade('H1'),trade('H2',1,110)],prices([100,110,104,103]),{'minutes':5},cap=1)
        self.assertEqual(r['accepted'],2);self.assertEqual(r['max_contracts'],1)
    def test_priority_not_future_return(self):
        r=simulate([trade('H1'),trade('H2')],prices([100,110,104]),{'minutes':5},cap=1,priority=['H2'])
        self.assertEqual(r['positions'][0]['family_id'],'H2')
    def test_opposed_positions_mark_together(self):
        r=simulate([trade('H1',side=1,cost=2),trade('H2',side=-1,cost=2)],prices([100,110,95,105,105]),{'minutes':15,'scope':'cohort','target':5})
        self.assertEqual(r['net_brl'],-4);self.assertTrue(all(x['equity_brl']==-4 for x in r['curve']));self.assertFalse(any(e['event']=='LOT_DECISION' for e in r['events']))
    def test_day_lock_blocks_later_entry(self):
        r=simulate([trade('H1'),trade('H2',3,103)],prices([100,110,104,103,103,103,103,103]),{'minutes':15,'scope':'day','target':10},cap=1)
        self.assertTrue(r['day_locked']);self.assertEqual(r['skipped_lock'],1);self.assertEqual(r['accepted'],1);self.assertEqual(r['net_brl'],4)
    def test_missing_bar_never_becomes_zero(self):
        with self.assertRaisesRegex(ValueError,'MISSING_CLOCK_BAR'):
            simulate([trade()],{START:100,plus(START,10):110},{'minutes':5})
    def test_cost_is_paid_once_and_reconciles(self):
        r=simulate([trade(cost=2)],prices([100,110,104,103]),{'minutes':10})
        self.assertEqual(r['net_brl'],2);self.assertEqual(r['cost_brl'],2);self.assertEqual(r['gross_brl']-r['cost_brl'],r['net_brl'])
    def test_no_signal_no_phantom_trade(self):
        r=simulate([],{}, {'minutes':60});self.assertEqual(r['accepted'],0);self.assertEqual(r['state'],'NO_TRIGGERS')
    def test_equality_boundary_triggers(self):
        r=simulate([trade()],prices([100,105,104,103]),{'minutes':10,'target':5});self.assertEqual(r['positions'][0]['reason'],'TARGET')

if __name__=='__main__':unittest.main()
