#!/usr/bin/env python3
import argparse,json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

def load(p):
 try:return json.loads(p.read_text(encoding='utf-8'))
 except:return {}


def materialization_progress(qual, readiness):
 """Report verified upstream stages; never activate or grant credit."""
 invalid={'status':'RECONCILIATION_REQUIRED'}
 expected_safety={'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0,'NO_BACKFILL':True,'NO_RETUNE':True,'FAIL_CLOSED':True}
 if readiness.get('schema')!='qrds.factory.qualified_materializer_readiness.v2' or readiness.get('safety')!=expected_safety:
  return invalid
 qualified=[f for f in qual.get('families',[]) if f.get('status')=='SOURCE_COST_QUALIFIED']
 rows=readiness.get('families')
 if not isinstance(rows,list) or len(rows)!=qual.get('qualified_count') or len(qualified)!=len(rows):
  return invalid
 qmap={f.get('family_id'):f for f in qualified}
 if None in qmap or len(qmap)!=len(rows):
  return invalid
 seen=set(); collecting=terminal=actionable=0; dispositions=[]
 for row in rows:
  fid=row.get('family_id');q=qmap.get(fid)
  if q is None or fid in seen or q.get('source_qualified') is not True or q.get('cost_applicability_proven') is not True:
   return invalid
  seen.add(fid)
  if row.get('qualified_sources')!=q.get('qualified_sources') or type(row.get('scientific_credit')) is not int or row['scientific_credit']!=0:
   return invalid
  state=row.get('implementation_status'); action=row.get('next_action')
  if state=='TERMINAL_SOURCE_BLOCKED_PIT_VALUES':
   if row.get('physical_capture_proven') is not True or row.get('collection_started') is not False or action!='SOURCE_REQUALIFICATION_ONLY_IF_VERSIONED_PIT_VALUES_FOUND':
    return invalid
   terminal+=1;kind='TERMINAL_SOURCE_REVIEW_CLOSED'
  elif state=='MATERIALIZER_PROVEN_OUTCOME_BLIND' and row.get('collection_started') is True:
   digest=row.get('capture_sha256','')
   if (not all(row.get(k) is True for k in ('physical_capture_proven','pit_feature_materialization_proven','capture_verified','prospective_preregistration_present'))
       or not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest)
       or action!='WAIT_NEXT_ELIGIBLE_OFFICIAL_PUBLICATION'):
    return invalid
   collecting+=1;kind='COLLECTING_WAIT_NEXT_PUBLICATION'
  elif row.get('collection_started') is False and (
       (state=='SOURCE_MATERIALIZER_REQUIRED' and action=='IMPLEMENT_OFFICIAL_SOURCE_CAPTURE_AND_PIT_TESTS')
       or (state=='MATERIALIZER_PROVEN_OUTCOME_BLIND' and action in ('SEPARATE_PROSPECTIVE_COLLECTION_PREREG_REQUIRED','START_PREREGISTERED_PROSPECTIVE_COLLECTION')
           and row.get('physical_capture_proven') is True and row.get('pit_feature_materialization_proven') is True)):
   actionable+=1;kind='ACTION_REQUIRED'
  else:
   return invalid
  dispositions.append({'family_id':fid,'disposition':kind,'next_action':action})
 return {'status':'RECONCILED','qualified_family_count':len(rows),'collecting_count':collecting,'terminal_source_blocked_count':terminal,'actionable_count':actionable,'families':dispositions,'scientific_credit_awarded':0,'promotion_authority':False}

def build(root):
 scout=load(root/'GRAMMAR_SCOUT_RUNTIME.json')
 hand=load(root/'GRAMMAR_HANDOFF_RUNTIME.json')
 trans=load(root/'GRAMMAR_PREREG_TRANSPORT_RUNTIME.json')
 intake=load(root/'GRAMMAR_SOURCE_COST_INTAKE_RUNTIME.json')
 qual=load(root/'GRAMMAR_SOURCE_COST_QUALIFICATION_RUNTIME.json')
 st=Counter(x.get('status','UNKNOWN') for x in scout.get('proposals',[]))
 sigs=set()
 for p in (root/'grammar_handoff_audits').glob('*.json') if (root/'grammar_handoff_audits').exists() else []:
  sigs.update(x.get('grammar_signature') for x in load(p).get('requests',[]) if x.get('grammar_signature'))
 prereg=list((root/'grammar_preregistrations').glob('XAGRAMMAR_*.json')) if (root/'grammar_preregistrations').exists() else []
 transported=int(intake.get('transported_count',0) or 0)
 qualified=int(qual.get('qualified_count',0) or 0)
 waiting=int(qual.get('waiting_count',0) or 0)
 blocked=int(qual.get('blocked_semantics_count',0) or 0)
 rejected=int(qual.get('rejected_count',0) or 0)
 adjudicated=qualified+waiting+blocked+rejected
 progress_path=root/'GRAMMAR_MATERIALIZER_READINESS_RUNTIME.json'
 progress=materialization_progress(qual,load(progress_path)) if qualified and progress_path.exists() else {'status':'NOT_AVAILABLE'}
 if waiting or blocked:
  next_stage='SOURCE_COST_QUALIFICATION_THEN_EXISTING_FACTORY'
 elif qualified and progress['status']=='RECONCILIATION_REQUIRED':
  next_stage='RECONCILE_QUALIFIED_MATERIALIZATION_STATUS'
 elif qualified and progress['status']=='RECONCILED':
  next_stage='ACTION_REQUIRED_FOR_QUALIFIED_MATERIALIZATION' if progress['actionable_count'] else 'WAIT_PROSPECTIVE_COLLECTION_OR_MATERIAL_NEW_EVIDENCE'
 elif qualified:
  next_stage='EXISTING_FACTORY_FOR_SOURCE_COST_QUALIFIED_FAMILIES'
 elif transported and rejected==transported and adjudicated==transported:
  next_stage='AUTONOMOUS_SCOUT_FOR_NEW_PREREGISTRATIONS'
 elif transported:
  next_stage='SOURCE_COST_QUALIFICATION_THEN_EXISTING_FACTORY'
 else:
  next_stage='AUTONOMOUS_SCOUT_HANDOFF_PREREG_SOURCE_COST_GATE'
 return {
  'schema':'qrds.factory.grammar_pipeline_status.v1',
  'generated_at_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
  'status':'ACTIVE_AUTONOMOUS' if scout else 'WAITING_FIRST_SCOUT',
  'counters':{
   'proposals_current':len(scout.get('proposals',[])),
   'eligible_current':st['SCOUTED_NOT_PREREGISTERED'],
   'duplicate_current':st['DUPLICATE_CHANNEL_SUPPRESSED'],
   'insufficient_evidence_current':st['INSUFFICIENT_EXTERNAL_EVIDENCE_FAIL_CLOSED'],
   'handoff_new_current':int(hand.get('request_count',0) or 0),
   'handoff_unique_cumulative':len(sigs),
   'preregistered_unique_cumulative':len(prereg),
   'transported_current':transported,
   'transported_incremental_last_handoff':int(trans.get('transported_count',0) or 0),
   'source_cost_qualified_current':qualified,
   'source_cost_waiting_current':waiting,
   'source_cost_blocked_semantics_current':blocked,
   'source_cost_rejected_current':rejected,
  },
  'next_stage':next_stage,
  'materialization_progress':progress,
  'safety':{'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0,'NO_RETUNE':True,'NO_BACKFILL':True,'NO_COUNTER_RESET':True,'FAIL_CLOSED':True}
 }

def main():
 a=argparse.ArgumentParser(); a.add_argument('--root',required=True); a.add_argument('--output',required=True); x=a.parse_args(); d=build(Path(x.root)); Path(x.output).write_text(json.dumps(d,indent=2)+'\n'); print(json.dumps(d['counters'],sort_keys=True))

if __name__=='__main__':main()
