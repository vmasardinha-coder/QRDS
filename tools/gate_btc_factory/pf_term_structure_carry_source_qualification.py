#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

BINANCE_EXCHANGE_INFO = "https://dapi.binance.com/dapi/v1/exchangeInfo"
BINANCE_TICKER = "https://dapi.binance.com/dapi/v1/ticker/price"
BINANCE_FUNDING = "https://dapi.binance.com/dapi/v1/fundingRate"
OKX_INSTRUMENTS = "https://www.okx.com/api/v5/public/instruments"
OKX_TICKER = "https://www.okx.com/api/v5/market/ticker"
OKX_FUNDING = "https://www.okx.com/api/v5/public/funding-rate"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(get, url, params=None):
    r = get(url, params=params, timeout=20)
    code = int(getattr(r, "status_code", 200))
    if code != 200:
        raise RuntimeError(f"HTTP_{code}:{url}")
    return r.json()


def _f(x):
    v = float(x)
    if not (v > 0):
        raise ValueError("nonpositive price")
    return v


def qualify(get=requests.get, now_ms: int | None = None) -> dict:
    now_ms = int(now_ms if now_ms is not None else time.time() * 1000)
    primary = {"provider": "BINANCE_COIN_M_PUBLIC_API", "status": "FAIL_CLOSED_SOURCE_UNVERIFIED"}
    validation = {"provider": "OKX_PUBLIC_API", "status": "VALIDATION_UNVERIFIED"}
    try:
        info = _json(get, BINANCE_EXCHANGE_INFO)
        symbols = [s for s in (info.get("symbols") or []) if s.get("pair") == "BTCUSD" and s.get("contractStatus") == "TRADING"]
        perp = next((s for s in symbols if s.get("contractType") == "PERPETUAL"), None)
        dated = [s for s in symbols if s.get("contractType") in {"CURRENT_QUARTER", "NEXT_QUARTER"} and int(s.get("deliveryDate") or 0) > now_ms]
        dated.sort(key=lambda s: int(s.get("deliveryDate") or 0))
        future = dated[0] if dated else None
        if not perp or not future:
            primary = {"provider": "BINANCE_COIN_M_PUBLIC_API", "status": "BLOCKED_REQUIRED_PUBLIC_TERM_STRUCTURE_FIELD_MISSING", "reason": "LIVE_PERPETUAL_OR_DATED_FUTURE_MISSING"}
        else:
            tickers = _json(get, BINANCE_TICKER)
            by_symbol = {r.get("symbol"): r for r in tickers if isinstance(r, dict)}
            perp_px = _f(by_symbol[perp["symbol"]]["price"])
            future_px = _f(by_symbol[future["symbol"]]["price"])
            funding_rows = _json(get, BINANCE_FUNDING, {"symbol": perp["symbol"], "limit": 1})
            if not funding_rows:
                raise ValueError("funding row missing")
            funding = float(funding_rows[-1]["fundingRate"])
            funding_time = int(funding_rows[-1]["fundingTime"])
            primary = {
                "provider": "BINANCE_COIN_M_PUBLIC_API",
                "status": "QUALIFIED_PUBLIC_SOURCE",
                "authentication_required": False,
                "perpetual_symbol": perp["symbol"],
                "dated_symbol": future["symbol"],
                "dated_contract_type": future["contractType"],
                "dated_expiry_ms": int(future["deliveryDate"]),
                "perpetual_price_observed": True,
                "dated_price_observed": True,
                "funding_rate_observed": True,
                "funding_time_ms": funding_time,
                "sample_checks": {
                    "perpetual_price_positive": perp_px > 0,
                    "dated_price_positive": future_px > 0,
                    "expiry_in_future": int(future["deliveryDate"]) > now_ms,
                    "funding_parseable": isinstance(funding, float)
                }
            }
    except (KeyError, TypeError, ValueError) as exc:
        primary = {"provider": "BINANCE_COIN_M_PUBLIC_API", "status": "BLOCKED_REQUIRED_PUBLIC_TERM_STRUCTURE_FIELD_MISSING", "reason": f"{type(exc).__name__}:{exc}"}
    except Exception as exc:
        primary = {"provider": "BINANCE_COIN_M_PUBLIC_API", "status": "FAIL_CLOSED_SOURCE_UNVERIFIED", "reason": f"{type(exc).__name__}:{exc}"}

    try:
        fut_payload = _json(get, OKX_INSTRUMENTS, {"instType": "FUTURES", "instFamily": "BTC-USD"})
        swap_payload = _json(get, OKX_INSTRUMENTS, {"instType": "SWAP", "instFamily": "BTC-USD"})
        futures = [r for r in (fut_payload.get("data") or []) if r.get("state") == "live" and int(r.get("expTime") or 0) > now_ms]
        futures.sort(key=lambda r: int(r.get("expTime") or 0))
        swaps = [r for r in (swap_payload.get("data") or []) if r.get("state") == "live" and r.get("instType") == "SWAP"]
        if not futures or not swaps:
            validation = {"provider": "OKX_PUBLIC_API", "status": "VALIDATION_REQUIRED_FIELD_MISSING"}
        else:
            future, swap = futures[0], swaps[0]
            ftk = _json(get, OKX_TICKER, {"instId": future["instId"]}).get("data") or []
            stk = _json(get, OKX_TICKER, {"instId": swap["instId"]}).get("data") or []
            fr = _json(get, OKX_FUNDING, {"instId": swap["instId"]}).get("data") or []
            if not ftk or not stk or not fr:
                raise ValueError("ticker or funding missing")
            _f(ftk[0]["last"]); _f(stk[0]["last"]); float(fr[0]["fundingRate"])
            validation = {
                "provider": "OKX_PUBLIC_API",
                "status": "PASS",
                "authentication_required": False,
                "perpetual_symbol": swap["instId"],
                "dated_symbol": future["instId"],
                "dated_expiry_ms": int(future["expTime"]),
                "public_tickers_observed": True,
                "public_funding_observed": True
            }
    except Exception as exc:
        validation = {"provider": "OKX_PUBLIC_API", "status": "VALIDATION_UNVERIFIED", "reason": f"{type(exc).__name__}:{exc}"}

    primary_ok = primary.get("status") == "QUALIFIED_PUBLIC_SOURCE"
    status = "SOURCE_QUALIFIED_AWAITING_SEPARATE_SIGNAL_PREREGISTRATION" if primary_ok else primary.get("status")
    return {
        "schema": "gate_btc_2.pf_source_qualification_runtime.v1",
        "generated_at_utc": utc_now(),
        "namespace": "PF::5c6294637c3b4e7f",
        "grammar_signature": "5c6294637c3b4e7f61f9f4419a68671e6b3503314b6520e093b1301d504b3503",
        "channel_id": "CRYPTO_TERM_STRUCTURE_CARRY",
        "status": status,
        "primary": primary,
        "validation": validation,
        "economic_outcomes_read": False,
        "carry_formula_defined": False,
        "direction_defined": False,
        "thresholds_defined": False,
        "lookbacks_defined": False,
        "return_horizon_defined": False,
        "historical_backfill_started": False,
        "next_gate": "SEPARATE_SIGNAL_PRODUCER_PREREGISTRATION_BEFORE_ANY_OUTCOME_READ" if primary_ok else "RETAIN_BLOCKER_OR_ADVANCE_PARALLEL_FRONTIER_WITHOUT_CREDIT",
        "safety": {"research_only": True, "shadow_only": True, "engine_feed": False, "orders": 0, "real_capital": 0, "no_retune": True, "no_backfill": True, "h1_h31_untouched": True, "canonical_580_untouched": True}
    }


def self_test() -> None:
    class R:
        def __init__(self, data, status=200): self._data=data; self.status_code=status
        def json(self): return self._data
    now = 1_800_000_000_000
    def fake(url, params=None, timeout=20):
        if url == BINANCE_EXCHANGE_INFO:
            return R({"symbols":[
                {"symbol":"BTCUSD_PERP","pair":"BTCUSD","contractType":"PERPETUAL","contractStatus":"TRADING","deliveryDate":0},
                {"symbol":"BTCUSD_270101","pair":"BTCUSD","contractType":"CURRENT_QUARTER","contractStatus":"TRADING","deliveryDate":now+10_000_000}
            ]})
        if url == BINANCE_TICKER: return R([{"symbol":"BTCUSD_PERP","price":"70000"},{"symbol":"BTCUSD_270101","price":"71000"}])
        if url == BINANCE_FUNDING: return R([{"symbol":"BTCUSD_PERP","fundingRate":"0.0001","fundingTime":now-1}])
        if url == OKX_INSTRUMENTS and params["instType"] == "FUTURES": return R({"data":[{"instId":"BTC-USD-270101","instType":"FUTURES","state":"live","expTime":str(now+10_000_000)}]})
        if url == OKX_INSTRUMENTS: return R({"data":[{"instId":"BTC-USD-SWAP","instType":"SWAP","state":"live","expTime":""}]})
        if url == OKX_TICKER: return R({"data":[{"last":"70000"}]})
        if url == OKX_FUNDING: return R({"data":[{"fundingRate":"0.0001"}]})
        raise AssertionError(url)
    d=qualify(fake, now)
    assert d["status"] == "SOURCE_QUALIFIED_AWAITING_SEPARATE_SIGNAL_PREREGISTRATION"
    assert d["primary"]["status"] == "QUALIFIED_PUBLIC_SOURCE"
    assert d["validation"]["status"] == "PASS"
    assert d["economic_outcomes_read"] is False and d["carry_formula_defined"] is False
    assert d["safety"]["canonical_580_untouched"] is True
    print("PF_TERM_STRUCTURE_SOURCE_SELF_TEST=PASS")


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output"); ap.add_argument("--self-test",action="store_true"); args=ap.parse_args()
    if args.self_test: self_test(); return 0
    if not args.output: ap.error("--output required")
    d=qualify(); Path(args.output).write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":d["status"],"primary":d["primary"]["status"],"validation":d["validation"]["status"]}))
    return 0

if __name__ == "__main__": raise SystemExit(main())
