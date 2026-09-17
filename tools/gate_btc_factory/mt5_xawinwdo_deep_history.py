#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.gate_btc_factory.mt5_shared_family_source import build_packet

FAMILY = "XAWINWDO_REGIME_001"
PAT = re.compile(r"^(WIN|WDO)[FGHJKMNQUVXZ]\d{2}$")
START = datetime(2020, 1, 1, tzinfo=timezone.utc)
END = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)


def iso(ts: int | float) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat().replace("+00:00", "Z")


def collect(mt5_module=None) -> dict[str, Any]:
    if mt5_module is None:
        import MetaTrader5 as mt5_module  # type: ignore
    mt5 = mt5_module
    if not mt5.initialize():
        return build_packet([], source_label="MT5_INIT_FAILED")
    try:
        symbols = sorted(
            [s for s in (mt5.symbols_get() or []) if PAT.fullmatch(str(getattr(s, "name", "") or ""))],
            key=lambda s: str(getattr(s, "name", "")),
        )
        records = []
        for s in symbols:
            name = str(getattr(s, "name", ""))
            if not mt5.symbol_select(name, True):
                continue
            rates = mt5.copy_rates_range(name, mt5.TIMEFRAME_M5, START, END)
            if rates is None or len(rates) == 0:
                continue
            bars = [{
                "timestamp_utc": iso(r["time"]), "open": float(r["open"]), "high": float(r["high"]),
                "low": float(r["low"]), "close": float(r["close"]), "tick_volume": int(r["tick_volume"]),
            } for r in rates]
            records.append({
                "symbol": name,
                "description": str(getattr(s, "description", "") or ""),
                "path": str(getattr(s, "path", "") or ""),
                "earliest_observation_utc": bars[0]["timestamp_utc"],
                "latest_observation_utc": bars[-1]["timestamp_utc"],
                "captured_bar_count": len(bars),
                "bars": bars,
            })
        p = build_packet(records)
        p["family_scope"] = FAMILY
        p["capture_window_utc"] = [START.isoformat().replace("+00:00", "Z"), END.isoformat().replace("+00:00", "Z")]
        p["capture_semantics"] = "PHYSICALLY_RETRIEVED_EXPIRY_CONTRACT_M5_NO_SYNTHETIC_BACKFILL"
        p["scientific_credit"] = 0
        return p
    finally:
        mt5.shutdown()


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--output", required=True); args = ap.parse_args()
    p = collect(); Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"family": FAMILY, "records": p.get("record_count", 0), "orders": 0, "real_capital": 0}, sort_keys=True))
    return 0

if __name__ == "__main__": raise SystemExit(main())
