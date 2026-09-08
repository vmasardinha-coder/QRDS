#!/usr/bin/env python3
from __future__ import annotations

"""Shadow-only H31 intraday entrypoint with explicit MT5 clock binding.

The frozen H31 rule is unchanged. Canonical prospective source binding is not
modified and receives zero credit here. When the preregistered H1 structural
schedule is exhausted, this SHADOW-ONLY entrypoint may continue only the exact
last frozen WIN/WDO front pair while both symbols still have current MT5 ticks.
It never auto-rolls to a new contract. A rollover therefore requires a separate
prospective source-binding decision rather than an implicit retune.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import MetaTrader5 as mt5

import gate_btc_b3_h31_intraday_entrypoint as guard
import gate_btc_b3_h31_intraday_shadow as h31
import gate_btc_h1_inspired_challenger_entrypoint as clock

TZ = h31.TZ


def arg_value(name: str, default: str) -> str:
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def bounded_shadow_schedule() -> dict[str, dict[str, str]]:
    schedule = h31.load_schedule_original() if hasattr(h31, "load_schedule_original") else h31.load_schedule()
    today = datetime.now(TZ).date().isoformat()
    if today in schedule:
        return schedule
    if not schedule:
        raise RuntimeError("EMPTY_FROZEN_FRONT_SCHEDULE")
    last_date = max(schedule)
    if today <= last_date:
        raise RuntimeError(f"NO_FROZEN_FRONT_SCHEDULE_FOR_DATE {today}")
    front = dict(schedule[last_date])

    # Shadow continuation is permitted only while the exact last frozen symbols
    # remain live. There is deliberately no automatic rollover.
    if not mt5.initialize():
        raise RuntimeError(f"MT5_INITIALIZE_FAILED_FOR_FRONT_BINDING {mt5.last_error()}")
    try:
        now = datetime.now(TZ)
        for root in ("WIN", "WDO"):
            symbol = front[root]
            if mt5.symbol_info(symbol) is None or not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"LAST_FROZEN_FRONT_NOT_SELECTABLE root={root} symbol={symbol}")
            mode, tick_ts = clock.detect_time_mode(mt5, symbol, now)
            print(
                f"H31_SHADOW_FRONT_CONTINUATION root={root} symbol={symbol} "
                f"from_date={last_date} mode={mode} tick={tick_ts.isoformat()}",
                flush=True,
            )
    finally:
        mt5.shutdown()

    extended = dict(schedule)
    extended[today] = front
    return extended


def _normalize_rates(rows, start: datetime, end: datetime, mode: str) -> list[dict]:
    out = []
    if rows is None:
        return out
    for r in rows:
        ts = clock.decode_epoch(int(r["time"]), mode)
        if start <= ts <= end:
            out.append(
                {
                    "timestamp": ts.isoformat(),
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                }
            )
    out.sort(key=lambda row: row["timestamp"])
    return out


def mt5_bars(mt5_api, symbol: str, start: datetime, end: datetime) -> list[dict]:
    now = datetime.now(TZ)
    mode, tick_ts = clock.detect_time_mode(mt5_api, symbol, now)
    range_rows = mt5_api.copy_rates_range(
        symbol,
        mt5_api.TIMEFRAME_M5,
        clock.query_time(start, mode),
        clock.query_time(end, mode),
    )
    range_error = mt5_api.last_error()
    pos_rows = mt5_api.copy_rates_from_pos(symbol, mt5_api.TIMEFRAME_M5, 0, 2500)
    pos_error = mt5_api.last_error()
    if range_rows is None and pos_rows is None:
        raise RuntimeError(
            f"MT5_RATES_FAILED symbol={symbol} mode={mode} tick={tick_ts.isoformat()} "
            f"range_error={range_error} pos_error={pos_error}"
        )
    merged: dict[str, dict] = {}
    for row in _normalize_rates(pos_rows, start, end, mode):
        merged[row["timestamp"]] = row
    for row in _normalize_rates(range_rows, start, end, mode):
        merged[row["timestamp"]] = row
    return [merged[key] for key in sorted(merged)]


def annotate_status(shadow_dir: Path) -> None:
    p = shadow_dir / "INTRADAY_STATUS.json"
    if not p.exists():
        return
    try:
        status = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return
    status["H31_SOURCE_BINDING_SCOPE"] = "SHADOW_ONLY_ZERO_CANONICAL_CREDIT"
    status["H31_FRONT_CONTINUATION_POLICY"] = "EXACT_LAST_FROZEN_PAIR_WHILE_LIVE_NO_AUTO_ROLL"
    status["NO_BACKFILL"] = True
    status["NO_RETUNE"] = True
    status["ORDERS"] = 0
    status["REAL_CAPITAL"] = 0
    p.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    shadow_dir = Path(arg_value("--shadow-dir", "runtime/ledgers/b3_h31_shadow_paper"))
    now = datetime.now(TZ)
    session = now.date().isoformat()
    window_end = datetime(now.year, now.month, now.day, 9, 30, tzinfo=TZ)
    deadline = window_end + timedelta(minutes=5)
    if now > deadline and not guard.has_decision(shadow_dir, session):
        guard.persist_missed_window(shadow_dir, session, now)
        annotate_status(shadow_dir)
        return 2

    # Preserve original loader before monkeypatching it.
    if not hasattr(h31, "load_schedule_original"):
        h31.load_schedule_original = h31.load_schedule
    h31.load_schedule = bounded_shadow_schedule
    h31.mt5_bars = mt5_bars
    rc = h31.main()
    annotate_status(shadow_dir)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
