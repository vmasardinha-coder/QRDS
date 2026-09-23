#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import requests

PRODUCER_ID="S-XTERM-CARRY-01"
OKX_INSTRUMENTS="https://www.okx.com/api/v5/public/instruments"
OKX_TICKER="https://www.okx.com/api/v5/market/ticker"
OKX_FUNDING="https://www.okx.com/api/v5/public/funding-rate"
YEAR_MS=365.0*24*60*60*1000


def stable_hash(obj: dict) -> str:
    payload=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def _json(get,url,params):
    r=get(url,params=params,timeout=20)
    r.raise_for_status()
    d=r.json()
    if d.get("code") not in (None,"0"):
        raise RuntimeError(f"OKX_ERROR:{d.get('code')}:{d.get('msg')}")
    return d


def collect(get=requests.get, now_ms: int | None=None) -> dict:
    capture_ms=int(now_ms if now_ms is not None else datetime.now(timezone.utc).timestamp()*1000)
    fut=_json(get,OKX_INSTRUMENTS,{"instType":"FUTURES","instFamily":"BTC-USD"}).get("data") or []
    swp=_json(get,OKX_INSTRUMENTS,{"instType":"SWAP","instFamily":"BTC-USD"}).get("data") or []
    futures=[r for r in fut if r.get("state")=="live" and int(r.get("expTime") or 0)>capture_ms]
    futures.sort(key=lambda r:int(r["expTime"]))
    swaps=[r for r in swp if r.get("state")=="live" and r.get("instType")=="SWAP"]
    if not futures or not swaps:
        raise RuntimeError("REQUIRED_LIVE_FUTURE_OR_SWAP_MISSING")
    future,swap=futures[0],swaps[0]
    ftk=_json(get,OKX_TICKER,{"instId":future["instId"]}).get("data") or []
    ptk=_json(get,OKX_TICKER,{"instId":swap["instId"]}).get("data") or []
    fr=_json(get,OKX_FUNDING,{"instId":swap["instId"]}).get("data") or []
    if not ftk or not ptk or not fr:
        raise RuntimeError("REQUIRED_PUBLIC_TERM_STRUCTURE_ROW_MISSING")
    future_px=float(ftk[0]["last"]); perp_px=float(ptk[0]["last"])
    expiry_ms=int(future["expTime"])
    funding=float(fr[0]["fundingRate"])
    funding_time=int(fr[0]["fundingTime"]); next_funding=int(fr[0]["nextFundingTime"])
    if future_px<=0 or perp_px<=0: raise RuntimeError("NONPOSITIVE_PRICE")
    if expiry_ms<=capture_ms: raise RuntimeError("EXPIRY_NOT_FUTURE")
    if next_funding<=funding_time: raise RuntimeError("NONPOSITIVE_FUNDING_INTERVAL")
    basis_ann=((future_px/perp_px)-1.0)*(YEAR_MS/(expiry_ms-capture_ms))
    funding_ann=funding*(YEAR_MS/(next_funding-funding_time))
    carry_gap=basis_ann-funding_ann
    signal=carry_gap/(1.0+abs(carry_gap))
    rec={
        "schema":"gate_btc_2.xagent_signal_observation.v1",
        "producer_id":PRODUCER_ID,
        "evidence_class":"DERIVATIVES_TERM_STRUCTURE_CARRY",
        "venue":"OKX",
        "market":"BTC-USD_DATED_FUTURE_VS_SWAP",
        "dated_symbol":future["instId"],
        "perpetual_symbol":swap["instId"],
        "capture_time_ms":capture_ms,
        "available_after_ms":capture_ms,
        "dated_expiry_ms":expiry_ms,
        "funding_time_ms":funding_time,
        "next_funding_time_ms":next_funding,
        "basis_annualized":basis_ann,
        "funding_annualized":funding_ann,
        "carry_gap":carry_gap,
        "signal":signal,
        "signal_range":[-1.0,1.0],
        "semantic_state":"DATED_PREMIUM_DOMINATES" if signal>0 else ("PERP_FUNDING_DOMINATES" if signal<0 else "BALANCED_CARRY"),
        "source_checks":{
            "dated_price_positive":True,"perpetual_price_positive":True,
            "expiry_strictly_future":True,"funding_interval_positive":True,
            "operational_primary":"OKX_PUBLIC_API",
            "source_qualified_via_preoutcome_transport_failover":True
        },
        "economic_outcomes_read":False,
        "economic_return_direction_claim":False,
        "alpha_claim":False,
        "scientific_credit":0,
        "survivor_credit":0,
        "promotion_authority":False,
        "engine_feed":False,"orders":0,"real_capital":0,"no_backfill":True,"no_retune":True
    }
    rec["record_sha256"]=stable_hash(rec)
    return rec


def self_test():
    class R:
        def __init__(self,d): self.d=d
        def raise_for_status(self): pass
        def json(self): return self.d
    now=1_800_000_000_000
    def fake(url,params=None,timeout=20):
        if url==OKX_INSTRUMENTS and params["instType"]=="FUTURES": return R({"code":"0","data":[{"instId":"BTC-USD-270101","instType":"FUTURES","state":"live","expTime":str(now+365*24*60*60*1000)}]})
        if url==OKX_INSTRUMENTS: return R({"code":"0","data":[{"instId":"BTC-USD-SWAP","instType":"SWAP","state":"live"}]})
        if url==OKX_TICKER and params["instId"].endswith("SWAP"): return R({"code":"0","data":[{"last":"100"}]})
        if url==OKX_TICKER: return R({"code":"0","data":[{"last":"110"}]})
        if url==OKX_FUNDING: return R({"code":"0","data":[{"fundingRate":"0.001","fundingTime":str(now),"nextFundingTime":str(now+8*60*60*1000)}]})
        raise AssertionError(url)
    d=collect(fake,now)
    expected_basis=0.1
    expected_funding=0.001*(365*24/8)
    gap=expected_basis-expected_funding
    expected=gap/(1+abs(gap))
    assert abs(d["basis_annualized"]-expected_basis)<1e-12
    assert abs(d["funding_annualized"]-expected_funding)<1e-12
    assert abs(d["signal"]-expected)<1e-12
    assert -1<d["signal"]<1
    assert d["economic_outcomes_read"] is False and d["survivor_credit"]==0
    print("S_XTERM_CARRY_01_SELF_TEST=PASS")


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output"); ap.add_argument("--self-test",action="store_true"); a=ap.parse_args()
    if a.self_test: self_test(); return 0
    if not a.output: ap.error("--output required")
    d=collect(); Path(a.output).write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"producer_id":d["producer_id"],"capture_time_ms":d["capture_time_ms"],"signal":d["signal"],"record_sha256":d["record_sha256"]},sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())
