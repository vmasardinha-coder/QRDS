#!/usr/bin/env python3
import argparse,json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
def load(p):
 try:return json.loads(p.read_text(encoding='utf-8'))
 except:return {}
def build(root):
 scout=load(root/'GRAMMAR_SCOUT_RUNTIME.json'); hand=load(root/'GRAMMAR_HANDOFF_RUNTIME.json'); trans=load(root/'GRAMMAR_PREREG_TRANSPORT_RUNTIME.json'); st=Counter(x.get('status','UNKNOWN') for x in scout.get('proposals',[])); sigs=set()
 for p in (root/'grammar_handoff_audits').glob('*.json') if (root/'grammar_handoff_audits').exists() else []: sigs.update(x.get('grammar_signature') for x in load(p).get('requests',[]) if x.get('grammar_signature'))
 prereg=list((root/'grammar_preregistrations').glob('XAGRAMMAR_*.json')) if (root/'grammar_preregistrations').exists() else []
 return {'schema':'qrds.factory.grammar_pipeline_status.v1','generated_at_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'status':'ACTIVE_AUTONOMOUS' if scout else 'WAITING_FIRST_SCOUT','counters':{'proposals_current':len(scout.get('proposals',[])),'eligible_current':st['SCOUTED_NOT_PREREGISTERED'],'duplicate_current':st['DUPLICATE_CHANNEL_SUPPRESSED'],'insufficient_evidence_current':st['INSUFFICIENT_EXTERNAL_EVIDENCE_FAIL_CLOSED'],'handoff_new_current':int(hand.get('request_count',0) or 0),'handoff_unique_cumulative':len(sigs),'preregistered_unique_cumulative':len(prereg),'transported_current':int(trans.get('transported_count',0) or 0)},'next_stage':'AUTONOMOUS_SCOUT_HANDOFF_PREREG_SOURCE_COST_GATE','safety':{'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0,'NO_RETUNE':True,'NO_BACKFILL':True,'NO_COUNTER_RESET':True,'FAIL_CLOSED':True}}
def main():
 a=argparse.ArgumentParser(); a.add_argument('--root',required=True); a.add_argument('--output',required=True); x=a.parse_args(); d=build(Path(x.root)); Path(x.output).write_text(json.dumps(d,indent=2)+'\n'); print(json.dumps(d['counters'],sort_keys=True))
if __name__=='__main__':main()
