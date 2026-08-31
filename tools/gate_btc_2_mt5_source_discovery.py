#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

SAFETY_KEYS={"MT5_READ_ONLY":True,"NO_ORDER_SEND":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_BACKFILL":True,"NO_RETUNE":True,"H1_ECONOMICS_READ":False}

def h(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def build(packet,candidate):
    s=packet.get('safety') or {}
    boundary=all(s.get(k)==v for k,v in SAFETY_KEYS.items()) and packet.get('primary_scientific_truth') is False and packet.get('factory_economics_feedback_allowed') is False
    linked=candidate.get('source_packet_sha256')==packet.get('packet_sha256')
    available=boundary and linked and packet.get('readiness')=='READY_SHADOW_DATA_ONLY' and candidate.get('status')=='AVAILABLE_FOR_SOURCE_DISCOVERY_ONLY'
    out={
      'schema':'gate_btc.2_0.mt5_source_discovery_evidence.v1',
      'generated_at_utc':packet.get('generated_at_utc'),
      'status':'AVAILABLE_SOURCE_CANDIDATE' if available else 'MT5_UNAVAILABLE_FAIL_OPEN_TO_OTHER_SOURCES',
      'source_packet_sha256':packet.get('packet_sha256'),
      'source_candidate_sha256':candidate.get('candidate_sha256'),
      'record_count':int(packet.get('record_count',0) or 0) if available else 0,
      'source_role':'AUXILIARY_READ_ONLY_RESEARCH_SOURCE',
      'source_admission_pass':False,
      'requires_normal_source_admission':True,
      'blocks_other_sources':False,
      'may_replace_canonical_source_silently':False,
      'prospective_credit':0,'scientific_promotion_credit':0,'historical_backfill_credit':0,
      'economics_feedback_allowed':False,
      'safety':{k:s.get(k) for k in SAFETY_KEYS},
    }
    out['evidence_sha256']=h(out); return out

def main():
    a=argparse.ArgumentParser();a.add_argument('--packet',required=True);a.add_argument('--candidate',required=True);a.add_argument('--output',required=True);x=a.parse_args()
    p=json.load(open(x.packet,encoding='utf-8')); c=json.load(open(x.candidate,encoding='utf-8')); out=build(p,c)
    q=Path(x.output);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,sort_keys=True))
if __name__=='__main__': main()
