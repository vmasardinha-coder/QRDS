import importlib.util,json,unittest
from pathlib import Path
from unittest.mock import patch

M=Path('tools/gate_btc_factory/grammar_008_industrial_evaluator.py')
spec=importlib.util.spec_from_file_location('g008eval',M);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
PR=json.loads(Path('tools/gate_btc_factory/GRAMMAR_008_FREQTRADE_INDUSTRIAL_PREREG_20260921.json').read_text())
SE=json.loads(Path('tools/gate_btc_factory/GRAMMAR_008_INDICATOR_SEMANTICS_20260921.json').read_text())

def dummy_fetch(calls):
    def f(product,start,end):
        calls.append((product,start,end))
        return [{'time':t,'open':100.0,'high':101.0,'low':99.0,'close':100.0,'volume':1.0} for t in range(start,end,m.HOUR)]
    return f

def fake_bt(_bars,spec,_prereg,_start,_end):
    return {'started':True,'ineligible':not spec['executable'],'reason':'PREREG_UNDERSPECIFIED_FAIL_CLOSED' if not spec['executable'] else None,'trades':[],'candidate_id':spec['candidate_id']}

class Grammar008EvaluatorTests(unittest.TestCase):
    def test_registered_and_executable_counts(self):
        xs=m.candidate_specs(PR,SE)
        self.assertEqual(len(xs),24);self.assertEqual(sum(x['executable'] for x in xs),22)
        self.assertEqual(sum(not x['executable'] for x in xs),2)
    def test_discovery_failure_never_fetches_validation_or_holdout(self):
        calls=[]
        def met(bt,_minimum): return {'started':True,'pass':False,'n':20,'effect':-0.1,'mean_net_primary':-0.001,'mean_net_stress':-0.002}
        with patch.object(m,'backtest_partition',fake_bt),patch.object(m,'metrics',met):
            r=m.execute(PR,SE,dummy_fetch(calls))
        self.assertEqual(len(calls),2);self.assertFalse(r['validation_source_opened']);self.assertFalse(r['holdout_source_opened']);self.assertEqual(r['historical_survivor_count'],0)
    def test_validation_failure_opens_only_one_validation_asset(self):
        calls=[];first='G008_BAND_MEAN_REVERSION::BB20_W2_0::BTC-USD'
        phase={}
        def met(bt,_minimum):
            cid=bt['candidate_id'];n=phase.get(cid,0);phase[cid]=n+1
            if cid==first and n==0:return {'started':True,'pass':True,'n':30,'effect':0.2,'mean_net_primary':0.01,'mean_net_stress':0.005}
            return {'started':True,'pass':False,'n':15,'effect':-0.1,'mean_net_primary':-0.01,'mean_net_stress':-0.02}
        with patch.object(m,'backtest_partition',fake_bt),patch.object(m,'metrics',met): r=m.execute(PR,SE,dummy_fetch(calls))
        self.assertEqual(len(calls),3);self.assertTrue(r['validation_source_opened']);self.assertFalse(r['holdout_source_opened']);self.assertEqual(r['validation_pass_count'],0)
    def test_holdout_fetched_only_after_validation_pass(self):
        calls=[];first='G008_BAND_MEAN_REVERSION::BB20_W2_0::BTC-USD';phase={}
        def met(bt,_minimum):
            cid=bt['candidate_id'];n=phase.get(cid,0);phase[cid]=n+1
            if cid==first:return {'started':True,'pass':True,'n':30,'effect':0.2,'mean_net_primary':0.01,'mean_net_stress':0.005}
            return {'started':True,'pass':False,'n':20,'effect':-0.1,'mean_net_primary':-0.01,'mean_net_stress':-0.02}
        with patch.object(m,'backtest_partition',fake_bt),patch.object(m,'metrics',met): r=m.execute(PR,SE,dummy_fetch(calls))
        self.assertEqual(len(calls),4);self.assertTrue(r['validation_source_opened']);self.assertTrue(r['holdout_source_opened']);self.assertEqual(r['historical_survivors'],[first])
    def test_math_primitives(self):
        self.assertEqual(m.sma([1,2,3],2),[None,1.5,2.5])
        self.assertAlmostEqual(m.popsd([1,3],2)[1],1.0)
        self.assertEqual(m.rsi_wilder([1]*20,14)[14],50.0)

if __name__=='__main__': unittest.main()
