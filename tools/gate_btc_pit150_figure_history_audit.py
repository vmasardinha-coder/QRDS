"""Audit Figure executions against independent hourly TRADE bars; never admits a source."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

def timestamp_ns(value):
    match = re.fullmatch(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,9}))?Z", value)
    if not match:
        raise ValueError("invalid nanosecond UTC timestamp")
    second = int(datetime.strptime(match[1], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
    return second * 10**9 + int((match[2] or "").ljust(9, "0"))

def number(value):
    result = Decimal(str(value))
    if not result.is_finite() or result <= 0:
        raise ValueError("nonphysical price or quantity")
    return result

def audit(root, cutoff, now=None):
    root = Path(root)
    end = datetime.strptime(cutoff, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    if end > (now or datetime.now(timezone.utc)):
        raise ValueError("cutoff is not a completed UTC day")
    start = end - timedelta(days=200)
    start_ns, end_ns = int(start.timestamp()) * 10**9, int(end.timestamp()) * 10**9
    files = []
    def read(path):
        raw = path.read_bytes()
        files.append({"file":path.name, "sha256":hashlib.sha256(raw).hexdigest()})
        return json.loads(raw, parse_float=Decimal)
    identity = read(root / "identity.json")
    required = {"id":"HASH-USD", "symbol":"HASH-USD", "denom":"HASH",
                "quoteDenom":"USD", "marketType":"CRYPTO", "status":"OPEN",
                "proTradeAvailable":True}
    if any(identity.get(key) != value for key,value in required.items()) or "nhash" not in identity.get("contractAddress", []):
        raise ValueError("exact HASH/native contract/spot identity mismatch")
    pages = sorted(root.glob("page_*.json"))
    if not pages or [x.name for x in pages] != [f"page_{i:03}.json" for i in range(len(pages))]:
        raise ValueError("missing or unordered raw trade page")
    cursor, seen = end_ns - 1, {}
    for index,path in enumerate(pages):
        payload = read(path)
        if any(payload.get(key) != value for key,value in {"denom":"HASH", "symbol":"HASH-USD", "marketId":"HASH-USD"}.items()):
            raise ValueError("trade response market mismatch")
        matches = payload.get("matches")
        if not isinstance(matches, list) or len(matches) > 200:
            raise ValueError("invalid trade page")
        stamps = [timestamp_ns(t["created"]) for t in matches]
        if stamps != sorted(stamps, reverse=True) or any(not start_ns <= t <= cursor for t in stamps):
            raise ValueError("trade pagination order or query boundary mismatch")
        before = len(seen)
        for trade in matches:
            if not isinstance(trade.get("id"), str) or not trade["id"]:
                raise ValueError("missing immutable trade identity")
            number(trade["price"]); number(trade["quantity"])
            if trade["id"] in seen and seen[trade["id"]] != trade:
                raise ValueError("conflicting immutable trade ID")
            seen[trade["id"]] = trade
        if index < len(pages)-1 and len(matches) != 200:
            raise ValueError("pages after an exhausted response")
        if matches:
            oldest = min(stamps)
            if oldest == cursor and len(seen) == before and len(matches) == 200:
                raise ValueError("unexhausted timestamp tie")
            cursor = oldest
    if len(matches) == 200:
        raise ValueError("terminal raw page does not prove exhaustion")
    hours = defaultdict(list)
    for trade in seen.values():
        hours[trade["created"][:13] + ":00:00Z"].append(trade)
    hourly = read(root / "hourly.json")
    if any(hourly.get(key) != value for key,value in {"denom":"HASH","symbol":"HASH-USD","marketId":"HASH-USD"}.items()):
        raise ValueError("hourly TRADE response market mismatch")
    bars = {}
    differences = []
    for bar in hourly["matchHistoryData"]:
        stamp = timestamp_ns(bar["date"])
        if stamp % (3600 * 10**9) or not start_ns <= stamp < end_ns or bar["date"] in bars:
            raise ValueError("unaligned, duplicate or out-of-range UTC hour")
        bars[bar["date"]] = bar
    if set(bars) != set(hours):
        raise ValueError("trade hours and physical bar hours differ")
    days = defaultdict(list)
    quote = defaultdict(lambda: Decimal(0))
    for hour, trades in sorted(hours.items()):
        bar = bars[hour]
        values = {key:number(bar[key]) for key in ["open","high","low","close","volume"]}
        base = sum((number(t["quantity"]) for t in trades), Decimal(0))
        if values["volume"] != base:
            differences.append({"hour":hour,"field":"base_volume",
                                "trades_sum":str(base),"hourly_bar":str(values["volume"])})
        prices = [number(t["price"]) for t in trades]
        first = min(timestamp_ns(t["created"]) for t in trades)
        last = max(timestamp_ns(t["created"]) for t in trades)
        opens = {number(t["price"]) for t in trades if timestamp_ns(t["created"]) == first}
        closes = {number(t["price"]) for t in trades if timestamp_ns(t["created"]) == last}
        if values["open"] not in opens or values["close"] not in closes or values["high"] != max(prices) or values["low"] != min(prices):
            differences.append({"hour":hour,"field":"physical_OHLC"})
        day = hour[:10]
        quote[day] += sum((number(t["price"]) * number(t["quantity"]) for t in trades), Decimal(0))
        days[day].append(bar)
    expected = [(start+timedelta(days=i)).date().isoformat() for i in range(200)]
    missing = [day for day in expected if day not in days]
    daily = [{"date":day,"symbol":"HASH","close_usd":float(days[day][-1]["close"]),
              "volume_usd":float(quote[day]),"source":"figure"} for day in sorted(days)]
    return {"schema_version":1,"coin_id":"hash-2","symbol":"HASH","cutoff":cutoff,
            "unique_trades":len(seen),"physical_hours":len(hours),"unique_days":len(days),
            "missing_days":missing,"cross_endpoint_differences":differences,
            "qualification":"PASS_SOURCE_CONSISTENCY" if not missing and not differences else "BLOCKED_SOURCE_CONSISTENCY",
            "source_admission":False,"historical_scientific_credit":0,
            "boundary_tie_rule":"Hourly provider TRADE close must equal a physical last-timestamp price; no lexical ID ordering",
            "quote_volume_rule":"sum(Decimal(price)*Decimal(quantity)); USD quote; no close-times-volume proxy",
            "raw_files":files,"daily_rows":daily}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",required=True);parser.add_argument("--cutoff",required=True);parser.add_argument("--output",required=True)
    args=parser.parse_args()
    result=audit(args.root,args.cutoff)
    Path(args.output).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({key:value for key,value in result.items() if key not in {"raw_files","daily_rows"}}))
    return 0 if result["qualification"] == "PASS_SOURCE_CONSISTENCY" else 2

if __name__=="__main__":
    raise SystemExit(main())
