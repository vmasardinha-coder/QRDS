#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re
from pathlib import Path
PAT=re.compile(r'^(WIN|WDO)[FGHJKMNQUVXZ]\d{2}$')
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--packet',required=True); a=ap.parse_args(); p=json.loads(Path(a.packet).read_text()); roots={'WIN':[],'WDO':[]}
 for r in p.get('records',[]):
  s=str(r.get('symbol',''))
  if PAT.fullmatch(s): roots[s[:3]].append({'symbol':s,'earliest':r.get('earliest_observation_utc') or (r.get('bars') or [{}])[0].get('timestamp_utc'),'latest':r.get('latest_observation_utc'),'bars':len(r.get('bars') or [])})
 if not all(roots.values()): raise SystemExit('FAIL_CLOSED: WIN/WDO coverage incomplete')
 out={'source':'MT5_TERMINAL','roots':roots,'earliest':{k:min(x['earliest'] for x in v if x['earliest']) for k,v in roots.items()},'latest':{k:max(x['latest'] for x in v if x['latest']) for k,v in roots.items()},'bars':{k:sum(x['bars'] for x in v) for k,v in roots.items()}}
 print(json.dumps(out,indent=2,sort_keys=True))
if __name__=='__main__': main()
