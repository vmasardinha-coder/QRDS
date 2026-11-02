import copy,json,tempfile,unittest
from datetime import date,timedelta
from pathlib import Path
from tools.gate_btc_system13_dataset_readiness import admission_dossier,partition_manifest,PROTOCOL_SHA256
from tools.gate_btc_system13_source_readiness import verified_identity_extension

def review(n=280):
 days=[(date(2026,1,1)+timedelta(days=i)).isoformat() for i in range(n)]
 return {'schema':'qrds.system13.governed_bar_import_review.v1','protocol_sha256':PROTOCOL_SHA256,
  'quote_conversion_applied':False,'sessions':[{'session':d,'observed_eligible_members':50,'available_bar_count':50,'coverage_fraction':1,'coverage_gate_pass':True} for d in days],
  'rows':[{'session':d,'coin_id':str(i)} for d in days for i in range(50)]}

class DatasetTests(unittest.TestCase):
 def test_exact_chronological_partitions_no_training_or_target_read(self):
  d=partition_manifest(review());self.assertEqual([len(p['sessions']) for p in d['partitions']],[60,120,5,30,5,60])
  self.assertTrue(d['chronological_partitions_qualified']);self.assertFalse(d['training_ready'])
  self.assertFalse(d['holdout_read_allowed']);self.assertFalse(d['target_or_outcome_read'])
  dates=[s for p in d['partitions'] for s in p['sessions']];self.assertEqual(len(set(dates)),280)
 def test_partial_coverage_cannot_be_bridged_or_called_mature(self):
  d=partition_manifest(review(85));self.assertFalse(d['chronological_partitions_qualified']);self.assertEqual(d['missing_sessions_in_selected_run'],195)
  r=review(281);r['sessions'][100].update(available_bar_count=0,coverage_fraction=0,coverage_gate_pass=False)
  r['rows']=[x for x in r['rows'] if x['session']!=r['sessions'][100]['session']]
  d=partition_manifest(r);self.assertFalse(d['chronological_partitions_qualified']);self.assertEqual(d['selected_contiguous_session_count'],100)
 def test_raw_panels_duplicate_rows_or_forged_coverage_rejected(self):
  with self.assertRaises(ValueError):partition_manifest({'schema':'qrds.system13.observed_panel.v1'})
  r=review(1);r['rows'].append(r['rows'][0])
  with self.assertRaisesRegex(ValueError,'DUPLICATE_ASSET'):partition_manifest(r)
  r=review(1);r['sessions'][0]['available_bar_count']=49
  with self.assertRaisesRegex(ValueError,'COVERAGE'):partition_manifest(r)
 def test_admission_queue_never_invents_factor_or_grants_past_eligibility(self):
  r={'protocol_sha256':PROTOCOL_SHA256,'observed_panel_sha256':'a'*64,'eligible_members':1,
    'rows':[{'coin_id':'asset','eligible_in_observed_panel':True,'exact_binding_candidate':True,'source_symbol':'ASSETUSDT','source_identity':'FIXTURE_SPOT','literal_quote_unit_candidate':'USDT'}]}
  n={'protocol_sha256':PROTOCOL_SHA256,'observed_panel_sha256':'a'*64,'rows':[{'coin_id':'asset','status':'NATIVE_CLOSED_OHLCV_OBSERVED_UNQUALIFIED','quote_currency':'USDT','volume_unit':'BASE_ASSET','factor':None}]}
  d=admission_dossier(r,n);self.assertEqual(d['qualified_system13_ohlcv_assets'],0)
  self.assertFalse(d['rows'][0]['gates']['adjustment_factor_evidence_admitted']);self.assertFalse(d['rows'][0]['gates']['system13_admission_before_session'])
  n['observed_panel_sha256']='b'*64
  with self.assertRaisesRegex(ValueError,'MEMBERSHIP'):admission_dossier(r,n)
 def test_real_extension_archived_identity_and_primary_receipts(self):
  root=Path(__file__).resolve().parents[1]
  p=root/'tools/gate_btc_factory/SYSTEM13_EXACT_IDENTITY_EXTENSION_20261101.json'
  d=json.loads(p.read_bytes());verified_identity_extension(d,root)
  self.assertTrue(all(not b['system13_source_admitted'] for r in d['entries'] for b in r['bindings']))
  bad=copy.deepcopy(d);bad['entries'][0]['bindings'][0]['coin_id']='other'
  with self.assertRaises(ValueError):verified_identity_extension(bad,root)
  bad=copy.deepcopy(d);bad['entries'][0]['bindings'][0]['primary_metadata_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'HASH'):verified_identity_extension(bad,root)

if __name__=='__main__':unittest.main()
