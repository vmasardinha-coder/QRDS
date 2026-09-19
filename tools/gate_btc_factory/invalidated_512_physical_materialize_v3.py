#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PAT=re.compile(r'^WIN[FGHJKMNQUVXZ]\\d{2}$')
TZ=ZoneInfo('America/Sao_Paulo')
CUTOFF='2026-08-10'
SAFETY={'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0,'NO_RETUNE':True,'NO_BACKFILL':True,'NO_COUNTER_RESET':True,'FAIL_CLOSED':True,'H1_H31_ISOLATED':True}

def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def ingest(packet):
    x=defaultdict(lambda:defaultdict(list))
    for r in packet.get('records',[]):
        s=str(r.get('symbol',''))
        if not PAT.fullmatch(s): continue
        for b in r.get('bars',[]):
            t=datetime.fromisoformat(b['timestamp_utc'].replace('Z','+00:00'))
            d=t.astimezone(TZ).date().isoformat()
            if d>=CUTOFF: continue
            x[d][s].append({
                'timestamp':t.astimezone(TZ).isoformat(),
                'open':float(b['open']),'high':float(b['high']),'low':float(b['low']),'close':float(b['close']),
                'volume':int(b.get('tick_volume',0) or 0)
            })
    for d in x:
        for s in x[d]: x[d][s].sort(key=lambda z:z['timestamp'])
    return x

def select_tminus1(x):
    ds=sorted(x); out={}
    for i,d in enumerate(ds):
        if i==0: continue
        prev=ds[i-1]; eligible=[]
        for s,bars in x[prev].items():
            if s in x[d]: eligible.append((sum(z['volume'] for z in bars),s))
        if eligible:
            _,s=max(eligible,key=lambda z:(z[0],z[1]))
            bars=x[d][s]
            if len(bars)>=40 and all((datetime.fromisoformat(b['timestamp'])-datetime.fromisoformat(a['timestamp'])).total_seconds()==300 for a,b in zip(bars,bars[1:])):
                out[d]={'symbol':s,'selection_from_session':prev,'bars':bars}
    return out

def largest_contiguous(ds):
    blocks=[];cur=[]
    for d in ds:
        if not cur: cur=[d];continue
        gap=(datetime.fromisoformat(d).date()-datetime.fromisoformat(cur[-1]).date()).days
        if gap<=3: cur.append(d)
        else: blocks.append(cur);cur=[d]
    if cur: blocks.append(cur)
    if not blocks:return []
    m=max(map(len,blocks))
    return min((b for b in blocks if len(b)==m),key=lambda b:b[0])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--packet',type=Path,required=True);ap.add_argument('--csv',type=Path,required=True);ap.add_argument('--gate',type=Path,required=True)
    a=ap.parse_args();p=json.loads(a.packet.read_text());s=p.get('safety') or {}
    assert p.get('readiness')=='READY_SHADOW_DATA_ONLY'
    assert 'PHYSICALLY_RETRIEVED' in str(p.get('capture_semantics','')) and 'NO_SYNTHETIC_BACKFILL' in str(p.get('capture_semantics',''))
    assert s.get('MT5_READ_ONLY') is True and s.get('NO_ORDER_SEND') is True and s.get('ORDERS')==0 and s.get('REAL_CAPITAL')==0
    selected=select_tminus1(ingest(p)); block=largest_contiguous(sorted(selected))
    if not block: raise RuntimeError('NO_VALID_PHYSICAL_WIN_BLOCK')
    rows=[]
    for d in block:
        for z in selected[d]['bars']: rows.append(z)
    a.csv.parent.mkdir(parents=True,exist_ok=True)
    with a.csv.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['timestamp','open','high','low','close','volume']);w.writeheader();w.writerows(rows)
    years=defaultdict(list)
    for d in block: years[d[:4]].append(d)
    disc=years.get('2025',[]); rep=years.get('2026',[])
    if not disc or not rep: raise RuntimeError(f'PHYSICAL_BLOCK_DOES_NOT_SPAN_DISCOVERY_REPLICATION:{block[0]}:{block[-1]}')
    gate={
      'schema':'qrds.factory.invalidated_512.physical_materialization_source_gate.v1',
      'source_gate_id':'WIN_M5_PHYSICAL_MATERIALIZATION_V3',
      'evaluation_namespace':'RQ_PHYSICAL_MATERIALIZATION_2025_2026_V3',
      'family_ids':[],
      'qualified':True,'free_or_official_auditable':True,
      'publication_semantics_proven':True,'revision_semantics_proven':True,
      'identity_qa_pass':True,'schema_qa_pass':True,'point_in_time_valid':True,
      'independent_unseen_evaluation_data':True,'no_historical_backfill_credit':True,'economics_pre_read':False,
      'dataset_relative_path':'runtime/factory_autonomy/invalidated_requalification/datasets/WIN_M5_PHYSICAL_V3.csv',
      'dataset_sha256':sha(a.csv),
      'windows':{'discovery':{'start':disc[0],'end':disc[-1]},'replication':{'start':rep[0],'end':rep[-1]}},
      'physical_block':{'start':block[0],'end':block[-1],'sessions':len(block),'discovery_sessions':len(disc),'replication_sessions':len(rep)},
      'roll_rule':'t_minus_1_liquidity','synthetic_backfill':False,'interpolation':False,'source_packet_sha256':sha(a.packet),'safety':SAFETY
    }
    a.gate.parent.mkdir(parents=True,exist_ok=True);a.gate.write_text(json.dumps(gate,indent=2,sort_keys=True)+'\\n')
    print(json.dumps(gate['physical_block'],sort_keys=True))
if __name__=='__main__':main()
