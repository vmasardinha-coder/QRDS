#!/usr/bin/env python3
import json,urllib.parse,urllib.request
from pathlib import Path
UA={"User-Agent":"QRDS-research-only/1.0"}
def get(params):
    u="https://api.bybit.com/v5/market/kline?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(u,headers=UA)
    with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode())
def fund(symbol):
    u="https://api.bybit.com/v5/market/funding/history?"+urllib.parse.urlencode({"category":"linear","symbol":symbol,"limit":1})
    req=urllib.request.Request(u,headers=UA)
    with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode())
def main():
    out={"schema":"qrds.factory.bybit_source_probe.v1","records":[],"errors":[],"scientific_credit":0,"economics_read":False}
    for a in ("BTC","ETH"):
        s=a+"USDT"
        for cat in ("spot","linear"):
            try:
                x=get({"category":cat,"symbol":s,"interval":"5","limit":3})
                assert x.get("retCode")==0 and x.get("result",{}).get("list")
                out["records"].append({"asset":a,"market":cat,"symbol":s,"rows":len(x["result"]["list"])})
            except Exception as e:out["errors"].append({"asset":a,"market":cat,"error":type(e).__name__+":"+str(e)})
        try:
            x=fund(s);assert x.get("retCode")==0 and x.get("result",{}).get("list")
            out["records"].append({"asset":a,"market":"funding","symbol":s,"rows":len(x["result"]["list"])})
        except Exception as e:out["errors"].append({"asset":a,"market":"funding","error":type(e).__name__+":"+str(e)})
    out["status"]="PASS" if len(out["records"])==6 and not out["errors"] else "FAIL_CLOSED"
    Path("out").mkdir(exist_ok=True);Path("out/BYBIT_SOURCE_PROBE.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
