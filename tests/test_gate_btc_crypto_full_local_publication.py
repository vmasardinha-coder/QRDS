import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tools.gate_btc_factory.crypto_full_local_publication import append_packet, refresh
from tests.test_gate_btc_crypto_full_source_admission import packet, seal

class FullLocalPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.bucket=int(datetime.now(timezone.utc).timestamp()//300)*300000-600000
        self.now=datetime.fromtimestamp((self.bucket+420000)/1000, timezone.utc)
        for name in ('LATEST.json','ACCESSIBLE_SOURCE_ADMISSION.json','ACCESSIBLE_BLIND_LEDGER.json'):
            (self.root/name).write_text('{"protected":"accessible"}\n')
        (self.root/'audits').mkdir()
        (self.root/'audits'/'hosted.json').write_text('{"status":"INCOMPLETE_FAIL_CLOSED"}')
        self.protected={p:p.read_bytes() for p in self.root.glob('*.json')}
        self.protected.update({p:p.read_bytes() for p in (self.root/'audits').glob('*.json')})

    def live(self, bucket):
        p=packet(bucket)
        p.update(capture_profile='full-source-contract',frozen_capture_delay_seconds=120)
        return seal(p)

    def three(self):
        for i in range(3):
            p=self.live(self.bucket+(i-2)*300000)
            captured=datetime.fromisoformat(p['captured_at_utc'])
            append_packet(self.root,p,now=captured)
        return refresh(self.root,now=self.now)

    def test_live_continuity_admits_only_source_and_preserves_accessible(self):
        result=self.three()
        self.assertTrue(result['source_admitted_forward_only'])
        self.assertEqual(result['complete_consecutive_streak'],3)
        self.assertEqual(result['source_route'],'WINDOWS_LOCAL_FULL_CONTRACT')
        self.assertEqual(result['economic_rows_appended'],0)
        self.assertFalse(result['engine_feed'])
        self.assertEqual(self.protected,{p:p.read_bytes() for p in self.protected})
        self.assertEqual(len(result['contract_semantic_sha256']),64)

    def test_hosted_partial_cannot_override_local_authority(self):
        self.three()
        (self.root/'audits'/'new-hosted.json').write_text('{"status":"INCOMPLETE_FAIL_CLOSED"}')
        self.assertTrue(refresh(self.root,now=self.now)['source_admitted_forward_only'])

    def test_stale_route_does_not_fallback_to_other_frontier(self):
        self.three()
        r=refresh(self.root,now=self.now+timedelta(seconds=601))
        self.assertTrue(r['source_qualification_admitted'])
        self.assertFalse(r['delivery_fresh'])
        self.assertFalse(r['source_admitted_forward_only'])
        self.assertEqual(r['family_state'],'WAITING_SOURCE')
        self.assertEqual(r['source_route'],'WINDOWS_LOCAL_FULL_CONTRACT')

    def test_duplicate_replay_is_idempotent_and_not_a_new_bucket(self):
        p=self.live(self.bucket)
        a=append_packet(self.root,p,now=self.now)
        b=append_packet(self.root,p,now=self.now)
        self.assertEqual(a,b)
        self.assertEqual(len(list(a.parent.glob('*.json'))),1)
        self.assertFalse(refresh(self.root,now=self.now)['source_admitted_forward_only'])

    def test_latest_incomplete_and_corrupt_packets_fail_closed(self):
        self.three()
        p=self.live(self.bucket+300000)
        p['status']='INCOMPLETE_FAIL_CLOSED'
        append_packet(self.root,seal(p),now=self.now+timedelta(seconds=300))
        self.assertFalse(refresh(self.root,now=self.now+timedelta(seconds=300))['source_admitted_forward_only'])
        (self.root/'full_local'/'audits'/'broken.json').write_text('[]')
        self.assertFalse(refresh(self.root,now=self.now+timedelta(seconds=300))['source_admitted_forward_only'])

    def test_old_qualification_default_profile_or_wrong_hash_cannot_be_imported(self):
        p=self.live(self.bucket)
        with self.assertRaises(ValueError):append_packet(self.root,p,now=self.now+timedelta(seconds=601))
        with self.assertRaises(ValueError):append_packet(self.root,packet(self.bucket),now=self.now)
        p['records'][0]['symbol']='OTHER'
        with self.assertRaises(ValueError):append_packet(self.root,p,now=self.now)

    def test_unconfigured_runtime_retains_hosted_gate(self):
        result=refresh(self.root,now=self.now)
        self.assertEqual(result['source_route'],'GITHUB_HOSTED_PUBLIC')
        self.assertFalse(result['source_admitted_forward_only'])

if __name__=='__main__':unittest.main()
