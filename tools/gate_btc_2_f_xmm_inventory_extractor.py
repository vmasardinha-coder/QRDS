#!/usr/bin/env python3
from __future__ import annotations
import argparse, asyncio, json, math, statistics, time
from collections import defaultdict
from pathlib import Path


def imbalance(bid_sizes, ask_sizes):
    b, a = sum(bid_sizes), sum(ask_sizes)
    if b + a <= 0:
        raise ValueError("nonpositive total depth")
    return (b - a) / (b + a)


def book_features(bids, asks):
    if len(bids) < 10 or len(asks) < 10:
        raise ValueError("need depth10")
    bids = [(float(p), float(s)) for p, s in bids[:10]]
    asks = [(float(p), float(s)) for p, s in asks[:10]]
    vals = [x for pair in bids + asks for x in pair]
    if not all(math.isfinite(x) and x > 0 for x in vals):
        raise ValueError("nonpositive/nonfinite level")
    if any(bids[i][0] <= bids[i+1][0] for i in range(9)):
        raise ValueError("bids not descending")
    if any(asks[i][0] >= asks[i+1][0] for i in range(9)):
        raise ValueError("asks not ascending")
    bid1, bsz1 = bids[0]; ask1, asz1 = asks[0]
    if bid1 > ask1:
        raise ValueError("crossed book")
    mid = (bid1 + ask1) / 2.0
    imb1 = imbalance([bsz1], [asz1])
    imb5 = imbalance([s for _, s in bids[:5]], [s for _, s in asks[:5]])
    imb10 = imbalance([s for _, s in bids], [s for _, s in asks])
    micro = (ask1 * bsz1 + bid1 * asz1) / (bsz1 + asz1)
    b10 = sum(s for _, s in bids); a10 = sum(s for _, s in asks)
    out = {
        "spread_bps": (ask1 - bid1) / mid * 10000.0,
        "imbalance_l1": imb1,
        "imbalance_l5": imb5,
        "imbalance_l10": imb10,
        "microprice_deviation_bps": (micro - mid) / mid * 10000.0,
        "bid_concentration_l1_l10": bsz1 / b10,
        "ask_concentration_l1_l10": asz1 / a10,
        "imbalance_shape": imb1 - imb10,
    }
    if not all(math.isfinite(v) for v in out.values()):
        raise ValueError("nonfinite feature")
    if any(abs(out[k]) > 1.0 + 1e-12 for k in ("imbalance_l1","imbalance_l5","imbalance_l10")):
        raise ValueError("imbalance out of bounds")
    return out


def summarize(events, rejected):
    by = defaultdict(list)
    for e in events: by[e["venue"]].append(e)
    if not by["BINANCE"] or not by["OKX"]:
        return {"quality_pass": False, "reason": "missing_venue"}
    for v in by: by[v].sort(key=lambda x: x["receipt_ms"])
    start = max(by["BINANCE"][0]["receipt_ms"], by["OKX"][0]["receipt_ms"])
    end = min(by["BINANCE"][-1]["receipt_ms"], by["OKX"][-1]["receipt_ms"])
    overlap = max(0.0, (end-start)/1000.0)
    med_spread = {v: statistics.median(x["features"]["spread_bps"] for x in by[v]) for v in by}
    crossed = sum(1 for e in events if e["crossed"])
    callbacks = len(events) + sum(rejected.values())
    accounted = (len(events) + sum(rejected.values())) / callbacks if callbacks else 0.0
    passed = (len(by["BINANCE"]) >= 100 and len(by["OKX"]) >= 100 and overlap >= 30 and crossed == 0 and all(x > 0 for x in med_spread.values()) and accounted >= 0.95)
    med = {v: {k: statistics.median(e["features"][k] for e in by[v]) for k in next(iter(by[v]))["features"]} for v in by}
    return {
        "quality_pass": passed,
        "updates": {v: len(by[v]) for v in by},
        "shared_overlap_seconds": overlap,
        "median_features": med,
        "median_spread_bps": med_spread,
        "crossed_accepted_books": crossed,
        "rejected": dict(sorted(rejected.items())),
        "callback_accounting_fraction": accounted,
        "disposition": "FAMILY_FEATURE_CAPTURE_READY" if passed else "CAPTURE_NOT_ESTABLISHED",
    }


def main():
    from cryptofeed import FeedHandler
    from cryptofeed.connection import RestEndpoint, Routes, WebsocketEndpoint
    from cryptofeed.defines import L2_BOOK
    from cryptofeed.exchanges import Binance, OKX
    class BinancePublicMirror(Binance):
        websocket_endpoints = [WebsocketEndpoint("wss://data-stream.binance.vision:443")]
        rest_endpoints = [RestEndpoint("https://data-api.binance.vision", routes=Routes("/api/v3/exchangeInfo", l2book="/api/v3/depth?symbol={}&limit={}"))]
    ap=argparse.ArgumentParser(); ap.add_argument("--duration", type=int, default=60); ap.add_argument("--output", required=True); args=ap.parse_args()
    out=Path(args.output); out.mkdir(parents=True, exist_ok=True)
    events=[]; rejected=defaultdict(int)
    async def cb(book, receipt_timestamp):
        venue=str(book.exchange).upper()
        if venue not in {"BINANCE","OKX"}: return
        try:
            bids=[book.book.bids.index(i) for i in range(10)]
            asks=[book.book.asks.index(i) for i in range(10)]
            feats=book_features(bids, asks)
            events.append({"venue":venue,"symbol":str(book.symbol),"receipt_ms":int(float(receipt_timestamp)*1000),"features":feats,"crossed":False})
        except Exception as exc:
            rejected[type(exc).__name__ + ":" + str(exc)] += 1
    fh=FeedHandler(); fh.add_feed(BinancePublicMirror(symbols=["BTC-USDT"], channels=[L2_BOOK], callbacks={L2_BOOK:cb}, max_depth=10)); fh.add_feed(OKX(symbols=["BTC-USDT"], channels=[L2_BOOK], callbacks={L2_BOOK:cb}, max_depth=10))
    loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop); loop.call_later(args.duration, loop.stop); started=time.time(); fh.run(); ended=time.time()
    with (out/"FEATURE_EVENTS.jsonl").open("w", encoding="utf-8") as f:
        for e in events: f.write(json.dumps(e, sort_keys=True)+"\n")
    s=summarize(events,rejected); s.update({"schema_version":"GATE_BTC_2_F_XMM_INVENTORY_V1","family_id":"F-XMM-INVENTORY","cryptofeed_version":"2.5.0","capture_duration_requested_seconds":args.duration,"capture_wall_seconds":ended-started,"accepted_events":len(events),"research_only":True,"shadow_only":True,"orders":0,"real_capital_brl":0,"no_retune":True,"no_backfill":True,"factory_runtime_untouched":True,"economic_claim_authorized":False,"factory_migration_authorized":False})
    (out/"SUMMARY.json").write_text(json.dumps(s,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(json.dumps(s,indent=2,sort_keys=True)); return 0 if s["quality_pass"] else 2
if __name__=="__main__": raise SystemExit(main())
