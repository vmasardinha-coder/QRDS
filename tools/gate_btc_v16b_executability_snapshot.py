#!/usr/bin/env python3
"""Capture causal Binance Spot/USD-M executability evidence for V16B.

The raw public responses are preserved and SHA-bound. A derived exchangeInfo
payload adds the independently captured serverTime required by the frozen V16B
entry builder. Research/shadow only; no order or capital path exists here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

SPOT_INFO = "https://api.binance.com/api/v3/exchangeInfo"
SPOT_TIME = "https://api.binance.com/api/v3/time"
USDM_INFO = "https://fapi.binance.com/fapi/v1/exchangeInfo"
USDM_TIME = "https://fapi.binance.com/fapi/v1/time"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_response(session: requests.Session, url: str) -> tuple[bytes, dict[str, Any]]:
    r = session.get(url, timeout=45)
    r.raise_for_status()
    raw = r.content
    obj = r.json()
    if not isinstance(obj, dict):
        raise RuntimeError(f"expected JSON object from {url}")
    return raw, obj


def merge_exchange_info(exchange_info: dict[str, Any], time_payload: dict[str, Any]) -> dict[str, Any]:
    symbols = exchange_info.get("symbols")
    server_time = time_payload.get("serverTime")
    if not isinstance(symbols, list) or not symbols:
        raise RuntimeError("exchangeInfo symbols missing/empty")
    if not isinstance(server_time, (int, float)) or server_time <= 0:
        raise RuntimeError("serverTime missing/invalid")
    out = dict(exchange_info)
    out["serverTime"] = int(server_time)
    out["v16b_server_time_source"] = "ADJACENT_PUBLIC_TIME_ENDPOINT"
    return out


def capture(out_dir: Path, now: datetime | None = None) -> dict[str, Any]:
    captured = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 GATE-BTC-Research-Only/1.0"})

    spot_info_raw, spot_info = _json_response(session, SPOT_INFO)
    spot_time_raw, spot_time = _json_response(session, SPOT_TIME)
    usdm_info_raw, usdm_info = _json_response(session, USDM_INFO)
    usdm_time_raw, usdm_time = _json_response(session, USDM_TIME)

    spot_merged = merge_exchange_info(spot_info, spot_time)
    usdm_merged = merge_exchange_info(usdm_info, usdm_time)

    stamp = captured.strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_payloads = {
        f"BINANCE_SPOT_EXCHANGEINFO_{stamp}.raw.json": spot_info_raw,
        f"BINANCE_SPOT_TIME_{stamp}.raw.json": spot_time_raw,
        f"BINANCE_USDM_EXCHANGEINFO_{stamp}.raw.json": usdm_info_raw,
        f"BINANCE_USDM_TIME_{stamp}.raw.json": usdm_time_raw,
    }
    hashes: dict[str, str] = {}
    for name, raw in raw_payloads.items():
        p = out_dir / name
        p.write_bytes(raw)
        hashes[name] = sha256_bytes(raw)

    spot_path = out_dir / f"V16B_EXECUTABILITY_SPOT_EXCHANGEINFO_{stamp}.json"
    usdm_path = out_dir / f"V16B_EXECUTABILITY_USDM_EXCHANGEINFO_{stamp}.json"
    spot_path.write_text(json.dumps(spot_merged, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    usdm_path.write_text(json.dumps(usdm_merged, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest = {
        "schema": "gate_btc.v16b.executability_snapshot.v1",
        "status": "PASS_CAPTURED",
        "captured_at_utc": captured.isoformat().replace("+00:00", "Z"),
        "spot_exchange_info": str(spot_path),
        "usdm_exchange_info": str(usdm_path),
        "spot_server_time": int(spot_merged["serverTime"]),
        "usdm_server_time": int(usdm_merged["serverTime"]),
        "spot_symbols": len(spot_merged["symbols"]),
        "usdm_symbols": len(usdm_merged["symbols"]),
        "raw_sha256": hashes,
        "raw_preserved": True,
        "derived_payload_semantics": "EXCHANGEINFO_PLUS_ADJACENT_PUBLIC_SERVER_TIME_ONLY",
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital": 0,
        "no_backfill": True,
        "no_counter_reset": True,
    }
    manifest_path = out_dir / f"V16B_EXECUTABILITY_MANIFEST_{stamp}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default="artifacts/gate_btc/v16b/executability")
    args = p.parse_args()
    result = capture(Path(args.out_dir))
    print(json.dumps({
        "status": result["status"],
        "captured_at_utc": result["captured_at_utc"],
        "spot_symbols": result["spot_symbols"],
        "usdm_symbols": result["usdm_symbols"],
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
