#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re
from collections import defaultdict
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
FAMILY="XAWINWDO_REGIME_005"; PAT=re.compile(r"^(WIN|WDO)[FGHJKMNQUVXZ]\d{2}$"); TZ=ZoneInfo("America/Sao_Paulo"); EMBARGO=20; MAX_LOOKBACK=60
SAFETY={"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"NO_COUNTER_RESET":True,"FAIL_CLOSED":True}
def sessions(packet):
 d=defaultdict(lambda:defaultdict(int))
 for r in packet.get("records",[]):
  s=r.get("symbol","")
  if not PAT.fullmatch(s): continue
  root=s[:3]
  for b in r.get("bars",[]):
   day=datetime.fromisoformat(b["timestamp_utc"].replace("Z","+00:00")).astimezone(TZ).date().isoformat(); d[root][day]+=1
 return sorted(set(d["WIN"])&set(d["WDO"]))
def blocks(ds):
 if not ds:return []
 out=[]; cur=[ds[0]]
 for x in ds[1:]:
  a=datetime.fromisoformat(cur[-1]).date(); b=datetime.fromisoformat(x).date()
  # continuity is trading-session continuity: weekend gaps allowed; longer calendar gaps terminate block.
  if (b-a).days<=3: cur.append(x)
  else: out.append(cur); cur=[x]
 out.append(cur); return out
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--packet",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
 p=json.load(open(a.packet,encoding="utf-8")); assert p.get("family_scope")=="XAWINWDO_REGIME_002"
 ds=sessions(p); bs=blocks(ds); best=sorted(bs,key=lambda x:(-len(x),x[0]))[0] if bs else []
 n=len(best); d=int(n*.5); v=int(n*.3); counts={"discovery":max(0,d-EMBARGO),"validation":max(0,(d+v-EMBARGO)-(d+EMBARGO)),"holdout":max(0,n-(d+v+EMBARGO))}
 capacity=n>MAX_LOOKBACK and all(x>0 for x in counts.values())
 out={"schema":"qrds.factory.xawinwdo_regime_003.capacity_audit.v1","family_id":FAMILY,"economics_read":False,"selection_rule":"largest_contiguous_synchronized_physical_session_block_earliest_tie","synchronized_session_count_all":len(ds),"block_count":len(bs),"largest_block":{"start":best[0] if best else None,"end":best[-1] if best else None,"sessions":n},"frozen_rolling_dependence_windows":[20,60],"frozen_max_lookback_sessions":MAX_LOOKBACK,"embargo_sessions":EMBARGO,"post_embargo_split_capacity":counts,"capacity_pass":capacity,"next_stage":"DISCOVERY_ALLOWED" if capacity else "FAIL_CLOSED_INSUFFICIENT_CONTIGUOUS_PHYSICAL_CAPACITY","safety":SAFETY}
 Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(out,indent=2)+"\n"); print(json.dumps(out,sort_keys=True))
if __name__=="__main__": main()
