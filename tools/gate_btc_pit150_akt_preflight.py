"""Read-only exact native AKT source qualification; no admission."""
import argparse,json,hashlib
from datetime import datetime,timedelta,timezone
from pathlib import Path
import requests
from tools.gate_btc_pit150_qualified_history import ROUTES,check_identity,check_gate_contract,normalize_history

def preflight(session,out,cutoff):
    if cutoff >= datetime.now(timezone.utc).date().isoformat():raise ValueError("incomplete UTC cutoff")
    out=Path(out);out.mkdir(parents=True,exist_ok=True);route=ROUTES["AKT"];payloads=[];manifest=[]
    urls=["https://api.gateio.ws/api/v4/spot/currency_pairs/AKT_USDT",
          "https://api.gateio.ws/api/v4/spot/currencies/AKT",
          "https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair=AKT_USDT&interval=1d&limit=1000"]
    for label,url in zip(("pair","currency","candles"),urls):
        r=session.get(url,timeout=40);r.raise_for_status();raw=r.content;(out/(label+".json")).write_bytes(raw)
        payloads.append(json.loads(raw));manifest.append({"file":label+".json","url":url,"sha256":hashlib.sha256(raw).hexdigest()})
    check_identity(route,payloads[0]);check_gate_contract(route,payloads[1])
    rows=normalize_history("AKT",route,payloads[2],cutoff)
    raw=(json.dumps(rows,indent=2)+"\n").encode();(out/"NORMALIZED.json").write_bytes(raw)
    result={"status":"PASS_NATIVE_AKT_PREFLIGHT_NOT_ADMISSION","symbol":"AKT","coin_id":route["coin_id"],
            "source":"gate","native_chain":"AKT","token_contract":"","cutoff":cutoff,
            "effective_cutoff":route["effective_cutoff"],"rows":len(rows),"first":rows[0]["date"],"last":rows[-1]["date"],
            "rows_sha256":hashlib.sha256(raw).hexdigest(),"raw_manifest":manifest,
            "historical_scientific_credit":0,"orders":0,"real_capital":0}
    (out/"RESULT.json").write_bytes((json.dumps(result,indent=2)+"\n").encode());return result

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    p.add_argument("--cutoff",default=(datetime.now(timezone.utc)-timedelta(days=1)).date().isoformat())
    a=p.parse_args();print(json.dumps(preflight(requests.Session(),a.out,a.cutoff)))
