"""Isolated documentary reporting checks. No collection, replay, or real state writes."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import runpy
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE/'tools'))
import gate_btc_d50_data_review_reporting as helper
REVIEW = BASE/'artifacts/gate_btc_2/separate_reviews_20261019/D50_PARECER.json'
CONTRACT = BASE/'artifacts/gate_btc_2/separate_reviews_20261019/d50_review_fixture/candidate_contract_v32.json'

class ReviewReportingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='d50_reporting_')
        self.root = Path(self.temp.name)
        self.kw = dict(review_path=REVIEW, contract_path=CONTRACT,
                       v32_zip_path=self.root/'unavailable_v32.zip')
    def tearDown(self):
        self.temp.cleanup()
    def test_accepts_exact_review_without_operational_approval(self):
        result = helper.documentary_adjudication(**self.kw)
        self.assertEqual(result['status'], 'VALID')
        self.assertTrue(result['INDEPENDENT_DATA_AUDIT_COMPLETED'])
        self.assertTrue(result['WINDOW_MAY_START_DOCUMENTAL'])
        self.assertFalse(result['WINDOW_MAY_START'])
        self.assertFalse(result['CAPITAL_REAL_ALLOWED'])
        self.assertFalse(result['production_attested'])
        self.assertEqual(result['subject_checks']['original_contract']['status'], 'MATCH')
        self.assertEqual(result['subject_checks']['frozen_v32_zip']['status'], 'UNAVAILABLE_NOT_ATTESTED')
    def test_missing_review_is_not_approval(self):
        result = helper.documentary_adjudication(self.root/'missing.json')
        self.assertEqual(result['status'], 'MISSING')
        self.assertFalse(result['INDEPENDENT_DATA_AUDIT_COMPLETED'])
        self.assertFalse(result['WINDOW_MAY_START_DOCUMENTAL'])
    def test_hash_mismatch_blocks_before_semantics(self):
        p=self.root/'tampered.json';p.write_bytes(REVIEW.read_bytes()+b' ')
        result=helper.documentary_adjudication(p)
        self.assertEqual(result['status'],'INVALID')
        self.assertEqual(result['reason'],'REVIEW_SHA256_MISMATCH')
        self.assertFalse(result['INDEPENDENT_DATA_AUDIT_COMPLETED'])
    def _semantic_mutation(self, change):
        review=json.loads(REVIEW.read_text(encoding="utf-8"));change(review)
        raw=json.dumps(review).encode();p=self.root/'semantic.json';p.write_bytes(raw)
        # Unit-only pin override exercises defense after byte validation.
        with patch.object(helper,'REVIEW_SHA256',hashlib.sha256(raw).hexdigest()):
            return helper.documentary_adjudication(p, contract_path=CONTRACT)
    def test_wrong_subject_in_review_rejected(self):
        result=self._semantic_mutation(lambda r:r.update(subject_zip_sha256='0'*64))
        self.assertEqual(result['reason'],'REVIEW_SUBJECT_MISMATCH')
        self.assertFalse(result['WINDOW_MAY_START_DOCUMENTAL'])
    def test_review_operational_capital_flag_true_rejected(self):
        result=self._semantic_mutation(lambda r:r.update(CAPITAL_REAL_ALLOWED=True))
        self.assertEqual(result['reason'],'REVIEW_FLAGS_INVALID')
        self.assertFalse(result['CAPITAL_REAL_ALLOWED'])
    def test_review_window_false_rejected(self):
        result=self._semantic_mutation(lambda r:r.update(WINDOW_MAY_START=False))
        self.assertEqual(result['reason'],'REVIEW_FLAGS_INVALID')
    def test_available_stable_subject_change_invalidates(self):
        subject=self.root/'candidate_contract_v32.json';subject.write_bytes(CONTRACT.read_bytes()+b' ')
        result=helper.documentary_adjudication(REVIEW,contract_path=subject)
        self.assertEqual(result['status'],'INVALID')
        self.assertEqual(result['reason'],'AVAILABLE_SUBJECT_MISMATCH:original_contract')
    def test_available_wrong_v32_zip_invalidates(self):
        p=self.root/'v32.zip';p.write_bytes(b'AUTOPILOT_V2_IS_NOT_V32')
        result=helper.documentary_adjudication(REVIEW,contract_path=CONTRACT,v32_zip_path=p)
        self.assertEqual(result['reason'],'AVAILABLE_SUBJECT_MISMATCH:frozen_v32_zip')
    def test_next_observation_and_rolling_window_do_not_require_new_review(self):
        state={'paired_prospective_observations':79,'next_checkpoint':80,
               'qualified_snapshot_ids':['NEW_ROLLING_WINDOW'], 'package_sha256':'NEW_DAILY_PACKAGE'}
        before=copy.deepcopy(state)
        result=helper.documentary_adjudication(**self.kw,prospective_status=state)
        self.assertEqual(result['status'],'VALID')
        self.assertEqual(result['economic_observations_current'],79)
        self.assertEqual(result['data_qualification_at_audit'],'7/7')
        self.assertFalse(result['cycles_completion_inferred'])
        self.assertEqual(state,before)
    def test_governance_fixture_publishes_review_without_touching_economic_input(self):
        install=self.root/'install';proj=install/'project';state=install/'state';downloads=self.root/'downloads'
        state.mkdir(parents=True);proj.mkdir();downloads.mkdir()
        economic=state/'D50_PROSPECTIVE_STATUS_V2.json'
        economic.write_text(json.dumps({'paired_prospective_observations':79,'next_checkpoint':80,'capital':0}), encoding='utf-8')
        before=economic.read_bytes()
        output=io.StringIO()
        with patch.object(helper,'DEFAULT_REVIEW_PATH',REVIEW), patch.object(sys,'argv',['governance',str(install),str(proj),str(state),str(downloads)]),contextlib.redirect_stdout(output):
            runpy.run_path(str(BASE/'artifacts/gate_btc_2/separate_reviews_20261019/d50_reporting_patches/gate_btc_governance_master_v1.py'))
        master=json.loads((state/'GATE_BTC_MASTER_POSITION_SIDECAR_LATEST.json').read_text(encoding='utf-8'))
        self.assertTrue(master['current_documentary_adjudication']['INDEPENDENT_DATA_AUDIT_COMPLETED'])
        self.assertFalse(master['governance']['engine_feed'])
        self.assertEqual(economic.read_bytes(),before)
        self.assertIn('WINDOW_MAY_START_DOCUMENTAL=True',output.getvalue())
        self.assertIn('INDEPENDENT_DATA_AUDIT_COMPLETED=True',(downloads/'GATE_BTC_GOVERNANCE_MASTER_LATEST.txt').read_text(encoding='utf-8'))
    def test_cli_status_fixture_preserves_original_certificate_flags(self):
        package='d50_reporting_fixture'
        modules={package:types.ModuleType(package)};modules[package].__path__=[]
        def stub(name,**values):
            module=types.ModuleType(package+'.'+name)
            for k,v in values.items():setattr(module,k,v)
            modules[module.__name__]=module
        certificate={'qualified':True,'latest_consecutive_pass_count':7,'WINDOW_MAY_START':False,'CAPITAL_REAL_ALLOWED':False}
        original=copy.deepcopy(certificate)
        stub('config',DEFAULT_INPUT_RELATIVE=Path('inputs'),DEFAULT_RUNTIME_RELATIVE=Path('runtime'))
        stub('finalize',build_independent_audit_package=None)
        stub('okx_client',OKXPublicDailyClient=lambda:None)
        stub('repair',repair_historical_master=None)
        stub('snapshot',collect_prospective_snapshot=None,evaluate_qualification=lambda runtime:certificate)
        modules[package+'.gate_btc_d50_data_review_reporting']=helper
        spec=importlib.util.spec_from_file_location(package+'.cli',BASE/'artifacts/gate_btc_2/separate_reviews_20261019/d50_reporting_patches/cli.py');cli=importlib.util.module_from_spec(spec)
        lines=[];output=io.StringIO()
        with patch.dict(sys.modules,modules),patch.object(helper,'DEFAULT_REVIEW_PATH',REVIEW):
            spec.loader.exec_module(cli)
            with patch.object(cli,'_write_report',lambda data,prefix:(lines.extend(data) or self.root/'report.txt')),contextlib.redirect_stdout(output):
                self.assertEqual(cli.run(['status','--repo-root',str(self.root)]),0)
        result=json.loads(output.getvalue())['result']
        self.assertTrue(result['current_documentary_adjudication']['INDEPENDENT_DATA_AUDIT_COMPLETED'])
        self.assertFalse(result['WINDOW_MAY_START'])
        self.assertEqual(certificate,original)
        self.assertIn('WINDOW_MAY_START_DOCUMENTAL=True',lines)

if __name__=='__main__':unittest.main(verbosity=2)
