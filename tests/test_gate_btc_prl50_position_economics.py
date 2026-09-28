import copy
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from tools import gate_btc_prl50_position_economics as e

CONTRACT=Path(__file__).resolve().parents[1]/'tools/gate_btc_prl50_position_shadow_contract_v1.json'
HASH=e.sha(CONTRACT)
def rows(values, rollover=False):
    result=[]
    for i,value in enumerate(values):
        day=(datetime(2026,8,31)+timedelta(days=i)).date().isoformat()
        sig='2026-09-30' if rollover and day>='2026-09-30' else '2026-08-31'
        active={s:{'signal_date':sig,'execution_eligible_from':'2026-10-01' if sig=='2026-09-30' else '2026-09-01',
                   'picks':[{'asset':'LINK' if sig=='2026-09-30' else 'SOL','weight':.3}]} for s in e.STRATEGIES}
        r={'snapshot_date':day,'signals':active,'active_signals':active,
           'selected_alt_closes':{} if value is None else {'SOL':value,'LINK':50.},
           'contract_sha256':HASH,'previous_row_sha256':result[-1]['row_sha256'] if result else None}
        r['row_sha256']=e.row_sha(r);result.append(r)
    return result
def seal(rs):
    for i,r in enumerate(rs):
        r['previous_row_sha256']=rs[i-1]['row_sha256'] if i else None
        r['row_sha256']=e.row_sha(r)
def strategy(rs): return e.evaluate(rs,HASH)[0]['strategies']['QOS_Moderada']

class EconomicsTests(unittest.TestCase):
    def test_trigger_and_execution_use_distinct_closes(self):
        r=strategy(rows([None,100,140,120,110,160]));p=r['positions']['SOL']
        self.assertEqual(p['trigger_date'],'2026-09-03');self.assertEqual(p['exit_date'],'2026-09-04')
        self.assertAlmostEqual(p['exit_return'],.1)
        self.assertAlmostEqual(r['prl50_return_contribution'],.03)
        self.assertAlmostEqual(r['control_hold_return_contribution'],.18)
    def test_pending_trigger_is_not_executed_same_bar(self):
        p=strategy(rows([None,100,140,120]))['positions']['SOL']
        self.assertIsNone(p['exit_date']);self.assertIsNone(p['exit_return'])
    def test_no_stop_before_activation_and_cash_after_exit(self):
        p=strategy(rows([None,100,50,100]))['positions']['SOL']
        self.assertFalse(p['armed']);self.assertIsNone(p['exit_return'])
        p=strategy(rows([None,100,140,120,110,300]))['positions']['SOL']
        self.assertAlmostEqual(p['exit_return'],.1)
    def test_missing_held_price_is_not_silently_excluded(self):
        rs=rows([None,100,140]);rs[-1]['selected_alt_closes']={};seal(rs)
        with self.assertRaisesRegex(ValueError,'HELD_PRICE'):e.evaluate(rs,HASH)
    def test_hash_gap_and_nonfinite_prices_rejected(self):
        rs=rows([None,100,140]);rs[-1]['snapshot_date']='2026-09-04';seal(rs)
        with self.assertRaisesRegex(ValueError,'MISSING_DAILY'):e.evaluate(rs,HASH)
        rs=rows([None,100]);rs[-1]['selected_alt_closes']['SOL']=float('nan');seal(rs)
        with self.assertRaisesRegex(ValueError,'HELD_PRICE'):e.evaluate(rs,HASH)
        rs=rows([None,100]);rs[-1]['row_sha256']='bad'
        with self.assertRaisesRegex(ValueError,'HASH'):e.evaluate(rs,HASH)
    def test_monthly_cohorts_close_and_reset_independently(self):
        rs=rows([None]+[100]*29+[120,130,150],rollover=True)
        out=e.evaluate(rs,HASH)
        self.assertEqual(out[0]['status'],'COMPLETED_VALID_CYCLE_GROSS_ONLY')
        a=out[0]['strategies']['QOS_Moderada'];self.assertEqual(a['last_price_date'],'2026-10-01')
        self.assertAlmostEqual(a['control_hold_return_contribution'],.09)
        b=out[1]['strategies']['QOS_Moderada'];self.assertEqual(set(b['positions']),{'LINK'})
        self.assertEqual(b['positions']['LINK']['entry'],50)
    def test_old_cohort_exit_price_remains_required_at_rollover(self):
        rs=rows([None]+[100]*31,rollover=True)
        del rs[-1]['selected_alt_closes']['SOL'];seal(rs)
        with self.assertRaisesRegex(ValueError,'HELD_PRICE:SOL'):e.evaluate(rs,HASH)
    def test_legacy_is_invalidated_without_rewrite_or_reconstruction(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);rs=rows([None,100])
            rs[-1].pop('active_signals');rs[-1]['selected_alt_closes']={};seal(rs)
            for r in rs:e.save(root/'snapshots'/(r['snapshot_date']+'.json'),r)
            e.save(root/'ANCHOR.json',{'old':'anchor'})
            e.save(root/'STATUS.json',{'status':'ACTIVE'})
            e.save(root/'ECONOMICS_STATUS.json',{'status':'OLD'})
            before={p.name:p.read_bytes() for p in (root/'snapshots').glob('*.json')}
            result=e.audit(root,CONTRACT,datetime(2026,9,28,tzinfo=timezone.utc))
            self.assertFalse(result['can_append'])
            self.assertEqual(result['proposed_next_untouched_signal'],'2026-09-30')
            self.assertEqual(e.load(root/'ECONOMICS_STATUS.json')['economic_credit'],0)
            self.assertEqual(e.load(root/'preserved/ECONOMICS_STATUS_BEFORE_REPAIR.json'),{'status':'OLD'})
            e.audit(root,CONTRACT,datetime(2026,9,28,tzinfo=timezone.utc))
            self.assertEqual(before,{p.name:p.read_bytes() for p in (root/'snapshots').glob('*.json')})
            (root/'snapshots'/'2026-09-01.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'EVIDENCE_CHANGED'):e.audit(root,CONTRACT)
    def test_current_valid_archive_can_continue_but_stale_archive_cannot(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for r in rows([None,100]):e.save(root/'snapshots'/(r['snapshot_date']+'.json'),r)
            e.save(root/'STATUS.json',{})
            self.assertTrue(e.audit(root,CONTRACT,datetime(2026,9,2,tzinfo=timezone.utc))['can_append'])
            self.assertFalse(e.audit(root,CONTRACT,datetime(2026,9,4,tzinfo=timezone.utc))['can_append'])


    def test_reporting_exposes_interruption_as_actionable_block(self):
        from tools.gate_btc_reporting_operational_overlay import enrich
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            e.save(root/'ledgers/prl50_position/DELIVERY_STATUS.json',{
                **e.SAFETY,'schema':'gate_btc.prl50.delivery.v1',
                'status':'BLOCKED_NEXT_MONTHLY_CYCLE_AUTHORIZATION_REQUIRED',
                'last_archived_date':'2026-09-04','can_append':False})
            out=enrich(root,{},as_of_utc=datetime(2026,9,28,tzinfo=timezone.utc))
            self.assertIn('prl50',out['warnings']['blocked_dependency_components'])
            self.assertFalse(out['delivery_complete'])
            self.assertNotEqual(out['components']['prl50']['collection_health_hint'],'GREEN_ACTIVE')

if __name__=='__main__':unittest.main()
