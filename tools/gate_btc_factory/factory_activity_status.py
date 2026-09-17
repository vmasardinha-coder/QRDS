#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
SCHEMA='qrds.factory.activity_status.v2'
def now_utc(): return datetime.now(timezone.utc)
def parse_ts(v):
 if not v:return None
 try:return datetime.fromisoformat(str(v).replace('Z','+00:00'))
 except ValueError:return None
def load(p):
 try:
  x=json.loads(p.read_text(encoding='utf-8')); return x if isinstance(x,dict) else None
 except Exception:return None
def age_hours(ts,now): return None if ts is None else max(0,(now-ts).total_seconds()/3600)
def component(name,path,keys,freshness,now,status_key='status'):
 d=load(path)
 if d is None:return {'name':name,'active':False,'freshness':'MISSING','status':'WAITING_FIRST_RUNTIME','path':str(path)}
 ts=next((parse_ts(d.get(k)) for k in keys if parse_ts(d.get(k))),None); age=age_hours(ts,now); fresh=age is not None and age<=freshness
 return {'name':name,'active':fresh,'freshness':'FRESH' if fresh else 'STALE_OR_UNDATED','age_hours':round(age,2) if age is not None else None,'status':d.get(status_key) or d.get('mode') or 'PRESENT','path':str(path)}
def grammar_counts(fa):
 scout=load(fa/'GRAMMAR_SCOUT_RUNTIME.json') or {}; hand=load(fa/'GRAMMAR_HANDOFF_RUNTIME.json') or {}; trans=load(fa/'GRAMMAR_PREREG_TRANSPORT_RUNTIME.json') or {}
 statuses=Counter(str(x.get('status','UNKNOWN')) for x in scout.get('proposals',[])); sigs=set()
 for p in (fa/'grammar_handoff_audits').glob('*.json') if (fa/'grammar_handoff_audits').exists() else []:
  d=load(p) or {}; sigs.update(r.get('grammar_signature') for r in d.get('requests',[]) if r.get('grammar_signature'))
 prereg=list((fa/'grammar_preregistrations').glob('XAGRAMMAR_*.json')) if (fa/'grammar_preregistrations').exists() else []
 return {'scout_proposals_current':len(scout.get('proposals',[])),'scouted_not_preregistered_current':statuses.get('SCOUTED_NOT_PREREGISTERED',0),'duplicate_suppressed_current':statuses.get('DUPLICATE_CHANNEL_SUPPRESSED',0),'insufficient_evidence_current':statuses.get('INSUFFICIENT_EXTERNAL_EVIDENCE_FAIL_CLOSED',0),'handoff_new_current':int(hand.get('request_count',0) or 0),'handoff_unique_cumulative':len(sigs),'preregistered_unique_cumulative':len(prereg),'transported_current':int(trans.get('transported_count',0) or 0)}
def xawin_counts(fa):
 q=load(fa/'win_wdo/MT5_QUALIFICATION.json') or {}; m=load(fa/'win_wdo/WIN_WDO_MATERIALIZED_SPLITS.json') or {}
 return {'qualified':q.get('qualified',False),'qualification_status':q.get('status','WAITING_FIRST_RUNTIME'),'mt5_record_count':q.get('record_count',0),'materialization_next_stage':m.get('next_stage','WAITING_FIRST_RUNTIME'),'aligned_session_count':m.get('aligned_session_count',0),'usable_return_count':m.get('usable_return_count',0),'split_counts':m.get('split_counts',{})}
def build(runtime_root,now=None):
 t=now or now_utc(); fa=runtime_root/'factory_autonomy'; grammar=component('grammar_scout',fa/'GRAMMAR_SCOUT_RUNTIME.json',('generated_at_utc',),36,t); source=component('source_qualification_search',fa/'invalidated_requalification/SOURCE_SEARCH_RUNTIME.json',('generated_at_utc',),4,t); queue=component('invalidated_family_requalification',fa/'invalidated_requalification/QUEUE.json',('updated_at_utc',),12,t,status_key='source_gate_status'); qd=load(fa/'invalidated_requalification/QUEUE.json') or {}
 queue.update({'affected_family_count':qd.get('affected_family_count'),'completed_family_count':qd.get('completed_family_count',0),'survivor_count':qd.get('survivor_count',0),'source_gate_green':qd.get('source_gate_green',False)})
 components={'grammar_scout':grammar,'source_qualification_search':source,'invalidated_family_requalification':queue}; overall='ACTIVE' if source['active'] and queue['active'] and (grammar['active'] or grammar['status']=='WAITING_FIRST_RUNTIME') else 'DEGRADED_WARMUP_OR_STALE'
 return {'schema':SCHEMA,'generated_at_utc':t.isoformat().replace('+00:00','Z'),'overall_status':overall,'monitor_cadence_minutes':15,'executive_counters':{'xawinwdo_correlation':xawin_counts(fa),'grammar_pipeline':grammar_counts(fa),'legacy_requalification':{'affected':qd.get('affected_family_count',0),'completed':qd.get('completed_family_count',0),'remaining':max(0,int(qd.get('affected_family_count',0) or 0)-int(qd.get('completed_family_count',0) or 0)),'survivors':qd.get('survivor_count',0),'source_gate_green':qd.get('source_gate_green',False)}},'cadence_policy':{'grammar_scout_hours':24,'source_qualification_search_hours':2,'requalification_hours':6,'factory_status_monitor_minutes':15},'components':components,'safety':{'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders':0,'real_capital':0,'no_retune':True,'no_backfill':True,'no_counter_reset':True,'fail_closed':True,'scientific_change_allowed':False}}
def markdown(d):
 e=d['executive_counters']; g=e['grammar_pipeline']; x=e['xawinwdo_correlation']; l=e['legacy_requalification']
 return f"## Factory executive status\nOverall: **{d['overall_status']}**\n\nXAWINWDO: qualified={x['qualified']} · stage={x['materialization_next_stage']} · aligned={x['aligned_session_count']} · usable={x['usable_return_count']} · splits={json.dumps(x['split_counts'],sort_keys=True)}\n\nGrammar: proposals={g['scout_proposals_current']} · eligible={g['scouted_not_preregistered_current']} · handoff new={g['handoff_new_current']} · handoff cumulative={g['handoff_unique_cumulative']} · prereg cumulative={g['preregistered_unique_cumulative']} · transported current={g['transported_current']}\n\nLegacy: affected={l['affected']} · completed={l['completed']} · remaining={l['remaining']} · survivors={l['survivors']} · source_gate_green={l['source_gate_green']}\n"
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--runtime-root',required=True); ap.add_argument('--output',required=True); ap.add_argument('--markdown-output'); a=ap.parse_args(); out=build(Path(a.runtime_root)); Path(a.output).write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');
 if a.markdown_output:Path(a.markdown_output).write_text(markdown(out),encoding='utf-8')
 print(json.dumps({'overall_status':out['overall_status'],'executive_counters':out['executive_counters']},sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
