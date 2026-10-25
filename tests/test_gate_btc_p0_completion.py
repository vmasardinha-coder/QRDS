import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('p0', ROOT / 'tools/gate_btc_p0_completion.py')
p0 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p0)

class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def h31(self):
        spool, target = self.root / 'spool', self.root / 'target'
        event = {'schema': 'gate_btc.b3.h31.intraday_shadow_event.v1', 'session': '2026-10-23',
                 'event_type': 'PAPER_CLOSE', 'ORDERS': 0, 'REAL_CAPITAL': 0, 'ENGINE_FEED': False,
                 'SHADOW_CREDIT_TO_CANONICAL': 0}
        event['event_hash_sha256'] = p0.sha(p0.canonical(event))
        path = spool / 'intraday_events/2026-10-23' / (event['event_hash_sha256'] + '.json')
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(event))
        status = {'schema': 'gate_btc.b3.h31.intraday_shadow_status.v1', 'H31_INTRADAY_SESSION': '2026-10-23',
                  'updated_at': '2026-10-23T11:39:00-03:00', 'ORDERS': 0, 'REAL_CAPITAL': 0,
                  'ENGINE_FEED': False, 'SHADOW_CREDIT_TO_CANONICAL': 0, 'CANONICAL_COUNTER_CHANGED': False,
                  'H31_SHADOW_SESSIONS': 31, 'H31_SHADOW_TRIGGERED_SESSIONS': 9,
                  'H31_SHADOW_CLOSED_TRADES': 8, 'H31_PAPER_POSITION': 'CLOSED'}
        (spool / 'INTRADAY_STATUS.json').write_text(json.dumps(status))
        return spool, target, path

    def test_append_idempotent_and_canonical_untouched(self):
        spool, target, path = self.h31()
        canonical = self.root / 'canonical.json'; canonical.write_bytes(b'unchanged')
        self.assertEqual(p0.publish_h31(spool, target)['events_added'], 1)
        self.assertEqual(p0.publish_h31(spool, target)['events_added'], 0)
        self.assertEqual(canonical.read_bytes(), b'unchanged')
        self.assertEqual((target / 'intraday_events/2026-10-23' / path.name).read_bytes(), path.read_bytes())

    def test_corrupt_event_rejected_before_write(self):
        spool, target, path = self.h31()
        d=p0.read(path); d['side']=1; path.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError, 'EVENT_HASH'):p0.publish_h31(spool,target)
        self.assertFalse(target.exists())

    def test_conflict_rejected_without_overwrite(self):
        spool,target,path=self.h31(); p0.publish_h31(spool,target)
        dest=target/'intraday_events/2026-10-23'/path.name;dest.write_text('{}')
        with self.assertRaisesRegex(ValueError,'CONFLICT'):p0.publish_h31(spool,target)
        self.assertEqual(dest.read_text(),'{}')

    def crypto(self, count=1440):
        root=self.root/'crypto/forward/cross_venue';parts=root/'partitions';parts.mkdir(parents=True)
        admission={'channels':[{'channel_id':'CRYPTO_CROSS_VENUE_PRICE_DISCOVERY','adjudication_decision':'SOURCE_COST_QUALIFIED'}],
                   'outcomes_read':False,'economics_read':False,'evidence_sha256':'a'*64}
        (root.parent.parent/'SOURCE_COST.json').write_text(json.dumps(admission))
        part={'schema':'qrds.factory.crypto_745_crossvenue_forward_partition.v2',
              'channel_id':'CRYPTO_CROSS_VENUE_PRICE_DISCOVERY','economics_read':False,
              'history_endpoint_used':False,'source_cost_evidence_sha256':'a'*64,
              'eligible_observation_count':count,
              'observations':[{'observation_id':str(1790023140000+i*60000),'eligible_for_future_evaluation':True} for i in range(count)]}
        (parts/'1.json').write_text(json.dumps(part))
        code=ROOT/'tools/gate_btc_factory/crypto_745_crossvenue_forward_capture.py'
        spec=importlib.util.spec_from_file_location('capture',code);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        (root/'MANIFEST.json').write_text(json.dumps(m.build_manifest(parts)))
        prereg=ROOT/'tools/gate_btc_factory/crypto_challenger_prereg/CRYPTO_CROSS_VENUE_PRICE_DISCOVERY_PREREG.v1.json'
        return root,prereg,code

    def test_checkpoint_binds_without_economics_and_is_idempotent(self):
        args=self.crypto(); r=p0.freeze_crossvenue(*args);self.assertEqual(r['status'],'BLINDED_DATASET_BOUND')
        out=args[0]/'DATASET_BINDING_N1440.json';before=out.read_bytes()
        self.assertFalse(p0.read(out)['economics_read'])
        self.assertEqual(p0.freeze_crossvenue(*args)['status'],'FROZEN_BINDING_PRESERVED')
        self.assertEqual(before,out.read_bytes())

    def test_no_early_binding(self):
        args=self.crypto(1439);self.assertEqual(p0.freeze_crossvenue(*args)['status'],'WAITING_CHECKPOINT')
        self.assertFalse((args[0]/'DATASET_BINDING_N1440.json').exists())

    def test_bound_partition_tampering_fails(self):
        args=self.crypto();p0.freeze_crossvenue(*args)
        (args[0]/'partitions/1.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'FROZEN_PARTITION_CHANGED'):p0.freeze_crossvenue(*args)

    def test_manifest_mismatch_fails(self):
        args=self.crypto();(args[0]/'MANIFEST.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'PUBLISHED_MANIFEST_MISMATCH'):p0.freeze_crossvenue(*args)

if __name__=='__main__':unittest.main()
