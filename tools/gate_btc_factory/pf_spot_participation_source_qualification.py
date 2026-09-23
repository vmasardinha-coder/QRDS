#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

BINANCE = "https://data-api.binance.vision/api/v3/klines"
OKX = "https://www.okx.com/api/v5/market/history-trades"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def probe_binance(get=requests.get) -> dict:
    r = get(BINANCE, params={"symbol": "BTCUSDT", "interval": "1m", "limit": 3}, timeout=20)
    r.raise_for_status()
    rows = r.json()
    if not isinstance(rows, list) or len(rows) < 2:
        raise RuntimeError("BINANCE_KLINES_INSUFFICIENT_ROWS")
    row = rows[-2]
    if not isinstance(row, list) or len(row) < 11:
        raise RuntimeError("BINANCE_KLINE_SCHEMA_FAIL")
    open_time = int(row[0]); close_time = int(row[6])
    volume = float(row[5]); quote_volume = float(row[7])
    trade_count = int(row[8]); taker_buy_base = float(row[9]); taker_buy_quote = float(row[10])
    if close_time <= open_time or min(volume, quote_volume, taker_buy_base, taker_buy_quote) < 0 or trade_count < 0:
        raise RuntimeError("BINANCE_KLINE_VALUE_FAIL")
    if taker_buy_base > volume + 1e-12:
        raise RuntimeError("BINANCE_TAKER_BUY_EXCEEDS_TOTAL")
    return {
        "status": "PASS",
        "venue": "BINANCE",
        "market": "SPOT",
        "instrument": "BTCUSDT",
        "endpoint": BINANCE,
        "authentication_required": False,
        "closed_row_used": True,
        "observables_present": [
            "open_time", "close_time", "volume", "quote_asset_volume",
            "number_of_trades", "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume"
        ],
        "sample_metadata": {
            "open_time": open_time,
            "close_time": close_time,
            "number_of_trades": trade_count,
            "nonnegative_volume_fields": True,
            "taker_buy_not_greater_than_total": True
        },
        "economic_outcomes_read": False
    }


def probe_okx(get=requests.get) -> dict:
    r = get(OKX, params={"instId": "BTC-USDT", "limit": 5}, timeout=20)
    r.raise_for_status()
    payload = r.json()
    if str(payload.get("code")) != "0":
        raise RuntimeError(f"OKX_CODE_FAIL:{payload.get('code')}:{payload.get('msg')}")
    rows = payload.get("data") or []
    if not rows:
        raise RuntimeError("OKX_HISTORY_TRADES_EMPTY")
    required = {"tradeId", "px", "sz", "side", "ts"}
    for row in rows:
        if not required.issubset(row):
            raise RuntimeError("OKX_TRADE_SCHEMA_FAIL")
        if row["side"] not in {"buy", "sell"}:
            raise RuntimeError("OKX_TAKER_SIDE_FAIL")
        int(row["ts"]); float(row["px"]); float(row["sz"])
    return {
        "status": "PASS",
        "venue": "OKX",
        "market": "SPOT",
        "instrument": "BTC-USDT",
        "endpoint": OKX,
        "authentication_required": False,
        "observables_present": sorted(required),
        "taker_side_semantics_observed": sorted({row["side"] for row in rows}),
        "sample_metadata": {"rows": len(rows), "timestamps_parse": True},
        "documented_public_history_window": "LAST_3_MONTHS",
        "economic_outcomes_read": False
    }


def qualify(get=requests.get) -> dict:
    primary = probe_binance(get)
    validation = probe_okx(get)
    return {
        "schema": "gate_btc_2.pf_source_qualification_runtime.v1",
        "generated_at_utc": now_utc(),
        "namespace": "PF::06c2f268bcaf9212",
        "grammar_signature": "06c2f268bcaf92121b084621b11225fb817f395bf2dadacb9cc0bc6da24e4574",
        "channel_id": "CRYPTO_SPOT_PARTICIPATION_FLOW",
        "status": "SOURCE_QUALIFIED_AWAITING_SEPARATE_CHILD_PREREGISTRATION",
        "primary": primary,
        "validation": validation,
        "economic_parameters_defined": False,
        "direction_defined": False,
        "thresholds_defined": False,
        "lookbacks_defined": False,
        "return_horizon_defined": False,
        "historical_backfill_started": False,
        "economic_outcomes_read": False,
        "next_gate": "SEPARATE_CHILD_PREREGISTRATION_BEFORE_ANY_OUTCOME_READ",
        "safety": {
            "research_only": True, "shadow_only": True, "engine_feed": False,
            "orders": 0, "real_capital": 0, "no_retune": True, "no_backfill": True,
            "h1_h31_untouched": True, "canonical_580_untouched": True
        }
    }


def self_test() -> None:
    class R:
        def __init__(self, data): self.data=data
        def raise_for_status(self): return None
        def json(self): return self.data
    def fake(url, params=None, timeout=None):
        if "binance" in url:
            return R([
                [1,"1","1","1","1","10",59999,"10",5,"4","4","0"],
                [60000,"1","1","1","1","12",119999,"12",7,"5","5","0"],
                [120000,"1","1","1","1","9",179999,"9",6,"3","3","0"],
            ])
        return R({"code":"0","msg":"","data":[{"tradeId":"1","px":"1","sz":"0.1","side":"buy","ts":"1000"},{"tradeId":"2","px":"1","sz":"0.2","side":"sell","ts":"999"}]})
    out=qualify(fake)
    assert out["status"].startswith("SOURCE_QUALIFIED_")
    assert out["primary"]["status"]=="PASS" and out["validation"]["status"]=="PASS"
    assert out["economic_outcomes_read"] is False
    assert out["historical_backfill_started"] is False
    assert out["safety"]["canonical_580_untouched"] is True
    print("PF_SPOT_PARTICIPATION_SOURCE_QUALIFICATION_SELF_TEST=PASS")


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--output")
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        self_test(); return 0
    if not a.output:
        ap.error("--output required")
    out=qualify()
    Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":out["status"],"primary":out["primary"]["status"],"validation":out["validation"]["status"]},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
