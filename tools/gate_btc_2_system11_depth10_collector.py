#!/usr/bin/env python3
from __future__ import annotations
import argparse, asyncio, json, math, time
from collections import defaultdict
from pathlib import Path

VENUES={"BINANCE","OKX"}

def okx_spot_feed_class(okx, rest_endpoint, routes):
    """Discover only the approved spot market; unrelated derivatives cannot abort it."""
    class OKXSpotOnly(okx):
        rest_endpoints = [rest_endpoint("https://www.okx.com", routes=routes(
            ["/api/v5/public/instruments?instType=SPOT"]))]

        @classmethod
        def _parse_symbol_data(cls, data):
            # Exchange.symbol_mapping unwraps a single REST response in 2.5.0.
            entries = [data] if isinstance(data, dict) else data
            for entry in entries:
                if str(entry.get("code", "0")) != "0":
                    raise ValueError("OKX_SPOT_DISCOVERY_ERROR")
                if any(e.get("instType") != "SPOT" for e in entry["data"]):
                    raise ValueError("NON_SPOT_DISCOVERY_REJECTED")
            return super()._parse_symbol_data(entries)

    return OKXSpotOnly

def normalize_levels(levels):
    out=[(float(p),float(s)) for p,s in levels[:10]]
    if len(out)<10 or not all(math.isfinite(x) and x>0 for q in out for x in q): raise ValueError("DEPTH10_REQUIRED_OR_INVALID")
    return out

def eligible_book(bids,asks):
    b=normalize_levels(bids); a=normalize_levels(asks)
    if any(b[i][0]<=b[i+1][0] for i in range(9)): raise ValueError("BIDS_NOT_DESCENDING")
    if any(a[i][0]>=a[i+1][0] for i in range(9)): raise ValueError("ASKS_NOT_ASCENDING")
    if b[0][0]>a[0][0]: raise ValueError("CROSSED_BOOK")
    return b,a

def pair_seconds(events):
    by=defaultdict(dict)
    for e in events:
        sec=e["receipt_ms"]//1000
        by[sec][e["venue"]]=e
    rows=[]
    for sec in sorted(by):
        z=by[sec]
        if VENUES.issubset(z):
            rows.append({"schema":"gate_btc.2_0.system11_depth10_pair.v1","pair_second_utc":sec,
              "observation_date":time.strftime("%Y-%m-%d",time.gmtime(sec)),"eligible_pair":True,
              "books":{v:{"receipt_ms":z[v]["receipt_ms"],"symbol":"BTC-USDT","bids":z[v]["bids"],"asks":z[v]["asks"]} for v in sorted(VENUES)}})
    return rows

def main():
    from cryptofeed import FeedHandler
    from cryptofeed.connection import RestEndpoint,Routes,WebsocketEndpoint
    from cryptofeed.defines import L2_BOOK
    from cryptofeed.exchanges import Binance,OKX
    class BinancePublicMirror(Binance):
        websocket_endpoints=[WebsocketEndpoint("wss://data-stream.binance.vision:443")]
        rest_endpoints=[RestEndpoint("https://data-api.binance.vision",routes=Routes("/api/v3/exchangeInfo",l2book="/api/v3/depth?symbol={}&limit={}"))]
    OKXSpotOnly = okx_spot_feed_class(OKX, RestEndpoint, Routes)
    ap=argparse.ArgumentParser(); ap.add_argument("--duration",type=int,default=300); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=True); events=[]; rejected=defaultdict(int); last_ms={}
    async def cb(book,receipt_timestamp):
        venue=str(book.exchange).upper()
        if venue not in VENUES:return
        try:
            ms=int(float(receipt_timestamp)*1000)
            if ms<=last_ms.get(venue,-1): raise ValueError("NON_CAUSAL_TIMESTAMP")
            bids=[book.book.bids.index(i) for i in range(10)]; asks=[book.book.asks.index(i) for i in range(10)]
            b,aa=eligible_book(bids,asks); last_ms[venue]=ms
            events.append({"venue":venue,"receipt_ms":ms,"bids":b,"asks":aa})
        except Exception as exc: rejected[str(exc)]+=1
    fh=FeedHandler(); fh.add_feed(BinancePublicMirror(symbols=["BTC-USDT"],channels=[L2_BOOK],callbacks={L2_BOOK:cb},max_depth=10)); fh.add_feed(OKXSpotOnly(symbols=["BTC-USDT"],channels=[L2_BOOK],callbacks={L2_BOOK:cb},max_depth=10))
    loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop); loop.call_later(a.duration,loop.stop); fh.run()
    pairs=pair_seconds(events)
    with (a.output/"PAIRS.jsonl").open("w") as f:
        for r in pairs:f.write(json.dumps(r,sort_keys=True)+"\n")
    s={"schema":"gate_btc.2_0.system11_depth10_capture.v1","status":"PROSPECTIVE_CAPTURE_COMPLETE","eligible_pairs":len(pairs),"raw_eligible_updates":len(events),"rejected":dict(rejected),"sampling_rule":"ONE_SYNCHRONIZED_ELIGIBLE_SNAPSHOT_PAIR_PER_SECOND","research_only":True,"shadow_only":True,"orders":0,"real_capital_brl":0,"no_backfill":True,"no_retune":True}
    (a.output/"SUMMARY.json").write_text(json.dumps(s,indent=2,sort_keys=True)+"\n"); print(json.dumps(s,indent=2,sort_keys=True))
if __name__=="__main__": main()
