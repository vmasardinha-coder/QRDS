"""A capture batch must never skip or enlarge a preregistered checkpoint."""
import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).resolve().parents[1]/'tools/gate_btc_factory/crypto_accessible_blind_evaluator.py'
S=importlib.util.spec_from_file_location('blind_checkpoint_reporting',P)
m=importlib.util.module_from_spec(S); S.loader.exec_module(m)


def rows(count):
    return [{'family_id':'COKBF01','signal_bucket_start_ms':i*300000,
             'net_return_primary':((i%3)-1)/10000} for i in range(count)]


class CheckpointReportingTests(unittest.TestCase):
    def test_59_remains_blind(self):
        self.assertEqual(m.completed_checkpoints(rows(59)),({},{}))

    def test_crossing_60_reports_exact_first_60_without_tail(self):
        prefix=rows(60)
        latest,history=m.completed_checkpoints(prefix+[{'family_id':'COKBF01','net_return_primary':1000}])
        original,_=m.completed_checkpoints(prefix)
        self.assertEqual(latest,original)
        self.assertEqual(list(history['COKBF01']),['60'])
        self.assertEqual(latest['COKBF01']['checkpoint'],60)

    def test_batch_crosses_multiple_checkpoints_and_preserves_each_prefix(self):
        latest,history=m.completed_checkpoints(rows(122))
        self.assertEqual(list(history['COKBF01']),['60','120'])
        self.assertEqual(latest['COKBF01']['checkpoint'],120)
        at_60,_=m.completed_checkpoints(rows(60))
        self.assertEqual(history['COKBF01']['60'],at_60['COKBF01'])
        self.assertEqual(m.completed_checkpoints(rows(122)),(latest,history))

    def test_families_have_independent_thresholds(self):
        observations=rows(61)+[{**r,'family_id':'COCV02'} for r in rows(59)]
        latest,history=m.completed_checkpoints(observations)
        self.assertEqual(set(latest),{'COKBF01'})
        self.assertNotIn('COCV02',history)


if __name__=='__main__': unittest.main()
