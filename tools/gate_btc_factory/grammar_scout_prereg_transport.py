#!/usr/bin/env python3
"""Transport Grammar Scout handoff requests into immutable separate preregistration envelopes.
No economics, H allocation, threshold search, or existing-family mutation is permitted here.
"""
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
SAFETY={'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0,'NO_RETUNE':True,'NO_BACKFILL':True,'NO_COUNTER_RESET':True,'FAIL_CLOSED':True,'H1_H31_UNTOUCHED':True}
def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True)
def family_id(sig): return 'XAGRAMMAR_'+sig[:12].upper()
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--handoff',required=True); ap.add_argument('--ledger-dir',required=True); ap.add_argument('--output',required=True); a=ap.parse_args()
 hand=json.loads(Path(a.handoff).read_text(encoding='utf-8')); led=Path(a.ledger_dir); led.mkdir(parents=True,exist_ok=True)
 if hand.get('mode')!='OUTCOME_BLIND_HANDOFF_ONLY': raise SystemExit('FAIL_CLOSED: handoff not outcome blind')
 emitted=[]
 for r in hand.get('requests',[]):
  if r.get('status')!='ELIGIBLE_FOR_SEPARATE_PREREGISTRATION_GATE' or r.get('economics_read') is not False: continue
  sig=r['grammar_signature']; fid=family_id(sig); p=led/(fid+'.json')
  envelope={'schema':'qrds.factory.grammar_scout_separate_prereg.v1','family_id':fid,'grammar_signature':sig,'channel_id':r.get('channel_id'),'mechanism':r.get('mechanism'),'required_new_data':r.get('required_new_data',[]),'official_free_source_candidates':r.get('official_free_source_candidates',[]),'created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'PREREGISTERED_AWAITING_SOURCE_COST_QUALIFICATION','source_qualification_required':True,'cost_applicability_required':True,'economics_read':False,'historical_testing_started':False,'prospective_credit':0,'existing_counter_credit':0,'next_stage':'SOURCE_COST_QUALIFICATION_THEN_EXISTING_FACTORY','safety':SAFETY}
  if p.exists():
   old=json.loads(p.read_text(encoding='utf-8'))
   if old.get('grammar_signature')!=sig: raise SystemExit('FAIL_CLOSED: family id collision')
  else: p.write_text(json.dumps(envelope,indent=2,sort_keys=True)+'\n',encoding='utf-8')
  emitted.append({'family_id':fid,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'status':'PREREGISTERED_AWAITING_SOURCE_COST_QUALIFICATION'})
 out={'schema':'qrds.factory.grammar_scout_prereg_transport_runtime.v1','generated_at_utc':datetime.now(timezone.utc).isoformat(),'transported_count':len(emitted),'families':emitted,'next_stage':'SOURCE_COST_QUALIFICATION_THEN_EXISTING_FACTORY','safety':SAFETY}
 Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(out,indent=2))
if __name__=='__main__': main()
