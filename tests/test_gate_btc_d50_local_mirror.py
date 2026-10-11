import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from tests.test_gate_btc_d50_mirror_reconcile import DATES, local_status, remote_status, rows_for_dates, write_csv
from tools.gate_btc_d50_local_mirror import prepare, verify_qualification
from tools.gate_btc_d50_mirror_reconcile import ReconciliationError


class LocalMirrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.local = self.root/'local'
        self.qual = self.root/'qualification'
        self.runtime = self.root/'runtime'
        s = {**local_status(), 'next_checkpoint': 30, 'source_hashes': {'ohlc':'a'*64,'funding':'b'*64}}
        self.write(self.local/'state/D50_PROSPECTIVE_STATUS_V2.json', s)
        write_csv(self.local/'state/d50_prospective_observations_v2.csv', rows_for_dates(DATES))
        r = remote_status()
        r['prospective_immutable_ledger'].update(status='ACTIVE',source_revision_only=False)
        self.write(self.runtime/'ledgers/d50/STATUS.json', r)
        self.write(self.runtime/'GATE_BTC_MEASUREMENT_STATUS.json', {**{k:r[k] for k in ('research_only','shadow_only','not_approved','orders_generated','real_capital_used')}, 'other_track':{'current':123}})
        previous = None
        hashes=[]
        for day in DATES:
            cutoff=day+'T20:10:00Z'
            s={'schema':'gate_btc.prospective_snapshot.v1','snapshot_id':day,'candidate':'D50',
               'previous_snapshot_sha256':previous,'WINDOW_MAY_START':False,'CAPITAL_REAL_ALLOWED':False,
               'qualification_pass':True,'synchronized_failure':False,'coverage_pct':1,'fresh_count':1,
               'universe_size':1,'decision_cutoff_utc':cutoff,
               'observations':[{'symbol':'BTC','date':day,'eligible':True,'fresh':True,'present':True,
                                'available_at_utc':day+'T20:05:00Z','decision_cutoff_utc':cutoff}]}
            previous=hashlib.sha256(json.dumps(s,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
            s['snapshot_sha256']=previous;hashes.append(previous)
            self.write(self.qual/'snapshots'/day/'snapshot.json', s)
        self.write(self.qual/'qualification_status.json', {'schema':'gate_btc.qualification_certificate.v1',
            'candidate':'D50','WINDOW_MAY_START':False,'CAPITAL_REAL_ALLOWED':False,'snapshot_count_total':7,
            'hash_chain_valid':True,'qualified':True,'latest_consecutive_pass_count':7,
            'required_consecutive_pass_count':7,'qualified_snapshot_ids':DATES,'qualified_snapshot_hashes':hashes})

    def write(self, path, obj):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj))

    def prepare(self):
        return prepare(self.local,self.qual,self.runtime,date(2026,8,9))

    def test_catchup_mirrors_existing_ledger_without_inventing_daily_appends(self):
        before={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        mirror, measurement, audit=self.prepare()
        self.assertEqual(mirror['prospective_immutable_ledger']['current'],7)
        self.assertEqual(mirror['prospective_immutable_ledger']['target'],30)
        self.assertEqual(measurement['other_track'],{'current':123})
        self.assertEqual(mirror['data_qualification']['current'],7)
        self.assertFalse(mirror['data_qualification']['WINDOW_MAY_START'])
        self.assertEqual(mirror['mirror_alignment']['economic_rows_mutated'],0)
        self.assertEqual(before,{p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.write(self.runtime/'ledgers/d50/STATUS.json',mirror)
        self.assertEqual(self.prepare()[0]['prospective_immutable_ledger']['current'],7)

    def test_stale_local_receipt_is_rejected(self):
        with self.assertRaisesRegex(ReconciliationError,'stale or future'):
            prepare(self.local,self.qual,self.runtime,date(2026,8,10))

    def test_modified_snapshot_is_rejected(self):
        p=self.qual/'snapshots'/DATES[-1]/'snapshot.json';s=json.loads(p.read_text());s['coverage_pct']=0
        self.write(p,s)
        with self.assertRaisesRegex(ReconciliationError,'hash chain'):self.prepare()

    def test_forged_certificate_counter_is_rejected(self):
        p=self.qual/'qualification_status.json';s=json.loads(p.read_text());s['latest_consecutive_pass_count']=99;self.write(p,s)
        with self.assertRaisesRegex(ReconciliationError,'streak'):self.prepare()

    def test_certificate_cannot_open_the_window(self):
        p=self.qual/'qualification_status.json';s=json.loads(p.read_text());s['WINDOW_MAY_START']=True;self.write(p,s)
        with self.assertRaisesRegex(ReconciliationError,'authority'):self.prepare()

    def test_duplicate_economic_row_is_rejected(self):
        rows=rows_for_dates(DATES);rows.append(rows[-1]);write_csv(self.local/'state/d50_prospective_observations_v2.csv',rows)
        with self.assertRaisesRegex(ReconciliationError,'duplicate'):self.prepare()

    def test_qualification_date_must_match_economic_date(self):
        with self.assertRaisesRegex(ReconciliationError,'dates differ'):
            verify_qualification(self.qual,'2026-08-07')

    def test_checkpoint_cannot_regress(self):
        p=self.local/'state/D50_PROSPECTIVE_STATUS_V2.json';s=json.loads(p.read_text());s['next_checkpoint']=6;self.write(p,s)
        with self.assertRaisesRegex(ReconciliationError,'checkpoint'):self.prepare()
