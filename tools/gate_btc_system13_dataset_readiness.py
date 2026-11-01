"""Build the admission evidence queue and chronological manifest; never admit/train."""
from __future__ import annotations
import argparse,json,math
from datetime import date,timedelta
from pathlib import Path
try:
 from .gate_btc_system13_governed_bars import PROTOCOL,PROTOCOL_SHA256
 from .gate_btc_factory.frozen_source_bytes import read_frozen_bytes
except ImportError:
 from gate_btc_system13_governed_bars import PROTOCOL,PROTOCOL_SHA256
 from gate_btc_factory.frozen_source_bytes import read_frozen_bytes

def protocol():return json.loads(read_frozen_bytes(PROTOCOL,PROTOCOL_SHA256))

def admission_dossier(readiness,native):
 if readiness.get('protocol_sha256')!=PROTOCOL_SHA256 or native.get('protocol_sha256')!=PROTOCOL_SHA256:
  raise ValueError('SYSTEM13_PROTOCOL_MISMATCH')
 if native.get('observed_panel_sha256')!=readiness.get('observed_panel_sha256'):
  raise ValueError('NATIVE_CAPTURE_MEMBERSHIP_MISMATCH')
 observed={r['coin_id']:r for r in native.get('rows',[])};result=[];seen=set()
 for r in readiness['rows']:
  coin=r['coin_id']
  if coin in seen:raise ValueError('DUPLICATE_OBSERVED_MEMBER')
  seen.add(coin)
  if r['eligible_in_observed_panel'] is not True:continue
  raw=observed.get(coin,{})
  gates={'exact_id_and_venue_binding':r.get('exact_binding_candidate') is True and bool(r.get('source_symbol')),
         'active_native_instrument_observed':raw.get('status')=='NATIVE_CLOSED_OHLCV_OBSERVED_UNQUALIFIED',
         'native_quote_currency_observed':raw.get('quote_currency') in ('USD','USDT') and raw.get('quote_currency')==r.get('literal_quote_unit_candidate'),
         'base_volume_unit_observed':raw.get('volume_unit')=='BASE_ASSET',
         'adjustment_factor_evidence_admitted':False,
         'system13_admission_before_session':False}
  missing=[k for k,v in gates.items() if not v]
  result.append({'coin_id':coin,'source_identity':r.get('source_identity'),'source_symbol':r.get('source_symbol'),
     'quote_currency':r.get('literal_quote_unit_candidate'),'gates':gates,'missing_evidence':missing,
     'native_raw_sha256':raw.get('raw_sha256'),'metadata_sha256':raw.get('metadata_sha256'),
     'required_adjustment_proof':'Official instrument-specific adjustment/factor policy, numeric factor and effective dates; migration/delisting treatment. No inferred factor=1.',
     'required_admission_proof':'Hash-bound System13 source review for exact identity, tradability, quote/base-volume and adjustment evidence, qualified before the future session opens.',
     'source_admitted':False,'qualified_ohlcv':False})
 if len(result)!=readiness['eligible_members']:raise ValueError('ELIGIBLE_DENOMINATOR_CHANGED')
 return {'schema':'qrds.system13.admission_evidence_queue.v1','protocol_sha256':PROTOCOL_SHA256,
    'observed_panel_sha256':readiness['observed_panel_sha256'],'eligible_members':len(result),
    'exact_bindings':sum(x['gates']['exact_id_and_venue_binding'] for x in result),
    'required_coverage':max(50,math.ceil(.8*len(result))),
    'qualified_system13_ohlcv_assets':0,'source_admitted':False,'training_ready':False,
    'holdout_read_allowed':False,'rows':result,'scientific_credit':0,'safety':protocol()['safety']}

def partition_manifest(review):
 c=protocol();p=c['training_protocol']
 if review.get('schema')!='qrds.system13.governed_bar_import_review.v1' or review.get('protocol_sha256')!=PROTOCOL_SHA256:
  raise ValueError('GOVERNED_IMPORT_REVIEW_REQUIRED')
 if review.get('quote_conversion_applied') is not False:raise ValueError('NATIVE_UNIT_ONLY')
 # Session eligibility is established by the existing governed importer, never raw panel counts.
 rows=review['rows'];qualified=[];seen=set()
 for session in sorted(review['sessions'],key=lambda x:x['session']):
  day=session['session']
  if day in seen:raise ValueError('DUPLICATE_SESSION')
  seen.add(day)
  source=[r for r in rows if r['session']==day]
  ids=[r['coin_id'] for r in source]
  if len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_ASSET_SESSION')
  eligible=session['observed_eligible_members'];coverage=len(ids)/eligible if eligible else 0
  if (session.get('available_bar_count')!=len(ids) or abs(session['coverage_fraction']-coverage)>1e-12
      or session.get('coverage_gate_pass') is not (len(ids)>=c['min_assets_per_session'] and coverage>=c['min_coverage_fraction'])):
   raise ValueError('SESSION_COVERAGE_RECEIPT_MISMATCH')
  if session['coverage_gate_pass'] is True:qualified.append(day)
 # Do not bridge ineligible or missing UTC sessions to form a training sequence.
 runs=[]
 for day in qualified:
  if not runs or date.fromisoformat(day)!=date.fromisoformat(runs[-1][-1])+timedelta(days=1):runs.append([])
  runs[-1].append(day)
 phases=[('warmup',p['warmup_sessions']),('train',p['train_sessions']),('purge',p['purge_after_train_sessions']),
         ('validation',p['validation_sessions']),('embargo',p['embargo_before_holdout_sessions']),('holdout',p['holdout_sessions'])]
 required=sum(n for _,n in phases);complete=next((r for r in runs if len(r)>=required),None)
 selected=complete[:required] if complete else (runs[0] if runs else [])
 assigned=[];offset=0
 for name,n in phases:
  ds=selected[offset:offset+n];assigned.append({'phase':name,'required_sessions':n,'sessions':ds,'complete':len(ds)==n});offset+=n
 return {'schema':'qrds.system13.chronological_dataset_manifest.v1','protocol_sha256':PROTOCOL_SHA256,
    'selection_rule':p['partition_rule'],'required_eligible_sessions':required,
    'qualified_sessions_observed':len(qualified),'selected_contiguous_session_count':len(selected),
    'missing_sessions_in_selected_run':max(0,required-len(selected)),
    'partitions':assigned,'chronological_partitions_qualified':complete is not None,
    'training_ready':False,'holdout_read_allowed':False,'training_executed':False,
    'target_or_outcome_read':False,'scientific_credit':0,'safety':c['safety']}

def main():
 p=argparse.ArgumentParser();p.add_argument('--readiness',type=Path);p.add_argument('--native',type=Path)
 p.add_argument('--governed-review',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 load=lambda path:json.loads(path.read_bytes())
 if a.governed_review:result=partition_manifest(load(a.governed_review))
 elif a.readiness and a.native:result=admission_dossier(load(a.readiness),load(a.native))
 else:p.error('supply a governed review or readiness and native receipt')
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('rows','partitions')},sort_keys=True))
if __name__=='__main__':main()
