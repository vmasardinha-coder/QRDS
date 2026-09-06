#!/usr/bin/env python3
"""Physical Binance Spot qualification for the 50 failures frozen by #606.

Reads the canonical #605 RESULTS.json so symbol/coin_id identity is inherited from
physical parent evidence. Tests only exact Binance {SYMBOL}USDT, 33 UTC daily
candles, with zero credit/admission and no route switching.
"""
from __future__ import annotations
import argparse, hashlib, json, math, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

WINDOW_START=date(2026,8,4); WINDOW_END=date(2026,9,5); REQUIRED_DAYS=33
UA="QRDS-GateBTC2-ResearchOnly/legacy50-binance-v1"
EXPECTED=set("AAVE ADA ALGO AR ATOM AVAX BCH BNB BTC BTT CAKE CFX COMP CRV DASH DCR DOGE DOT ETC ETH FET FIL GNO GRT HBAR ICP INJ JST LINK LTC NEAR ONDO PAXG POL QNT RAY SHIB SOL STX SUN TRX TWT UNI VET WIF XLM XMR XRP XTZ ZEC".split())

def sha(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def req(url:str,retries:int=6)->bytes:
    last=None
    for n in range(retries):
        try:
            r=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":UA})
            with urllib.request.urlopen(r,timeout=60) as x: return x.read()
        except Exception as e:
            last=e; time.sleep(min(20,1.5*(2**n)))
    raise RuntimeError(f"request failed: {type(last).__name__}: {last}")
def u(base:str,params:dict)->str: return base+"?"+urllib.parse.urlencode(params)

def cg_bridge(coin_id:str,symbol:str)->tuple[bool,list[str],list[str]]:
    hashes=[]; seen=[]
    for page in range(1,4):
        raw=req(u(f"https://api.coingecko.com/api/v3/coins/{urllib.parse.quote(coin_id,safe='')}/tickers",{"page":page,"order":"trust_score_desc"}))
        hashes.append(sha(raw)); obj=json.loads(raw); arr=obj.get("tickers",[]) if isinstance(obj,dict) else []
        for t in arr:
            market=str((t.get("market") or {}).get("identifier","")).lower(); base=str(t.get("base","")).upper(); target=str(t.get("target","")).upper()
            seen.append(f"{market}:{base}/{target}")
            if market=="binance" and base==symbol and target=="USDT": return True,hashes,seen
        if len(arr)<100: break
        time.sleep(.8)
    return False,hashes,seen

def qa(rows:list)->dict:
    days=[r["day"] for r in rows]; have=set(days); miss=[]; d=WINDOW_START
    while d<=WINDOW_END:
        if d.isoformat() not in have: miss.append(d.isoformat())
        d+=timedelta(days=1)
    dup=len(days)-len(have)
    numeric=all(all(math.isfinite(float(r[k])) for k in ("open","high","low","close")) and float(r["low"])<=min(float(r["open"]),float(r["close"]))<=max(float(r["open"]),float(r["close"]))<=float(r["high"]) for r in rows)
    mono=days==sorted(days)
    passed=len(rows)==REQUIRED_DAYS and dup==0 and not miss and numeric and mono
    return {"daily_bucket_count":len(rows),"duplicate_days":dup,"missing_days":miss,"finite_ohlc_and_invariant":numeric,"monotonic_daily_dates":mono,"qa_pass":passed}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--parent-results",type=Path,required=True); ap.add_argument("--out",type=Path,required=True); a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    parent=json.loads(a.parent_results.read_text(encoding="utf-8"))
    failed={x["symbol"]:x for x in parent if x.get("symbol") in EXPECTED}
    if set(failed)!=EXPECTED or len(failed)!=50: raise RuntimeError(f"frozen failure-set mismatch: {len(failed)}")
    exraw=req("https://api.binance.com/api/v3/exchangeInfo"); exhash=sha(exraw); ex=json.loads(exraw); exmap={x.get("symbol"):x for x in ex.get("symbols",[])}
    start_ms=int(datetime.combine(WINDOW_START,datetime.min.time(),tzinfo=timezone.utc).timestamp()*1000); end_ms=int(datetime.combine(WINDOW_END+timedelta(days=1),datetime.min.time(),tzinfo=timezone.utc).timestamp()*1000)-1
    results=[]
    for i,s in enumerate(sorted(EXPECTED),1):
        p=failed[s]; coin_id=p.get("coin_id",""); pair=f"{s}USDT"; print(f"QUALIFY {i}/50 {pair}",flush=True)
        r={"symbol":s,"coin_id":coin_id,"provider":"BINANCE_SPOT","pair":pair,"qualification":"QUALIFICATION_ONLY","source_admitted":False,"scientific_credit":False,"prospective_credit":False,"d0_credit":0}
        try:
            bridge,bh,seen=cg_bridge(coin_id,s)
            ident=exmap.get(pair) or {}; ident_ok=ident.get("baseAsset")==s and ident.get("quoteAsset")=="USDT"
            raw=req(u("https://api.binance.com/api/v3/klines",{"symbol":pair,"interval":"1d","startTime":start_ms,"endTime":end_ms,"limit":1000})); arr=json.loads(raw)
            rows=[{"day":datetime.fromtimestamp(int(x[0])/1000,timezone.utc).date().isoformat(),"open":float(x[1]),"high":float(x[2]),"low":float(x[3]),"close":float(x[4])} for x in arr]
            q=qa(rows); r.update({"coingecko_exact_market_bridge":bridge,"bridge_response_sha256":bh,"bridge_seen_sample":seen[:20],"official_identity_ok":ident_ok,"exchange_info_sha256":exhash,"official_identity":ident,"candle_response_sha256":sha(raw),**q})
            r["status"]="QUALIFIED_PHYSICAL_SOURCE_PENDING_SEPARATE_ADJUDICATION" if bridge and ident_ok and q["qa_pass"] else "FAIL_CLOSED_FULL_CORPUS_OR_IDENTITY_QA"
        except Exception as e: r.update({"qa_pass":False,"status":"FAIL_CLOSED_SOURCE_OR_PARSE","error":f"{type(e).__name__}: {e}"})
        results.append(r); time.sleep(.25)
    failed_syms=[x["symbol"] for x in results if x.get("status")!="QUALIFIED_PHYSICAL_SOURCE_PENDING_SEPARATE_ADJUDICATION"]
    summary={"schema_version":"GATE_BTC_2_V2A_LEGACY50_BINANCE_QUALIFICATION_V1","parent_pr":605,"prereg_pr":606,"window_start_utc":WINDOW_START.isoformat(),"window_end_utc":WINDOW_END.isoformat(),"target_symbol_count":50,"passed_symbol_count":50-len(failed_syms),"failed_symbol_count":len(failed_syms),"failed_symbols":failed_syms,"all_50_pass":not failed_syms,"results":results,"qualification_only":True,"source_admission_changed":False,"complete_registry_claimed":False,"collector_override_activation_allowed":False,"d0_started":False,"historical_credit":0,"scientific_credit":False,"prospective_credit":False,"d0_credit":0,"research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders":0,"real_capital_brl":0,"no_retune":True,"no_backfill":True,"no_counter_reset":True,"no_silent_source_substitution":True,"fail_closed":True}
    (a.out/"RESULTS.json").write_text(json.dumps(results,indent=2,sort_keys=True)+"\n",encoding="utf-8"); (a.out/"SUMMARY.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:summary[k] for k in ("target_symbol_count","passed_symbol_count","failed_symbol_count","failed_symbols","all_50_pass")},sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
