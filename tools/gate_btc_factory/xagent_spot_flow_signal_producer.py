#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

ENDPOINT = "https://data-api.binance.vision/api/v3/klines"
PRODUCER_ID = "S-XSPOT-FLOW-01"


def stable_hash(obj: dict) -> str:
    payload=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def collect(get=requests.get, now_ms: int | None=None) -> dict:
    now_ms = now_ms if now_ms is not None else int(datetime.now(timezone.utc).timestamp()*1000)
    r=get(ENDPOINT,params={"symbol":"BTCUSDT","interval":"1h","limit":3},timeout=20)
    r.raise_for_status()
    rows=r.json()
    closed=[row for row in rows if isinstance(row,list) and len(row)>=11 and int(row[6]) < now_ms]
    if not closed:
        raise RuntimeError("NO_CLOSED_BINANCE_1H_KLINE")
    row=closed[-1]
    volume=float(row[5]); taker_buy=float(row[9])
    if volume <= 0:
        raise RuntimeError("TOTAL_BASE_ASSET_VOLUME_LE_ZERO")
    if taker_buy < 0 or taker_buy > volume + 1e-12:
        raise RuntimeError("TAKER_BUY_VOLUME_INVALID")
    signal=2.0*(taker_buy/volume)-1.0
    signal=max(-1.0,min(1.0,signal))
    rec={
        "schema":"gate_btc_2.xagent_signal_observation.v1",
        "producer_id":PRODUCER_ID,
        "evidence_class":"SPOT_PARTICIPATION_TAKER_FLOW",
        "venue":"BINANCE",
        "market":"SPOT",
        "instrument":"BTCUSDT",
        "interval":"1h",
        "open_time_ms":int(row[0]),
        "close_time_ms":int(row[6]),
        "available_after_ms":int(row[6]),
        "signal":signal,
        "signal_range":[-1.0,1.0],
        "semantic_state":"TAKER_BUY_DOMINANCE" if signal>0 else ("TAKER_SELL_DOMINANCE" if signal<0 else "BALANCED_TAKER_FLOW"),
        "source_checks":{
            "closed_kline":True,
            "total_volume_positive":True,
            "taker_buy_within_total":True,
            "number_of_trades":int(row[8])
        },
        "economic_outcomes_read":False,
        "economic_return_direction_claim":False,
        "alpha_claim":False,
        "scientific_credit":0,
        "survivor_credit":0,
        "promotion_authority":False,
        "engine_feed":False,
        "orders":0,
        "real_capital":0,
        "no_backfill":True,
        "no_retune":True
    }
    rec["record_sha256"]=stable_hash(rec)
    return rec


def self_test() -> None:
    class R:
        def raise_for_status(self): pass
        def json(self):
            return [
                [0,"1","1","1","1","100",3599999,"100",10,"40","40","0"],
                [3600000,"1","1","1","1","100",7199999,"100",11,"60","60","0"],
                [7200000,"1","1","1","1","100",10799999,"100",12,"50","50","0"]
            ]
    d=collect(lambda *a,**k:R(), now_ms=8000000)
    assert d["close_time_ms"]==7199999
    assert abs(d["signal"]-0.2)<1e-12
    assert -1 <= d["signal"] <= 1
    assert d["economic_outcomes_read"] is False
    assert d["survivor_credit"]==0
    print("S_XSPOT_FLOW_01_SELF_TEST=PASS")


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--output")
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        self_test(); return 0
    if not a.output:
        ap.error("--output required")
    d=collect()
    Path(a.output).write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"producer_id":d["producer_id"],"close_time_ms":d["close_time_ms"],"signal":d["signal"],"record_sha256":d["record_sha256"]},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
