#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import requests

INSTRUMENTS="https://www.okx.com/api/v5/public/instruments"
CANDLES="https://www.okx.com/api/v5/market/candles"
FUNDING_HISTORY="https://www.okx.com/api/v5/public/funding-rate-history"
SPOT="BTC-USDT"
SWAP="BTC-USDT-SWAP"


def utc_now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def _json(get,url,params):
    r=get(url,params=params,timeout=20); r.raise_for_status(); d=r.json()
    if d.get("code") not in (None,"0"): raise RuntimeError(f"OKX_ERROR:{d.get('code')}:{d.get('msg')}")
    return d

def _closed(rows):
    out={}
    for r in rows:
        if isinstance(r,list) and len(r)>=9 and str(r[8])=="1": out[int(r[0])]=r
    return out

def qualify(get=requests.get):
    source={"provider":"OKX_PUBLIC_API","status":"FAIL_CLOSED_SOURCE_UNVERIFIED"}
    try:
        spot_meta=_json(get,INSTRUMENTS,{"instType":"SPOT","instId":SPOT}).get("data") or []
        swap_meta=_json(get,INSTRUMENTS,{"instType":"SWAP","instId":SWAP}).get("data") or []
        if not spot_meta or not swap_meta or spot_meta[0].get("state")!="live" or swap_meta[0].get("state")!="live":
            raise ValueError("LIVE_INSTRUMENT_METADATA_MISSING")
        srows=_closed(_json(get,CANDLES,{"instId":SPOT,"bar":"1H","limit":10}).get("data") or [])
        prows=_closed(_json(get,CANDLES,{"instId":SWAP,"bar":"1H","limit":10}).get("data") or [])
        common=sorted(set(srows).intersection(prows))
        if not common: raise ValueError("NO_COMMON_CLOSED_1H_BAR")
        ts=common[-1]
        # OKX candle timestamp is bar open; confirmed 1H bar is available only after its close.
        bar_close_ms=ts+60*60*1000
        fh=_json(get,FUNDING_HISTORY,{"instId":SWAP,"limit":20}).get("data") or []
        causal=[]
        for row in fh:
            try:
                ft=int(row.get("fundingTime") or 0); fr=float(row["fundingRate"])
            except (ValueError,TypeError,KeyError):
                continue
            if ft<=bar_close_ms: causal.append((ft,fr))
        if not causal: raise ValueError("NO_CAUSAL_FUNDING_HISTORY_AT_COMMON_BAR_CLOSE")
        causal.sort()
        s=srows[ts]; p=prows[ts]
        if float(s[4])<=0 or float(p[4])<=0: raise ValueError("NONPOSITIVE_CLOSE")
        source={
            "provider":"OKX_PUBLIC_API","status":"QUALIFIED_PUBLIC_SOURCE","authentication_required":False,
            "spot_symbol":SPOT,"perpetual_symbol":SWAP,"interval":"1H",
            "common_closed_bar_open_ms":ts,"common_closed_bar_close_ms":bar_close_ms,
            "spot_closed_ohlcv_observed":True,"perpetual_closed_ohlcv_observed":True,
            "spot_metadata_live":True,"perpetual_metadata_live":True,
            "causal_funding_history_observed":True,"latest_causal_funding_time_ms":causal[-1][0],
            "sample_checks":{"spot_close_positive":True,"perpetual_close_positive":True,"funding_time_not_after_bar_close":causal[-1][0]<=bar_close_ms}
        }
    except (ValueError,TypeError,KeyError) as exc:
        source={"provider":"OKX_PUBLIC_API","status":"BLOCKED_REQUIRED_PUBLIC_SPOT_PERP_FIELD_MISSING","reason":f"{type(exc).__name__}:{exc}"}
    except Exception as exc:
        source={"provider":"OKX_PUBLIC_API","status":"FAIL_CLOSED_SOURCE_UNVERIFIED","reason":f"{type(exc).__name__}:{exc}"}
    ok=source["status"]=="QUALIFIED_PUBLIC_SOURCE"
    return {
        "schema":"gate_btc_2.pf_source_qualification_runtime.v1",
        "generated_at_utc":utc_now(),"namespace":"PF::68f5b4b1bcb58e95",
        "grammar_signature":"68f5b4b1bcb58e95ffec65c0e62e69da82c7d8f477f48c4d5d732ca5b24030ae",
        "channel_id":"CRYPTO_SPOT_PERP_BASIS_FUNDING","status":"SOURCE_QUALIFIED_FAMILY_READY_XAGENT_THIRD_INPUT_NOT_AUTHORIZED" if ok else source["status"],
        "source":source,
        "xagent_third_input_eligibility":{"status":"NOT_ESTABLISHED_SHARED_COMPONENTS","shared_with":"S-XTERM-CARRY-01","shared_components":["PERPETUAL_MARKET","FUNDING"],"count_as_third_input":False},
        "economic_outcomes_read":False,"signal_formula_defined":False,"direction_defined":False,"thresholds_defined":False,"historical_backfill_started":False,
        "next_gate":"ADVANCE_PARALLEL_FRONTIER_FOR_DISTINCT_XAGENT_CHANNEL" if ok else "RETAIN_BLOCKER_OR_ADVANCE_WITHOUT_CREDIT",
        "safety":{"research_only":True,"shadow_only":True,"engine_feed":False,"orders":0,"real_capital":0,"no_retune":True,"no_backfill":True,"h1_h31_untouched":True,"canonical_580_untouched":True}
    }

def self_test():
    class R:
        def __init__(self,d): self.d=d
        def raise_for_status(self): pass
        def json(self): return self.d
    ts=1800000000000
    candle=[str(ts),"100","101","99","100","10","10","1000","1"]
    def fake(url,params=None,timeout=20):
        if url==INSTRUMENTS: return R({"code":"0","data":[{"instId":params["instId"],"state":"live"}]})
        if url==CANDLES: return R({"code":"0","data":[candle]})
        if url==FUNDING_HISTORY: return R({"code":"0","data":[{"fundingTime":str(ts+1000),"fundingRate":"0.0001"}]})
        raise AssertionError(url)
    d=qualify(fake)
    assert d["status"]=="SOURCE_QUALIFIED_FAMILY_READY_XAGENT_THIRD_INPUT_NOT_AUTHORIZED"
    assert d["source"]["status"]=="QUALIFIED_PUBLIC_SOURCE"
    assert d["xagent_third_input_eligibility"]["count_as_third_input"] is False
    assert d["economic_outcomes_read"] is False
    print("PF_SPOT_PERP_SOURCE_SELF_TEST=PASS")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output"); ap.add_argument("--self-test",action="store_true"); a=ap.parse_args()
    if a.self_test: self_test(); return 0
    if not a.output: ap.error("--output required")
    d=qualify(); Path(a.output).write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":d["status"],"source":d["source"]["status"],"count_as_third":d["xagent_third_input_eligibility"]["count_as_third_input"]}))
    return 0
if __name__=="__main__": raise SystemExit(main())
