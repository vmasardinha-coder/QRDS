import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

PATH=Path('tools/gate_btc_factory/crypto_745_basis_forward_capture.py')
spec=importlib.util.spec_from_file_location('bf',PATH)
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)


def ticker(inst,ts):
    return {'instId':inst,'bid':'99','ask':'101','ts_ms':ts}

def pair(spot_ts,perp_ts):
    return {'spot':ticker('BTC-USDT',spot_ts),'perp':ticker('BTC-USDT-SWAP',perp_ts),'captured_at_ms':max(spot_ts,perp_ts)}

class BasisForwardTests(unittest.TestCase):
    def simulated_attempt(self, now_ms, max_wait_seconds):
        settlement = 2000000
        clock = [now_ms / 1000]
        def sleep(seconds):
            clock[0] += seconds
        def funding():
            return b'funding', {
                'funding_time_ms': settlement,
                'ts_ms': int(clock[0] * 1000),
                'funding_rate': '0.0001',
            }
        def quote_pair():
            stamp = int(clock[0] * 1000)
            return pair(stamp, stamp)
        with patch.object(b, 'qualified_source_cost', return_value=({}, 'sealed-source')), \
             patch.object(b, 'fetch_funding', side_effect=funding), \
             patch.object(b, 'fetch_quote_pair', side_effect=quote_pair) as quotes, \
             patch.object(b.time, 'time', side_effect=lambda: clock[0]), \
             patch.object(b.time, 'sleep', side_effect=sleep):
            out = b.capture_attempt(Path('unused-admission'), max_wait_seconds, 0.5)
            return out, quotes.call_count

    def test_operational_runway_arms_future_window_without_moving_clocks(self):
        # Equivalent to starting at 07:40 for an 08:00 settlement.
        out, calls = self.simulated_attempt(800000, 1800)
        self.assertEqual(out['status'], 'SEALED_ELIGIBLE_OBSERVATION')
        self.assertTrue(out['attempted_window'])
        self.assertGreater(calls, 0)
        self.assertEqual(out['decision_ms'], 1700000)
        self.assertEqual(out['settlement_ms'], 2000000)
        self.assertLessEqual(out['observation']['predecision_pair']['spot']['ts_ms'], 1700000)
        self.assertGreaterEqual(out['observation']['entry_pair']['spot']['ts_ms'], 1700000)
        self.assertGreaterEqual(out['observation']['exit_pair']['spot']['ts_ms'], 2000000)
        self.assertLessEqual(out['observation']['exit_pair']['spot']['ts_ms'], 2060000)
        self.assertFalse(out['economics_read'])
        self.assertEqual(out['scientific_credit'], 0)

    def test_original_short_runway_returns_waiting_without_capture(self):
        out, calls = self.simulated_attempt(800000, 420)
        self.assertEqual(out['status'], 'WAITING_FUTURE_DECISION_WINDOW')
        self.assertFalse(out['attempted_window'])
        self.assertEqual(calls, 0)

    def test_longer_wait_never_reconstructs_missed_predecision(self):
        out, calls = self.simulated_attempt(1702000, 1800)
        self.assertEqual(out['status'], 'MISSED_PREDECISION_WINDOW_ZERO_CREDIT')
        self.assertFalse(out['attempted_window'])
        self.assertEqual(out['eligible_observation_count'], 0)
        self.assertEqual(calls, 0)

    def test_longer_wait_does_not_reinterpret_past_funding_time(self):
        out, calls = self.simulated_attempt(2001000, 1800)
        self.assertEqual(out['status'], 'NONFUTURE_FUNDING_TIME_FAIL_CLOSED')
        self.assertFalse(out['attempted_window'])
        self.assertEqual(out['eligible_observation_count'], 0)
        self.assertEqual(calls, 0)

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

