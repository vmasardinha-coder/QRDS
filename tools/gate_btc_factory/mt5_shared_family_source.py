#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "qrds.factory.mt5_shared_family_source.v1"
BTC2_SCHEMA = "gate_btc.2_0.mt5_source_candidate.v1"
SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "MT5_READ_ONLY": True,
    "NO_ORDER_SEND": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "NO_RETUNE": True,
    "NO_BACKFILL": True,
    "H1_ECONOMICS_READ": False,
}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canon_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _iso_epoch(ts: int | float | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat().replace("+00:00", "Z")


def validate_packet(packet: dict[str, Any]) -> None:
    assert packet.get("schema") == SCHEMA
    assert packet.get("safety") == SAFETY
    assert packet.get("primary_scientific_truth") is False
    assert packet.get("canonical_prospective_credit") == 0
    assert packet.get("scientific_promotion_credit") == 0
    assert packet.get("factory_economics_feedback_allowed") is False
    assert packet.get("historical_backfill_credit") == 0
    assert packet.get("availability_semantics") == "VERIFIABLE_CAPTURE_TIMESTAMP_ONLY"
    unsigned = dict(packet)
    claimed = unsigned.pop("packet_sha256", None)
    assert isinstance(claimed, str) and claimed == canon_hash(unsigned)


def build_packet(records: list[dict[str, Any]], captured_at_utc: str | None = None, source_label: str = "MT5_TERMINAL") -> dict[str, Any]:
    captured_at_utc = captured_at_utc or utcnow()
    usable = [r for r in records if r.get("latest_observation_utc") and r.get("bars")]
    packet = {
        "schema": SCHEMA,
        "generated_at_utc": captured_at_utc,
        "source": source_label,
        "readiness": "READY_SHADOW_DATA_ONLY" if usable else "MT5_UNAVAILABLE_OR_NO_FRESH_DATA",
        "factory_family_research_available": bool(usable),
        "btc2_source_discovery_available": bool(usable),
        "primary_scientific_truth": False,
        "canonical_prospective_credit": 0,
        "scientific_promotion_credit": 0,
        "historical_backfill_credit": 0,
        "factory_economics_feedback_allowed": False,
        "availability_semantics": "VERIFIABLE_CAPTURE_TIMESTAMP_ONLY",
        "source_identity_semantics": "MT5_BROKER_TERMINAL_READ_ONLY_CAPTURE",
        "records": usable,
        "record_count": len(usable),
        "safety": SAFETY,
    }
    packet["packet_sha256"] = canon_hash(packet)
    validate_packet(packet)
    return packet


def build_btc2_candidate(packet: dict[str, Any]) -> dict[str, Any]:
    validate_packet(packet)
    out = {
        "schema": BTC2_SCHEMA,
        "generated_at_utc": packet["generated_at_utc"],
        "status": "AVAILABLE_FOR_SOURCE_DISCOVERY_ONLY" if packet["btc2_source_discovery_available"] else "MT5_UNAVAILABLE",
        "source_packet_sha256": packet["packet_sha256"],
        "source_role": "AUXILIARY_READ_ONLY_CAPTURE_SOURCE",
        "may_satisfy_source_admission_without_separate_review": False,
        "may_replace_canonical_source_silently": False,
        "prospective_credit": 0,
        "historical_backfill_credit": 0,
        "safety": SAFETY,
    }
    out["candidate_sha256"] = canon_hash(out)
    return out


def collect_live(max_symbols: int = 200, bars_per_symbol: int = 96, mt5_module=None) -> dict[str, Any]:
    if mt5_module is None:
        import MetaTrader5 as mt5_module  # type: ignore
    mt5 = mt5_module
    if not mt5.initialize():
        return build_packet([], source_label="MT5_INIT_FAILED")
    try:
        symbols = list(mt5.symbols_get() or [])
        symbols.sort(key=lambda s: (0 if bool(getattr(s, "visible", False)) else 1, str(getattr(s, "name", ""))))
        records: list[dict[str, Any]] = []
        for s in symbols[:max_symbols]:
            name = str(getattr(s, "name", "") or "")
            if not name or not mt5.symbol_select(name, True):
                continue
            rates = mt5.copy_rates_from_pos(name, mt5.TIMEFRAME_M5, 0, bars_per_symbol)
            if rates is None or len(rates) == 0:
                continue
            bars = []
            for row in rates:
                bars.append({
                    "timestamp_utc": _iso_epoch(row["time"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "tick_volume": int(row["tick_volume"]),
                })
            tick = mt5.symbol_info_tick(name)
            bid = float(getattr(tick, "bid", 0) or 0) if tick is not None else 0.0
            ask = float(getattr(tick, "ask", 0) or 0) if tick is not None else 0.0
            records.append({
                "symbol": name,
                "description": str(getattr(s, "description", "") or ""),
                "path": str(getattr(s, "path", "") or ""),
                "currency_base": str(getattr(s, "currency_base", "") or ""),
                "currency_profit": str(getattr(s, "currency_profit", "") or ""),
                "digits": int(getattr(s, "digits", 0) or 0),
                "latest_observation_utc": bars[-1]["timestamp_utc"],
                "tick_timestamp_utc": _iso_epoch(getattr(tick, "time", 0) if tick is not None else 0),
                "bid": bid if bid > 0 else None,
                "ask": ask if ask > 0 else None,
                "spread": (ask - bid) if bid > 0 and ask > 0 else None,
                "bars": bars,
            })
        return build_packet(records)
    finally:
        mt5.shutdown()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--btc2-output")
    ap.add_argument("--max-symbols", type=int, default=200)
    ap.add_argument("--bars-per-symbol", type=int, default=96)
    args = ap.parse_args()
    packet = collect_live(max_symbols=args.max_symbols, bars_per_symbol=args.bars_per_symbol)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.btc2_output:
        candidate = build_btc2_candidate(packet)
        Path(args.btc2_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.btc2_output).write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"readiness": packet["readiness"], "records": packet["record_count"], "orders": 0, "real_capital": 0, "engine_feed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
