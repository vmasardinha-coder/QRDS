import copy
from datetime import datetime as RealDatetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import gate_btc_h1_schedule_continuation as continuation
import gate_btc_b3_h1_daily as collector
import gate_btc_b3_h1_runtime_ledger as publisher
import gate_btc_h1_materialize_collector as materializer


class FutureContinuation(unittest.TestCase):
    def source(self):
        c = continuation.load_continuation()
        return {'schema':'gate_btc.b3.h1.cloud_structural.v2', 'date':'2026-11-03',
                'status':'STRUCTURAL_PASS', 'qualified':True, 'h1_increment_candidate':1,
                'research_only':True, 'shadow_only':True, 'not_approved':True,
                'orders':0, 'real_capital':0, 'economics_locked':True, 'economic_functions_called':False,
                'front_contracts':{'WIN':'WINZ26','WDO':'WDOZ26'},
                'freeze_status':c['freeze_status'], 'schedule_amendment_sha256':continuation.CONTINUATION_SHA256,
                'full_frozen_schedule_sha256':c['legacy_full_frozen_schedule_sha256'],
                'h1_schedule_prefix_sha256':c['legacy_schedule_prefix_sha256'],
                'qa':{'m1_to_m5_exact':True,'tick_grid':'PASS','ohlc_integrity':'PASS'}}

    def test_only_declared_future_sessions_and_no_change_to_legacy_seals(self):
        dates = continuation.continuation_schedule()
        self.assertEqual(len(dates),10)
        self.assertNotIn('2026-11-02', dates)
        self.assertNotIn('2026-10-30', dates)
        self.assertFalse(set(dates) & set(collector.load_schedule()))
        self.assertFalse(set(dates) & set(collector.load_amendment_schedule()))
        self.assertFalse(set(dates) & set(collector.extension_schedule()))
        self.assertEqual(hashlib.sha256(collector.AMENDMENT_FILE.read_bytes()).hexdigest(),collector.AMENDMENT_SHA256)
        self.assertEqual(continuation.load_continuation()['canonical_counter_preserved'],18)

    def test_contract_tampering_clock_qa_and_identity_are_rejected(self):
        mutations = [lambda d:d.update(preregistered_at_utc='2026-11-03T12:00:00Z'),
                     lambda d:d.update(preregistered_at_utc='2026-11-01T12:00:00'),
                     lambda d:d.update(parent_extension_sha256='a'*64),
                     lambda d:d['sessions'][0].update(date='2026-10-30'),
                     lambda d:d['sessions'][0].update(WDO='WDOX26'),
                     lambda d:d['qa_unchanged'].update(expected_m5_per_root=101),
                     lambda d:d['safety'].update(economics_locked=False),
                     lambda d:d.update(target=21)]
        for mutate in mutations:
            d=copy.deepcopy(continuation.load_continuation());mutate(d);raw=json.dumps(d).encode()
            with tempfile.TemporaryDirectory() as td:
                p=Path(td)/'receipt.json';p.write_bytes(raw)
                with patch.object(continuation,'CONTINUATION_FILE',p),patch.object(continuation,'CONTINUATION_SHA256',hashlib.sha256(raw).hexdigest()):
                    with self.assertRaises(RuntimeError):continuation.load_continuation()

    def run_collector(self,today,day,source_pending=False):
        class Clock(RealDatetime):
            @classmethod
            def now(cls,tz=None):return cls.fromisoformat(today).astimezone(tz)
        with tempfile.TemporaryDirectory() as td,patch.object(collector,'datetime',Clock),patch.object(collector,'fetch_raw',return_value=(None,{'state':'PENDING_SOURCE_NOT_PUBLISHED'})) as fetch:
            with patch.object(sys,'argv',['collector','--date',day,'--out-dir',td]):self.assertEqual(collector.main(),0)
            status=json.loads((Path(td)/day/'H1_STRUCTURAL_STATUS.json').read_text())
            self.assertEqual(status['h1_increment_candidate'],0)
            self.assertEqual(fetch.call_count,1 if source_pending else 0)
            return status

    def test_future_expired_and_holiday_never_fetch_or_create_observation(self):
        for today,day in [('2026-11-01T15:00:00-03:00','2026-11-03'),('2026-11-05T15:00:00-03:00','2026-11-03')]:
            self.assertEqual(self.run_collector(today,day)['status'],'PROSPECTIVE_WINDOW_EXPIRED_OR_NOT_OPEN')
        self.assertEqual(self.run_collector('2026-11-02T15:00:00-03:00','2026-11-02')['status'],'NO_FROZEN_H1_SCHEDULE_FOR_DATE')

    def test_open_future_opportunity_records_seal_without_source_credit(self):
        d=self.run_collector('2026-11-03T22:00:00-03:00','2026-11-03',True)
        self.assertEqual(d['status'],'PENDING_SOURCE_NOT_PUBLISHED')
        self.assertEqual(d['schedule_amendment_sha256'],continuation.CONTINUATION_SHA256)
        self.assertEqual(d['front_contracts'],{'WIN':'WINZ26','WDO':'WDOZ26'})
        self.assertTrue(d['economics_locked'])

    def test_publisher_checks_new_seal_and_preserves_existing_entries(self):
        good=self.source();publisher.validate_source(good)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'status.json';p.write_text(json.dumps(good));before={'entries':[{'date':'2026-10-23','qualified':True,'proof':'unchanged'}]}
            saved=copy.deepcopy(before);after=publisher.build(good,p,before,'fixture')
            self.assertEqual(before,saved);self.assertEqual(after['entries'][0],saved['entries'][0])
            self.assertEqual(publisher.build(good,p,after,'fixture2')['entries'],after['entries'])
        for field,value in [('schedule_amendment_sha256',collector.EXTENSION_SHA256),('front_contracts',{'WIN':'WINZ26','WDO':'WDOX26'}),('date','2026-10-30')]:
            bad={**good,field:value}
            with self.assertRaises(RuntimeError):publisher.validate_source(bad)

    def test_canonical_counter_reaches_twenty_only_with_real_qualified_inputs_and_stops(self):
        spec=importlib.util.spec_from_file_location('canonical_gate',ROOT/'tools/gate_btc_factory/h1_canonical_runtime.py')
        gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
        anchor={'canonical_evidence':{'qualified':8,'last_candidate_date':'2026-08-28'}}
        original={'qualified':18,'post_anchor_events':[]};before=copy.deepcopy(original)
        pending=gate.build(anchor,original,'2026-11-03','gap','SOURCE_NOT_PUBLISHED','fixture')
        self.assertEqual(pending['qualified'],18);self.assertEqual(original,before)
        at19=gate.build(anchor,pending,'2026-11-04','qualified','STRUCTURAL_PASS','fixture')
        at20=gate.build(anchor,at19,'2026-11-05','qualified','STRUCTURAL_PASS','fixture')
        self.assertEqual(at20['qualified'],20);self.assertTrue(at20['economics_locked']);self.assertFalse(at20['collector_should_continue'])
        with self.assertRaisesRegex(RuntimeError,'already at 20'):gate.build(anchor,at20,'2026-11-06','qualified','STRUCTURAL_PASS','fixture')


class Materialization(unittest.TestCase):
    def setup_repo(self,root):
        source=root/'source';source.mkdir()
        def git(*args):subprocess.run(['git','-C',str(source),*args],check=True,capture_output=True)
        git('init');git('config','core.autocrlf','false');git('config','user.name','fixture');git('config','user.email','fixture@example.invalid')
        for name in materializer.FILES:
            target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
        git('add','.');git('commit','-m','fixture')
        return source,git

    def test_exact_git_blob_materialization_is_idempotent_and_preserves_other_files(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source,_=self.setup_repo(root);out=root/'collector';out.mkdir();history=out/'ledger.json';history.write_bytes(b'preserved')
            check=materializer.materialize(source,out,True);self.assertEqual(list(out.iterdir()),[history]);self.assertFalse(check['collector_executed'])
            first=materializer.materialize(source,out);self.assertEqual(len(first['files']),7)
            for name in materializer.FILES:self.assertEqual((out/Path(name).relative_to('tools')).read_bytes(),(ROOT/name).read_bytes())
            second=materializer.materialize(source,out);self.assertTrue(all(not f['changed'] for f in second['files']))
            self.assertEqual(history.read_bytes(),b'preserved');self.assertFalse(second['counter_changed'])

    def test_bad_sealed_input_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source,git=self.setup_repo(root);out=root/'collector'
            path=source/materializer.FILES[-1];path.write_bytes(path.read_bytes()+b' ');git('add','.');git('commit','-m','tamper')
            with self.assertRaisesRegex(RuntimeError,'HASH_MISMATCH'):materializer.materialize(source,out)
            self.assertFalse(out.exists())
            with self.assertRaisesRegex(RuntimeError,'INSIDE_SOURCE'):materializer.materialize(source,source/'nested')


if __name__=='__main__':unittest.main()
