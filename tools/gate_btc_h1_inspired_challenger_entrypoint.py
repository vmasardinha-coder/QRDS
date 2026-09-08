#!/usr/bin/env python3
from __future__ import annotations

"""Mechanical MT5 clock-binding entrypoint for H1 Inspired shadow.

This wrapper does not change the frozen H1 Inspired signal, timing, side, costs,
or safety contract. It only binds broker-provided MT5 epoch fields to the wall
clock representation that is actually current on the connected terminal.
"""

import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import gate_btc_h1_inspired_challenger_shadow as h1

TZ = ZoneInfo("America/Sao_Paulo")
MAX_TICK_STALENESS_SECONDS = 15 * 60


def _utc_epoch_to_brt(epoch: int) -> datetime:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).astimezone(TZ)


def _broker_local_epoch_to_brt(epoch: int) -> datetime:
    # Some MT5/B3 broker terminals expose a Unix-like integer whose displayed
    # clock components are broker-local rather than UTC. Preserve those wall
    # clock components and bind them explicitly to America/Sao_Paulo.
    return datetime.fromtimestamp(epoch, tz=timezone.utc).replace(tzinfo=None).replace(tzinfo=TZ)


def detect_time_mode(mt5, symbol: str, now: datetime) -> tuple[str, datetime]:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None or int(getattr(tick, "time", 0) or 0) <= 0:
        raise RuntimeError(f"NO_TICK_FOR_TIME_BINDING symbol={symbol}")
    epoch = int(tick.time)
    candidates = {
        "UTC_EPOCH": _utc_epoch_to_brt(epoch),
        "BROKER_LOCAL_EPOCH": _broker_local_epoch_to_brt(epoch),
    }
    mode = min(candidates, key=lambda key: abs((now - candidates[key]).total_seconds()))
    delta = abs((now - candidates[mode]).total_seconds())
    if delta > MAX_TICK_STALENESS_SECONDS:
        raise RuntimeError(
            f"MT5_TICK_NOT_CURRENT symbol={symbol} mode={mode} delta_seconds={delta:.3f} "
            f"utc_candidate={candidates['UTC_EPOCH'].isoformat()} "
            f"broker_local_candidate={candidates['BROKER_LOCAL_EPOCH'].isoformat()}"
        )
    return mode, candidates[mode]


def decode_epoch(epoch: int, mode: str) -> datetime:
    if mode == "UTC_EPOCH":
        return _utc_epoch_to_brt(epoch)
    if mode == "BROKER_LOCAL_EPOCH":
        return _broker_local_epoch_to_brt(epoch)
    raise RuntimeError(f"UNKNOWN_MT5_TIME_MODE {mode}")


def query_time(dt: datetime, mode: str) -> datetime:
    if mode == "UTC_EPOCH":
        return dt.astimezone(timezone.utc)
    if mode == "BROKER_LOCAL_EPOCH":
        return dt.replace(tzinfo=None).replace(tzinfo=timezone.utc)
    raise RuntimeError(f"UNKNOWN_MT5_TIME_MODE {mode}")


def resolve_current_win(mt5, now: datetime) -> str:
    candidates = []
    for s in list(mt5.symbols_get(group="WIN*") or []):
        name = str(s.name)
        key = h1.expiry_key(name)
        if key is None:
            continue
        desc = str(getattr(s, "description", "")).upper()
        path = str(getattr(s, "path", ""))
        if "IBOVESPA MINI" not in desc or "BVMF-Derivatives" not in path:
            continue
        year, month, _ = key
        if (year, month) < (now.year, now.month):
            continue
        if not mt5.symbol_select(name, True):
            continue
        try:
            mode, tick_ts = detect_time_mode(mt5, name, now)
        except Exception:
            continue
        candidates.append((year, month, name, mode, tick_ts))
    if not candidates:
        raise RuntimeError("NO_ACTIVE_WIN_BVMF_MINI_CONTRACT")
    candidates.sort(key=lambda row: (row[0], row[1], row[2]))
    chosen = candidates[0]
    print(
        f"H1_MT5_TIME_BINDING symbol={chosen[2]} mode={chosen[3]} tick={chosen[4].isoformat()}",
        flush=True,
    )
    return chosen[2]


def _normalize_rates(rows, start: datetime, end: datetime, mode: str) -> list[dict]:
    out = []
    if rows is None:
        return out
    for r in rows:
        ts = decode_epoch(int(r["time"]), mode)
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


def mt5_bars(mt5, symbol: str, start: datetime, end: datetime) -> list[dict]:
    now = datetime.now(TZ)
    mode, tick_ts = detect_time_mode(mt5, symbol, now)
    range_rows = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_M5,
        query_time(start, mode),
        query_time(end, mode),
    )
    range_error = mt5.last_error()
    pos_rows = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 2500)
    pos_error = mt5.last_error()
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


def main() -> int:
    h1.resolve_current_win = resolve_current_win
    h1.mt5_bars = mt5_bars
    return h1.main()


if __name__ == "__main__":
    raise SystemExit(main())
