import copy,csv,hashlib,io,unittest,zipfile
from dataclasses import replace
import test_gate_btc_dynamics_target_intake as fixtures
from tools import gate_btc_dynamics_source_costs as cost
from tools import gate_btc_dynamics_spot_accounting as book

class SourceCostsTests(unittest.TestCase):
    script='EST_FEE_BPS_PER_SIDE = 6.0\nEST_SLIPPAGE_BPS_PER_SIDE = 8.0\nEST_SHORT_FUNDING_BPS_PER_DAY = 1.5\nraise RuntimeError("NEVER EXECUTE ARCHIVE PYTHON")\n'
    def archive(self,script=None):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:z.writestr(cost.SCRIPT,script or self.script)
        return out.getvalue()
    def prepare(self,change=None):
        helper=fixtures.TargetIntakeTests();s,files,p=helper.source()
        reader=csv.DictReader(io.StringIO(files['strategy_execution_profiles.csv'].decode()))
        fields=list(reader.fieldnames)+['estimated_daily_turnover','estimated_trading_cost_bps_per_day',
            'estimated_short_funding_bps_per_day','estimated_total_drag_bps_per_day',
            'stop_rules_backtested','walk_forward_backtested']
        rows=list(reader)
        for r in rows:r.update(estimated_daily_turnover='.05',estimated_trading_cost_bps_per_day='1.4000000000000001',
            estimated_short_funding_bps_per_day='0',estimated_total_drag_bps_per_day='1.4000000000000001',
            stop_rules_backtested='False',walk_forward_backtested='False')
        if change:change(rows)
        out=io.StringIO();w=csv.DictWriter(out,fields);w.writeheader();w.writerows(rows)
        raw=out.getvalue().encode();files['strategy_execution_profiles.csv']=raw;helper.rehash(s,files)
        return helper.admit(s,files,p),raw
    def run_audit(self,script=None,change=None):
        admission,raw=self.prepare(change);archive=self.archive(script)
        return cost.audit_costs(archive,hashlib.sha256(archive).hexdigest(),raw,admission)
    def instruments(self):
        return (book.SpotInstrument('AAA','BINANCE:SPOT:AAAUSDT','BINANCE','AAAUSDT','USDT','1','0','0'),)
    def test_extract_without_executing_and_separate_daily_drag_from_fill_rates(self):
        out=self.run_audit()
        self.assertEqual(len(out['profiles']),3)
        q=out['profiles']['QOS_Base'];self.assertEqual(q['fee_bps_per_side'],'6.0')
        self.assertEqual(q['slippage_bps_per_side'],'8.0')
        self.assertEqual(q['estimated_daily_trading_drag_bps'],'1.4000000000000001')
        self.assertFalse(out['production_activation']);self.assertFalse(out['executable_calendar_defined'])
        self.assertEqual(out['orders'],0)
    def test_binds_new_inactive_instruments_without_mutating_input(self):
        original=self.instruments();new=cost.bind_cost_assumptions(original,self.run_audit(),'QOS_Base')
        self.assertEqual((new[0].fee_bps_per_side,new[0].slippage_bps_per_side),('6.0','8.0'))
        self.assertEqual(original[0].fee_bps_per_side,'0')
    def test_wrong_archive_digest_rejected(self):
        admission,raw=self.prepare()
        with self.assertRaisesRegex(ValueError,'archive hash mismatch'):
            cost.audit_costs(self.archive(),'a'*64,raw,admission)
    def test_changed_csv_or_admission_rejected(self):
        admission,raw=self.prepare();z=self.archive();sha=hashlib.sha256(z).hexdigest()
        with self.assertRaisesRegex(ValueError,'not the admitted source'):cost.audit_costs(z,sha,raw+b'\n',admission)
        admission['profiles']['QOS_Base']['spot_target_weights']['CASH']='0'
        with self.assertRaisesRegex(ValueError,'admission changed'):cost.audit_costs(z,sha,raw,admission)
    def test_missing_duplicate_computed_or_invalid_constant_blocks(self):
        for script in [self.script.replace('EST_FEE_BPS_PER_SIDE = 6.0\n',''),
            self.script+'EST_FEE_BPS_PER_SIDE = 7\n',self.script.replace('= 6.0','= 3 + 3'),
            self.script.replace('= 6.0','= True'),self.script.replace('= 6.0','= 10000')]:
            with self.assertRaises(ValueError):self.run_audit(script=script)
    def test_daily_drag_or_spot_funding_cannot_be_silently_reinterpreted(self):
        for field,value in [('estimated_trading_cost_bps_per_day','6'),
            ('estimated_short_funding_bps_per_day','1'),('estimated_total_drag_bps_per_day','0')]:
            def change(rows):
                next(r for r in rows if r['strategy']=='QOS_Base')[field]=value
            with self.assertRaisesRegex(ValueError,'does not reconcile'):self.run_audit(change=change)
    def test_invalid_turnover_blocks(self):
        for v in ['NaN','-0.1','1.1']:
            def change(rows):next(r for r in rows if r['strategy']=='QOS_Base')['estimated_daily_turnover']=v
            with self.assertRaises(ValueError):self.run_audit(change=change)
    def test_backtest_claim_requires_new_review(self):
        def change(rows):next(r for r in rows if r['strategy']=='QOS_Base')['stop_rules_backtested']='True'
        with self.assertRaisesRegex(ValueError,'backtest claim'):self.run_audit(change=change)
    def test_seal_corruption_blocks_binding(self):
        audit=self.run_audit();audit['profiles']['QOS_Base']['fee_bps_per_side']='0'
        with self.assertRaisesRegex(ValueError,'audit changed'):
            cost.bind_cost_assumptions(self.instruments(),audit,'QOS_Base')
    def test_no_derivative_or_ambiguous_currency_binding(self):
        audit=self.run_audit()
        with self.assertRaisesRegex(ValueError,'three admitted'):
            cost.bind_cost_assumptions(self.instruments(),audit,'Delta_LS_50_50')
        for change in [dict(quote_currency='USD'),dict(venue='OTHER'),dict(instrument_type='SWAP'),
                       dict(exact_identity='TICKER_ONLY')]:
            with self.assertRaises(ValueError):
                cost.bind_cost_assumptions((replace(self.instruments()[0],**change),),audit,'QOS_Base')
    def test_duplicate_or_empty_bindings_block(self):
        for instruments in [(),self.instruments()*2]:
            with self.assertRaises(ValueError):cost.bind_cost_assumptions(instruments,self.run_audit(),'QOS_Base')

if __name__=='__main__':unittest.main()
