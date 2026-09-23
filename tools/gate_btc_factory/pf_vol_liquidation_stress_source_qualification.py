#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

BINANCE_BASE = "https://fapi.binance.com"
BINANCE_KLINES = BINANCE_BASE + "/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=2"
BINANCE_OI = BINANCE_BASE + "/fapi/v1/openInterest?symbol=BTCUSDT"
BINANCE_FUNDING = BINANCE_BASE + "/fapi/v1/premiumIndex?symbol=BTCUSDT"
BINANCE_FORCE_ORDER_WS = "wss://fstream.binance.com/ws/btcusdt@forceOrder"

OKX_BASE = "https://www.okx.com"
OKX_CANDLES = OKX_BASE + "/api/v5/market/candles?instId=BTC-USDT-SWAP&bar=1H&limit=2"
OKX_OI = OKX_BASE + "/api/v5/public/open-interest?instType=SWAP&instId=BTC-USDT-SWAP"
OKX_FUNDING = OKX_BASE + "/api/v5/public/funding-rate?instId=BTC-USDT-SWAP"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _get_json(get: Callable[..., Any], url: str) -> dict[str, Any]:
    try:
        response = get(url, timeout=20)
    except Exception as exc:
        return {"http_status": None, "payload": None, "error": f"{type(exc).__name__}:{exc}"}
    code = int(getattr(response, "status_code", 200))
    if code in (401, 403):
        return {"http_status": code, "payload": None, "error": "AUTHORIZATION_OR_PRODUCT_TIER_REQUIRED"}
    if code != 200:
        return {"http_status": code, "payload": None, "error": "UNEXPECTED_HTTP_STATUS"}
    try:
        payload = response.json()
    except Exception:
        return {"http_status": code, "payload": None, "error": "INVALID_JSON"}
    return {"http_status": code, "payload": payload, "error": None}


def _binance_klines_schema(payload: Any) -> tuple[bool, bool]:
    if not isinstance(payload, list) or not payload:
        return False, False
    row = payload[-1]
    schema = isinstance(row, list) and len(row) >= 7
    timestamp = bool(schema and isinstance(row[6], (int, float)))
    return schema, timestamp


def _binance_oi_schema(payload: Any) -> tuple[bool, bool]:
    schema = isinstance(payload, dict) and "openInterest" in payload and "symbol" in payload
    timestamp = bool(schema and isinstance(payload.get("time"), (int, float)))
    return schema, timestamp


def _binance_funding_schema(payload: Any) -> tuple[bool, bool]:
    schema = isinstance(payload, dict) and "lastFundingRate" in payload and "symbol" in payload
    timestamp = bool(schema and isinstance(payload.get("time"), (int, float)))
    return schema, timestamp


def _okx_data(payload: Any) -> list[Any]:
    if not isinstance(payload, dict) or str(payload.get("code")) != "0":
        return []
    data = payload.get("data")
    return data if isinstance(data, list) else []


def _okx_candles_schema(payload: Any) -> tuple[bool, bool]:
    rows = _okx_data(payload)
    if not rows:
        return False, False
    row = rows[0]
    schema = isinstance(row, list) and len(row) >= 9
    timestamp = bool(schema and str(row[0]).isdigit())
    return schema, timestamp


def _okx_oi_schema(payload: Any) -> tuple[bool, bool]:
    rows = _okx_data(payload)
    row = rows[0] if rows else None
    schema = isinstance(row, dict) and "oi" in row and "instId" in row
    timestamp = bool(schema and str(row.get("ts", "")).isdigit())
    return schema, timestamp


def _okx_funding_schema(payload: Any) -> tuple[bool, bool]:
    rows = _okx_data(payload)
    row = rows[0] if rows else None
    schema = isinstance(row, dict) and "fundingRate" in row and "instId" in row
    timestamp = bool(schema and (str(row.get("fundingTime", "")).isdigit() or str(row.get("nextFundingTime", "")).isdigit()))
    return schema, timestamp


def _probe_force_order_ws(ws_connect: Callable[..., Any] | None) -> dict[str, Any]:
    if ws_connect is None:
        try:
            import websocket  # type: ignore
        except Exception as exc:
            return {"connected": False, "event_read": False, "error": f"IMPORT:{type(exc).__name__}:{exc}"}
        ws_connect = websocket.create_connection
    conn = None
    try:
        conn = ws_connect(BINANCE_FORCE_ORDER_WS, timeout=8)
        connected = bool(getattr(conn, "connected", True))
        return {"connected": connected, "event_read": False, "error": None if connected else "NOT_CONNECTED"}
    except Exception as exc:
        return {"connected": False, "event_read": False, "error": f"{type(exc).__name__}:{exc}"}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def qualify(get=requests.get, ws_connect: Callable[..., Any] | None = None) -> dict[str, Any]:
    bk = _get_json(get, BINANCE_KLINES)
    bo = _get_json(get, BINANCE_OI)
    bf = _get_json(get, BINANCE_FUNDING)
    ok = _get_json(get, OKX_CANDLES)
    oo = _get_json(get, OKX_OI)
    of = _get_json(get, OKX_FUNDING)
    ws = _probe_force_order_ws(ws_connect)

    bk_schema, bk_ts = _binance_klines_schema(bk["payload"])
    bo_schema, bo_ts = _binance_oi_schema(bo["payload"])
    bf_schema, bf_ts = _binance_funding_schema(bf["payload"])
    ok_schema, ok_ts = _okx_candles_schema(ok["payload"])
    oo_schema, oo_ts = _okx_oi_schema(oo["payload"])
    of_schema, of_ts = _okx_funding_schema(of["payload"])

    responses = [bk, bo, bf, ok, oo, of]
    auth_blocked = any(r["error"] == "AUTHORIZATION_OR_PRODUCT_TIER_REQUIRED" for r in responses)
    binance_rest_pass = bk_schema and bo_schema and bf_schema and bk_ts and bo_ts and bf_ts
    okx_validation_pass = ok_schema and oo_schema and of_schema and ok_ts and oo_ts and of_ts
    complete_primary = binance_rest_pass and ws["connected"]

    if auth_blocked:
        status = "BLOCKED_AUTHORIZATION_OR_PRODUCT_TIER_REQUIRED"
        reason = "REQUIRED_PUBLIC_MARKET_DATA_RETURNED_AUTHORIZATION_BLOCK"
    elif complete_primary:
        status = "SOURCE_QUALIFIED_AWAITING_SEPARATE_CHILD_PREREGISTRATION"
        reason = "BINANCE_PUBLIC_REST_AND_FORCE_ORDER_WEBSOCKET_TRANSPORT_QUALIFIED"
    elif binance_rest_pass and not ws["connected"]:
        status = "BLOCKED_PUBLIC_LIQUIDATION_TRANSPORT_UNAVAILABLE"
        reason = "BINANCE_PUBLIC_REST_QUALIFIED_BUT_FORCE_ORDER_WEBSOCKET_HANDSHAKE_FAILED"
    else:
        status = "FAIL_CLOSED_SOURCE_UNVERIFIED"
        reason = "REQUIRED_BINANCE_PUBLIC_REST_SCHEMA_OR_TIMESTAMPS_NOT_CONFIRMED"

    return {
        "schema": "gate_btc_2.pf_source_qualification_runtime.v1",
        "generated_at_utc": now(),
        "namespace": "PF::fc39959718b10656",
        "grammar_signature": "fc39959718b106564ff15db9cda660aa42e9a9c1c247aa87c576aca4efaa3bee",
        "channel_id": "CRYPTO_VOL_LIQUIDATION_STRESS",
        "primary_provider": "BINANCE_USDS_M_PUBLIC_MARKET_DATA",
        "independent_validation_provider": "OKX_PUBLIC_MARKET_DATA",
        "authentication_supplied": False,
        "binance": {
            "ohlcv": {"url": BINANCE_KLINES, "http_status": bk["http_status"], "schema_ok": bk_schema, "timestamp_present": bk_ts},
            "open_interest": {"url": BINANCE_OI, "http_status": bo["http_status"], "schema_ok": bo_schema, "timestamp_present": bo_ts},
            "funding": {"url": BINANCE_FUNDING, "http_status": bf["http_status"], "schema_ok": bf_schema, "timestamp_present": bf_ts},
            "public_liquidation_stream": {
                "url": BINANCE_FORCE_ORDER_WS,
                "transport_connected": ws["connected"],
                "event_read_during_probe": False,
                "event_required_during_probe": False,
                "error": ws["error"],
            },
            "rest_capabilities_pass": binance_rest_pass,
            "complete_required_capabilities_pass": complete_primary,
        },
        "okx": {
            "ohlcv": {"url": OKX_CANDLES, "http_status": ok["http_status"], "schema_ok": ok_schema, "timestamp_present": ok_ts},
            "open_interest": {"url": OKX_OI, "http_status": oo["http_status"], "schema_ok": oo_schema, "timestamp_present": oo_ts},
            "funding": {"url": OKX_FUNDING, "http_status": of["http_status"], "schema_ok": of_schema, "timestamp_present": of_ts},
            "independent_validation_pass": okx_validation_pass,
            "liquidation_substitute_claimed": False,
        },
        "qualification": {"status": status, "reason": reason},
        "liquidation_event_payload_read": False,
        "signal_formula_defined": False,
        "direction_defined": False,
        "thresholds_defined": False,
        "lookbacks_defined": False,
        "economic_outcomes_read": False,
        "historical_backfill_started": False,
        "new_stress_proxy_invented": False,
        "next_gate": (
            "SEPARATE_CHILD_PREREGISTRATION_BEFORE_ANY_SIGNAL_OR_OUTCOME_READ"
            if status == "SOURCE_QUALIFIED_AWAITING_SEPARATE_CHILD_PREREGISTRATION"
            else "RETAIN_BLOCKER_AND_ADVANCE_PARALLEL_FRONTIER_OUTCOME_BLIND"
        ),
        "safety": {
            "research_only": True,
            "shadow_only": True,
            "engine_feed": False,
            "orders": 0,
            "real_capital": 0,
            "no_retune": True,
            "no_backfill": True,
            "h1_h31_untouched": True,
            "canonical_580_untouched": True,
        },
    }


def self_test() -> None:
    class R:
        def __init__(self, status: int, payload: Any):
            self.status_code = status
            self._payload = payload
        def json(self):
            return self._payload

    class WS:
        connected = True
        def close(self):
            pass

    payloads = iter([
        R(200, [[1, "1", "2", "0", "1", "5", 2, "0", 1, "0", "0", "0"]]),
        R(200, {"symbol": "BTCUSDT", "openInterest": "1", "time": 1}),
        R(200, {"symbol": "BTCUSDT", "lastFundingRate": "0", "time": 1}),
        R(200, {"code": "0", "data": [["1", "1", "2", "0", "1", "5", "5", "0", "1"]]}),
        R(200, {"code": "0", "data": [{"instId": "BTC-USDT-SWAP", "oi": "1", "ts": "1"}]}),
        R(200, {"code": "0", "data": [{"instId": "BTC-USDT-SWAP", "fundingRate": "0", "fundingTime": "1"}]}),
    ])
    d = qualify(lambda *a, **k: next(payloads), lambda *a, **k: WS())
    assert d["qualification"]["status"] == "SOURCE_QUALIFIED_AWAITING_SEPARATE_CHILD_PREREGISTRATION"
    assert d["binance"]["complete_required_capabilities_pass"] is True
    assert d["okx"]["independent_validation_pass"] is True
    assert d["liquidation_event_payload_read"] is False
    assert d["economic_outcomes_read"] is False

    payloads = iter([
        R(200, [[1, "1", "2", "0", "1", "5", 2, "0", 1, "0", "0", "0"]]),
        R(200, {"symbol": "BTCUSDT", "openInterest": "1", "time": 1}),
        R(200, {"symbol": "BTCUSDT", "lastFundingRate": "0", "time": 1}),
        R(200, {"code": "0", "data": [["1", "1", "2", "0", "1", "5", "5", "0", "1"]]}),
        R(200, {"code": "0", "data": [{"instId": "BTC-USDT-SWAP", "oi": "1", "ts": "1"}]}),
        R(200, {"code": "0", "data": [{"instId": "BTC-USDT-SWAP", "fundingRate": "0", "fundingTime": "1"}]}),
    ])
    def broken_ws(*a, **k):
        raise OSError("blocked")
    blocked = qualify(lambda *a, **k: next(payloads), broken_ws)
    assert blocked["qualification"]["status"] == "BLOCKED_PUBLIC_LIQUIDATION_TRANSPORT_UNAVAILABLE"
    assert blocked["new_stress_proxy_invented"] is False
    print("PF_VOL_LIQUIDATION_STRESS_SOURCE_QUALIFICATION_SELF_TEST=PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.output:
        parser.error("--output required")
    data = qualify()
    Path(args.output).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": data["qualification"]["status"],
        "binance_complete": data["binance"]["complete_required_capabilities_pass"],
        "okx_validation": data["okx"]["independent_validation_pass"],
        "next_gate": data["next_gate"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
