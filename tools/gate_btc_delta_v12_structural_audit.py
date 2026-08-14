#!/usr/bin/env python3
"""Offline structural audit for Delta V12 hypotheses.

Research/shadow only. This module reads immutable Daily Research evidence, compares
pre-registered weekly structural hypotheses, emits diagnostics, and has no engine,
order, account, credential, or capital path.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
}
WEEKDAYS = {"MONDAY": 0, "TUESDAY": 1, "WEDNESDAY": 2, "THURSDAY": 3, "FRIDAY": 4}


def cross_section_z(frame: pd.DataFrame) -> pd.DataFrame:
    mean = frame.mean(axis=1)
    std = frame.std(axis=1).replace(0, np.nan)
    return frame.sub(mean, axis=0).div(std, axis=0)


def load_contract(path: Path) -> dict[str, Any]:
    c = json.loads(path.read_text(encoding="utf-8"))
    assert c["research_only"] is True and c["shadow_only"] is True
    assert c["not_approved"] is True and c["engine_feed"] is False
    assert c["orders"] == 0 and c["real_capital"] == 0
    assert c["promotion_eligible"] is False
    return c


def read_outer_artifact(path: Path) -> tuple[dict[str, Any], bytes]:
    with zipfile.ZipFile(path) as zf:
        handoff = json.loads(zf.read("daily_handoff/GATE_BTC_DAILY_RESEARCH_MANIFEST.json").decode("utf-8-sig"))
        assert handoff["status"] in {"PASS", "PASS_WITH_DATA_WARNINGS"}
        assert handoff["research_only"] is True
        assert handoff["operational_status"] == "NOT_APPROVED"
        assert handoff["orders_generated"] == 0 and handoff["real_capital_used"] == 0
        nested = zf.read("qos_daily/delta_public_input_snapshot.zip")
    return handoff, nested


def read_inputs(nested: bytes) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(nested)) as zf:
        manifest = json.loads(zf.read("delta_input_snapshot_manifest.json").decode("utf-8-sig"))
        ohlc = pd.read_csv(zf.open("inputs/delta_ohlc_daily.csv"))
        funding = pd.read_csv(zf.open("inputs/delta_funding_events.csv"))
    for col in ("date",):
        ohlc[col] = pd.to_datetime(ohlc[col]).dt.normalize()
        if col in funding.columns:
            funding[col] = pd.to_datetime(funding[col]).dt.normalize()
    return ohlc, funding, manifest


def build_panels(ohlc: pd.DataFrame) -> dict[str, pd.DataFrame]:
    panels = {field: ohlc.pivot(index="date", columns="symbol", values=field).sort_index()
              for field in ("open", "high", "low", "close", "volume")}
    close = panels["close"]
    returns = close.pct_change(fill_method=None)
    ret7 = close.div(close.shift(7)).sub(1)
    ret14 = close.div(close.shift(14)).sub(1)
    ret30 = close.div(close.shift(30)).sub(1)
    vol30 = returns.rolling(30, min_periods=30).std()
    liquidity = np.log1p(panels["volume"].rolling(14, min_periods=7).median())
    score = (0.20 * cross_section_z(ret7) + 0.35 * cross_section_z(ret14)
             + 0.35 * cross_section_z(ret30) - 0.10 * cross_section_z(vol30)
             + 0.05 * cross_section_z(liquidity))
    panels.update({"returns": returns, "vol30": vol30, "score": score})
    return panels


def raw_side(score: pd.DataFrame, n_long: int, n_short: int) -> dict[pd.Timestamp, dict[str, int]]:
    out: dict[pd.Timestamp, dict[str, int]] = {}
    for date, row in score.iterrows():
        valid = row.dropna().sort_values(ascending=False)
        if len(valid) < n_long + n_short:
            out[date] = {}
            continue
        longs = list(valid.head(n_long).index)
        shorts = [x for x in valid.tail(n_short).index if x not in longs]
        out[date] = {**{x: 1 for x in longs}, **{x: -1 for x in shorts}}
    return out


def target_for_signal(panels: dict[str, pd.DataFrame], raw: dict[pd.Timestamp, dict[str, int]],
                      signal_date: pd.Timestamp, previous_signal: pd.Timestamp | None,
                      n_long: int, n_short: int, weighting: str) -> dict[str, float]:
    current = raw.get(signal_date, {})
    if previous_signal is not None:
        previous = raw.get(previous_signal, {})
        current = {s: side for s, side in current.items() if previous.get(s) == side}
    targets: dict[str, float] = {}
    for side, count in ((1, n_long), (-1, n_short)):
        names = [s for s, v in current.items() if v == side]
        if not names:
            continue
        if weighting == "INVERSE_VOL_SIDE":
            vols = panels["vol30"].loc[signal_date, names].replace([np.inf, -np.inf], np.nan).dropna()
            vols = vols[vols > 0]
            if vols.empty:
                continue
            inv = 1.0 / vols
            weights = 0.5 * inv / inv.sum()
            for s, w in weights.items():
                targets[s] = side * float(w)
        else:
            w = 0.5 / float(count)
            for s in names:
                targets[s] = side * w
    return targets


def weekly_schedule(panels: dict[str, pd.DataFrame], weekday: int, n_long: int, n_short: int,
                    weighting: str) -> dict[pd.Timestamp, dict[str, float]]:
    dates = list(panels["score"].index)
    raw = raw_side(panels["score"], n_long, n_short)
    schedule: dict[pd.Timestamp, dict[str, float]] = {}
    for i, execution_date in enumerate(dates):
        if execution_date.weekday() != weekday or i == 0:
            continue
        signal_date = dates[i - 1]
        previous_signal = dates[i - 2] if i >= 2 else None
        schedule[execution_date] = target_for_signal(
            panels, raw, signal_date, previous_signal, n_long, n_short, weighting
        )
    return schedule


def daily_funding(funding: pd.DataFrame) -> dict[tuple[pd.Timestamp, str], float]:
    if funding.empty or "funding_rate" not in funding:
        return {}
    grouped = funding.groupby(["date", "symbol"], as_index=False)["funding_rate"].sum()
    return {(pd.Timestamp(r.date), str(r.symbol)): float(r.funding_rate) for r in grouped.itertuples()}


def simulate(panels: dict[str, pd.DataFrame], funding: pd.DataFrame,
             weekday: int, n_long: int, n_short: int, weighting: str,
             start: str = "2026-05-15") -> tuple[pd.DataFrame, pd.DataFrame]:
    schedule = weekly_schedule(panels, weekday, n_long, n_short, weighting)
    dates = [d for d in panels["close"].index if d >= pd.Timestamp(start)]
    funding_map = daily_funding(funding)
    cost_rate = 0.0008
    weights: dict[str, float] = {}
    equity = 1.0
    rows: list[dict[str, Any]] = []
    last_targets: list[dict[str, Any]] = []
    for idx, date in enumerate(dates):
        prev_candidates = panels["close"].index[panels["close"].index < date]
        prev = prev_candidates[-1] if len(prev_candidates) else None
        gross_ret = 0.0
        funding_ret = 0.0
        trading_cost = 0.0
        turnover = 0.0
        if prev is not None:
            for sym, w in list(weights.items()):
                if sym not in panels["close"].columns:
                    continue
                p0 = panels["close"].at[prev, sym]
                op = panels["open"].at[date, sym]
                if pd.notna(p0) and pd.notna(op) and p0 > 0:
                    gross_ret += w * (float(op) / float(p0) - 1.0)
        if date in schedule:
            desired = schedule[date]
            names = set(weights) | set(desired)
            turnover = float(sum(abs(desired.get(s, 0.0) - weights.get(s, 0.0)) for s in names))
            trading_cost = turnover * cost_rate
            weights = dict(desired)
            last_targets = [{"date": date.date().isoformat(), "symbol": s, "weight": w,
                             "side": "LONG" if w > 0 else "SHORT"} for s, w in sorted(weights.items())]
        for sym, w in weights.items():
            op = panels["open"].at[date, sym] if sym in panels["open"].columns else np.nan
            cl = panels["close"].at[date, sym] if sym in panels["close"].columns else np.nan
            if pd.notna(op) and pd.notna(cl) and op > 0:
                gross_ret += w * (float(cl) / float(op) - 1.0)
            rate = funding_map.get((date, sym), 0.0)
            funding_ret += -w * rate
        net = gross_ret + funding_ret - trading_cost
        equity *= (1.0 + net)
        rows.append({
            "date": date.date().isoformat(), "net_return": net, "gross_return": gross_ret,
            "funding_return": funding_ret, "trading_cost": trading_cost, "turnover": turnover,
            "gross_exposure": sum(abs(v) for v in weights.values()),
            "net_exposure": sum(weights.values()), "position_count": len(weights), "equity": equity,
        })
    return pd.DataFrame(rows), pd.DataFrame(last_targets)


def metrics(frame: pd.DataFrame, btc: pd.Series) -> dict[str, float | int | None]:
    if frame.empty:
        return {}
    ret = frame["net_return"].astype(float)
    eq = frame["equity"].astype(float)
    peak = eq.cummax()
    dd = eq.div(peak).sub(1.0)
    vol = float(ret.std(ddof=1) * math.sqrt(365)) if len(ret) > 1 else 0.0
    sharpe = float(ret.mean() / ret.std(ddof=1) * math.sqrt(365)) if len(ret) > 1 and ret.std(ddof=1) > 0 else None
    aligned = pd.DataFrame({"r": ret.values}, index=pd.to_datetime(frame["date"]))
    aligned["btc"] = btc.reindex(aligned.index)
    aligned = aligned.dropna()
    beta = None
    if len(aligned) > 5 and float(aligned["btc"].var()) > 0:
        beta = float(aligned[["r", "btc"]].cov().iloc[0, 1] / aligned["btc"].var())
    return {
        "observations": int(len(frame)),
        "total_return": float(eq.iloc[-1] - 1.0),
        "annualized_volatility": vol,
        "sharpe_rf0": sharpe,
        "max_drawdown": float(dd.min()),
        "win_rate": float((ret > 0).mean()),
        "btc_beta": beta,
        "turnover_sum": float(frame["turnover"].sum()),
        "trading_cost_sum": float(frame["trading_cost"].sum()),
        "funding_return_sum": float(frame["funding_return"].sum()),
        "average_gross_exposure": float(frame["gross_exposure"].mean()),
        "average_abs_net_exposure": float(frame["net_exposure"].abs().mean()),
        "latest_position_count": int(frame["position_count"].iloc[-1]),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-artifact", type=Path, required=True)
    ap.add_argument("--contract", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    contract = load_contract(args.contract)
    handoff, nested = read_outer_artifact(args.source_artifact)
    ohlc, funding, input_manifest = read_inputs(nested)
    panels = build_panels(ohlc)
    btc = panels["close"]["BTC"].pct_change(fill_method=None)
    variants = {
        "V12A": (4, 5, 5, "EQUAL_SIDE"),
        "V12B": (4, 7, 7, "EQUAL_SIDE"),
        "V12C": (4, 7, 7, "INVERSE_VOL_SIDE"),
        "V12D": (4, 10, 10, "EQUAL_SIDE"),
    }
    out_rows = []
    latest_frames = []
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for vid, spec in variants.items():
        frame, latest = simulate(panels, funding, *spec)
        m = metrics(frame, btc)
        out_rows.append({"variant": vid, **m})
        latest.insert(0, "variant", vid)
        latest_frames.append(latest)
        frame.to_csv(args.out_dir / f"{vid}_daily.csv", index=False)
    placebo_rows = []
    for name, wd in WEEKDAYS.items():
        frame, _ = simulate(panels, funding, wd, 7, 7, "EQUAL_SIDE")
        placebo_rows.append({"weekday": name, **metrics(frame, btc)})
    metrics_df = pd.DataFrame(out_rows)
    placebo_df = pd.DataFrame(placebo_rows)
    metrics_df.to_csv(args.out_dir / "V12_METRICS.csv", index=False)
    placebo_df.to_csv(args.out_dir / "WEEKDAY_PLACEBO.csv", index=False)
    pd.concat(latest_frames, ignore_index=True).to_csv(args.out_dir / "LATEST_TARGETS.csv", index=False)
    status = {
        "status": "PASS_RESEARCH_AUDIT",
        "data_cutoff": str(handoff.get("data_cutoff")),
        "contract_version": contract["version"],
        "input_manifest_status": input_manifest.get("status"),
        "variants": out_rows,
        "weekday_placebo": placebo_rows,
        "interpretation_guard": "No variant is promotion eligible; external evidence may audit but never tune this family.",
        **SAFETY,
    }
    (args.out_dir / "STATUS.json").write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
