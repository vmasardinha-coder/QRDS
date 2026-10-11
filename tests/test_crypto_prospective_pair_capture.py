import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

CAPTURE_PATH=Path('tools/gate_btc_factory/crypto_forward_public_capture.py')
EVAL_PATH=Path('tools/gate_btc_factory/crypto_accessible_blind_evaluator.py')

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

c=load_module('crypto_capture',CAPTURE_PATH)
e=load_module('crypto_eval',EVAL_PATH)

def packet(t):
    records=[]
    for asset in ('BTC','ETH'):
        for market in ('SPOT','PERPETUAL'):
            records.append({'venue':'OKX','asset':asset,'market':market,'bar':{'start_ms':t,'open':'100','high':'101','low':'99','close':'100','volume':'1'}})
        records.append({'venue':'OKX','asset':asset,'market':'FUNDING','funding_rate':'0.0001'})
        records.append({'venue':'COINBASE','asset':asset,'market':'SPOT','bar':{'start_s':t//1000,'open':'100','high':'101','low':'99','close':'100','volume':'1'}})
    return {'captured_at_utc':'2026-09-21T12:00:00Z','records':records,'scientific_credit':0,'historical_backfill_credit':0,'economics_feedback_allowed':False,'safety':{'ORDERS':0,'REAL_CAPITAL':0}}

class PairCaptureTests(unittest.TestCase):
    def test_exact_next_bucket_pair_is_sealed(self):
        xs=[packet(1000000),packet(1000000),packet(1300000)]
        def cap(): return xs.pop(0)
        p0,p1=c.capture_prospective_pair(capture_fn=cap,sleep_fn=lambda _:None,max_wait_seconds=60,poll_seconds=0)
        self.assertEqual(c.accessible_bucket_start_ms(p1)-c.accessible_bucket_start_ms(p0),300000)
        self.assertEqual(p0['prospective_pair']['pair_id'],p1['prospective_pair']['pair_id'])
        self.assertEqual(p0['prospective_pair']['role'],'SIGNAL_T')
        self.assertEqual(p1['prospective_pair']['role'],'OUTCOME_T_PLUS_1')
        self.assertFalse(p0['prospective_pair']['retroactive_pairing_allowed'])

    def test_skipped_next_bucket_fails_closed(self):
        xs=[packet(1000000),packet(1600000)]
        with self.assertRaisesRegex(RuntimeError,'EXACT_NEXT_BUCKET_MISSED_FAIL_CLOSED'):
            c.capture_prospective_pair(capture_fn=lambda:xs.pop(0),sleep_fn=lambda _:None,max_wait_seconds=60,poll_seconds=0)

    def test_evaluator_ignores_legacy_snapshots_and_accepts_sealed_pair(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            legacy=packet(700000);legacy['captured_at_utc']='2026-09-21T12:00:00Z'
            (root/'legacy.json').write_text(json.dumps(legacy))
            p0=packet(1000000);p1=packet(1300000)
            pair_id='PAIR-1'
            c.stamp_pair(p0,pair_id,'SIGNAL_T',1000000);c.stamp_pair(p1,pair_id,'OUTCOME_T_PLUS_1',1000000)
            p0['captured_at_utc']='2026-09-21T12:01:00Z';p1['captured_at_utc']='2026-09-21T12:06:00Z'
            (root/'t.json').write_text(json.dumps(p0));(root/'t1.json').write_text(json.dumps(p1))
            pairs,ignored=e.sealed_pairs(root,'2026-09-21T00:00:00Z')
            self.assertEqual(len(pairs),1);self.assertEqual(ignored,1)
            self.assertEqual(pairs[0][1],pair_id)

if __name__=='__main__': unittest.main()
