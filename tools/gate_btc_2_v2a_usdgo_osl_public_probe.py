#!/usr/bin/env python3
"""Bounded physical probe for preregistered USDGO/USD on OSL Global public market data.

This probe can confirm the exact live market identity but MUST NOT promote live ticker data
into historical OHLCV. Historical source qualification remains fail-closed unless an exact,
free, public and auditable OSL historical execution surface is physically demonstrated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

WS_CANDIDATES = (
    "wss://stream-api.osl.com/openapi/v1/ws",
    "wss://stream-api.osl.com/v2/ws/public",
)
SUBSCRIBE = {
    "op": "subscribe",
    "args": [{"channel": "ticker", "instType": "sp", "instId": "usdgousd"}],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--seconds", type=int, default=20)
    args = ap.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    messages: list[dict] = []
    attempts: list[dict] = []
    exact_live_market_confirmed = False
    error = None

    try:
        import websocket  # websocket-client, installed only in the evidence workflow
    except Exception as exc:
        error = f"WEBSOCKET_IMPORT_FAILED:{type(exc).__name__}:{exc}"
        websocket = None

    if websocket is not None:
        for url in WS_CANDIDATES:
            ws = None
            try:
                ws = websocket.create_connection(url, timeout=8, origin="https://www.osl.com")
                payload = json.dumps(SUBSCRIBE, separators=(",", ":"))
                ws.send(payload)
                deadline = time.time() + args.seconds
                seen = 0
                while time.time() < deadline and seen < 20:
                    try:
                        raw = ws.recv()
                    except Exception as exc:
                        attempts.append({"url": url, "stage": "recv", "error": f"{type(exc).__name__}:{exc}"})
                        break
                    if raw is None:
                        continue
                    if isinstance(raw, bytes):
                        raw_bytes = raw
                        text = raw.decode("utf-8", errors="replace")
                    else:
                        text = str(raw)
                        raw_bytes = text.encode("utf-8")
                    seen += 1
                    row = {
                        "url": url,
                        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                        "text": text[:4000],
                    }
                    messages.append(row)
                    low = text.lower().replace("_", "").replace("-", "")
                    if "usdgousd" in low or ("usdgo" in low and "usd" in low):
                        exact_live_market_confirmed = True
                attempts.append({"url": url, "stage": "subscribe", "result": "PASS", "messages": seen})
                if exact_live_market_confirmed:
                    break
            except Exception as exc:
                attempts.append({"url": url, "stage": "connect_or_subscribe", "result": "FAIL", "error": f"{type(exc).__name__}:{exc}"})
            finally:
                if ws is not None:
                    try:
                        ws.close()
                    except Exception:
                        pass

    if exact_live_market_confirmed:
        status = "LIVE_MARKET_CONFIRMED_HISTORICAL_PUBLIC_TAPE_UNPROVEN"
    else:
        status = "FAIL_CLOSED_SOURCE_OR_TRANSPORT"

    summary = {
        "schema_version": "GATE_BTC_2_V2A_USDGO_OSL_PUBLIC_PROBE_V1",
        "symbol": "USDGO",
        "provider": "OSL_GLOBAL_PUBLIC_MARKET_DATA",
        "frozen_market_identity": "USDGO/USD",
        "inst_type": "sp",
        "inst_id": "usdgousd",
        "ws_candidates": list(WS_CANDIDATES),
        "exact_live_market_confirmed": exact_live_market_confirmed,
        "historical_execution_surface_proven": False,
        "historical_33_bucket_qa_pass": False,
        "status": status,
        "error": error,
        "attempts": attempts,
        "captured_message_count": len(messages),
        "qualification_only": True,
        "source_admitted": False,
        "historical_credit": 0,
        "scientific_credit": False,
        "prospective_credit": False,
        "d0_credit": 0,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill": True,
        "no_counter_reset": True,
        "no_silent_source_substitution": True,
        "fail_closed": True,
    }
    (out / "MESSAGES.json").write_text(json.dumps(messages, indent=2, sort_keys=True) + "\n")
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
