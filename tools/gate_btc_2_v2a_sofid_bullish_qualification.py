#!/usr/bin/env python3
"""Fail-closed physical qualifier for preregistered SOFID/Bullish spot source.

Qualification only. Preserves raw bytes/SHA-256 and validates exact market identity
plus physical public market data. Never admits source or grants D0/scientific credit.
If Bullish's candle surface is unavailable, the already-preregistered same-provider
public historical-trades surface is tried explicitly and recorded, never silently.
"""
from __future__ import annotations
import argparse, hashlib, json, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = "https://api.exchange.bullish.com/trading-api"

def request_bytes(url: str, retries: int = 3) -> bytes:
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept":"application/json","User-Agent":"QRDS-GateBTC2-ResearchOnly/1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as exc:
            last = exc; time.sleep(2**i)
    raise RuntimeError(f"source request failed after {retries} attempts: {last}")

def parse_identity(raw: bytes, pair: str) -> dict:
    obj = json.loads(raw.decode())
    if not isinstance(obj, dict): raise ValueError("unexpected Bullish market payload")
    if obj.get("symbol") != pair: raise ValueError("Bullish symbol mismatch")
    if obj.get("baseSymbol") != "SOFID" or obj.get("quoteSymbol") != "USDC": raise ValueError("Bullish base/quote mismatch")
    if obj.get("marketType") != "SPOT" or obj.get("spotTradingEnabled") is not True: raise ValueError("Bullish market is not enabled SPOT")
    if obj.get("timeZone") not in ("Etc/UTC", "UTC"): raise ValueError("Bullish market timezone not UTC")
    return obj

def unwrap(raw: bytes) -> tuple[list[dict], dict]:
    obj = json.loads(raw.decode())
    if isinstance(obj, list): return obj, {}
    if isinstance(obj, dict) and isinstance(obj.get("data"), list): return obj["data"], obj.get("links") or {}
    raise ValueError("unexpected Bullish market-data envelope")

def parse_candles(items: list[dict], end: date) -> list[dict]:
    rows=[]
    for x in items:
        if not isinstance(x, dict): raise ValueError("Bullish candle row not object")
        needed=("createdAtTimestamp","open","high","low","close")
        if any(k not in x for k in needed): raise ValueError("Bullish candle schema mismatch")
        ts=int(x["createdAtTimestamp"]); op=float(x["open"]); hi=float(x["high"]); lo=float(x["low"]); cl=float(x["close"])
        bv=float(x.get("baseVolume", x.get("volume", 0))); qv=float(x.get("quoteVolume", 0))
        if bv < 0 or qv < 0: raise ValueError("negative volume")
        if not (lo <= min(op,cl) <= max(op,cl) <= hi): raise ValueError("OHLC invariant failed")
        day=datetime.fromtimestamp(ts/1000, timezone.utc).date()
        if day <= end: rows.append({"timestamp":ts,"day":day.isoformat(),"open":op,"high":hi,"low":lo,"close":cl,"base_volume":bv,"quote_volume":qv})
    return rows

def parse_trades(items: list[dict], pair: str, start_ms: int, end_ms: int) -> list[dict]:
    rows=[]
    for x in items:
        if not isinstance(x, dict): raise ValueError("Bullish trade row not object")
        needed=("tradeId","symbol","createdAtTimestamp","price","quantity")
        if any(k not in x for k in needed): raise ValueError("Bullish trade schema mismatch")
        if x["symbol"] != pair: raise ValueError("Bullish trade symbol mismatch")
        ts=int(x["createdAtTimestamp"]); px=float(x["price"]); qty=float(x["quantity"])
        if px <= 0 or qty < 0: raise ValueError("invalid trade price/quantity")
        if start_ms <= ts <= end_ms:
            rows.append({"trade_id":str(x["tradeId"]),"timestamp":ts,"price":px,"quantity":qty})
    return rows

def aggregate_daily(trades: list[dict]) -> list[dict]:
    grouped={}
    for t in sorted(trades,key=lambda r:(r["timestamp"],r["trade_id"])):
        day=datetime.fromtimestamp(t["timestamp"]/1000, timezone.utc).date().isoformat(); grouped.setdefault(day,[]).append(t)
    rows=[]
    for day, xs in sorted(grouped.items()):
        prices=[x["price"] for x in xs]; bv=sum(x["quantity"] for x in xs); qv=sum(x["price"]*x["quantity"] for x in xs)
        rows.append({"timestamp":xs[0]["timestamp"],"day":day,"open":prices[0],"high":max(prices),"low":min(prices),"close":prices[-1],"base_volume":bv,"quote_volume":qv,"trade_count":len(xs)})
    return rows

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--end",required=True); p.add_argument("--output",required=True); a=p.parse_args()
    out=Path(a.output); out.mkdir(parents=True,exist_ok=True); end=date.fromisoformat(a.end); pair="SOFIDUSDC"
    status="FAIL_CLOSED_SOURCE_OR_PARSE_ERROR"; err=None; rows=[]; pages=[]; identity=None; identity_sha=None; data_surface=None; candle_error=None
    try:
        iraw=request_bytes(f"{BASE}/v1/markets/{pair}"); (out/"RAW_IDENTITY.json").write_bytes(iraw); identity_sha=hashlib.sha256(iraw).hexdigest(); identity=parse_identity(iraw,pair)
        try:
            url=f"{BASE}/v1/markets/{pair}/candle?_pageSize=100&_metaData=true"
            seen=set()
            for n in range(20):
                raw=request_bytes(url); (out/f"RAW_CANDLE_{n:03d}.json").write_bytes(raw); items,links=unwrap(raw); parsed=parse_candles(items,end); rows.extend(parsed)
                pages.append({"surface":"CANDLE","page":n,"url":url,"sha256":hashlib.sha256(raw).hexdigest(),"raw_rows":len(items),"accepted_rows":len(parsed)})
                nxt=links.get("next") if isinstance(links,dict) else None
                if not nxt: break
                url=nxt if nxt.startswith("http") else "https://api.exchange.bullish.com"+nxt
                if url in seen: raise ValueError("repeated candle pagination link")
                seen.add(url)
            if not rows: raise ValueError("no in-window SOFIDUSDC candles")
            data_surface="PUBLIC_CANDLE"
        except Exception as exc:
            candle_error=str(exc); rows=[]
            # Same preregistered provider/market, explicit public historical-trades surface.
            start=end-timedelta(days=6)
            start_ms=int(datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc).timestamp()*1000)
            end_ms=int(datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc).timestamp()*1000)
            params={"createdAtTimestamp[gte]":str(start_ms),"createdAtTimestamp[lte]":str(end_ms),"_pageSize":"100","_metaData":"true"}
            url=f"{BASE}/v1/history/markets/{pair}/trades?"+urllib.parse.urlencode(params)
            seen=set(); trades=[]; pages=[]
            for n in range(100):
                raw=request_bytes(url); (out/f"RAW_TRADES_{n:03d}.json").write_bytes(raw); items,links=unwrap(raw); parsed=parse_trades(items,pair,start_ms,end_ms); trades.extend(parsed)
                pages.append({"surface":"HISTORICAL_TRADES","page":n,"url":url,"sha256":hashlib.sha256(raw).hexdigest(),"raw_rows":len(items),"accepted_rows":len(parsed)})
                nxt=links.get("next") if isinstance(links,dict) else None
                if not nxt: break
                url=nxt if nxt.startswith("http") else "https://api.exchange.bullish.com"+nxt
                if url in seen: raise ValueError("repeated trade pagination link")
                seen.add(url)
            ids=[t["trade_id"] for t in trades]
            if not trades: raise ValueError("no SOFIDUSDC historical trades in seven-day qualification window")
            if len(ids) != len(set(ids)): raise ValueError("duplicate Bullish trade ids")
            if not all(trades[i]["timestamp"] <= trades[i+1]["timestamp"] for i in range(len(trades)-1)): trades=sorted(trades,key=lambda r:(r["timestamp"],r["trade_id"]))
            rows=aggregate_daily(trades)
            expected={(start+timedelta(days=i)).isoformat() for i in range(7)}; have={r["day"] for r in rows}; missing=sorted(expected-have)
            if missing: raise ValueError(f"missing UTC trade-days in qualification window: {missing}")
            data_surface="PUBLIC_HISTORICAL_TRADES_AGGREGATED_DAILY"
        uniq={r["timestamp"]:r for r in rows}; rows=sorted(uniq.values(),key=lambda r:r["timestamp"])
        if len(uniq) != len(rows): raise ValueError("duplicate daily timestamps")
        if not all(rows[i]["timestamp"] < rows[i+1]["timestamp"] for i in range(len(rows)-1)): raise ValueError("non-monotonic timestamps")
        for r in rows:
            if r["base_volume"] < 0 or r["quote_volume"] < 0 or not (r["low"] <= min(r["open"],r["close"]) <= max(r["open"],r["close"]) <= r["high"]): raise ValueError("daily OHLCV QA failed")
        status="QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION"
    except Exception as exc: err=str(exc)
    summary={"schema_version":"GATE_BTC_2_V2A_SOFID_BULLISH_QUALIFICATION_V2","symbol":"SOFID","coin_id":"sofiusd","provider":"BULLISH","market":"SPOT","pair":"SOFID/USDC","api_symbol":pair,"status":status,"requested_end_utc":a.end,"timezone":"UTC","identity_sha256":identity_sha,"instrument_identity":identity,"data_surface":data_surface,"candle_surface_error":candle_error,"pages":pages,"physical_rows_ok":len(rows),"earliest_day":rows[0]["day"] if rows else None,"latest_day":rows[-1]["day"] if rows else None,"qa_pass":status=="QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION","research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders":0,"real_capital_brl":0,"no_retune":True,"no_backfill":True,"no_counter_reset":True,"no_silent_source_substitution":True,"fail_closed":True,"qualification_only":True,"scientific_credit":False,"prospective_credit":False,"dataset_sealed":False,"promotion_allowed":False,"admission_scope":"NONE","retroactive_v2a_repair_allowed":False,"historical_coverage_sufficiency_asserted":False,"source_qualification_outcome":"ELIGIBLE_FOR_SEPARATE_PROSPECTIVE_ONLY_ADJUDICATION" if status=="QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION" else "FAIL_CLOSED","error":err}
    (out/"CANDLES.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in rows)); (out/"SUMMARY.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n"); print(json.dumps(summary,indent=2,sort_keys=True)); return 0 if summary["qa_pass"] else 2
if __name__ == "__main__": raise SystemExit(main())
