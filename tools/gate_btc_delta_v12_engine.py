#!/usr/bin/env python3
"""Delta V12 prospective long/short engine over the TOP100 universe.

Research/shadow only. No credentials, no order path, no engine feed, no capital.

This implements DELTA_V12_ENGINE_1.0, frozen on 2026-08-21 before any TOP100
return existed. Every selection and risk rule is inherited from the canonical
DELTA_WALK_FORWARD_1.1 script unchanged; what differs is the universe (20 names
to TOP100), the selection size (5+5 to 10+10), the price pipeline (OKX-only to
multi-venue with venue pins) and the cost model (flat 3 bps to liquidity-tiered).

Prospective discipline, which is the whole point of the exercise:

  * The anchor is the latest completed UTC close seen by the FIRST run, recorded
    once in ANCHOR.json and never chosen again. Simulation starts the day after
    it with an empty book, so no pre-anchor return can enter the ledger.
  * History before the anchor is read only to warm up ret30/vol30/liquidity.
    Those are inputs to a signal, never evidence of a return.
  * The ledger is append-only and hash-chained. Each run recomputes the whole
    post-anchor series and refuses to write if a previously committed row
    changed, so a silent restatement cannot pass as new evidence.
  * A missing UTC day fails closed. Gaps are never backfilled.

Funding comes from tools/gate_btc_delta_v12_funding.py, read from the venue each
asset is pinned to. Pass --funding-csv and the model is OBSERVED; omit it and
funding books as zero, which flatters a long-tilted book and is recorded as such
in every position row. Under the OBSERVED model, holding an asset the feed does
not cover fails closed rather than quietly costing it nothing.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA = "gate_btc.delta_v12_engine.v1"
ENGINE_VERSION = "DELTA_V12_ENGINE_1.0"
ZERO_HASH = "0" * 64

# The four books run in parallel, always. Picking the leader after seeing the
# returns is the exact bias the preregistration exists to prevent.
BOOKS = (
    {"strategy": "V12_LS_70_30", "gross_long": 0.70, "gross_short": 0.30, "stopvol": False},
    {"strategy": "V12_LS_70_30_StopVol", "gross_long": 0.70, "gross_short": 0.30, "stopvol": True},
    {"strategy": "V12_LS_50_50", "gross_long": 0.50, "gross_short": 0.50, "stopvol": False},
    {"strategy": "V12_LS_50_50_StopVol", "gross_long": 0.50, "gross_short": 0.50, "stopvol": True},
)

FUNDING_OBSERVED = "OBSERVED_PER_PINNED_VENUE_SUMMED_TO_THE_UTC_DAY_OF_SETTLEMENT"
FUNDING_ABSENT = "ABSENT_FROM_V12_PRICE_PIPELINE_TREATED_AS_ZERO_NOT_A_CLAIM_OF_ZERO_CARRY"
# Retained under the old name so an older ledger's marker still resolves.
FUNDING_MODEL = FUNDING_ABSENT

SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "engine_feed": False,
    "exchange_auth_allowed": False,
    "promotion_allowed": False,
    "official_replica_claim": False,
    "methodology_changes": 0,
    "orders_generated": 0,
    "real_capital_used": 0,
}


class EngineError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# small numeric helpers; the panel is 100 names by ~100 days, so stdlib is ample
# --------------------------------------------------------------------------

def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()


def sample_stdev(values: list[float]) -> float | None:
    """ddof=1, matching pandas .std() on a rolling window."""
    return statistics.stdev(values) if len(values) > 1 else None


def population_stdev(values: list[float]) -> float | None:
    """ddof=0, matching pandas .std(axis=1, ddof=0) for the cross-section."""
    return statistics.pstdev(values) if values else None


def cross_section_z(row: dict[str, float | None], bases: list[str]) -> dict[str, float | None]:
    present = [row[b] for b in bases if row.get(b) is not None]
    if not present:
        return {b: None for b in bases}
    mu = statistics.fmean(present)
    sd = population_stdev(present)
    # pandas replaces a zero cross-sectional std with NaN; a flat cross-section
    # carries no ranking information and must not be divided through.
    if not sd:
        return {b: None for b in bases}
    return {b: (None if row.get(b) is None else (row[b] - mu) / sd) for b in bases}


# --------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------

def read_prices(path: Path) -> tuple[list[str], list[str], dict[str, dict[str, dict[str, float]]]]:
    """DAILY_PRICES.csv from the multi-venue adapter into date -> base -> field."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise EngineError(f"price panel {path} is empty")
    panel: dict[str, dict[str, dict[str, float]]] = {}
    bases: set[str] = set()
    for row in rows:
        day = str(row["date"])[:10]
        base = str(row["base"]).strip().upper()
        bases.add(base)
        try:
            bar = {field: float(row[field]) for field in ("open", "high", "low", "close", "volume")}
        except (TypeError, ValueError) as exc:
            raise EngineError(f"non-numeric bar for {base} on {day}: {exc}") from exc
        if bar["close"] <= 0 or bar["open"] <= 0:
            raise EngineError(f"non-positive price for {base} on {day}")
        panel.setdefault(day, {})[base] = bar
    return sorted(panel), sorted(bases), panel


def read_universe_bands(path: Path) -> dict[str, int]:
    """Base asset to liquidity rank, which selects the slippage band."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    bands = {}
    for row in rows:
        base = str(row.get("baseAsset") or "").strip().upper()
        if base:
            bands[base] = int(row["liquidity_rank"])
    if not bands:
        raise EngineError(f"universe {path} has no baseAsset rows")
    return bands


def slippage_bps(rank: int | None, bands: dict[str, float]) -> float:
    """Tiered slippage. An unranked name takes the widest band, never the tightest."""
    if rank is None:
        return max(float(v) for v in bands.values())
    for label, value in sorted(bands.items(), key=lambda kv: int(str(kv[0]).split("-")[0])):
        low, high = (int(part) for part in str(label).split("-"))
        if low <= rank <= high:
            return float(value)
    return max(float(v) for v in bands.values())


def assert_no_gaps(dates: list[str]) -> None:
    """FAIL_CLOSED_NO_BACKFILL: a missing UTC day is a refusal, never a fill."""
    for earlier, later in zip(dates, dates[1:]):
        expected = date.fromisoformat(earlier) + timedelta(days=1)
        if date.fromisoformat(later) != expected:
            raise EngineError(
                f"FAIL_CLOSED: price panel gap between {earlier} and {later}; "
                "the frozen gap policy forbids backfilling a missed day")


# --------------------------------------------------------------------------
# signal panels — every formula below is DELTA_WALK_FORWARD_1.1 verbatim
# --------------------------------------------------------------------------

def build_panels(dates: list[str], bases: list[str],
                 panel: dict[str, dict[str, dict[str, float]]],
                 cfg: dict[str, Any]) -> dict[str, dict[str, dict[str, float | None]]]:
    close = {d: {b: panel[d].get(b, {}).get("close") for b in bases} for d in dates}
    volume = {d: {b: panel[d].get(b, {}).get("volume") for b in bases} for d in dates}
    index = {d: i for i, d in enumerate(dates)}
    min_history = int(cfg["minimum_signal_history"])

    def shifted_return(day: str, base: str, lag: int) -> float | None:
        i = index[day]
        if i < lag:
            return None
        past = close[dates[i - lag]][base]
        now = close[day][base]
        if past is None or now is None or past <= 0:
            return None
        return now / past - 1

    returns: dict[str, dict[str, float | None]] = {}
    for day in dates:
        returns[day] = {b: shifted_return(day, b, 1) for b in bases}

    vol30: dict[str, dict[str, float | None]] = {}
    liquidity: dict[str, dict[str, float | None]] = {}
    for day in dates:
        i = index[day]
        vol_row: dict[str, float | None] = {}
        liq_row: dict[str, float | None] = {}
        for base in bases:
            window = [returns[dates[j]][base] for j in range(max(0, i - 29), i + 1)]
            clean = [v for v in window if v is not None]
            vol_row[base] = sample_stdev(clean) if len(clean) >= min_history else None
            vol_window = [volume[dates[j]][base] for j in range(max(0, i - 13), i + 1)]
            vol_clean = [v for v in vol_window if v is not None]
            liq_row[base] = math.log1p(statistics.median(vol_clean)) if len(vol_clean) >= 7 else None
        vol30[day] = vol_row
        liquidity[day] = liq_row

    score: dict[str, dict[str, float | None]] = {}
    for day in dates:
        z7 = cross_section_z({b: shifted_return(day, b, 7) for b in bases}, bases)
        z14 = cross_section_z({b: shifted_return(day, b, 14) for b in bases}, bases)
        z30 = cross_section_z({b: shifted_return(day, b, 30) for b in bases}, bases)
        zvol = cross_section_z(vol30[day], bases)
        zliq = cross_section_z(liquidity[day], bases)
        row: dict[str, float | None] = {}
        for base in bases:
            parts = (z7[base], z14[base], z30[base], zvol[base], zliq[base])
            # Any missing component makes the score undefined, as a NaN sum does
            # in the canonical script. A partial score is not a weaker signal,
            # it is a different formula.
            row[base] = None if any(p is None for p in parts) else (
                0.20 * parts[0] + 0.35 * parts[1] + 0.35 * parts[2]
                - 0.10 * parts[3] + 0.05 * parts[4])
        score[day] = row

    return {"close": close, "volume": volume, "returns": returns,
            "vol30": vol30, "liquidity": liquidity, "score": score}


def raw_selections(dates: list[str], bases: list[str],
                   score: dict[str, dict[str, float | None]],
                   cfg: dict[str, Any]) -> dict[str, dict[str, int]]:
    n_long, n_short = int(cfg["top_n"]), int(cfg["bottom_n"])
    result: dict[str, dict[str, int]] = {}
    for day in dates:
        valid = [(b, v) for b, v in score[day].items() if v is not None]
        if len(valid) < n_long + n_short:
            result[day] = {}
            continue
        ordered = [b for b, _ in sorted(valid, key=lambda kv: -kv[1])]
        longs = ordered[:n_long]
        shorts = [b for b in ordered[-n_short:] if b not in longs]
        result[day] = {**{b: 1 for b in longs}, **{b: -1 for b in shorts}}
    return result


def target_schedule(dates: list[str], bases: list[str], panels: dict[str, Any],
                    book: dict[str, Any], cfg: dict[str, Any],
                    ) -> tuple[dict[str, dict[str, float]], list[dict[str, Any]]]:
    score, vol30 = panels["score"], panels["vol30"]
    raw = raw_selections(dates, bases, score, cfg)
    persistence = int(cfg["persistence_days"])
    schedule: dict[str, dict[str, float]] = {}
    rows: list[dict[str, Any]] = []
    for i in range(persistence - 1, len(dates) - 1):
        signal_day, execution_day = dates[i], dates[i + 1]
        persistent = {
            symbol: side for symbol, side in raw.get(signal_day, {}).items()
            if all(raw.get(dates[i - lag], {}).get(symbol) == side for lag in range(persistence))
        }
        targets: dict[str, float] = {}
        for side, gross, count in ((1, float(book["gross_long"]), int(cfg["top_n"])),
                                   (-1, float(book["gross_short"]), int(cfg["bottom_n"]))):
            base_weight = gross / count
            for symbol in sorted(s for s, v in persistent.items() if v == side):
                scale = 1.0
                if book["stopvol"]:
                    observed = vol30[signal_day][symbol]
                    if observed is None or observed <= 0:
                        continue
                    scale = min(1.0, float(cfg["stopvol_target_daily_vol"]) / float(observed))
                signed = side * base_weight * scale
                targets[symbol] = signed
                rows.append({
                    "strategy": book["strategy"], "signal_date": signal_day,
                    "execution_date": execution_day, "symbol": symbol,
                    "side": "LONG" if side > 0 else "SHORT",
                    "score": score[signal_day][symbol], "vol30_daily": vol30[signal_day][symbol],
                    "target_weight": signed, "selection_persistence_days": persistence,
                    "lookahead_guard": "signal_close_then_next_daily_open",
                })
        schedule[execution_day] = targets
    return schedule, rows


# --------------------------------------------------------------------------
# simulation — the canonical loop, with per-symbol tiered cost
# --------------------------------------------------------------------------

def stop_parameters(vol_daily: float | None, cfg: dict[str, Any]) -> tuple[float, float, float]:
    multiplier = float(cfg["stop_vol_multiplier"])
    volatility = (float(vol_daily) if vol_daily is not None and math.isfinite(vol_daily)
                  and vol_daily > 0 else float(cfg["stop_floor"]) / multiplier)
    stop = min(max(multiplier * volatility, float(cfg["stop_floor"])), float(cfg["stop_cap"]))
    take = min(0.90, stop * float(cfg["take_profit_r_multiple"]))
    trailing = min(max(float(cfg["trailing_vol_multiplier"]) * volatility,
                       float(cfg["trailing_floor"])), float(cfg["trailing_cap"]))
    return stop, take, trailing


def stop_levels(position: dict[str, Any]) -> tuple[float, float]:
    if position["weight"] > 0:
        stop = max(position["entry"] * (1 - position["stop_pct"]),
                   position["best"] * (1 - position["trail_pct"]))
        take = position["entry"] * (1 + position["take_pct"])
    else:
        stop = min(position["entry"] * (1 + position["stop_pct"]),
                   position["best"] * (1 + position["trail_pct"]))
        take = position["entry"] * (1 - position["take_pct"])
    return stop, take


def read_funding(path: Path | None) -> tuple[dict[tuple[str, str], float], set[str], str]:
    """Daily funding by (date, symbol), plus the symbols the feed actually covers."""
    if path is None:
        return {}, set(), FUNDING_ABSENT
    rates: dict[tuple[str, str], float] = {}
    covered: set[str] = set()
    for row in read_csv_rows(path):
        symbol = str(row["symbol"]).strip().upper()
        rates[(str(row["date"])[:10], symbol)] = float(row["funding_rate"])
        covered.add(symbol)
    if not covered:
        raise EngineError(f"funding file {path} is empty; refusing to imply zero carry")
    return rates, covered, FUNDING_OBSERVED


def simulate(book: dict[str, Any], dates: list[str], bases: list[str], panels: dict[str, Any],
             panel: dict[str, dict[str, dict[str, float]]], cost_rate: dict[str, float],
             anchor: str, cfg: dict[str, Any],
             funding: dict[tuple[str, str], float] | None = None,
             funded: set[str] | None = None,
             funding_model: str = FUNDING_ABSENT) -> dict[str, list[dict[str, Any]]]:
    name = book["strategy"]
    schedule, selections = target_schedule(dates, bases, panels, book, cfg)
    traded = [d for d in dates if d > anchor]
    index = {d: i for i, d in enumerate(dates)}

    positions: dict[str, dict[str, Any]] = {}
    cooldown_until: dict[str, int] = {}
    kill_until = -1
    equity = 1.0
    daily: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    holdings: list[dict[str, Any]] = []

    def bar(day: str, symbol: str) -> dict[str, float] | None:
        return panel.get(day, {}).get(symbol)

    for day_index, day in enumerate(traded):
        previous = dates[index[day] - 1] if index[day] > 0 else None
        overnight = intraday = funding_return = trading_cost = turnover = 0.0
        stopped_at_open: set[str] = set()

        # Mark from the prior close to today's open, then honour gap exits.
        for symbol in list(positions):
            today_bar = bar(day, symbol)
            prior_bar = bar(previous, symbol) if previous else None
            if not today_bar or not prior_bar or prior_bar["close"] <= 0:
                continue
            position = positions[symbol]
            open_price = today_bar["open"]
            overnight += position["weight"] * (open_price / prior_bar["close"] - 1)
            stop_level, take_level = stop_levels(position)
            reason = None
            if position["weight"] > 0:
                if open_price <= stop_level:
                    reason = "STOP_GAP"
                elif open_price >= take_level:
                    reason = "TAKE_PROFIT_GAP"
            else:
                if open_price >= stop_level:
                    reason = "STOP_GAP"
                elif open_price <= take_level:
                    reason = "TAKE_PROFIT_GAP"
            if reason:
                weight = abs(position["weight"])
                trading_cost += weight * cost_rate[symbol]
                turnover += weight
                events.append({
                    "strategy": name, "date": day, "symbol": symbol, "event": reason,
                    "side": "LONG" if position["weight"] > 0 else "SHORT",
                    "price": open_price, "entry_price": position["entry"],
                    "signed_weight": position["weight"],
                    "stop_level": stop_level, "take_level": take_level})
                del positions[symbol]
                cooldown_until[symbol] = day_index + int(cfg["reentry_cooldown_days"])
                stopped_at_open.add(symbol)

        desired = dict(schedule.get(day, {}))
        kill_switch_active = day_index <= kill_until
        if kill_switch_active:
            desired = {}
        for symbol in list(desired):
            if day_index <= cooldown_until.get(symbol, -1) or symbol in stopped_at_open:
                desired.pop(symbol, None)
            elif not bar(day, symbol):
                desired.pop(symbol, None)

        # Rebalance at the open.
        for symbol in sorted(set(positions) | set(desired)):
            old_weight = float(positions.get(symbol, {}).get("weight", 0.0))
            new_weight = float(desired.get(symbol, 0.0))
            delta = new_weight - old_weight
            if abs(delta) > 1e-12:
                turnover += abs(delta)
                trading_cost += abs(delta) * cost_rate[symbol]
            today_bar = bar(day, symbol)
            open_price = today_bar["open"] if today_bar else None
            crossing = old_weight != 0 and (new_weight == 0 or (old_weight > 0) != (new_weight > 0))
            if crossing:
                events.append({
                    "strategy": name, "date": day, "symbol": symbol, "event": "REBALANCE_EXIT",
                    "side": "LONG" if old_weight > 0 else "SHORT", "price": open_price,
                    "entry_price": positions[symbol]["entry"], "signed_weight": old_weight})
                positions.pop(symbol, None)
            opening = new_weight != 0 and (old_weight == 0 or (old_weight > 0) != (new_weight > 0))
            if opening:
                signal_day = dates[index[day] - 1]
                stop_pct, take_pct, trail_pct = stop_parameters(
                    panels["vol30"][signal_day][symbol], cfg)
                positions[symbol] = {
                    "weight": new_weight, "entry": open_price, "best": open_price,
                    "stop_pct": stop_pct, "take_pct": take_pct, "trail_pct": trail_pct}
                events.append({
                    "strategy": name, "date": day, "symbol": symbol, "event": "ENTRY",
                    "side": "LONG" if new_weight > 0 else "SHORT", "price": open_price,
                    "entry_price": open_price, "signed_weight": new_weight,
                    "stop_pct": stop_pct, "take_pct": take_pct, "trailing_pct": trail_pct})
            elif new_weight != 0 and symbol in positions:
                positions[symbol]["weight"] = new_weight

        # Intraday stop/take. When both are touched the stop wins, conservatively.
        for symbol in list(positions):
            position = positions[symbol]
            today_bar = bar(day, symbol)
            if not today_bar:
                continue
            open_price, high, low, close = (today_bar["open"], today_bar["high"],
                                            today_bar["low"], today_bar["close"])
            stop_level, take_level = stop_levels(position)
            exit_price = exit_reason = None
            if position["weight"] > 0:
                if low <= stop_level:
                    exit_price, exit_reason = float(stop_level), "STOP_INTRADAY"
                elif high >= take_level:
                    exit_price, exit_reason = float(take_level), "TAKE_PROFIT_INTRADAY"
            else:
                if high >= stop_level:
                    exit_price, exit_reason = float(stop_level), "STOP_INTRADAY"
                elif low <= take_level:
                    exit_price, exit_reason = float(take_level), "TAKE_PROFIT_INTRADAY"
            mark = exit_price if exit_price is not None else float(close)
            intraday += position["weight"] * (mark / float(open_price) - 1)
            if exit_price is not None:
                weight = abs(position["weight"])
                trading_cost += weight * cost_rate[symbol]
                turnover += weight
                events.append({
                    "strategy": name, "date": day, "symbol": symbol, "event": exit_reason,
                    "side": "LONG" if position["weight"] > 0 else "SHORT", "price": exit_price,
                    "entry_price": position["entry"], "signed_weight": position["weight"],
                    "stop_level": stop_level, "take_level": take_level})
                del positions[symbol]
                cooldown_until[symbol] = day_index + int(cfg["reentry_cooldown_days"])
            else:
                position["best"] = (max(position["best"], float(high)) if position["weight"] > 0
                                    else min(position["best"], float(low)))

        for symbol, position in sorted(positions.items()):
            if funding_model == FUNDING_OBSERVED:
                if symbol not in (funded or set()):
                    # Booking a day we cannot cost is how a zero assumption
                    # sneaks back in one asset at a time.
                    raise EngineError(
                        f"FAIL_CLOSED: {symbol} is held on {day} but the funding feed "
                        "does not cover it; refusing to book an uncosted position")
                rate = float((funding or {}).get((day, symbol), 0.0))
            else:
                rate = 0.0
            funding_return += -position["weight"] * rate
            holdings.append({
                "strategy": name, "date": day, "symbol": symbol,
                "side": "LONG" if position["weight"] > 0 else "SHORT",
                "signed_weight": position["weight"], "entry_price": position["entry"],
                "best_price": position["best"], "funding_rate_daily": rate,
                "funding_model": funding_model})

        gross_return = overnight + intraday + funding_return
        net_return = gross_return - trading_cost
        equity *= max(0.000001, 1 + net_return)
        daily.append({
            "strategy": name, "date": day, "gross_return": gross_return,
            "trading_cost_return": trading_cost, "funding_return": funding_return,
            "net_return": net_return, "normalized_nav": equity, "turnover": turnover,
            "gross_long": sum(max(0.0, p["weight"]) for p in positions.values()),
            "gross_short_abs": sum(abs(min(0.0, p["weight"])) for p in positions.values()),
            "net_exposure": sum(p["weight"] for p in positions.values()),
            "open_positions": len(positions),
            "kill_switch_active": kill_switch_active})

        if net_return <= -float(cfg["daily_loss_kill_switch"]):
            kill_until = max(kill_until, day_index + int(cfg["daily_kill_cooldown_days"]))
            events.append({"strategy": name, "date": day, "symbol": "PORTFOLIO",
                           "event": "DAILY_KILL_SWITCH", "price": None,
                           "signed_weight": net_return})
        recent = [row["net_return"] for row in daily[-7:]]
        if len(recent) == 7:
            weekly = math.prod(1 + r for r in recent) - 1
            if weekly <= -float(cfg["weekly_loss_kill_switch"]):
                kill_until = max(kill_until, day_index + int(cfg["weekly_kill_cooldown_days"]))
                events.append({"strategy": name, "date": day, "symbol": "PORTFOLIO",
                               "event": "WEEKLY_KILL_SWITCH", "price": None,
                               "signed_weight": weekly})

    peak = 0.0
    for row in daily:
        peak = max(peak, row["normalized_nav"])
        row["drawdown"] = row["normalized_nav"] / peak - 1 if peak > 0 else 0.0

    return {"daily": daily, "events": events, "holdings": holdings,
            "selections": [r for r in selections if r["execution_date"] > anchor]}


# --------------------------------------------------------------------------
# metrics and the frozen evidence gate
# --------------------------------------------------------------------------

def metrics(daily: list[dict[str, Any]], anchor: str, cfg: dict[str, Any]) -> dict[str, Any]:
    returns = [row["net_return"] for row in daily]
    if not returns:
        return {"observations": 0}
    annualization = float(cfg["annualization_days"])
    start, end = date.fromisoformat(anchor), date.fromisoformat(daily[-1]["date"])
    elapsed = max(1, (end - start).days)
    total = math.prod(1 + r for r in returns) - 1
    cagr = (1 + total) ** (annualization / elapsed) - 1 if total > -1 else -1.0
    daily_std = sample_stdev(returns)
    ann_vol = daily_std * math.sqrt(annualization) if daily_std else None
    product_sharpe = cagr / ann_vol if ann_vol and ann_vol > 0 else None
    rf_daily = (1 + float(cfg["risk_free_annual"])) ** (1 / annualization) - 1
    standard_sharpe = ((statistics.fmean(returns) - rf_daily) / daily_std
                       * math.sqrt(annualization)) if daily_std and daily_std > 0 else None
    return {
        "start": anchor, "end": daily[-1]["date"], "elapsed_calendar_days": elapsed,
        "observations": len(returns), "total_return": total,
        "annualized_return_cagr": cagr, "annualized_volatility": ann_vol,
        "product_compatible_sharpe_rf0": product_sharpe,
        "standard_daily_sharpe_rf_adjusted": standard_sharpe,
        "max_drawdown": min(row["drawdown"] for row in daily),
        "daily_win_rate": sum(1 for r in returns if r > 0) / len(returns),
    }


def evidence_gate(summaries: dict[str, dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    min_obs = int(cfg["evidence_gate_min_observations"])
    min_sharpe = float(cfg["evidence_gate_min_product_sharpe"])
    max_dd = float(cfg["evidence_gate_max_drawdown"])
    gate: dict[str, Any] = {}
    for name, summary in summaries.items():
        reasons: list[str] = []
        observations = int(summary.get("observations") or 0)
        total = summary.get("total_return")
        product = summary.get("product_compatible_sharpe_rf0")
        standard = summary.get("standard_daily_sharpe_rf_adjusted")
        drawdown = summary.get("max_drawdown")
        if observations < min_obs:
            reasons.append(f"observations_below_{min_obs}")
        if total is None or total <= 0:
            reasons.append("nonpositive_total_return")
        if product is None or product < min_sharpe:
            reasons.append(f"product_sharpe_below_{min_sharpe:g}")
        if standard is None or standard <= 0:
            reasons.append("nonpositive_standard_sharpe")
        if drawdown is None or drawdown < max_dd:
            reasons.append(f"drawdown_below_{max_dd:g}")
        gate[name] = {"evidence_eligible": not reasons, "rejection_reasons": reasons,
                      "observations": observations}
    # A StopVol variant may not qualify merely by shrinking exposure: it has to
    # beat its own base on Sharpe and on drawdown, not just differ from it.
    for name in list(gate):
        if not name.endswith("_StopVol"):
            continue
        base = name[: -len("_StopVol")]
        if base not in summaries:
            continue
        stop_sharpe = summaries[name].get("product_compatible_sharpe_rf0")
        base_sharpe = summaries[base].get("product_compatible_sharpe_rf0")
        stop_dd = summaries[name].get("max_drawdown")
        base_dd = summaries[base].get("max_drawdown")
        dominated = (stop_sharpe is None or base_sharpe is None
                     or stop_sharpe <= base_sharpe
                     or stop_dd is None or base_dd is None or stop_dd <= base_dd)
        if dominated:
            gate[name]["evidence_eligible"] = False
            gate[name]["rejection_reasons"].append("stopvol_does_not_improve_base")
    return gate


# --------------------------------------------------------------------------
# append-only ledger with a hash chain
# --------------------------------------------------------------------------

LEDGER_FIELDS = ["date", "strategy", "gross_return", "trading_cost_return", "funding_return",
                 "net_return", "normalized_nav", "drawdown", "turnover", "gross_long",
                 "gross_short_abs", "net_exposure", "open_positions", "kill_switch_active",
                 "engine_version", "prev_chain_sha256", "chain_sha256"]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or not path.read_text(encoding="utf-8-sig").strip():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def chain_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous = ZERO_HASH
    chained: list[dict[str, Any]] = []
    for row in rows:
        body = {k: row.get(k) for k in LEDGER_FIELDS if k not in ("prev_chain_sha256", "chain_sha256")}
        digest = sha256_bytes(previous.encode() + canonical(body))
        chained.append({**row, "prev_chain_sha256": previous, "chain_sha256": digest})
        previous = digest
    return chained


def assert_append_only(existing: list[dict[str, str]], recomputed: list[dict[str, Any]]) -> None:
    """A recomputed run may extend the ledger. It may never restate it."""
    if len(recomputed) < len(existing):
        raise EngineError(
            f"FAIL_CLOSED: recomputed ledger has {len(recomputed)} rows against "
            f"{len(existing)} already committed; refusing to shorten an append-only ledger")
    for position, (old, new) in enumerate(zip(existing, recomputed)):
        if old["chain_sha256"] != new["chain_sha256"]:
            raise EngineError(
                f"FAIL_CLOSED: committed row {position} ({old['date']} {old['strategy']}) "
                f"changed on recomputation; committed {old['chain_sha256'][:12]}, "
                f"recomputed {new['chain_sha256'][:12]}. A restatement is not new evidence")


def load_or_create_anchor(path: Path, latest_close: str, not_before: str,
                          run_id: str) -> tuple[str, bool]:
    if path.exists():
        stored = json.loads(path.read_text(encoding="utf-8-sig"))
        return str(stored["anchor_date"]), False
    if latest_close < not_before:
        raise EngineError(
            f"FAIL_CLOSED: latest completed close {latest_close} precedes the frozen "
            f"not_before {not_before}; the anchor may never be backdated")
    payload = {
        "schema": SCHEMA, "engine_version": ENGINE_VERSION,
        "anchor_date": latest_close, "initial_nav": 1.0,
        "established_at_utc": datetime.now(timezone.utc).isoformat(),
        "established_by_run_id": run_id,
        "rule": "First completed UTC close seen by the first production run after venue pinning.",
        "backdating_prohibited": True,
        "pre_anchor_status": "DIAGNOSTIC_ONLY_NEVER_PROSPECTIVE_EVIDENCE",
        **SAFETY,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return latest_close, True


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------

def run(prices_csv: Path, universe_csv: Path, contract_path: Path, out_dir: Path,
        run_id: str = "", funding_csv: Path | None = None) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8-sig"))
    if contract["version"] != ENGINE_VERSION:
        raise EngineError(f"contract version {contract['version']} is not {ENGINE_VERSION}")

    cfg = {
        "top_n": contract["selection"]["top_n"],
        "bottom_n": contract["selection"]["bottom_n"],
        "persistence_days": contract["selection"]["persistence_days"],
        "minimum_signal_history": contract["selection"]["minimum_signal_history"],
        "annualization_days": contract["annualization_days"],
        "risk_free_annual": contract["risk_free_annual"],
        "evidence_gate_min_observations": contract["evidence"]["min_observations"],
        "evidence_gate_min_product_sharpe": contract["evidence"]["min_product_sharpe"],
        "evidence_gate_max_drawdown": contract["evidence"]["max_drawdown"],
        **contract["risk"],
    }

    dates, bases, panel = read_prices(prices_csv)
    assert_no_gaps(dates)
    ranks = read_universe_bands(universe_csv)
    bands = contract["costs"]["slippage_by_band"]
    fee = float(contract["costs"]["fee_bps_per_side"])
    cost_rate = {b: (fee + slippage_bps(ranks.get(b), bands)) / 10000.0 for b in bases}

    anchor, first_run = load_or_create_anchor(
        out_dir / "ANCHOR.json", dates[-1], contract["anchor"]["not_before"], run_id)
    if anchor not in dates:
        raise EngineError(
            f"FAIL_CLOSED: anchor {anchor} is absent from the price panel "
            f"({dates[0]}..{dates[-1]}); the ledger cannot be continued from a close "
            "the pipeline can no longer produce")

    panels = build_panels(dates, bases, panel, cfg)
    funding, funded, funding_model = read_funding(funding_csv)

    ledger: list[dict[str, Any]] = []
    selections: list[dict[str, Any]] = []
    holdings: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, Any]] = {}
    for book in BOOKS:
        result = simulate(book, dates, bases, panels, panel, cost_rate, anchor, cfg,
                          funding, funded, funding_model)
        for row in result["daily"]:
            row["engine_version"] = ENGINE_VERSION
        ledger.extend(result["daily"])
        selections.extend(result["selections"])
        holdings.extend(result["holdings"])
        events.extend(result["events"])
        summaries[book["strategy"]] = metrics(result["daily"], anchor, cfg)

    ledger.sort(key=lambda r: (r["date"], r["strategy"]))
    chained = chain_rows(ledger)
    assert_append_only(read_csv_rows(out_dir / "DAILY_NAV.csv"), chained)

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv_rows(out_dir / "DAILY_NAV.csv", chained, LEDGER_FIELDS)
    write_csv_rows(out_dir / "SELECTIONS_HISTORY.csv", sorted(
        selections, key=lambda r: (r["execution_date"], r["strategy"], r["side"], r["symbol"])),
        ["execution_date", "signal_date", "strategy", "symbol", "side", "score", "vol30_daily",
         "target_weight", "selection_persistence_days", "lookahead_guard"])
    write_csv_rows(out_dir / "POSITIONS_HISTORY.csv", sorted(
        holdings, key=lambda r: (r["date"], r["strategy"], r["symbol"])),
        ["date", "strategy", "symbol", "side", "signed_weight", "entry_price", "best_price",
         "funding_rate_daily", "funding_model"])
    write_csv_rows(out_dir / "TRADE_EVENTS.csv", sorted(
        events, key=lambda r: (r["date"], r["strategy"], str(r["symbol"]), r["event"])),
        ["date", "strategy", "symbol", "event", "side", "price", "entry_price",
         "signed_weight", "stop_level", "take_level", "stop_pct", "take_pct", "trailing_pct"])

    gate = evidence_gate(summaries, cfg)
    observed_days = len({row["date"] for row in ledger})
    status = {
        "schema": SCHEMA, "engine_version": ENGINE_VERSION,
        "status": "ACTIVE_PROSPECTIVE_SHADOW" if observed_days else "ANCHOR_ESTABLISHED_AWAITING_FIRST_CLOSE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "anchor_date": anchor, "anchor_established_this_run": first_run,
        "data_as_of": dates[-1], "observed_days": observed_days,
        "universe_stratum": contract["universe"]["stratum"],
        "universe_size": len(bases),
        "selection": {"top_n": cfg["top_n"], "bottom_n": cfg["bottom_n"]},
        "books": {b["strategy"]: {**summaries[b["strategy"]], **gate[b["strategy"]]}
                  for b in BOOKS},
        "evidence_gate_min_observations": cfg["evidence_gate_min_observations"],
        "leaderboard_descriptive_only": True,
        "retrospective_winner_selection_forbidden": True,
        "funding_model": funding_model,
        "funding_covered_symbols": len(funded),
        "gap_policy": "FAIL_CLOSED_NO_BACKFILL",
        "latest_chain_sha256": chained[-1]["chain_sha256"] if chained else ZERO_HASH,
        "price_panel_sha256": sha256_bytes(prices_csv.read_bytes()),
        "run_id": run_id,
        **SAFETY,
    }
    (out_dir / "STATUS.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "EVIDENCE_GATE.json").write_text(
        json.dumps({"schema": SCHEMA, "as_of": dates[-1], "gate": gate,
                    "summaries": summaries}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prices-csv", type=Path, required=True)
    parser.add_argument("--universe-csv", type=Path, required=True)
    parser.add_argument("--contract", type=Path,
                        default=Path("migration/reporting/delta_v12_engine_contract.json"))
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--funding-csv", type=Path, default=None,
                        help="FUNDING_DAILY.csv; omitted means funding is booked as zero")
    args = parser.parse_args()
    status = run(args.prices_csv, args.universe_csv, args.contract, args.out_dir,
                 args.run_id, args.funding_csv)
    print(json.dumps({k: status[k] for k in (
        "status", "anchor_date", "data_as_of", "observed_days", "universe_size",
        "anchor_established_this_run", "funding_model", "latest_chain_sha256")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
