import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PATH=Path('tools/gate_btc_factory/crypto_745_basis_forward_capture.py')
spec=importlib.util.spec_from_file_location('bf',PATH)
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)


def ticker(inst,ts):
    return {'instId':inst,'bid':'99','ask':'101','ts_ms':ts}

def pair(spot_ts,perp_ts):
    return {'spot':ticker('BTC-USDT',spot_ts),'perp':ticker('BTC-USDT-SWAP',perp_ts),'captured_at_ms':max(spot_ts,perp_ts)}

class BasisForwardTests(unittest.TestCase):
    def test_normalize_funding_binds_funding_time(self):
        obj={'code':'0','data':[{'instId':'BTC-USDT-SWAP','fundingRate':'0.0001','fundingTime':'200000','nextFundingTime':'300000','ts':'100000','settState':'settled'}]}
        x=b.normalize_funding(obj)
        self.assertEqual(x['funding_time_ms'],200000)
        self.assertEqual(x['next_funding_time_ms'],300000)
        self.assertEqual(x['funding_rate'],'0.0001')

    def test_pair_requires_five_second_cross_leg_skew(self):
        self.assertTrue(b.synchronized_pair(pair(99000,99500),'at_or_before',100000))
        self.assertFalse(b.synchronized_pair(pair(93000,99500),'at_or_before',100000))

    def test_latest_predecision_never_uses_postdecision_quote(self):
        xs=[pair(98000,98100),pair(99900,99800),pair(100100,100200)]
        x=b.select_latest_predecision(xs,100000)
        self.assertEqual(x['spot']['ts_ms'],99900)

    def test_first_postclock_honors_max_delay(self):
        xs=[pair(99900,99950),pair(100100,100200),pair(106000,106100)]
        x=b.select_first_postclock(xs,100000,5000)
        self.assertEqual(x['spot']['ts_ms'],100100)
        self.assertIsNone(b.select_first_postclock([pair(106000,106100)],100000,5000))

    def test_funding_must_be_published_before_decision_and_bound_to_settlement(self):
        xs=[
            {'ts_ms':99000,'funding_time_ms':200000,'funding_rate':'0.1'},
            {'ts_ms':99900,'funding_time_ms':200000,'funding_rate':'0.2'},
            {'ts_ms':100100,'funding_time_ms':200000,'funding_rate':'0.3'},
            {'ts_ms':99950,'funding_time_ms':300000,'funding_rate':'0.4'},
        ]
        x=b.select_latest_funding_before(xs,100000,200000)
        self.assertEqual(x['funding_rate'],'0.2')

    def test_manifest_duplicates_are_zero_credit(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            base={
                'schema':'qrds.factory.crypto_745_basis_forward_attempt.v1',
                'channel_id':b.CHANNEL_ID,'economics_read':False,'attempted_window':True,
                'source_cost_evidence_sha256':'abc',
                'observation':{'observation_id':'200000','eligible_for_future_evaluation':True},
            }
            (root/'1.json').write_text(json.dumps(base))
            (root/'2.json').write_text(json.dumps(base))
            m=b.build_manifest(root)
            self.assertEqual(m['eligible_unique_observation_count'],1)
            self.assertEqual(m['duplicate_observation_ids_zero_credit'],['200000'])
            self.assertFalse(m['economics_read_allowed'])
            self.assertFalse(m['checkpoint_ready_for_dataset_binding'])

    def test_permanent_safety_locks(self):
        self.assertTrue(b.SAFETY['RESEARCH_ONLY'])
        self.assertTrue(b.SAFETY['SHADOW_ONLY'])
        self.assertTrue(b.SAFETY['NOT_APPROVED'])
        self.assertFalse(b.SAFETY['ENGINE_FEED'])
        self.assertEqual(b.SAFETY['ORDERS'],0)
        self.assertEqual(b.SAFETY['REAL_CAPITAL'],0)
        self.assertTrue(b.SAFETY['NO_BACKFILL'])
        self.assertTrue(b.SAFETY['NO_LATE_SEAL'])
        self.assertTrue(b.SAFETY['NO_COUNTER_RESET'])
        self.assertTrue(b.SAFETY['NO_RETUNE'])
        self.assertTrue(b.SAFETY['FAIL_CLOSED'])

if __name__=='__main__':unittest.main()
