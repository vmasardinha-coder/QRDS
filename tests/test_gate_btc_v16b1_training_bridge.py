import copy
import csv
import io
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tools import gate_btc_v16b1_training_bridge as b
from tools.gate_btc_v16b_signal_source import load_historical_universe


class TrainingBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.output = self.root/'derived.csv'
        self.first = date(2026, 10, 8)

    def encoded(self, o): return (json.dumps(o, sort_keys=True)+'\n').encode()

    def csv_bytes(self, records):
        buf = io.StringIO(newline=''); w = csv.DictWriter(buf, fieldnames=list(records[0]), lineterminator='\n')
        w.writeheader(); w.writerows(records); return buf.getvalue().encode()

    def week(self, day=None, mature=True, mutate=None):
        day = day or self.first; d = self.root/b.BASE/day.isoformat(); d.mkdir(parents=True)
        records = [{'signal_date':day.isoformat(), 'symbol':'TEST'+str(i)+'USDT',
            'evidence_class':'CURRENT_PROSPECTIVE_PIT', 'snapshot_effective_date':day.isoformat(),
            'retrieved_at_utc':day.isoformat()+'T12:00:00Z', 'universe_source_ref':'official-captured-snapshot',
            'universe_snapshot_sha256':'a'*64, **{k:1.0 for k in b.FEATURES}, 'feature_ok':True}
            for i in range(20)]
        if mutate: mutate(records)
        raw = self.csv_bytes(records); excluded = b'symbol,reason,missing_features\n'
        labels = self.csv_bytes([{'symbol':r['symbol'],'fwd_ret':i/100} for i,r in enumerate(records)])
        meta = {'signal_date':day.isoformat(), 'entry_date':(day+timedelta(days=1)).isoformat(),
            'exit_date':(day+timedelta(days=8)).isoformat(), 'features_sha256':b.sha(raw),
            'exclusions_sha256':b.sha(excluded), 'eligible_feature_rows':len(records),
            'label_status':'PENDING_FROZEN_EXIT', 'RESEARCH_ONLY':True, 'SHADOW_ONLY':True,
            'NOT_APPROVED':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0,
            'NO_BACKFILL':True,'NO_RETUNE':True,'scientific_credit':0}
        week_raw = self.encoded(meta)
        evidence = {'week_sha256':b.sha(week_raw), 'features_sha256':b.sha(raw),
            'labels_sha256':b.sha(labels),'signal_date':day.isoformat(),
            'source':'BINANCE_SPOT_DAILY_KLINE_DATA_VISION_CHECKSUM'}
        evidence_raw = self.encoded(evidence)
        files = {'FEATURES.csv':raw,'EXCLUSIONS.csv':excluded,'WEEK.json':week_raw,
                 'LABELS.csv':labels,'LABEL_EVIDENCE.json':evidence_raw}
        if mature:
            files['MATURED.json'] = self.encoded({**meta,'label_status':'SEALED_AFTER_FROZEN_EXIT',
                'labels_sha256':b.sha(labels),'label_evidence_sha256':b.sha(evidence_raw)})
        for name, content in files.items(): (d/name).write_bytes(content)
        return d

    def run_bridge(self, target='2026-10-22', now=None):
        return b.prepare(self.root,target,self.output,now or datetime(2028,1,1,tzinfo=timezone.utc))

    def test_one_matured_week_waits_without_creating_training_input_or_mutating_source(self):
        d = self.week(); before = {p.name:p.read_bytes() for p in d.iterdir()}
        result = self.run_bridge()
        self.assertEqual(result['matured_prior_weeks'],1)
        self.assertEqual(result['remaining_prior_weeks'],51)
        self.assertFalse(self.output.exists())
        self.assertEqual(before,{p.name:p.read_bytes() for p in d.iterdir()})

    def test_52_gate_and_existing_frozen_loader_compatibility(self):
        for i in range(51): self.week(self.first+timedelta(weeks=i))
        target = (self.first+timedelta(weeks=53)).isoformat()
        self.assertFalse(self.run_bridge(target)['model_input_created'])
        self.week(self.first+timedelta(weeks=51))
        result = self.run_bridge(target)
        self.assertTrue(result['model_input_created'])
        import pandas as pd
        loaded = load_historical_universe(self.output,pd.Timestamp(target))
        self.assertEqual(loaded.signal_date.nunique(),52)
        self.assertEqual(len(loaded),1040)
        self.assertTrue(loaded.evidence_class.eq(b.MODEL_ONLY).all())
        self.assertEqual(result['scientific_credit'],0)

    def test_pending_and_not_yet_closed_weeks_do_not_count(self):
        self.week(mature=False)
        self.week(self.first+timedelta(weeks=1))
        self.assertEqual(self.run_bridge(now=datetime(2026,10,23,tzinfo=timezone.utc))['matured_prior_weeks'],0)

    def test_hash_tampering_of_each_source_component_fails(self):
        d = self.week()
        for name in ['FEATURES.csv','EXCLUSIONS.csv','LABELS.csv','LABEL_EVIDENCE.json']:
            original = (d/name).read_bytes(); (d/name).write_bytes(original+b' ')
            with self.subTest(name=name), self.assertRaises(ValueError): self.run_bridge()
            (d/name).write_bytes(original)

    def test_late_snapshot_wrong_class_duplicate_membership_and_nan_fail(self):
        for kind in ['late','class','duplicate','nan']:
            with tempfile.TemporaryDirectory() as tmp:
                self.root = Path(tmp); self.output = self.root/'derived.csv'
                def mutate(rows):
                    if kind=='late':rows[0]['retrieved_at_utc']='2026-10-10T00:00:00Z'
                    elif kind=='class':rows[0]['evidence_class']=b.MODEL_ONLY
                    elif kind=='duplicate':rows[0]['symbol']=rows[1]['symbol']
                    else:rows[0][b.FEATURES[0]]=float('nan')
                self.week(mutate=mutate)
                with self.subTest(kind=kind), self.assertRaises(ValueError): self.run_bridge()

    def test_tombstone_source_dates_and_safety_cannot_be_changed(self):
        d=self.week(); p=d/'MATURED.json'; original=json.loads(p.read_bytes())
        for key,value in [('exit_date','2026-10-15'),('ORDERS',1),('features_sha256','b'*64)]:
            p.write_bytes(self.encoded({**original,key:value}))
            with self.subTest(key=key),self.assertRaises(ValueError):self.run_bridge()

    def test_stale_derived_file_cannot_bypass_insufficient_readiness(self):
        self.week(); self.output.write_text('stale approved-looking data')
        with self.assertRaises(ValueError): self.run_bridge()


if __name__ == '__main__': unittest.main()
