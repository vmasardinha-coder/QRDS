#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

FAMILY='XAWINWDO_REGIME_001'
PAT=re.compile(r'^(WIN|WDO)[FGHJKMNQUVXZ]\d{2}$')

def h(b): return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--packet',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
 raw=Path(a.packet).read_bytes(); p=json.loads(raw)
 if p.get('source')!='MT5_TERMINAL' or p.get('readiness')!='READY_SHADOW_DATA_ONLY': raise SystemExit('FAIL_CLOSED: MT5 packet unavailable')
 records=[r for r in p.get('records',[]) if PAT.fullmatch(str(r.get('symbol',''))) and r.get('bars')]
 roots={r['symbol'][:3] for r in records}
 if roots!={'WIN','WDO'}: raise SystemExit('FAIL_CLOSED: both WIN and WDO qualified contracts required')
 for r in records:
  bars=r['bars']; ts=[b.get('timestamp_utc') for b in bars]
  if not all(ts) or ts!=sorted(ts) or len(ts)!=len(set(ts)): raise SystemExit(f"FAIL_CLOSED: invalid timestamps {r['symbol']}")
  if not all(all(b.get(k) is not None for k in ('open','high','low','close','tick_volume')) for b in bars): raise SystemExit(f"FAIL_CLOSED: incomplete OHLCV {r['symbol']}")
 earliest=min(b['timestamp_utc'] for r in records for b in r['bars']); latest=max(b['timestamp_utc'] for r in records for b in r['bars'])
 out={'schema':'qrds.factory.xawinwdo.mt5_qualification.v1','family':FAMILY,'source':'MT5_TERMINAL','source_packet_sha256':h(raw),'status':'QUALIFIED_FOR_XAWINWDO_PRIMARY_EXPERIMENT_ONLY','contract_count':len(records),'roots':sorted(roots),'earliest_observation_utc':earliest,'latest_observation_utc':latest,'bars_total':sum(len(r['bars']) for r in records),'scientific_credit':0,'historical_backfill_credit':0,'safety':{'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0,'NO_RETUNE':True,'NO_COUNTER_RESET':True,'FAIL_CLOSED':True,'H1_H31_UNTOUCHED':True}}
 Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps(out,sort_keys=True))
if __name__=='__main__': main()
