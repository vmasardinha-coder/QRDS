#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import time
from pathlib import Path

from cryptofeed import FeedHandler
from cryptofeed.connection import RestEndpoint, Routes, WebsocketEndpoint
from cryptofeed.defines import L2_BOOK
from cryptofeed.exchanges import Binance, OKX


class BinancePublicMirror(Binance):
    """Same Binance spot venue via Binance's public market-data mirror.

    GitHub-hosted runners in some US regions receive HTTP 451 from
    api.binance.com before Cryptofeed can resolve symbols. This changes only
    the public transport endpoint, not venue, symbol, channel, or hypothesis.
    """
    websocket_endpoints = [WebsocketEndpoint("wss://data-stream.binance.vision:443")]
    rest_endpoints = [RestEndpoint(
        "https://data-api.binance.vision",
        routes=Routes("/api/v3/exchangeInfo", l2book="/api/v3/depth?symbol={}&limit={}"),
    )]


def corr(xs, ys):
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    vx = sum((x-mx)**2 for x in xs)
    vy = sum((y-my)**2 for y in ys)
    if vx <= 0 or vy <= 0:
        return 0.0
    return sum((x-mx)*(y-my) for x, y in zip(xs, ys)) / math.sqrt(vx*vy)


def analyze(events, grid_ms=250, max_age_ms=2000):
    by = {"BINANCE": [], "OKX": []}
    for e in events:
        by[e["venue"]].append(e)
    for v in by:
        by[v].sort(key=lambda x: x["receipt_ms"])
    if not by["BINANCE"] or not by["OKX"]:
        return {"quality_pass": False, "reason": "missing_venue"}

    start = max(by["BINANCE"][0]["receipt_ms"], by["OKX"][0]["receipt_ms"])
    end = min(by["BINANCE"][-1]["receipt_ms"], by["OKX"][-1]["receipt_ms"])
    start = ((start + grid_ms - 1)//grid_ms)*grid_ms
    end = (end//grid_ms)*grid_ms
    ptr = {"BINANCE": 0, "OKX": 0}
    last = {"BINANCE": None, "OKX": None}
    grid = []
    for t in range(start, end + 1, grid_ms):
        row = {"t_ms": t}
        ok = True
        for v in ("BINANCE", "OKX"):
            arr = by[v]
            while ptr[v] < len(arr) and arr[ptr[v]]["receipt_ms"] <= t:
                last[v] = arr[ptr[v]]
                ptr[v] += 1
            if last[v] is None or t - last[v]["receipt_ms"] > max_age_ms:
                ok = False
                break
            row[v] = last[v]["mid"]
        if ok:
            grid.append(row)

    overlap_s = max(0.0, (end-start)/1000.0)
    med_spread = {v: statistics.median([x["spread"] for x in by[v]]) for v in by}
    crossed = sum(1 for x in events if x["bid"] > x["ask"])
    quality_pass = (
        len(by["BINANCE"]) >= 100 and len(by["OKX"]) >= 100 and overlap_s >= 60 and
        len(grid) >= 200 and crossed == 0 and med_spread["BINANCE"] > 0 and med_spread["OKX"] > 0
    )

    rb, ro = [], []
    for a, b in zip(grid, grid[1:]):
        rb.append(math.log(b["BINANCE"] / a["BINANCE"]))
        ro.append(math.log(b["OKX"] / a["OKX"]))
    p_x, p_y, r_x, r_y = [], [], [], []
    nonzero_pairs = 0
    for i in range(len(rb)-1):
        x, y = rb[i], ro[i+1]
        xr, yr = ro[i], rb[i+1]
        p_x.append(x); p_y.append(y); r_x.append(xr); r_y.append(yr)
        if x != 0.0 or y != 0.0:
            nonzero_pairs += 1
    primary = corr(p_x, p_y)
    reverse = corr(r_x, r_y)
    lead_pass = bool(
        quality_pass and primary is not None and reverse is not None and
        primary > 0.05 and (primary-reverse) > 0.02 and nonzero_pairs >= 100
    )
    if not quality_pass:
        disposition = "CAPTURE_NOT_ESTABLISHED"
    elif lead_pass:
        disposition = "COMPONENT_PASS / LEAD_LAG_CANDIDATE"
    else:
        disposition = "COMPONENT_PASS / LEAD_LAG_REJECTED"
    return {
        "quality_pass": quality_pass,
        "disposition": disposition,
        "updates": {v: len(by[v]) for v in by},
        "shared_overlap_seconds": overlap_s,
        "grid_rows": len(grid),
        "median_spread": med_spread,
        "crossed_books": crossed,
        "primary_corr_binance_t_to_okx_t1": primary,
        "reverse_corr_okx_t_to_binance_t1": reverse,
        "primary_minus_reverse": None if primary is None or reverse is None else primary-reverse,
        "nonzero_primary_pairs": nonzero_pairs,
        "lead_lag_pass": lead_pass,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=int, default=120)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    events = []
    rejected = 0

    async def book_cb(book, receipt_timestamp):
        nonlocal rejected
        if not len(book.book.bids) or not len(book.book.asks):
            rejected += 1; return
        bid, _ = book.book.bids.index(0)
        ask, _ = book.book.asks.index(0)
        bid, ask = float(bid), float(ask)
        if bid <= 0 or ask <= 0 or bid > ask:
            rejected += 1; return
        venue = str(book.exchange).upper()
        if venue not in {"BINANCE", "OKX"}:
            return
        events.append({
            "venue": venue,
            "symbol": str(book.symbol),
            "receipt_ts": float(receipt_timestamp),
            "receipt_ms": int(float(receipt_timestamp)*1000),
            "bid": bid,
            "ask": ask,
            "mid": (bid+ask)/2.0,
            "spread": ask-bid,
        })

    fh = FeedHandler()
    fh.add_feed(BinancePublicMirror(symbols=["BTC-USDT"], channels=[L2_BOOK], callbacks={L2_BOOK: book_cb}, max_depth=1))
    fh.add_feed(OKX(symbols=["BTC-USDT"], channels=[L2_BOOK], callbacks={L2_BOOK: book_cb}, max_depth=1))
    loop = asyncio.get_event_loop()
    loop.call_later(args.duration, loop.stop)
    started = time.time()
    fh.run()
    ended = time.time()

    with (out / "events.jsonl").open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    result = analyze(events)
    result.update({
        "schema_version": "GATE_BTC_2_CRYPTOFEED_CROSSVENUE_V1",
        "cryptofeed_version": "2.5.0",
        "binance_transport": "data-api.binance.vision + data-stream.binance.vision",
        "capture_duration_requested_seconds": args.duration,
        "capture_wall_seconds": ended-started,
        "accepted_events": len(events),
        "rejected_events": rejected,
        "research_only": True,
        "shadow_only": True,
        "orders": 0,
        "real_capital_brl": 0,
        "no_backfill": True,
        "no_retune": True,
        "factory_runtime_untouched": True,
        "economic_claim_authorized": False,
        "factory_migration_authorized": False,
    })
    (out / "SUMMARY.json").write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["quality_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
