#!/usr/bin/env python3
"""Pre-registered D50 candidate engine for GATE BTC Sprint 0.

This module never places orders. It can validate mechanics on the deterministic
fixture bundled with Delta v1.1, or replay real candidates only when the exact
raw OHLC and funding inputs are explicitly supplied.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REQUIRED_OHLC = {"date", "symbol", "open", "high", "low", "close", "volume"}
REQUIRED_FUNDING = {"date", "symbol", "funding_rate"}


def load_baseline_module(baseline_root: Path):
    script = baseline_root / "scripts" / "00_run_delta_v11.py"
    spec = importlib.util.spec_from_file_location("delta_v11_sprint0_baseline", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Delta baseline: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    frame.to_csv(partial, index=False)
    os.replace(partial, path)


def atomic_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    os.replace(partial, path)


def _daily_ranks(score_row: pd.Series) -> tuple[list[str], list[str]]:
    valid = score_row.dropna().sort_values(ascending=False)
    return list(valid.index), list(valid.index[::-1])


def _persistent_side(
    raw: dict[pd.Timestamp, dict[str, int]],
    dates: list[pd.Timestamp],
    index: int,
    side: int,
    persistence: int,
) -> set[str]:
    current = raw.get(dates[index], {})
    return {
        symbol
        for symbol, selected_side in current.items()
        if selected_side == side
        and all(raw.get(dates[index - lag], {}).get(symbol) == side for lag in range(persistence))
    }


def build_cost_aware_schedule(
    baseline,
    panels: dict[str, pd.DataFrame],
) -> tuple[dict[pd.Timestamp, dict[str, float]], pd.DataFrame]:
    """Top/bottom 5 entries with top/bottom 7 retention hysteresis."""

    score = panels["score"]
    raw = baseline.raw_selections(score)
    dates = list(score.index)
    persistence = int(baseline.CFG["persistence_days"])
    n = int(baseline.CFG["top_n"])
    retention = 7
    schedule: dict[pd.Timestamp, dict[str, float]] = {}
    rows: list[dict[str, Any]] = []
    incumbent_longs: list[str] = []
    incumbent_shorts: list[str] = []

    for index in range(persistence - 1, len(dates) - 1):
        signal_date = dates[index]
        execution_date = dates[index + 1]
        long_order, short_order = _daily_ranks(score.loc[signal_date])
        long_rank = {symbol: rank for rank, symbol in enumerate(long_order, start=1)}
        short_rank = {symbol: rank for rank, symbol in enumerate(short_order, start=1)}
        persistent_longs = _persistent_side(raw, dates, index, 1, persistence)
        persistent_shorts = _persistent_side(raw, dates, index, -1, persistence)

        kept_longs = [symbol for symbol in incumbent_longs if long_rank.get(symbol, 10**9) <= retention]
        kept_shorts = [symbol for symbol in incumbent_shorts if short_rank.get(symbol, 10**9) <= retention]
        long_entries = [symbol for symbol in long_order[:n] if symbol in persistent_longs and symbol not in kept_longs]
        short_entries = [symbol for symbol in short_order[:n] if symbol in persistent_shorts and symbol not in kept_shorts]
        longs = (kept_longs + long_entries)[:n]
        shorts = (kept_shorts + short_entries)[:n]
        incumbent_longs, incumbent_shorts = longs, shorts
        targets = {**{symbol: 0.10 for symbol in longs}, **{symbol: -0.10 for symbol in shorts}}
        schedule[execution_date] = targets

        for symbol in longs:
            rows.append(
                {
                    "strategy": "D50_COST_AWARE",
                    "signal_date": signal_date,
                    "execution_date": execution_date,
                    "symbol": symbol,
                    "side": "LONG",
                    "score": score.at[signal_date, symbol],
                    "rank": long_rank[symbol],
                    "target_weight": 0.10,
                    "selection_reason": "RETAIN_TOP7" if symbol in kept_longs else "ENTER_TOP5_PERSISTENT",
                }
            )
        for symbol in shorts:
            rows.append(
                {
                    "strategy": "D50_COST_AWARE",
                    "signal_date": signal_date,
                    "execution_date": execution_date,
                    "symbol": symbol,
                    "side": "SHORT",
                    "score": score.at[signal_date, symbol],
                    "rank": short_rank[symbol],
                    "target_weight": -0.10,
                    "selection_reason": "RETAIN_BOTTOM7" if symbol in kept_shorts else "ENTER_BOTTOM5_PERSISTENT",
                }
            )
    return schedule, pd.DataFrame(rows)


def _levels(position: dict[str, Any], mode: str) -> tuple[float, float]:
    if mode == "exit_2sigma":
        if position["weight"] > 0:
            return (
                position["entry"] * (1 - position["hard_stop_pct"]),
                position["entry"] * (1 + position["take_pct"]),
            )
        return (
            position["entry"] * (1 + position["hard_stop_pct"]),
            position["entry"] * (1 - position["take_pct"]),
        )
    if position["weight"] > 0:
        return (
            max(
                position["entry"] * (1 - position["stop_pct"]),
                position["best"] * (1 - position["trail_pct"]),
            ),
            position["entry"] * (1 + position["take_pct"]),
        )
    return (
        min(
            position["entry"] * (1 + position["stop_pct"]),
            position["best"] * (1 + position["trail_pct"]),
        ),
        position["entry"] * (1 - position["take_pct"]),
    )


def simulate_candidate(
    baseline,
    name: str,
    mode: str,
    schedule: dict[pd.Timestamp, dict[str, float]],
    selection_history: pd.DataFrame,
    panels: dict[str, pd.DataFrame],
    funding_daily: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Simulate a pre-registered candidate with full fees/funding/gaps."""

    cfg = baseline.CFG
    funding_map = (
        funding_daily.set_index(["date", "symbol"])["funding_rate"].to_dict()
        if not funding_daily.empty
        else {}
    )
    dates = [date for date in panels["close"].index if date >= pd.Timestamp(cfg["start_date"])]
    cost_rate = (float(cfg["fee_bps_per_side"]) + float(cfg["slippage_bps_per_side"])) / 10_000
    positions: dict[str, dict[str, Any]] = {}
    cooldown_until: dict[str, int] = {}
    signal_reset_block: dict[str, int] = {}
    kill_until = -1
    equity = 1.0
    daily_rows: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    position_rows: list[dict[str, Any]] = []

    for day_index, date in enumerate(dates):
        if date not in panels["open"].index:
            continue
        overnight = intraday = funding_return = trading_cost = turnover = 0.0
        stopped_at_open: set[str] = set()
        previous_dates = panels["close"].index[panels["close"].index < date]
        previous_date = previous_dates[-1] if len(previous_dates) else None

        for symbol in list(positions):
            if previous_date is None or symbol not in panels["open"].columns:
                continue
            open_price = panels["open"].at[date, symbol]
            previous_close = panels["close"].at[previous_date, symbol]
            if pd.isna(open_price) or pd.isna(previous_close) or previous_close <= 0:
                continue
            position = positions[symbol]
            overnight += position["weight"] * (float(open_price) / float(previous_close) - 1)
            stop_level, take_level = _levels(position, mode)
            gap_reason: str | None = None
            if position["weight"] > 0:
                if open_price <= stop_level:
                    gap_reason = "HARD_STOP_GAP" if mode == "exit_2sigma" else "STOP_GAP"
                elif open_price >= take_level:
                    gap_reason = "TAKE_PROFIT_GAP"
            else:
                if open_price >= stop_level:
                    gap_reason = "HARD_STOP_GAP" if mode == "exit_2sigma" else "STOP_GAP"
                elif open_price <= take_level:
                    gap_reason = "TAKE_PROFIT_GAP"
            if gap_reason is None and bool(position.get("pending_soft_exit", False)):
                gap_reason = "STOP_CLOSE_CONFIRMED_NEXT_OPEN"
            if gap_reason:
                weight = abs(position["weight"])
                trading_cost += weight * cost_rate
                turnover += weight
                ledger.append(
                    {
                        "strategy": name,
                        "date": date,
                        "symbol": symbol,
                        "event": gap_reason,
                        "side": "LONG" if position["weight"] > 0 else "SHORT",
                        "price": float(open_price),
                        "entry_price": position["entry"],
                        "signed_weight": position["weight"],
                    }
                )
                signal_reset_block[symbol] = int(np.sign(position["weight"]))
                cooldown_until[symbol] = day_index + int(cfg["reentry_cooldown_days"])
                del positions[symbol]
                stopped_at_open.add(symbol)

        desired = dict(schedule.get(date, {}))
        for symbol, blocked_side in list(signal_reset_block.items()):
            if int(np.sign(desired.get(symbol, 0.0))) != blocked_side:
                signal_reset_block.pop(symbol, None)
        kill_switch_active = day_index <= kill_until
        if kill_switch_active:
            desired = {}
        for symbol in list(desired):
            side = int(np.sign(desired[symbol]))
            if (
                day_index <= cooldown_until.get(symbol, -1)
                or symbol in stopped_at_open
                or signal_reset_block.get(symbol) == side
                or symbol not in panels["open"].columns
                or pd.isna(panels["open"].at[date, symbol])
            ):
                desired.pop(symbol, None)

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
                        "strategy": name,
                        "date": date,
                        "symbol": symbol,
                        "event": "REBALANCE_EXIT",
                        "side": "LONG" if old_weight > 0 else "SHORT",
                        "price": float(open_price),
                        "entry_price": positions[symbol]["entry"],
                        "signed_weight": old_weight,
                    }
                )
                positions.pop(symbol, None)
            if new_weight != 0 and (old_weight == 0 or np.sign(old_weight) != np.sign(new_weight)):
                signal_dates = panels["vol30"].index[panels["vol30"].index < date]
                if not len(signal_dates):
                    continue
                observed_vol = float(panels["vol30"].at[signal_dates[-1], symbol])
                if not np.isfinite(observed_vol) or observed_vol <= 0:
                    continue
                if mode == "exit_2sigma":
                    soft_stop_pct = float(np.clip(2.0 * observed_vol, 0.04, 0.25))
                    hard_stop_pct = float(np.clip(2.5 * observed_vol, 0.06, 0.35))
                    position = {
                        "weight": new_weight,
                        "entry": float(open_price),
                        "best": float(open_price),
                        "soft_stop_pct": soft_stop_pct,
                        "hard_stop_pct": hard_stop_pct,
                        "take_pct": min(0.90, 2.0 * soft_stop_pct),
                        "pending_soft_exit": False,
                    }
                else:
                    stop_pct, take_pct, trail_pct = baseline.stop_parameters(observed_vol)
                    position = {
                        "weight": new_weight,
                        "entry": float(open_price),
                        "best": float(open_price),
                        "stop_pct": stop_pct,
                        "take_pct": take_pct,
                        "trail_pct": trail_pct,
                    }
                positions[symbol] = position
                ledger.append(
                    {
                        "strategy": name,
                        "date": date,
                        "symbol": symbol,
                        "event": "ENTRY",
                        "side": "LONG" if new_weight > 0 else "SHORT",
                        "price": float(open_price),
                        "entry_price": float(open_price),
                        "signed_weight": new_weight,
                    }
                )
            elif new_weight != 0 and symbol in positions:
                positions[symbol]["weight"] = new_weight

        for symbol in list(positions):
            position = positions[symbol]
            open_price = panels["open"].at[date, symbol]
            high = panels["high"].at[date, symbol]
            low = panels["low"].at[date, symbol]
            close = panels["close"].at[date, symbol]
            if any(pd.isna(value) for value in (open_price, high, low, close)):
                continue
            stop_level, take_level = _levels(position, mode)
            exit_price: float | None = None
            exit_reason: str | None = None
            if position["weight"] > 0:
                if low <= stop_level:
                    exit_price = float(stop_level)
                    exit_reason = "HARD_STOP_INTRADAY" if mode == "exit_2sigma" else "STOP_INTRADAY"
                elif high >= take_level:
                    exit_price, exit_reason = float(take_level), "TAKE_PROFIT_INTRADAY"
            else:
                if high >= stop_level:
                    exit_price = float(stop_level)
                    exit_reason = "HARD_STOP_INTRADAY" if mode == "exit_2sigma" else "STOP_INTRADAY"
                elif low <= take_level:
                    exit_price, exit_reason = float(take_level), "TAKE_PROFIT_INTRADAY"
            mark = exit_price if exit_price is not None else float(close)
            intraday += position["weight"] * (mark / float(open_price) - 1)
            if exit_price is not None:
                weight = abs(position["weight"])
                trading_cost += weight * cost_rate
                turnover += weight
                ledger.append(
                    {
                        "strategy": name,
                        "date": date,
                        "symbol": symbol,
                        "event": exit_reason,
                        "side": "LONG" if position["weight"] > 0 else "SHORT",
                        "price": exit_price,
                        "entry_price": position["entry"],
                        "signed_weight": position["weight"],
                    }
                )
                signal_reset_block[symbol] = int(np.sign(position["weight"]))
                cooldown_until[symbol] = day_index + int(cfg["reentry_cooldown_days"])
                del positions[symbol]
            else:
                if mode == "exit_2sigma":
                    soft_level = position["entry"] * (
                        1 - position["soft_stop_pct"] if position["weight"] > 0 else 1 + position["soft_stop_pct"]
                    )
                    position["pending_soft_exit"] = bool(
                        close <= soft_level if position["weight"] > 0 else close >= soft_level
                    )
                else:
                    position["best"] = (
                        max(position["best"], float(high))
                        if position["weight"] > 0
                        else min(position["best"], float(low))
                    )

        for symbol, position in positions.items():
            rate = float(funding_map.get((date, symbol), 0.0))
            funding_return += -position["weight"] * rate
            position_rows.append(
                {
                    "strategy": name,
                    "date": date,
                    "symbol": symbol,
                    "side": "LONG" if position["weight"] > 0 else "SHORT",
                    "signed_weight": position["weight"],
                    "entry_price": position["entry"],
                    "funding_rate_daily": rate,
                }
            )

        gross_return = overnight + intraday + funding_return
        net_return = gross_return - trading_cost
        equity *= max(0.000001, 1 + net_return)
        daily_rows.append(
            {
                "strategy": name,
                "date": date,
                "gross_return": gross_return,
                "trading_cost_return": trading_cost,
                "funding_return": funding_return,
                "net_return": net_return,
                "equity": equity,
                "turnover": turnover,
                "gross_long": sum(max(0.0, p["weight"]) for p in positions.values()),
                "gross_short_abs": sum(abs(min(0.0, p["weight"])) for p in positions.values()),
                "net_exposure": sum(p["weight"] for p in positions.values()),
                "kill_switch_active": kill_switch_active,
            }
        )
        if net_return <= -float(cfg["daily_loss_kill_switch"]):
            kill_until = max(kill_until, day_index + int(cfg["daily_kill_cooldown_days"]))
            ledger.append({"strategy": name, "date": date, "symbol": "PORTFOLIO", "event": "DAILY_KILL_SWITCH", "return": net_return})
        recent = [row["net_return"] for row in daily_rows[-7:]]
        weekly_return = float(np.prod(np.asarray(recent) + 1) - 1) if recent else 0.0
        if len(recent) == 7 and weekly_return <= -float(cfg["weekly_loss_kill_switch"]):
            kill_until = max(kill_until, day_index + int(cfg["weekly_kill_cooldown_days"]))
            ledger.append({"strategy": name, "date": date, "symbol": "PORTFOLIO", "event": "WEEKLY_KILL_SWITCH", "return": weekly_return})

    return (
        pd.DataFrame(daily_rows),
        pd.DataFrame(ledger),
        pd.DataFrame(position_rows),
        selection_history,
    )


def run_engine(
    baseline_root: Path,
    output_dir: Path,
    fixture_mode: bool,
    ohlc_path: Path | None,
    funding_path: Path | None,
) -> dict[str, Any]:
    baseline = load_baseline_module(baseline_root)
    if fixture_mode:
        ohlc, funding_events, _quality, _failures = baseline.build_fixture_data()
        evidence_role = "MECHANICS_ONLY_DETERMINISTIC_FIXTURE"
    else:
        if ohlc_path is None or funding_path is None:
            raise RuntimeError("real replay requires --ohlc and --funding")
        ohlc = pd.read_csv(ohlc_path, parse_dates=["date"])
        funding_events = pd.read_csv(funding_path, parse_dates=["date"])
        if not REQUIRED_OHLC.issubset(ohlc.columns):
            raise RuntimeError(f"OHLC missing columns: {sorted(REQUIRED_OHLC - set(ohlc.columns))}")
        if not REQUIRED_FUNDING.issubset(funding_events.columns):
            raise RuntimeError(f"funding missing columns: {sorted(REQUIRED_FUNDING - set(funding_events.columns))}")
        evidence_role = "DIAGNOSTIC_HISTORICAL_REPLAY_NOT_PROMOTION"

    ohlc["date"] = pd.to_datetime(ohlc["date"])
    funding_events["date"] = pd.to_datetime(funding_events["date"])
    funding_daily = funding_events.groupby(["date", "symbol"], as_index=False)["funding_rate"].sum()
    panels = baseline.build_panels(ohlc)
    base_definition = {"strategy": "Delta_LS_50_50", "gross_long": 0.50, "gross_short": 0.50, "stopvol": False}
    base_schedule, base_selections = baseline.build_target_schedule(panels, base_definition)
    cost_schedule, cost_selections = build_cost_aware_schedule(baseline, panels)

    control_daily, control_ledger, control_positions, control_selections = baseline.simulate_strategy(
        base_definition, panels, funding_daily
    )
    control_daily = control_daily.assign(strategy="D50_CONTROL")
    control_ledger = control_ledger.assign(strategy="D50_CONTROL")
    control_positions = control_positions.assign(strategy="D50_CONTROL")
    control_selections = control_selections.assign(strategy="D50_CONTROL")
    cost = simulate_candidate(
        baseline, "D50_COST_AWARE", "cost_aware", cost_schedule, cost_selections, panels, funding_daily
    )
    exit2 = simulate_candidate(
        baseline, "D50_EXIT_2SIGMA", "exit_2sigma", base_schedule, base_selections, panels, funding_daily
    )

    daily = pd.concat([control_daily, cost[0], exit2[0]], ignore_index=True)
    ledger = pd.concat([control_ledger, cost[1], exit2[1]], ignore_index=True)
    positions = pd.concat([control_positions, cost[2], exit2[2]], ignore_index=True)
    selections = pd.concat([control_selections, cost[3], exit2[3]], ignore_index=True)
    summary_rows: list[dict[str, Any]] = []
    for strategy, group in daily.groupby("strategy"):
        metrics = baseline.calculate_metrics(group["net_return"], group["date"], pd.Timestamp(baseline.CFG["start_date"]))
        economics = baseline.calculate_economics(group)
        summary_rows.append({"strategy": strategy, **metrics, **economics})
    summary = pd.DataFrame(summary_rows)

    atomic_csv(daily, output_dir / "candidate_daily_returns.csv")
    atomic_csv(ledger, output_dir / "candidate_trade_ledger.csv")
    atomic_csv(positions, output_dir / "candidate_daily_positions.csv")
    atomic_csv(selections, output_dir / "candidate_selection_history.csv")
    atomic_csv(summary, output_dir / "candidate_summary.csv")
    manifest = {
        "version": "GATE_BTC_D50_SPRINT0_ENGINE_V1",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "fixture_mode": fixture_mode,
        "evidence_role": evidence_role,
        "research_only": True,
        "operational_status": "NOT_APPROVED",
        "orders": 0,
        "capital": 0,
        "strategies": summary["strategy"].tolist(),
        "observations": {row.strategy: int(row.observations) for row in summary.itertuples()},
        "vol20_status": "CODE_SPECIFIED_DISABLED_BY_PREREGISTRATION_GATE",
    }
    atomic_json(manifest, output_dir / "candidate_engine_manifest.json")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fixture-mode", action="store_true")
    parser.add_argument("--ohlc", type=Path)
    parser.add_argument("--funding", type=Path)
    args = parser.parse_args(argv)
    manifest = run_engine(args.baseline_root, args.output_dir, args.fixture_mode, args.ohlc, args.funding)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
