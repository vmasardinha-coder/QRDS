"""Reconcile superseded preflight with existing ex-ante authorities and terminal receipt.

Reads only authority and already-published evaluation receipts. Never runs an
evaluator, opens a target source or selects a new statistic.
"""
import argparse,hashlib,json
from pathlib import Path
try:from .frozen_source_bytes import read_frozen_bytes
except ImportError:from frozen_source_bytes import read_frozen_bytes

CASES_SHA='c6b1540ac3d2c5ebbced51d5bca5308b84684ac2e1371ff4a5522fa01c2dd856'
STAT_SHA='c4f416d6bb28ae3fc8dbd0546c3542a296c15bcafabf833d2a9d8e97452f342f'
ORDER=['G007_FOCUS_50_50_V1','G007_FOCUS_IPCA_ONLY_V1','G007_FOCUS_SELIC_ONLY_V1']
HISTORY=[{'stage':'SCALAR_CASE_AUTHORITY','commit':'0324080699ee550c0af4872ad872a28e7da0dc62','at_utc':'2026-09-21T10:34:24Z'},
 {'stage':'PEARSON_AUTHORITY','commit':'4e3cbae4b37cc9885960ce0b9a8a41e60f87faa6','at_utc':'2026-09-21T11:01:19Z'},
 {'stage':'PUBLISHED_HISTORICAL_EVALUATION','commit':'35149e8bba6197db3884d8e05ba0ccd94abae756','at_utc':'2026-09-21T11:15:02Z'}]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def reconcile(root):
 source=Path(__file__).resolve().parent
 bound=[]
 for name,digest,runtime in [
   ('GRAMMAR_007_EFFECT_CASES_AUTH_20260921.json',CASES_SHA,'GRAMMAR_007_EFFECT_CASES_AUTH_RUNTIME.json'),
   ('GRAMMAR_007_EFFECT_STAT_AUTH_20260921.json',STAT_SHA,'GRAMMAR_007_EFFECT_STAT_AUTH_RUNTIME.json')]:
  raw=read_frozen_bytes(source/name,digest)
  d=json.loads(raw)
  if json.loads((root/runtime).read_bytes())!=d:raise ValueError('RUNTIME_AUTHORITY_MISMATCH')
  if d['target_boundary_at_freeze']!={'target_source_opened':False,'target_bytes_read':False,'outcomes_read':False,'economics_read':False}:
   raise ValueError('AUTHORITY_NOT_BEFORE_TARGET_READ')
  bound.append({'file':name,'source_sha256':digest,'runtime_file':runtime})
 preflight_raw=(root/'GRAMMAR_007_SEALED_PARTITION_PREFLIGHT_RUNTIME.json').read_bytes()
 preflight=json.loads(preflight_raw)
 raw=(root/'GRAMMAR_007_PEARSON_HISTORICAL_EVAL_RUNTIME.json').read_bytes();result=json.loads(raw)
 if (preflight['partitions_frozen'] is not True or preflight['partition_contract']!='50_30_20_CHRONOLOGICAL'
     or preflight['embargo_sessions']!=60):raise ValueError('SEALED_PARTITIONS_CHANGED')
 if (result['status']!='HISTORICAL_EVALUATION_COMPLETE_NO_SURVIVOR' or result['survivors']!=[]
     or result['partition_contract']!=preflight['partition_contract'] or result['embargo_sessions']!=60
     or result['effect_statistic']!='PEARSON_PRODUCT_MOMENT_CORRELATION'
     or result['target_source']['holdout_year_2026_ever_fetched'] is not False):raise ValueError('TERMINAL_EVALUATION_NOT_PROVEN')
 if [r['case_id'] for r in result['cases']]!=ORDER:raise ValueError('CASE_UNIVERSE_CHANGED')
 for r in result['cases']:
  if (r['terminal_status']!='REJECTED_VALIDATION_NO_RETUNE' or r['validation']['pass'] is not False
      or r['holdout']['started'] is not False or r['holdout']['n']!=0):raise ValueError('TERMINAL_CASE_MISMATCH')
 for key in ('scientific_credit','prospective_credit','historical_backfill_credit'):
  if result[key]!=0:raise ValueError('CREDIT_CHANGED')
 return {'schema':'qrds.factory.grammar007.current_disposition.v1',
    'status':'ENCERRADO_DESCARTADO_NO_SURVIVOR','method_blocker_resolved':True,
    'resolution':'EXISTING_PREOUTCOME_SCALAR_CASES_AND_PEARSON_AUTHORITY_NOT_NEW_METHOD',
    'superseded_preflight_sha256':sha(preflight_raw),'preflight_preserved':True,
    'authorities':bound,'git_history':HISTORY,'published_evaluation_sha256':sha(raw),
    'cases':[{'case_id':r['case_id'],'terminal_status':r['terminal_status'],'holdout_read':False} for r in result['cases']],
    'recurring_historical_evaluation_task':False,'successor_generation_created':False,
    'new_target_source_opened':False,'new_target_bytes_read':False,'new_outcomes_computed':False,
    'focus_prospective_disposition':'SEPARATE_COLLECTOR_WAIT_ELIGIBLE_PUBLICATION',
    'cvm_disposition':'TERMINAL_SOURCE_BLOCKED_UNLESS_NEW_VERSIONED_PIT_VALUES',
    'scientific_credit':0,'survivors':[],'safety':result['safety']}

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 result=reconcile(a.root);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
