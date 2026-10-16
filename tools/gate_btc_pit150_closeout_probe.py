"""Read-only public-host capability receipt; no universe or ledger writes."""
import argparse,json
from datetime import datetime,timedelta,timezone
from pathlib import Path
import requests
from tools.gate_btc_pit150_qualified_history import collect_history,load_bybit_public_capture,ROUTES,BYBIT_CAPTURE_EFFECTIVE_CUTOFF

def main():
 p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);p.add_argument("--cutoff")
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 now=datetime.now(timezone.utc);cutoff=a.cutoff or (now-timedelta(days=1)).date().isoformat()
 result={"schema":"gate_btc.pit150_public_host_probe.v1","observed_at_utc":now.isoformat(),"cutoff":cutoff,"orders":0,"capital":0,"prospective_credit":0,"runtime_admission":False}
 try:
  rows,e=collect_history(requests.Session(),"USDY","ondo-us-dollar-yield",cutoff,a.out,now=now)
  result.update(status="PASS_EXACT_HISTORY_SOURCE_ONLY",closed_rows=len(rows),first=rows[0]["date"],last=rows[-1]["date"],evidence=e)
 except Exception as exc:
  result.update(status="SOURCE_UNAVAILABLE",error_type=type(exc).__name__,error=str(exc))
  try:
   rows,e=load_bybit_public_capture(requests.Session(),ROUTES["USDY"],"USDY",cutoff,a.out,now=now)
   result.update(status="PASS_PUBLIC_CAPTURE_PREFLIGHT_NOT_ADMISSION",closed_rows=len(rows),evidence=e,
                 production_effective_cutoff=BYBIT_CAPTURE_EFFECTIVE_CUTOFF)
  except Exception as relay_exc:
   result["capture_error"]=str(relay_exc)
 (a.out/"RESULT.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(result))
if __name__=="__main__":main()
