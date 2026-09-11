import csv,io,json,tempfile,unittest,zipfile
from pathlib import Path
from tools import gate_btc_delta_paper_monitor as mon

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/'migration'/'reporting'/'delta_paper_monitor_contract.json'
STRATS=['Delta_LS_70_30','Delta_LS_70_30_StopVol','Delta_LS_50_50','Delta_LS_50_50_StopVol']

def csvb(rs):
    if not rs:return b''
    x=io.StringIO(); w=csv.DictWriter(x,fieldnames=list(rs[0])); w.writeheader(); w.writerows(rs); return x.getvalue().encode()

def fixture(path,asof,ret=.01,unsafe=False,gate_window=True):
    daily=[]; pos=[]; gate=[]
    for s in STRATS:
        daily.append({'strategy':s,'date':asof,'gross_return':ret+.001,'trading_cost_return':.001,'funding_return':0,'net_return':ret,'equity':1,'turnover':.2,'kill_switch_active':'False'})
        pos.append({'strategy':s,'date':asof,'symbol':'BTC','side':'LONG','signed_weight':'.1'})
        row={'strategy':s,'evidence_eligible':'False','rejection_reasons':'test'}
        if gate_window:
            # The engine's own window, which is NOT the shadow's observed_days.
            row.update({'window':'EXPANDING_FROM_D0','observations':'90','end':asof})
        gate.append(row)
    manifest={'technical_status':'FAIL' if unsafe else 'PASS','operational_status':'NOT_APPROVED','real_orders':0,'capital_used':0,'evidence_status':'WALK_FORWARD_RESEARCH_SHORT_SAMPLE_NO_OPERATIONAL_PROMOTION','data_as_of':asof,'version':'DELTA_WALK_FORWARD_1.1'}
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('outputs/delta_v11_run_manifest.json',json.dumps(manifest))
        z.writestr('outputs/delta_daily_returns.csv',csvb(daily))
        z.writestr('outputs/delta_trade_ledger.csv',csvb([{'strategy':STRATS[0],'date':asof,'symbol':'ETH','event':'ENTRY','side':'LONG','price':'100'}]))
        z.writestr('outputs/delta_daily_positions.csv',csvb(pos))
        z.writestr('outputs/delta_historical_selections.csv',csvb([{'strategy':STRATS[0],'signal_date':asof,'execution_date':asof,'symbol':'ETH','side':'LONG','target_weight':'.1'}]))
        z.writestr('outputs/strategy_evidence_gate.csv',csvb(gate))
        z.writestr('outputs/strategy_selection_current.json',json.dumps({'data_as_of':asof,'regime':'NEUTRAL','price_zone':'ABOVE_60K','stabilization_confirmed':True,'btc_close':60000}))
        z.writestr('outputs/btc_regime_daily.csv',csvb([{'date':asof,'btc_close':'60000','regime':'NEUTRAL','raw_regime':'NEUTRAL','price_zone':'ABOVE_60K','stabilization_confirmed':'True'}]))

class TestDeltaPaperMonitor(unittest.TestCase):
    def test_anchor_first_return_and_hash_chain(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); rt=td/'rt'; a=td/'a.zip'; fixture(a,'2026-08-13')
            x=mon.process(CONTRACT,a,rt,'100'); self.assertEqual(x['status'],'ARMED_WAITING_FIRST_RETURN'); self.assertEqual(x['observed_days'],0)
            b=td/'b.zip'; fixture(b,'2026-08-14',.01); y=mon.process(CONTRACT,b,rt,'101'); self.assertEqual(y['observed_days'],1)
            self.assertAlmostEqual(y['strategies'][STRATS[0]]['normalized_nav'],1.01,12)
            with (rt/'DAILY_NAV.csv').open() as h: rs=list(csv.DictReader(h))
            self.assertEqual(len(rs),4); self.assertEqual(len({r['chain_sha256'] for r in rs}),4); self.assertTrue((rt/'SOURCE_CHAIN.csv').exists()); self.assertTrue((rt/'LATEST.md').exists())

    def test_duplicate_identical_noop_conflict_and_gap_fail(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); rt=td/'rt'; a=td/'a.zip'; fixture(a,'2026-08-13'); mon.process(CONTRACT,a,rt,'100')
            b=td/'b.zip'; fixture(b,'2026-08-14',.01); mon.process(CONTRACT,b,rt,'101'); before=(rt/'DAILY_NAV.csv').read_text()
            mon.process(CONTRACT,b,rt,'102'); self.assertEqual(before,(rt/'DAILY_NAV.csv').read_text())
            c=td/'c.zip'; fixture(c,'2026-08-14',.02)
            with self.assertRaises(mon.MonitorError): mon.process(CONTRACT,c,rt,'103')
            g=td/'g.zip'; fixture(g,'2026-08-16',.01)
            with self.assertRaises(mon.MonitorError): mon.process(CONTRACT,g,rt,'104')

    def test_the_gate_window_is_carried_through_and_is_not_the_shadow_counter(self):
        # The whole point of carrying these fields: 90 engine observations beside
        # 1 shadow observation, so a reader can never confuse the two counters.
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); rt=td/'rt'; a=td/'a.zip'; fixture(a,'2026-08-13'); mon.process(CONTRACT,a,rt,'100')
            b=td/'b.zip'; fixture(b,'2026-08-14',.01); y=mon.process(CONTRACT,b,rt,'101')
            book=y['strategies'][STRATS[0]]
            self.assertEqual(book['evidence_window'],'EXPANDING_FROM_D0')
            self.assertEqual(book['evidence_observations'],90)
            self.assertEqual(book['evidence_window_end'],'2026-08-14')
            self.assertEqual(y['observed_days'],1)
            self.assertNotEqual(book['evidence_observations'],y['observed_days'])

    def test_a_source_without_the_window_fields_still_loads(self):
        # Older collection artifacts predate these columns. The monitor must keep
        # booking the close and report the window as unknown, never invent one.
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); rt=td/'rt'; a=td/'a.zip'; fixture(a,'2026-08-13',gate_window=False); mon.process(CONTRACT,a,rt,'100')
            b=td/'b.zip'; fixture(b,'2026-08-14',.01,gate_window=False); y=mon.process(CONTRACT,b,rt,'101')
            book=y['strategies'][STRATS[0]]
            self.assertEqual(book['evidence_window'],'')
            self.assertEqual(book['evidence_observations'],0)
            self.assertEqual(book['evidence_rejection_reasons'],'test')

    def test_the_window_fields_are_summary_only_and_never_reach_the_economics(self):
        """The reporting-only proof, stated as the invariant that actually holds.

        Whether the gate row carries the window columns must not move one economic
        figure nor the hash of the economic row. It deliberately does NOT claim the
        chain hash is unchanged: the chain binds source_zip_sha256, so a different
        source artifact is a different chain by design — that binding is the
        tamper-evidence, not a regression. What must never move is the economics.
        """
        econ_fields=['date','strategy','gross_return','trading_cost_return',
                     'funding_return','net_return','turnover','kill_switch_active',
                     'normalized_nav','drawdown','source_economic_row_sha256']
        def build(gate_window):
            td=Path(tempfile.mkdtemp()); rt=td/'rt'
            a=td/'a.zip'; fixture(a,'2026-08-13',gate_window=gate_window); mon.process(CONTRACT,a,rt,'100')
            b=td/'b.zip'; fixture(b,'2026-08-14',.01,gate_window=gate_window); mon.process(CONTRACT,b,rt,'101')
            with (rt/'DAILY_NAV.csv').open() as h:
                return [{k:r[k] for k in econ_fields} for r in csv.DictReader(h)]
        self.assertEqual(build(True),build(False))

    def test_the_summary_window_fields_are_absent_from_the_ledger_columns(self):
        # A reporting field that leaked into the append-only economic evidence
        # would be a schema change to the ledger, not a report change.
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); rt=td/'rt'; a=td/'a.zip'; fixture(a,'2026-08-13'); mon.process(CONTRACT,a,rt,'100')
            b=td/'b.zip'; fixture(b,'2026-08-14',.01); mon.process(CONTRACT,b,rt,'101')
            with (rt/'DAILY_NAV.csv').open() as h: columns=set(csv.DictReader(h).fieldnames or [])
        for leaked in ('evidence_window','evidence_observations','evidence_window_end',
                       'evidence_eligible','evidence_rejection_reasons'):
            self.assertNotIn(leaked,columns)

    def test_unsafe_source_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); x=td/'x.zip'; fixture(x,'2026-08-13',unsafe=True)
            with self.assertRaises(mon.MonitorError): mon.process(CONTRACT,x,td/'rt','1')

if __name__=='__main__':unittest.main()
