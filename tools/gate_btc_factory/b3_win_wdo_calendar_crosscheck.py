#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SAFETY={"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"NO_COUNTER_RESET":True,"FAIL_CLOSED":True,"H1_ECONOMICS_READ":False}
ACCEPTED_KNOWN_GAPS={"2021-06-10":"OPERATOR_ACCEPTED_ISOLATED_PRIMARY_SOURCE_GAP_NO_RECONSTRUCTION_NO_BACKFILL"}

def sessions(capture_dir:Path)->set[str]:
 out=set()
 for zp in sorted(capture_dir.glob('COTAHIST_A*.ZIP')):
  with zipfile.ZipFile(zp) as z:
   for raw in z.open([n for n in z.namelist() if not n.endswith('/')][0]):
    line=raw.rstrip(b'\r\n')
    if len(line)==245 and line[:2]==b'01':
     ds=line[2:10].decode('ascii'); datetime.strptime(ds,'%Y%m%d'); out.add(f'{ds[:4]}-{ds[4:6]}-{ds[6:8]}')
 return out

def main()->int:
 ap=argparse.ArgumentParser(); ap.add_argument('--coverage-dir',required=True); ap.add_argument('--cotahist-dir',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
 files=sorted(Path(a.coverage_dir).glob('20??_Q?.json'))
 if len(files)!=20: raise RuntimeError(f'expected 20 quarter coverage files, got {len(files)}')
 cov=[]
 for p in files:
  x=json.loads(p.read_text());
  if x.get('schema')!='qrds.factory.b3_win_wdo_coverage_block.v1' or x.get('block_contract_pass') is not True: raise RuntimeError(f'{p.name}: invalid coverage block')
  cov.append(x)
 sess=sessions(Path(a.cotahist_dir)); noobj=sorted({d for x in cov for d in x.get('weekday_no_object_dates',[])})
 raw=sorted(d for d in noobj if d in sess); accepted=sorted(d for d in raw if d in ACCEPTED_KNOWN_GAPS); unresolved=sorted(d for d in raw if d not in ACCEPTED_KNOWN_GAPS)
 published=sorted({r['date'] for x in cov for r in x.get('rows',[]) if r.get('http_status')==200 and r.get('leaf_payloads')}); badpub=sorted(d for d in published if d not in sess)
 passed=not unresolved and not badpub
 result={"schema":"qrds.factory.b3_win_wdo_calendar_crosscheck.v1","generated_at_utc":datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),"frontier":"WIN_UNIVARIATE_WDO_UNIVARIATE","stage":"DATA_CALENDAR_CROSSCHECK","coverage_horizon":["2020-01-01","2024-12-31"],"calendar_reference":"OFFICIAL_B3_COTAHIST_DAILY_QUOTE_DATES","primary_surface":"BVBG.086.01_PRICEREPORT","quarter_count":20,"cotahist_session_count":len([d for d in sess if '2020-01-01'<=d<='2024-12-31']),"weekday_no_object_count":len(noobj),"weekday_no_object_dates":noobj,"corroborated_non_session_dates":sorted(d for d in noobj if d not in sess),"raw_primary_price_report_gaps_on_cotahist_sessions":raw,"accepted_known_primary_source_gaps":accepted,"accepted_known_gap_policy":ACCEPTED_KNOWN_GAPS,"inconsistent_price_report_gaps_on_cotahist_sessions":unresolved,"published_price_report_dates_not_in_cotahist":badpub,"calendar_crosscheck_pass":passed,"source_admission_pass":False,"source_admission_blocker":"IDENTITY_DEDUPE_PUBLICATION_TIMING_AND_PIT_QA_NOT_YET_FROZEN" if passed else "CALENDAR_CROSSCHECK_FAIL_UNRESOLVED_OFFICIAL_SESSION_GAP","economics_read_allowed":False,"family_creation_allowed":False,"prospective_credit":0,"scientific_credit":0,"safety":SAFETY}
 out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n'); print(json.dumps({"calendar_crosscheck_pass":passed,"accepted_known_gap_count":len(accepted),"unresolved_session_gap_count":len(unresolved),"source_admission_pass":False},sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
