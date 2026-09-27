#!/usr/bin/env python3
"""Delta Walk-Forward v1.1.

Research-only event engine. No API key, account, order or real capital.
V1.1 adds an evidence-gated current selection, persistent BTC regimes,
window-specific economics and a frozen-versus-expanding comparison protocol.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import time
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
try:
    import requests
except ImportError:  # fixture mode remains testable before requirements are installed
    requests = None


VERSION = "DELTA_WALK_FORWARD_1.1"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DATA = ROOT / "data"
CFG = json.loads((ROOT / "config_delta_v11.json").read_text(encoding="utf-8"))
OKX_BASE = "https://www.okx.com"
STRATEGIES = [
    {"strategy": "Delta_LS_70_30", "gross_long": 0.70, "gross_short": 0.30, "stopvol": False},
    {"strategy": "Delta_LS_70_30_StopVol", "gross_long": 0.70, "gross_short": 0.30, "stopvol": True},
    {"strategy": "Delta_LS_50_50", "gross_long": 0.50, "gross_short": 0.50, "stopvol": False},
    {"strategy": "Delta_LS_50_50_StopVol", "gross_long": 0.50, "gross_short": 0.50, "stopvol": True},
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def reset_run_dirs() -> None:
    for directory in (OUT, DATA):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(text, encoding="utf-8")
    os.replace(partial, path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_text(path, json.dumps(payload, indent=2, ensure_ascii=False, default=str))


def save_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    frame.to_csv(partial, index=False)
    os.replace(partial, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def zip_tree(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(".partial.zip")
    if partial.exists():
        partial.unlink()
    with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(ROOT).as_posix())
        for path in (ROOT / "README.md", ROOT / "config_delta_v11.json", ROOT / "requirements.txt"):
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.write(Path(__file__), Path(__file__).relative_to(ROOT).as_posix())
    with zipfile.ZipFile(partial, "r") as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"corrupt output member: {bad}")
    os.replace(partial, destination)


def get_json(session: requests.Session, path: str, params: dict[str, Any]) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = session.get(OKX_BASE + path, params=params, timeout=25)
            response.raise_for_status()
            payload = response.json()
            if str(payload.get("code")) != "0":
                raise RuntimeError(f"OKX code={payload.get('code')} msg={payload.get('msg')}")
            return payload
        except Exception as exc:  # network is external and retried deliberately
            last_error = exc
            time.sleep(0.7 * (attempt + 1))
    raise RuntimeError(f"OKX request failed {path} {params}: {last_error}")


def okx_id(symbol: str) -> str:
    return f"{symbol}-USDT-SWAP"


def fetch_okx_candles(
    session: requests.Session, symbol: str, start: pd.Timestamp, end: pd.Timestamp
) -> pd.DataFrame:
    rows: list[list[Any]] = []
    cursor: str | None = None
    previous_oldest: int | None = None
    start_ms = int(start.tz_localize("UTC").timestamp() * 1000)
    for _ in range(20):
        params: dict[str, Any] = {"instId": okx_id(symbol), "bar": CFG["okx_bar"], "limit": 100}
        if cursor:
            params["after"] = cursor
        payload = get_json(session, "/api/v5/market/history-candles", params)
        page = payload.get("data") or []
        if not page:
            break
        rows.extend(page)
        oldest = min(int(item[0]) for item in page)
        if oldest <= start_ms or oldest == previous_oldest:
            break
        previous_oldest = oldest
        cursor = str(oldest)
        time.sleep(0.12)  # stay below the documented 20 requests / 2 seconds candle limit
    if not rows:
        raise RuntimeError(f"no OHLC returned for {symbol}")
    parsed = []
    for item in rows:
        if len(item) < 6:
            continue
        timestamp = pd.to_datetime(int(item[0]), unit="ms", utc=True).tz_convert(None).normalize()
        confirmed = str(item[8]) if len(item) > 8 else "1"
        if confirmed != "1":
            continue
        parsed.append(
            {
                "date": timestamp,
                "symbol": symbol,
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[7]) if len(item) > 7 else float(item[5]),
                "source": "okx_public_swap_1Dutc",
            }
        )
    frame = pd.DataFrame(parsed).drop_duplicates(["date", "symbol"], keep="last")
    frame = frame[(frame["date"] >= start) & (frame["date"] <= end)].sort_values("date")
    if frame.empty:
        raise RuntimeError(f"OHLC outside requested range for {symbol}")
    return frame


def fetch_okx_funding(
    session: requests.Session, symbol: str, start: pd.Timestamp, end: pd.Timestamp
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    cursor: str | None = None
    previous_oldest: int | None = None
    start_ms = int(start.tz_localize("UTC").timestamp() * 1000)
    for _ in range(20):
        params: dict[str, Any] = {"instId": okx_id(symbol), "limit": 100}
        if cursor:
            params["after"] = cursor
        payload = get_json(session, "/api/v5/public/funding-rate-history", params)
        page = payload.get("data") or []
        if not page:
            break
        for item in page:
            timestamp_ms = int(item["fundingTime"])
            records.append(
                {
                    "date": pd.to_datetime(timestamp_ms, unit="ms", utc=True).tz_convert(None).normalize(),
                    "symbol": symbol,
                    "funding_rate": float(item["fundingRate"]),
                    "funding_time_utc": pd.to_datetime(timestamp_ms, unit="ms", utc=True).isoformat(),
                    "source": "okx_public_funding_history",
                }
            )
        oldest = min(int(item["fundingTime"]) for item in page)
        if oldest <= start_ms or oldest == previous_oldest:
            break
        previous_oldest = oldest
        cursor = str(oldest)
        time.sleep(0.22)  # conservative throttle for the public funding endpoint
    if not records:
        raise RuntimeError(f"no funding returned for {symbol}")
    frame = pd.DataFrame(records).drop_duplicates(["funding_time_utc", "symbol"], keep="last")
    return frame[(frame["date"] >= start) & (frame["date"] <= end)].sort_values(["date", "symbol"])


def collect_public_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if requests is None:
        raise RuntimeError("requests is required for public mode; install requirements.txt")
    start = pd.Timestamp(CFG["warmup_start"])
    end = pd.Timestamp.utcnow().tz_localize(None).normalize() - pd.Timedelta(days=1)
    session = requests.Session()
    session.headers.update({"User-Agent": "QOS-Delta-WalkForward-Research/1.0"})
    candles: list[pd.DataFrame] = []
    funding: list[pd.DataFrame] = []
    quality: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for symbol in CFG["universe"]:
        candle_frame: pd.DataFrame | None = None
        funding_frame: pd.DataFrame | None = None
        try:
            candle_frame = fetch_okx_candles(session, symbol, start, end)
            candles.append(candle_frame)
        except Exception as exc:
            failures.append({"symbol": symbol, "layer": "ohlc", "error": str(exc)})
        try:
            funding_frame = fetch_okx_funding(session, symbol, pd.Timestamp(CFG["start_date"]), end)
            funding.append(funding_frame)
        except Exception as exc:
            failures.append({"symbol": symbol, "layer": "funding", "error": str(exc)})
        quality.append(
            {
                "symbol": symbol,
                "ohlc_rows": 0 if candle_frame is None else len(candle_frame),
                "ohlc_start": None if candle_frame is None else candle_frame["date"].min(),
                "ohlc_end": None if candle_frame is None else candle_frame["date"].max(),
                "funding_events": 0 if funding_frame is None else len(funding_frame),
                "funding_start": None if funding_frame is None else funding_frame["date"].min(),
                "funding_end": None if funding_frame is None else funding_frame["date"].max(),
            }
        )
    if not candles:
        raise RuntimeError("no OKX OHLC datasets loaded")
    return (
        pd.concat(candles, ignore_index=True),
        pd.concat(funding, ignore_index=True) if funding else pd.DataFrame(columns=["date", "symbol", "funding_rate"]),
        pd.DataFrame(quality),
        pd.DataFrame(failures, columns=["symbol", "layer", "error"]),
    )


def build_fixture_data(end_date: str = "2026-07-17") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = pd.date_range(CFG["warmup_start"], end_date, freq="D")
    rng = np.random.default_rng(int(CFG["random_seed"]))
    market = rng.normal(0.0005, 0.014, len(dates))
    post = dates >= pd.Timestamp(CFG["start_date"])
    market[post] += -0.0032
    market += 0.003 * np.sin(np.arange(len(dates)) / 13.0)
    candle_rows: list[dict[str, Any]] = []
    funding_rows: list[dict[str, Any]] = []
    for index, symbol in enumerate(CFG["universe"]):
        beta = 0.75 + 0.035 * index
        alpha = (index - (len(CFG["universe"]) - 1) / 2) * 0.00008
        asset_returns = beta * market + alpha + rng.normal(0, 0.009 + (index % 4) * 0.002, len(dates))
        base_price = 70000.0 if symbol == "BTC" else 150.0 / (1 + index / 2)
        previous_close = base_price
        for i, date in enumerate(dates):
            gap = rng.normal(0, 0.0025)
            open_price = previous_close * (1 + gap)
            intraday = asset_returns[i] - gap
            close_price = max(0.000001, open_price * (1 + intraday))
            spread = abs(rng.normal(0.008, 0.004))
            high = max(open_price, close_price) * (1 + spread)
            low = min(open_price, close_price) * max(0.01, 1 - spread)
            candle_rows.append(
                {
                    "date": date,
                    "symbol": symbol,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close_price,
                    "volume": 50_000_000 * (1 + index / 5) * float(rng.lognormal(0, 0.2)),
                    "source": "deterministic_fixture",
                }
            )
            previous_close = close_price
            if date >= pd.Timestamp(CFG["start_date"]):
                rate = 0.00008 + (index % 5 - 2) * 0.000015 + rng.normal(0, 0.000025)
                funding_rows.append(
                    {
                        "date": date,
                        "symbol": symbol,
                        "funding_rate": rate,
                        "funding_time_utc": f"{date.date()}T16:00:00+00:00",
                        "source": "deterministic_fixture",
                    }
                )
    ohlc = pd.DataFrame(candle_rows)
    funding = pd.DataFrame(funding_rows)
    quality = (
        ohlc.groupby("symbol", as_index=False)
        .agg(ohlc_rows=("date", "size"), ohlc_start=("date", "min"), ohlc_end=("date", "max"))
        .merge(funding.groupby("symbol", as_index=False).agg(funding_events=("date", "size"), funding_start=("date", "min"), funding_end=("date", "max")), on="symbol", how="left")
    )
    return ohlc, funding, quality, pd.DataFrame(columns=["symbol", "layer", "error"])


def cross_section_z(frame: pd.DataFrame) -> pd.DataFrame:
    means = frame.mean(axis=1)
    stds = frame.std(axis=1, ddof=0).replace(0, np.nan)
    return frame.sub(means, axis=0).div(stds, axis=0)


def build_panels(ohlc: pd.DataFrame) -> dict[str, pd.DataFrame]:
    panels = {
        field: ohlc.pivot(index="date", columns="symbol", values=field).sort_index()
        for field in ("open", "high", "low", "close", "volume")
    }
    close = panels["close"]
    returns = close.pct_change(fill_method=None)
    ret7 = close.div(close.shift(7)).sub(1)
    ret14 = close.div(close.shift(14)).sub(1)
    ret30 = close.div(close.shift(30)).sub(1)
    vol30 = returns.rolling(30, min_periods=int(CFG["minimum_signal_history"])).std()
    liquidity = np.log1p(panels["volume"].rolling(14, min_periods=7).median())
    score = (
        0.20 * cross_section_z(ret7)
        + 0.35 * cross_section_z(ret14)
        + 0.35 * cross_section_z(ret30)
        - 0.10 * cross_section_z(vol30)
        + 0.05 * cross_section_z(liquidity)
    )
    panels.update({"returns": returns, "ret7": ret7, "ret14": ret14, "ret30": ret30, "vol30": vol30, "score": score})
    return panels


def raw_selections(score: pd.DataFrame) -> dict[pd.Timestamp, dict[str, int]]:
    result: dict[pd.Timestamp, dict[str, int]] = {}
    n_long = int(CFG["top_n"])
    n_short = int(CFG["bottom_n"])
    for date, row in score.iterrows():
        valid = row.dropna().sort_values(ascending=False)
        if len(valid) < n_long + n_short:
            result[date] = {}
            continue
        longs = list(valid.head(n_long).index)
        shorts = [symbol for symbol in valid.tail(n_short).index if symbol not in longs]
        result[date] = {**{symbol: 1 for symbol in longs}, **{symbol: -1 for symbol in shorts}}
    return result


def build_target_schedule(
    panels: dict[str, pd.DataFrame], definition: dict[str, Any]
) -> tuple[dict[pd.Timestamp, dict[str, float]], pd.DataFrame]:
    score = panels["score"]
    vol30 = panels["vol30"]
    raw = raw_selections(score)
    dates = list(score.index)
    persistence = int(CFG["persistence_days"])
    schedule: dict[pd.Timestamp, dict[str, float]] = {}
    rows: list[dict[str, Any]] = []
    for index in range(persistence - 1, len(dates) - 1):
        signal_date = dates[index]
        execution_date = dates[index + 1]
        current = raw.get(signal_date, {})
        persistent: dict[str, int] = {}
        for symbol, side in current.items():
            if all(raw.get(dates[index - lag], {}).get(symbol) == side for lag in range(persistence)):
                persistent[symbol] = side
        targets: dict[str, float] = {}
        for side, gross, count in (
            (1, float(definition["gross_long"]), int(CFG["top_n"])),
            (-1, float(definition["gross_short"]), int(CFG["bottom_n"])),
        ):
            selected = [symbol for symbol, selected_side in persistent.items() if selected_side == side]
            base_weight = gross / count
            for symbol in selected:
                scale = 1.0
                if bool(definition["stopvol"]):
                    observed = vol30.at[signal_date, symbol]
                    if pd.isna(observed) or observed <= 0:
                        continue
                    scale = min(1.0, float(CFG["stopvol_target_daily_vol"]) / float(observed))
                signed_weight = side * base_weight * scale
                targets[symbol] = signed_weight
                rows.append(
                    {
                        "strategy": definition["strategy"],
                        "signal_date": signal_date,
                        "execution_date": execution_date,
                        "symbol": symbol,
                        "side": "LONG" if side > 0 else "SHORT",
                        "score": score.at[signal_date, symbol],
                        "vol30_daily": vol30.at[signal_date, symbol],
                        "target_weight": signed_weight,
                        "selection_persistence_days": persistence,
                        "lookahead_guard": "signal_close_then_next_daily_open",
                    }
                )
        schedule[execution_date] = targets
    return schedule, pd.DataFrame(rows)


def stop_parameters(vol_daily: float) -> tuple[float, float, float]:
    volatility = float(vol_daily) if np.isfinite(vol_daily) and vol_daily > 0 else float(CFG["stop_floor"]) / float(CFG["stop_vol_multiplier"])
    stop = float(np.clip(float(CFG["stop_vol_multiplier"]) * volatility, CFG["stop_floor"], CFG["stop_cap"]))
    take = min(0.90, stop * float(CFG["take_profit_r_multiple"]))
    trailing = float(np.clip(float(CFG["trailing_vol_multiplier"]) * volatility, CFG["trailing_floor"], CFG["trailing_cap"]))
    return stop, take, trailing


def stop_levels(position: dict[str, Any]) -> tuple[float, float]:
    if position["weight"] > 0:
        stop = max(position["entry"] * (1 - position["stop_pct"]), position["best"] * (1 - position["trail_pct"]))
        take = position["entry"] * (1 + position["take_pct"])
    else:
        stop = min(position["entry"] * (1 + position["stop_pct"]), position["best"] * (1 + position["trail_pct"]))
        take = position["entry"] * (1 - position["take_pct"])
    return stop, take


def simulate_strategy(
    definition: dict[str, Any],
    panels: dict[str, pd.DataFrame],
    funding_daily: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    name = str(definition["strategy"])
    schedule, selection_history = build_target_schedule(panels, definition)
    funding_map = funding_daily.set_index(["date", "symbol"])["funding_rate"].to_dict() if not funding_daily.empty else {}
    dates = [date for date in panels["close"].index if date >= pd.Timestamp(CFG["start_date"])]
    cost_rate = (float(CFG["fee_bps_per_side"]) + float(CFG["slippage_bps_per_side"])) / 10000.0
    positions: dict[str, dict[str, Any]] = {}
    cooldown_until: dict[str, int] = {}
    kill_until = -1
    equity = 1.0
    daily_rows: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    position_rows: list[dict[str, Any]] = []
    for day_index, date in enumerate(dates):
        if date not in panels["open"].index:
            continue
        overnight = 0.0
        intraday = 0.0
        funding_return = 0.0
        trading_cost = 0.0
        turnover = 0.0
        stopped_at_open: set[str] = set()
        previous_date_candidates = panels["close"].index[panels["close"].index < date]
        previous_date = previous_date_candidates[-1] if len(previous_date_candidates) else None

        # Mark old positions from prior close to today's open and apply gap exits.
        for symbol in list(positions):
            if previous_date is None or symbol not in panels["open"].columns:
                continue
            open_price = panels["open"].at[date, symbol]
            previous_close = panels["close"].at[previous_date, symbol]
            if pd.isna(open_price) or pd.isna(previous_close) or previous_close <= 0:
                continue
            position = positions[symbol]
            overnight += position["weight"] * (float(open_price) / float(previous_close) - 1)
            stop_level, take_level = stop_levels(position)
            gap_reason = None
            if position["weight"] > 0:
                if open_price <= stop_level:
                    gap_reason = "STOP_GAP"
                elif open_price >= take_level:
                    gap_reason = "TAKE_PROFIT_GAP"
            else:
                if open_price >= stop_level:
                    gap_reason = "STOP_GAP"
                elif open_price <= take_level:
                    gap_reason = "TAKE_PROFIT_GAP"
            if gap_reason:
                weight = abs(position["weight"])
                trading_cost += weight * cost_rate
                turnover += weight
                ledger.append(
                    {
                        "strategy": name, "date": date, "symbol": symbol, "event": gap_reason,
                        "side": "LONG" if position["weight"] > 0 else "SHORT", "price": float(open_price),
                        "entry_price": position["entry"], "signed_weight": position["weight"],
                        "stop_level": stop_level, "take_level": take_level,
                    }
                )
                del positions[symbol]
                cooldown_until[symbol] = day_index + int(CFG["reentry_cooldown_days"])
                stopped_at_open.add(symbol)

        desired = dict(schedule.get(date, {}))
        kill_switch_active = day_index <= kill_until
        if kill_switch_active:
            desired = {}
        for symbol in list(desired):
            if day_index <= cooldown_until.get(symbol, -1) or symbol in stopped_at_open:
                desired.pop(symbol, None)
            elif symbol not in panels["open"].columns or pd.isna(panels["open"].at[date, symbol]):
                desired.pop(symbol, None)

        # Rebalance at the open. Current-composition retrospective reuse is impossible here.
        for symbol in sorted(set(positions) | set(desired)):
            old_weight = float(positions.get(symbol, {}).get("weight", 0.0))
            new_weight = float(desired.get(symbol, 0.0))
            delta_weight = new_weight - old_weight
            if abs(delta_weight) > 1e-12:
                turnover += abs(delta_weight)
                trading_cost += abs(delta_weight) * cost_rate
            open_price = panels["open"].at[date, symbol] if symbol in panels["open"].columns else np.nan
            if old_weight != 0 and (new_weight == 0 or np.sign(old_weight) != np.sign(new_weight)):
                ledger.append(
                    {
                        "strategy": name, "date": date, "symbol": symbol, "event": "REBALANCE_EXIT",
                        "side": "LONG" if old_weight > 0 else "SHORT", "price": float(open_price),
                        "entry_price": positions[symbol]["entry"], "signed_weight": old_weight,
                    }
                )
                positions.pop(symbol, None)
            if new_weight != 0 and (old_weight == 0 or np.sign(old_weight) != np.sign(new_weight)):
                signal_dates = panels["vol30"].index[panels["vol30"].index < date]
                signal_date = signal_dates[-1]
                observed_vol = panels["vol30"].at[signal_date, symbol]
                stop_pct, take_pct, trail_pct = stop_parameters(float(observed_vol))
                positions[symbol] = {
                    "weight": new_weight, "entry": float(open_price), "best": float(open_price),
                    "stop_pct": stop_pct, "take_pct": take_pct, "trail_pct": trail_pct,
                }
                ledger.append(
                    {
                        "strategy": name, "date": date, "symbol": symbol, "event": "ENTRY",
                        "side": "LONG" if new_weight > 0 else "SHORT", "price": float(open_price),
                        "entry_price": float(open_price), "signed_weight": new_weight,
                        "stop_pct": stop_pct, "take_pct": take_pct, "trailing_pct": trail_pct,
                    }
                )
            elif new_weight != 0 and symbol in positions:
                positions[symbol]["weight"] = new_weight

        # Intraday stop/take processing. If both are touched, stop wins conservatively.
        for symbol in list(positions):
            position = positions[symbol]
            open_price = panels["open"].at[date, symbol]
            high = panels["high"].at[date, symbol]
            low = panels["low"].at[date, symbol]
            close = panels["close"].at[date, symbol]
            if any(pd.isna(value) for value in (open_price, high, low, close)):
                continue
            stop_level, take_level = stop_levels(position)
            exit_price: float | None = None
            exit_reason: str | None = None
            if position["weight"] > 0:
                stop_touched = low <= stop_level
                take_touched = high >= take_level
                if stop_touched:
                    exit_price, exit_reason = float(stop_level), "STOP_INTRADAY"
                elif take_touched:
                    exit_price, exit_reason = float(take_level), "TAKE_PROFIT_INTRADAY"
            else:
                stop_touched = high >= stop_level
                take_touched = low <= take_level
                if stop_touched:
                    exit_price, exit_reason = float(stop_level), "STOP_INTRADAY"
                elif take_touched:
                    exit_price, exit_reason = float(take_level), "TAKE_PROFIT_INTRADAY"
            mark = exit_price if exit_price is not None else float(close)
            intraday += position["weight"] * (mark / float(open_price) - 1)
            if exit_price is not None:
                weight = abs(position["weight"])
                trading_cost += weight * cost_rate
                turnover += weight
                ledger.append(
                    {
                        "strategy": name, "date": date, "symbol": symbol, "event": exit_reason,
                        "side": "LONG" if position["weight"] > 0 else "SHORT", "price": exit_price,
                        "entry_price": position["entry"], "signed_weight": position["weight"],
                        "stop_level": stop_level, "take_level": take_level,
                    }
                )
                del positions[symbol]
                cooldown_until[symbol] = day_index + int(CFG["reentry_cooldown_days"])
            else:
                position["best"] = max(position["best"], float(high)) if position["weight"] > 0 else min(position["best"], float(low))

        for symbol, position in positions.items():
            rate = float(funding_map.get((date, symbol), 0.0))
            funding_return += -position["weight"] * rate
            position_rows.append(
                {
                    "strategy": name, "date": date, "symbol": symbol,
                    "side": "LONG" if position["weight"] > 0 else "SHORT",
                    "signed_weight": position["weight"], "entry_price": position["entry"],
                    "best_price": position["best"], "funding_rate_daily": rate,
                }
            )

        gross_return = overnight + intraday + funding_return
        net_return = gross_return - trading_cost
        equity *= max(0.000001, 1 + net_return)
        daily_rows.append(
            {
                "strategy": name, "date": date, "gross_return": gross_return,
                "trading_cost_return": trading_cost, "funding_return": funding_return,
                "net_return": net_return, "equity": equity, "turnover": turnover,
                "gross_long": sum(max(0.0, p["weight"]) for p in positions.values()),
                "gross_short_abs": sum(abs(min(0.0, p["weight"])) for p in positions.values()),
                "net_exposure": sum(p["weight"] for p in positions.values()),
                "kill_switch_active": kill_switch_active,
            }
        )
        if net_return <= -float(CFG["daily_loss_kill_switch"]):
            kill_until = max(kill_until, day_index + int(CFG["daily_kill_cooldown_days"]))
            ledger.append({"strategy": name, "date": date, "symbol": "PORTFOLIO", "event": "DAILY_KILL_SWITCH", "return": net_return})
        recent = [row["net_return"] for row in daily_rows[-7:]]
        weekly_return = float(np.prod(np.asarray(recent) + 1) - 1) if recent else 0.0
        if len(recent) == 7 and weekly_return <= -float(CFG["weekly_loss_kill_switch"]):
            kill_until = max(kill_until, day_index + int(CFG["weekly_kill_cooldown_days"]))
            ledger.append({"strategy": name, "date": date, "symbol": "PORTFOLIO", "event": "WEEKLY_KILL_SWITCH", "return": weekly_return})
    return pd.DataFrame(daily_rows), pd.DataFrame(ledger), pd.DataFrame(position_rows), selection_history


def calculate_metrics(
    returns: pd.Series, dates: pd.Series, start_label: pd.Timestamp | None = None
) -> dict[str, Any]:
    clean = pd.DataFrame(
        {
            "date": pd.to_datetime(np.asarray(dates)),
            "return": pd.to_numeric(np.asarray(returns), errors="coerce"),
        }
    ).dropna()
    if clean.empty:
        return {"observations": 0}
    start = start_label if start_label is not None else clean["date"].min()
    end = clean["date"].max()
    elapsed_days = max(1, int((end - start).days))
    total = float(np.prod(1 + clean["return"].to_numpy()) - 1)
    cagr = float((1 + total) ** (float(CFG["annualization_days"]) / elapsed_days) - 1) if total > -1 else -1.0
    daily_std = float(clean["return"].std(ddof=1)) if len(clean) > 1 else float("nan")
    ann_vol = daily_std * math.sqrt(float(CFG["annualization_days"])) if np.isfinite(daily_std) else float("nan")
    product_sharpe = cagr / ann_vol if np.isfinite(ann_vol) and ann_vol > 0 else float("nan")
    risk_free_daily = (1 + float(CFG["risk_free_annual"])) ** (1 / float(CFG["annualization_days"])) - 1
    standard_sharpe = ((float(clean["return"].mean()) - risk_free_daily) / daily_std * math.sqrt(float(CFG["annualization_days"]))) if np.isfinite(daily_std) and daily_std > 0 else float("nan")
    equity = (1 + clean["return"]).cumprod()
    drawdown = equity.div(equity.cummax()).sub(1)
    return {
        "start": start.date().isoformat(), "end": end.date().isoformat(), "elapsed_calendar_days": elapsed_days,
        "observations": len(clean), "total_return": total, "annualized_return_cagr": cagr,
        "annualized_volatility": ann_vol, "product_compatible_sharpe_rf0": product_sharpe,
        "standard_daily_sharpe_rf_adjusted": standard_sharpe, "max_drawdown": float(drawdown.min()),
        "daily_win_rate": float((clean["return"] > 0).mean()),
    }


def calculate_economics(daily: pd.DataFrame) -> dict[str, Any]:
    """Return economics for the exact metric window, never for future rows."""
    if daily.empty:
        return {
            "total_trading_cost_return_sum": 0.0,
            "total_funding_return_sum": 0.0,
            "average_daily_turnover": 0.0,
            "kill_switch_days": 0,
        }
    return {
        "total_trading_cost_return_sum": float(pd.to_numeric(daily["trading_cost_return"], errors="coerce").fillna(0).sum()),
        "total_funding_return_sum": float(pd.to_numeric(daily["funding_return"], errors="coerce").fillna(0).sum()),
        "average_daily_turnover": float(pd.to_numeric(daily["turnover"], errors="coerce").fillna(0).mean()),
        "kill_switch_days": int(daily["kill_switch_active"].fillna(False).astype(bool).sum()),
    }


def classify_price_zone(price: float) -> str:
    if price >= 60000:
        return "ABOVE_60K"
    if price >= 55000:
        return "EARLY_FLOOR_55K_60K"
    if price >= 49000:
        return "INSTITUTIONAL_SUPPORT_49K_55K"
    if price >= 42000:
        return "PREFERRED_BOTTOM_42K_49K"
    if price >= 31000:
        return "DEEP_STRESS_31K_42K"
    return "EXTREME_TAIL_BELOW_31K"


def build_btc_regime(close: pd.Series) -> pd.DataFrame:
    frame = pd.DataFrame({"date": close.index, "btc_close": close.values}).sort_values("date")
    frame["sma20"] = frame["btc_close"].rolling(20).mean()
    frame["sma50"] = frame["btc_close"].rolling(50).mean()
    frame["sma200"] = frame["btc_close"].rolling(200).mean()
    frame["ret10"] = frame["btc_close"].pct_change(10)
    frame["ret20"] = frame["btc_close"].pct_change(20)
    frame["vol30_ann"] = frame["btc_close"].pct_change().rolling(30).std() * math.sqrt(365)
    frame["drawdown_180"] = frame["btc_close"].div(frame["btc_close"].rolling(180, min_periods=60).max()).sub(1)
    raw_regimes = []
    stabilized = []
    zones = []
    for row in frame.itertuples(index=False):
        zones.append(classify_price_zone(float(row.btc_close)))
        stable = bool(pd.notna(row.sma20) and pd.notna(row.ret10) and row.btc_close > row.sma20 and row.ret10 > 0 and (pd.isna(row.vol30_ann) or row.vol30_ann < 0.85))
        stabilized.append(stable)
        if pd.notna(row.drawdown_180) and row.drawdown_180 <= -0.35 and pd.notna(row.sma50) and row.btc_close < row.sma50:
            regime = "CRASH"
        elif pd.notna(row.sma50) and (row.btc_close < row.sma50 or (pd.notna(row.ret20) and row.ret20 < 0)):
            regime = "STRESS"
        elif pd.notna(row.sma200) and row.btc_close > row.sma50 > row.sma200 and pd.notna(row.ret20) and row.ret20 > 0:
            regime = "BULL"
        else:
            regime = "NEUTRAL"
        raw_regimes.append(regime)
    frame["price_zone"] = zones
    frame["stabilization_confirmed"] = stabilized
    frame["raw_regime"] = raw_regimes
    persistence = max(1, int(CFG.get("regime_persistence_days", 3)))
    persisted: list[str] = []
    streaks: list[int] = []
    active = raw_regimes[0] if raw_regimes else "NEUTRAL"
    candidate = active
    streak = 0
    for raw in raw_regimes:
        if raw == candidate:
            streak += 1
        else:
            candidate = raw
            streak = 1
        if candidate != active and streak >= persistence:
            active = candidate
        persisted.append(active)
        streaks.append(streak)
    frame["regime"] = persisted
    frame["raw_regime_streak"] = streaks
    frame["regime_persistence_days"] = persistence
    return frame


def build_evidence_gate(delta_summary: pd.DataFrame) -> pd.DataFrame:
    """Evaluate only the expanding walk-forward evidence available at D0+today."""
    expanding = delta_summary[delta_summary["window"] == "EXPANDING_FROM_D0"].copy()
    minimum_observations = int(CFG.get("evidence_gate_min_observations", 60))
    minimum_sharpe = float(CFG.get("evidence_gate_min_product_sharpe", 0.5))
    maximum_drawdown = float(CFG.get("evidence_gate_max_drawdown", -0.15))
    rows: list[dict[str, Any]] = []
    for row in expanding.itertuples(index=False):
        reasons: list[str] = []
        observations = int(getattr(row, "observations", 0) or 0)
        total_return = float(getattr(row, "total_return", float("nan")))
        product_sharpe = float(getattr(row, "product_compatible_sharpe_rf0", float("nan")))
        max_drawdown = float(getattr(row, "max_drawdown", float("nan")))
        standard_sharpe = float(getattr(row, "standard_daily_sharpe_rf_adjusted", float("nan")))
        if observations < minimum_observations:
            reasons.append(f"observations_below_{minimum_observations}")
        if not np.isfinite(total_return) or total_return <= 0:
            reasons.append("nonpositive_total_return")
        if not np.isfinite(product_sharpe) or product_sharpe < minimum_sharpe:
            reasons.append(f"product_sharpe_below_{minimum_sharpe:g}")
        if not np.isfinite(standard_sharpe) or standard_sharpe <= 0:
            reasons.append("nonpositive_standard_sharpe")
        if not np.isfinite(max_drawdown) or max_drawdown < maximum_drawdown:
            reasons.append(f"drawdown_below_{maximum_drawdown:g}")
        rows.append(
            {
                "strategy": row.strategy,
                "window": row.window,
                "end": row.end,
                "observations": observations,
                "total_return": total_return,
                "product_compatible_sharpe_rf0": product_sharpe,
                "standard_daily_sharpe_rf_adjusted": standard_sharpe,
                "max_drawdown": max_drawdown,
                "evidence_eligible": not reasons,
                "rejection_reasons": ";".join(reasons),
            }
        )
    gate = pd.DataFrame(rows)
    if gate.empty:
        return gate
    # A StopVol variant cannot pass merely by shrinking exposure; it must improve
    # both Sharpe and drawdown relative to its matching non-StopVol base.
    indexed = gate.set_index("strategy")
    for strategy in gate.loc[gate["strategy"].str.endswith("_StopVol"), "strategy"]:
        base = strategy.removesuffix("_StopVol")
        if base not in indexed.index:
            continue
        stop_row = indexed.loc[strategy]
        base_row = indexed.loc[base]
        dominated = (
            float(stop_row["product_compatible_sharpe_rf0"]) <= float(base_row["product_compatible_sharpe_rf0"])
            or float(stop_row["max_drawdown"]) <= float(base_row["max_drawdown"])
        )
        if dominated:
            mask = gate["strategy"] == strategy
            gate.loc[mask, "evidence_eligible"] = False
            existing = gate.loc[mask, "rejection_reasons"].iloc[0]
            gate.loc[mask, "rejection_reasons"] = ";".join(filter(None, [existing, "stopvol_does_not_improve_base"]))
    return gate


def select_strategy(
    regime: str,
    zone: str,
    stabilized: bool,
    evidence_gate: pd.DataFrame | None = None,
) -> dict[str, Any]:
    bottom_zones = {"INSTITUTIONAL_SUPPORT_49K_55K", "PREFERRED_BOTTOM_42K_49K", "DEEP_STRESS_31K_42K"}
    if regime == "CRASH" and not stabilized:
        preferred = "NO_TRADE_RESEARCH"
        manual = "CASH_DYNAMIC_DEFENSE_WATCH"
        transition = "WAIT_FOR_STABILIZATION"
    elif regime == "STRESS" and not stabilized:
        preferred = "Delta_LS_50_50_StopVol"
        manual = "Dynamic_Defense_or_Vol_Target"
        transition = "NO_LONG_ONLY_EXPANSION"
    elif zone in bottom_zones and stabilized:
        preferred = "Delta_LS_70_30_StopVol"
        manual = "Vol_Target_plus_staged_BTC_ETH_long_only"
        transition = "BOTTOM_CONFIRMATION_LONG_TRANSITION_WATCH"
    elif regime == "BULL" and stabilized:
        preferred = "QOS_Agressiva_long_only_watch"
        manual = "Staged_BTC_ETH_long_only"
        transition = "REDUCE_DEFENSIVE_DELTA_GRADUALLY"
    else:
        preferred = "Delta_LS_70_30_StopVol"
        manual = "Vol_Target_or_Dynamic_Defense"
        transition = "RADAR_ONLY"
    eligible: list[str] = []
    rejected: dict[str, str] = {}
    if evidence_gate is not None and not evidence_gate.empty:
        eligible = evidence_gate.loc[evidence_gate["evidence_eligible"].astype(bool), "strategy"].astype(str).tolist()
        rejected = {
            str(row.strategy): str(row.rejection_reasons)
            for row in evidence_gate.loc[~evidence_gate["evidence_eligible"].astype(bool)].itertuples(index=False)
        }
    if preferred == "NO_TRADE_RESEARCH":
        research = preferred
        override_reason = "regime_requires_no_trade"
    elif preferred in eligible:
        research = preferred
        override_reason = "preferred_strategy_passed_evidence_gate"
    elif eligible:
        ranked = evidence_gate[evidence_gate["strategy"].isin(eligible)].sort_values(
            ["product_compatible_sharpe_rf0", "max_drawdown"], ascending=[False, False]
        )
        research = str(ranked.iloc[0]["strategy"])
        override_reason = f"preferred_rejected_fallback_to_best_eligible:{preferred}"
    else:
        research = "NO_ELIGIBLE_DELTA_STRATEGY"
        override_reason = f"preferred_rejected_no_eligible_fallback:{preferred}"
    return {
        "regime_preferred_strategy": preferred,
        "research_selection": research,
        "evidence_gate_applied": evidence_gate is not None,
        "evidence_eligible_strategies": eligible,
        "evidence_rejected_strategies": rejected,
        "selection_override_reason": override_reason,
        "manual_low_risk_selection": manual,
        "transition_state": transition,
        "short_policy": "RESEARCH_BENCHMARK_ONLY_NOT_OPERATIONAL",
        "price_alone_can_trigger": False,
        "operational_status": "NOT_APPROVED",
    }


def bottom_estimates_table() -> pd.DataFrame:
    source = "USER_SUPPLIED_WUBLOCKCHAIN_2026_07_14_NOT_INDEPENDENTLY_VERIFIED"
    rows = [
        ("Standard Chartered", 59000, 59000, "possible_cycle_bottom"),
        ("10x Research", 46628, 50732, "model_target"),
        ("CryptoQuant", 53600, 53600, "on_chain_valuation_floor"),
        ("Citi", 53000, 53000, "bearish_scenario_not_explicit_bottom"),
        ("NYDIG", 53700, 53700, "cost_basis_level"),
        ("NYDIG", 37900, 37900, "extreme_70pct_drawdown_scenario"),
        ("Galaxy Research", 40000, 46000, "base_case_bottom"),
        ("Bitfinex", 53400, 53400, "structural_support"),
        ("Bitfinex", 40000, 40000, "weak_demand_scenario"),
        ("22V Research", 40000, 40000, "conditional_target_if_60k_breaks"),
        ("Zacks", 40000, 40000, "deep_bear_market_scenario"),
        ("Stifel", 38000, 38000, "potential_target"),
        ("Ned Davis Research", 31000, 31000, "crypto_winter_scenario"),
    ]
    return pd.DataFrame(rows, columns=["institution", "low_usd", "high_usd", "assessment_type"]).assign(source_status=source)


def monte_carlo_summary(returns: pd.Series, strategy: str, fixture_mode: bool) -> dict[str, Any]:
    clean = pd.to_numeric(returns, errors="coerce").dropna().to_numpy()
    if len(clean) < 30:
        return {"strategy": strategy, "status": "INSUFFICIENT_OOS_RETURNS", "observations": len(clean)}
    paths = 1000 if fixture_mode else int(CFG["monte_carlo_paths"])
    horizon = int(CFG["monte_carlo_horizon_days"])
    block = int(CFG["monte_carlo_block_days"])
    rng = np.random.default_rng(int(CFG["random_seed"]) + sum(ord(char) for char in strategy))
    totals = np.empty(paths)
    max_drawdowns = np.empty(paths)
    for index in range(paths):
        sampled: list[float] = []
        while len(sampled) < horizon:
            start = int(rng.integers(0, max(1, len(clean) - block + 1)))
            sampled.extend(clean[start : start + block])
        path_returns = np.asarray(sampled[:horizon])
        equity = np.cumprod(1 + path_returns)
        totals[index] = equity[-1] - 1
        max_drawdowns[index] = np.min(equity / np.maximum.accumulate(equity) - 1)
    return {
        "strategy": strategy, "status": "EXPLORATORY_SCENARIO_ENGINE_SHORT_SAMPLE",
        "observations": len(clean), "paths": paths, "horizon_days": horizon, "block_days": block,
        "return_p05": float(np.quantile(totals, 0.05)), "return_p25": float(np.quantile(totals, 0.25)),
        "return_p50": float(np.quantile(totals, 0.50)), "return_p75": float(np.quantile(totals, 0.75)),
        "return_p95": float(np.quantile(totals, 0.95)), "probability_loss": float(np.mean(totals < 0)),
        "max_drawdown_p50": float(np.quantile(max_drawdowns, 0.50)),
        "max_drawdown_p05_worse_tail": float(np.quantile(max_drawdowns, 0.05)),
        "decision_role": "SCENARIO_ENGINE_NOT_ALPHA",
    }


def build_chart(all_daily: pd.DataFrame, btc_close: pd.Series) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 1, figsize=(11, 8), constrained_layout=True)
    for strategy, group in all_daily.groupby("strategy"):
        axes[0].plot(group["date"], group["equity"], label=strategy, linewidth=1.4)
        drawdown = group["equity"].div(group["equity"].cummax()).sub(1)
        axes[1].plot(group["date"], drawdown, label=strategy, linewidth=1.2)
    btc = btc_close[btc_close.index >= pd.Timestamp(CFG["start_date"])]
    if not btc.empty:
        axes[0].plot(btc.index, btc / btc.iloc[0], label="BTC close benchmark", color="black", linewidth=1.5, linestyle="--")
    axes[0].axhline(1.0, color="gray", linewidth=0.8)
    axes[0].set_title("Delta walk-forward desde 15/05/2026 - liquido de custos e funding")
    axes[0].set_ylabel("Capital normalizado")
    axes[1].set_title("Drawdown")
    axes[1].set_ylabel("Drawdown")
    axes[1].set_xlabel("Data")
    axes[0].legend(fontsize=8, ncol=2)
    axes[1].legend(fontsize=8, ncol=2)
    fig.savefig(OUT / "delta_walk_forward_equity_drawdown.png", dpi=160)
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-mode", action="store_true")
    parser.add_argument("--output-zip", default=str(ROOT / "delta_walk_forward_outputs_v11.zip"))
    args = parser.parse_args(argv)
    reset_run_dirs()
    output_zip = Path(args.output_zip).resolve()
    manifest: dict[str, Any] = {
        "version": VERSION, "run_utc": utc_now(),
        "mode": "offline_fixture_no_network" if args.fixture_mode else "okx_public_no_api_key_no_orders",
        "technical_status": "RUNNING", "data_quality_status": "PENDING",
        "evidence_status": "PENDING", "operational_status": "NOT_APPROVED",
        "real_orders": 0, "capital_used": 0, "position_size_real": 0,
        "start_date": CFG["start_date"], "benchmark_end_date_inferred": CFG["benchmark_end_date_inferred"],
        "errors": [], "warnings": [],
    }
    caught: Exception | None = None
    try:
        ohlc, funding_events, quality, failures = build_fixture_data() if args.fixture_mode else collect_public_data()
        ohlc["date"] = pd.to_datetime(ohlc["date"])
        funding_events["date"] = pd.to_datetime(funding_events["date"])
        loaded = sorted(ohlc["symbol"].unique())
        if "BTC" not in loaded:
            raise RuntimeError("BTC OHLC is mandatory")
        if len(loaded) < int(CFG["minimum_loaded_assets"]):
            raise RuntimeError(f"insufficient OHLC assets loaded: {len(loaded)}")
        funding_daily = (
            funding_events.groupby(["date", "symbol"], as_index=False)["funding_rate"].sum()
            if not funding_events.empty else pd.DataFrame(columns=["date", "symbol", "funding_rate"])
        )
        save_csv(DATA / "delta_ohlc_daily.csv", ohlc)
        save_csv(DATA / "delta_funding_events.csv", funding_events)
        save_csv(OUT / "data_quality_by_asset.csv", quality)
        save_csv(OUT / "download_failures.csv", failures)
        panels = build_panels(ohlc)
        data_as_of = pd.Timestamp(panels["close"]["BTC"].dropna().index.max())
        if data_as_of < pd.Timestamp(CFG["start_date"]):
            raise RuntimeError("BTC data ends before Delta D0")
        all_daily_frames = []
        all_ledger_frames = []
        all_position_frames = []
        all_selection_frames = []
        summary_rows: list[dict[str, Any]] = []
        comparison_rows: list[dict[str, Any]] = []
        mc_rows: list[dict[str, Any]] = []
        benchmark_end = min(data_as_of, pd.Timestamp(CFG["benchmark_end_date_inferred"]))
        for definition in STRATEGIES:
            daily, ledger, positions, selections = simulate_strategy(definition, panels, funding_daily)
            if daily.empty:
                raise RuntimeError(f"no walk-forward returns for {definition['strategy']}")
            all_daily_frames.append(daily)
            all_ledger_frames.append(ledger)
            all_position_frames.append(positions)
            all_selection_frames.append(selections)
            common = daily[daily["date"] <= benchmark_end]
            common_metrics = calculate_metrics(common["net_return"], common["date"], pd.Timestamp(CFG["start_date"]))
            expanding_metrics = calculate_metrics(daily["net_return"], daily["date"], pd.Timestamp(CFG["start_date"]))
            summary_rows.append(
                {
                    "strategy": definition["strategy"],
                    "window": "COMMON_62_CALENDAR_DAY_BENCHMARK",
                    **common_metrics,
                    **calculate_economics(common),
                }
            )
            summary_rows.append(
                {
                    "strategy": definition["strategy"],
                    "window": "EXPANDING_FROM_D0",
                    **expanding_metrics,
                    **calculate_economics(daily),
                }
            )
            for observations in (30, 60):
                rolling = daily.tail(observations)
                rolling_metrics = calculate_metrics(rolling["net_return"], rolling["date"])
                summary_rows.append(
                    {
                        "strategy": definition["strategy"],
                        "window": f"ROLLING_{observations}_OBSERVATIONS",
                        **rolling_metrics,
                        **calculate_economics(rolling),
                    }
                )
            comparison_rows.append({"source": "OUR_WALK_FORWARD", "strategy": definition["strategy"], **common_metrics})
            mc_rows.append(monte_carlo_summary(daily["net_return"], definition["strategy"], args.fixture_mode))
        all_daily = pd.concat(all_daily_frames, ignore_index=True)
        all_ledger = pd.concat(all_ledger_frames, ignore_index=True) if any(not frame.empty for frame in all_ledger_frames) else pd.DataFrame()
        all_positions = pd.concat(all_position_frames, ignore_index=True) if any(not frame.empty for frame in all_position_frames) else pd.DataFrame()
        all_selections = pd.concat(all_selection_frames, ignore_index=True) if any(not frame.empty for frame in all_selection_frames) else pd.DataFrame()
        save_csv(OUT / "delta_daily_returns.csv", all_daily)
        save_csv(OUT / "delta_trade_ledger.csv", all_ledger)
        save_csv(OUT / "delta_daily_positions.csv", all_positions)
        save_csv(OUT / "delta_historical_selections.csv", all_selections)
        summary = pd.DataFrame(summary_rows)
        save_csv(OUT / "delta_summary.csv", summary)
        save_csv(OUT / "delta_monte_carlo_10000_summary.csv", pd.DataFrame(mc_rows))

        benchmark = dict(CFG["external_delta_benchmark"])
        write_json(OUT / "external_delta_benchmark_user_supplied.json", benchmark)
        comparison_rows.insert(
            0,
            {
                "source": benchmark["source_status"], "strategy": "EXTERNAL_DELTA_REAL_AGGREGATE",
                "start": benchmark["start_date"], "end": benchmark["end_date"],
                "elapsed_calendar_days": benchmark["window_days"], "observations": None,
                "total_return": benchmark["total_return"], "annualized_return_cagr": benchmark["annualized_return"],
                "annualized_volatility": benchmark["annualized_volatility"],
                "product_compatible_sharpe_rf0": benchmark["product_compatible_sharpe_rf0"],
                "standard_daily_sharpe_rf_adjusted": None, "max_drawdown": benchmark["max_drawdown"],
                "daily_win_rate": benchmark["daily_win_rate"],
            },
        )
        btc_close = panels["close"]["BTC"].dropna()
        # Include the prior close so the comparator has a return dated on D0,
        # matching the strategy's open-to-close D0 convention.
        btc_all_returns = btc_close.pct_change(fill_method=None).dropna()
        btc_common_returns = btc_all_returns[
            (btc_all_returns.index >= pd.Timestamp(CFG["start_date"]))
            & (btc_all_returns.index <= benchmark_end)
        ]
        btc_metrics = calculate_metrics(btc_common_returns, pd.Series(btc_common_returns.index), pd.Timestamp(CFG["start_date"]))
        comparison_rows.append({"source": "OKX_PUBLIC_CLOSE_TO_CLOSE", "strategy": "BTC_PUBLIC_COMPARATOR", **btc_metrics})
        comparison = pd.DataFrame(comparison_rows)
        external_sharpe = float(benchmark["product_compatible_sharpe_rf0"])
        comparison["sharpe_difference_vs_external_delta"] = pd.to_numeric(comparison["product_compatible_sharpe_rf0"], errors="coerce") - external_sharpe
        comparison["comparison_status"] = np.where(
            comparison["source"].eq("OUR_WALK_FORWARD"),
            np.where(comparison["sharpe_difference_vs_external_delta"] > 0, "ABOVE_EXTERNAL_AGGREGATE_POINT_ESTIMATE", "BELOW_OR_EQUAL_EXTERNAL_AGGREGATE_POINT_ESTIMATE"),
            "REFERENCE",
        )
        comparison["statistical_claim_allowed"] = False
        save_csv(OUT / "delta_vs_external_benchmark.csv", comparison)

        regimes = build_btc_regime(btc_close)
        save_csv(OUT / "btc_regime_daily.csv", regimes)
        current_regime = regimes.iloc[-1].to_dict()
        evidence_gate = build_evidence_gate(summary)
        save_csv(OUT / "strategy_evidence_gate.csv", evidence_gate)
        selection = select_strategy(
            str(current_regime["regime"]),
            str(current_regime["price_zone"]),
            bool(current_regime["stabilization_confirmed"]),
            evidence_gate,
        )
        current_payload = {
            "data_as_of": pd.Timestamp(current_regime["date"]).date().isoformat(),
            "btc_close": float(current_regime["btc_close"]), "regime": current_regime["regime"],
            "raw_regime": current_regime["raw_regime"],
            "regime_persistence_days": int(current_regime["regime_persistence_days"]),
            "raw_regime_streak": int(current_regime["raw_regime_streak"]),
            "price_zone": current_regime["price_zone"],
            "stabilization_confirmed": bool(current_regime["stabilization_confirmed"]),
            **selection,
            "decision_rule": "persistent_regime_plus_price_zone_trend_volatility_drawdown_stabilization_and_evidence_gate",
        }
        write_json(OUT / "strategy_selection_current.json", current_payload)
        write_json(
            OUT / "comparison_protocol.json",
            {
                "version": "DELTA_COMPARISON_PROTOCOL_1.0",
                "fixed_external_window": {
                    "start": CFG["start_date"],
                    "end": CFG["benchmark_end_date_inferred"],
                    "role": "permanent apples-to-apples comparison with the user-supplied external aggregate",
                    "updates_after_end": False,
                },
                "expanding_internal_window": {
                    "start": CFG["start_date"],
                    "end": data_as_of.date().isoformat(),
                    "role": "ongoing internal monitoring; never compared directly with a frozen external aggregate after its end date",
                    "updates_after_end": True,
                },
                "rolling_internal_windows": [30, 60],
                "external_daily_curve_available": False,
                "statistical_claim_allowed": False,
            },
        )
        save_csv(OUT / "btc_bottom_estimates_user_supplied.csv", bottom_estimates_table())
        build_chart(all_daily, btc_close)

        funding_symbols = int(funding_events["symbol"].nunique()) if not funding_events.empty else 0
        funding_coverage = funding_symbols / len(loaded)
        latest_lag = int((data_as_of - pd.Timestamp(CFG["benchmark_end_date_inferred"])).days)
        data_quality_status = "PASS" if funding_coverage >= 0.80 else "PASS_WITH_WARNINGS"
        if funding_coverage < 0.80:
            manifest["warnings"].append(f"funding coverage below 80%: {funding_coverage:.1%}")
        manifest.update(
            {
                "technical_status": "PASS", "data_quality_status": data_quality_status,
                "evidence_status": "WALK_FORWARD_RESEARCH_SHORT_SAMPLE_NO_OPERATIONAL_PROMOTION",
                "data_as_of": data_as_of.date().isoformat(), "common_benchmark_end": benchmark_end.date().isoformat(),
                "loaded_assets": len(loaded), "loaded_symbols": loaded, "funding_symbols": funding_symbols,
                "funding_coverage": funding_coverage, "latest_lag_vs_benchmark_end_days": latest_lag,
                "ohlc_rows": len(ohlc), "funding_event_rows": len(funding_events),
                "daily_return_rows": len(all_daily), "trade_ledger_rows": len(all_ledger),
                "selection_rows": len(all_selections),
                "lookahead_guard": "signals use prior close and execute next daily open",
                "current_composition_retrospective_use": "PROHIBITED",
                "cost_model": {"fee_bps_per_side": CFG["fee_bps_per_side"], "slippage_bps_per_side": CFG["slippage_bps_per_side"]},
                "funding_model": "OKX public events aggregated daily; timing approximation disclosed",
                "benchmark_status": benchmark["source_status"],
                "monte_carlo_role": "SCENARIO_ENGINE_NOT_ALPHA",
                "survivorship_bias_status": "PRESENT_FIXED_CURRENT_LIQUID_UNIVERSE",
                "selection_evidence_gate": "ENABLED",
                "regime_persistence_days": int(CFG.get("regime_persistence_days", 3)),
                "comparison_protocol": "FIXED_EXTERNAL_PLUS_EXPANDING_AND_ROLLING_INTERNAL",
            }
        )
    except Exception as exc:
        caught = exc
        manifest["technical_status"] = "FAIL"
        manifest["data_quality_status"] = "NOT_EVALUATED"
        manifest["evidence_status"] = "NO_EVIDENCE_RUN_FAILED"
        manifest["errors"].append({"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
    write_json(OUT / "delta_v11_run_manifest.json", manifest)
    evidence_text = (
        "# Evidence status\n\n"
        f"- Technical: `{manifest['technical_status']}`\n"
        f"- Data quality: `{manifest['data_quality_status']}`\n"
        f"- Evidence: `{manifest['evidence_status']}`\n"
        "- Operational: `NOT_APPROVED`\n"
        "- D0: `2026-05-15`\n"
        "- External Sharpe 1.30: user-supplied aggregate, not independently audited.\n"
        "- Monte Carlo is scenario-only and cannot create edge.\n"
        "- Real orders: 0; capital used: 0.\n"
    )
    atomic_text(OUT / "EVIDENCE_STATUS.md", evidence_text)
    report_name = f"DELTA_V11_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_lines = [
        "DELTA WALK-FORWARD V1.1 - EVIDENCE-GATED RESEARCH_ONLY",
        f"Generated UTC: {manifest['run_utc']}",
        f"Technical status: {manifest['technical_status']}",
        f"Data quality: {manifest['data_quality_status']}",
        f"Evidence: {manifest['evidence_status']}",
        f"D0: {manifest['start_date']}",
        f"Data as of: {manifest.get('data_as_of', 'unavailable')}",
        "External Delta benchmark Sharpe: 1.30 (user-supplied aggregate)",
        "Operational status: NOT_APPROVED",
        "Real orders: 0 | Capital used: 0",
    ]
    if manifest["errors"]:
        report_lines.extend(["", "ERRORS", json.dumps(manifest["errors"], indent=2, ensure_ascii=False)])
    atomic_text(OUT / report_name, "\n".join(report_lines) + "\n")
    try:
        zip_tree(OUT, output_zip)
        digest = sha256(output_zip)
        atomic_text(output_zip.with_suffix(output_zip.suffix + ".sha256"), f"{digest}  {output_zip.name}\n")
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        print(f"DELTA_OUTPUT_ZIP={output_zip}")
        print(f"DELTA_REPORT={OUT / report_name}")
    except Exception as packaging_error:
        if caught is None:
            caught = packaging_error
        print(traceback.format_exc(), file=sys.stderr)
    return 1 if caught is not None else 0


if __name__ == "__main__":
    raise SystemExit(main())
