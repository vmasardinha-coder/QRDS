import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PATH=Path('tools/gate_btc_factory/crypto_745_crossvenue_forward_capture.py')
spec=importlib.util.spec_from_file_location('cv',PATH)
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


def ev(ts, price='100'):
    return {'ts_ms':ts,'price':price,'trade_id':str(ts)}


def admission(path):
    obj={
        'outcomes_read':False,'economics_read':False,'evidence_sha256':'abc123',
        'channels':[{'channel_id':c.CHANNEL_ID,'adjudication_decision':'SOURCE_COST_QUALIFIED'}]
    }
    Path(path).write_text(json.dumps(obj))


class CrossVenueForwardTests(unittest.TestCase):
    def test_select_close_requires_five_second_freshness(self):
        xs=[ev(94000),ev(97000),ev(99900)]
        self.assertEqual(c.select_last_at_or_before(xs,100000)['ts_ms'],99900)
        self.assertIsNone(c.select_last_at_or_before([ev(94999)],100000))

    def test_select_entry_requires_five_second_delay(self):
        xs=[ev(104999),ev(105100),ev(109900)]
        self.assertEqual(c.select_first_at_or_after(xs,105000)['ts_ms'],105100)
        self.assertIsNone(c.select_first_at_or_after([ev(110001)],105000))

    def test_pending_and_finalize_do_not_compute_economics(self):
        prev={'boundary_ms':60000,'source_close':ev(59900),'execution_close':ev(59800)}
        cur={
            'boundary_ms':120000,'decision_ms':125000,
            'source_close':ev(119900),'execution_close':ev(119800),'entry':ev(125100),
        }
        pending=c.pending_from(prev,cur)
        self.assertEqual(pending['exit_target_ms'],185100)
        nxt={'okx_events':[ev(185200)]}
        out=c.finalize_pending(pending,nxt)
        self.assertTrue(out['eligible_for_future_evaluation'])
        self.assertNotIn('return',out)
        self.assertNotIn('pnl',out)

    def test_source_cost_admission_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a.json'
            p.write_text(json.dumps({'outcomes_read':False,'economics_read':False,'evidence_sha256':'x','channels':[]}))
            with self.assertRaisesRegex(RuntimeError,'SOURCE_COST_NOT_QUALIFIED'):
                c.qualified_source_cost(p)

    def test_manifest_counts_unique_only_and_never_allows_economics(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            base={
                'schema':'qrds.factory.crypto_745_crossvenue_forward_partition.v1',
                'channel_id':c.CHANNEL_ID,'economics_read':False,
                'source_cost_evidence_sha256':'abc123','eligible_observation_count':1,
                'observations':[{'observation_id':'120000','eligible_for_future_evaluation':True}],
            }
            (root/'1.json').write_text(json.dumps(base))
            (root/'2.json').write_text(json.dumps(base))
            m=c.build_manifest(root)
            self.assertEqual(m['eligible_unique_observation_count'],1)
            self.assertEqual(m['duplicate_observation_ids_zero_credit'],['120000'])
            self.assertFalse(m['checkpoint_ready_for_dataset_binding'])
            self.assertFalse(m['economics_read'])
            self.assertFalse(m['economics_read_allowed'])

    def test_permanent_safety_locks(self):
        self.assertTrue(c.SAFETY['RESEARCH_ONLY'])
        self.assertTrue(c.SAFETY['SHADOW_ONLY'])
        self.assertTrue(c.SAFETY['NOT_APPROVED'])
        self.assertFalse(c.SAFETY['ENGINE_FEED'])
        self.assertEqual(c.SAFETY['ORDERS'],0)
        self.assertEqual(c.SAFETY['REAL_CAPITAL'],0)
        self.assertTrue(c.SAFETY['NO_BACKFILL'])
        self.assertTrue(c.SAFETY['NO_LATE_SEAL'])
        self.assertTrue(c.SAFETY['NO_COUNTER_RESET'])
        self.assertTrue(c.SAFETY['NO_RETUNE'])
        self.assertTrue(c.SAFETY['FAIL_CLOSED'])

if __name__=='__main__':unittest.main()
