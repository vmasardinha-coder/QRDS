#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

COST_REF = 2.0
COST_STRESS = 3.0
MIN_TRADES = 60
MIN_SIDE = 15
MIN_BUCKET = 15
MAX_TOP5 = 0.40


def load_data(csv_path: Path) -> dict[str, pd.DataFrame]:
    df = pd.read_csv(csv_path)
    needed = {"timestamp", "open", "high", "low", "close", "volume"}
    if not needed.issubset(df.columns):
        raise RuntimeError(f"SCHEMA_MISSING:{sorted(needed-set(df.columns))}")
    ts = pd.to_datetime(df["timestamp"], errors="raise")
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize("America/Sao_Paulo")
    else:
        ts = ts.dt.tz_convert("America/Sao_Paulo")
    df["timestamp"] = ts
    if (df["timestamp"] >= pd.Timestamp("2026-08-10", tz="America/Sao_Paulo")).any():
        raise RuntimeError("H1_CUTOFF_BREACH")
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="raise")
    df["session"] = df["timestamp"].dt.date.astype(str)
    out = {}
    for s, g0 in df.groupby("session", sort=True):
        g = g0.sort_values("timestamp").reset_index(drop=True)
        if len(g) < 40:
            continue
        if (g["timestamp"].diff().dropna().dt.total_seconds() != 300).any():
            continue
        out[s] = g
    return out


def raw_feature(name: str, g: pd.DataFrame, window: int, prior_close: float | None) -> float:
    n = max(1, window // 5)
    x = g.iloc[:n]
    op = float(g.iloc[0]["open"])
    cl = float(x.iloc[-1]["close"])
    hi = float(x["high"].max())
    lo = float(x["low"].min())
    if name == "OPEN_RETURN":
        return cl / op - 1.0
    if name == "OPEN_RANGE":
        return (hi - lo) / op
    if name == "REALIZED_VOL":
        r = x["close"].astype(float).pct_change().dropna()
        return float(r.std(ddof=0)) if len(r) else 0.0
    if name == "VOLUME_EARLY":
        return float(x["volume"].sum())
    if name == "BAR_IMBALANCE":
        d = np.sign(x["close"].to_numpy(float) - x["open"].to_numpy(float))
        return float(d.mean())
    if name == "CLOSE_LOCATION":
        return 0.0 if hi <= lo else (cl - lo) / (hi - lo) - 0.5
    if name == "BODY_RANGE":
        return 0.0 if hi <= lo else (cl - op) / (hi - lo)
    if name == "GAP_FROM_PRIOR_CLOSE":
        return float("nan") if not prior_close or prior_close <= 0 else op / prior_close - 1.0
    raise RuntimeError(f"UNKNOWN_FEATURE:{name}")


def causal_z(values: list[float], x: float) -> float | None:
    hist = np.asarray([v for v in values[-20:] if math.isfinite(v)], dtype=float)
    if len(hist) < 20 or not math.isfinite(x):
        return None
    med = float(np.median(hist))
    mad = float(np.median(np.abs(hist - med)))
    if mad <= 0:
        return None
    return (x - med) / (1.4826 * mad)


def half_bucket(s: str) -> str:
    d = pd.Timestamp(s)
    return f"{d.year}H{1 if d.month <= 6 else 2}"


def build_trades(sessions: dict[str, pd.DataFrame], fam: dict) -> pd.DataFrame:
    rows = []
    history: list[float] = []
    prior_close = None
    window = int(fam["decision_window_minutes"])
    signal_idx = window // 5 - 1
    direction = 1 if fam["direction"] == "CONTINUATION" else -1
    threshold = float(fam["abs_z_threshold"])
    for s in sorted(sessions):
        g = sessions[s]
        x = raw_feature(fam["feature"], g, window, prior_close)
        z = causal_z(history, x)
        if math.isfinite(x):
            history.append(x)
        prior_close = float(g.iloc[-1]["close"])
        if z is None or abs(z) < threshold:
            continue
        side = (1 if z > 0 else -1) * direction
        entry_idx = signal_idx + 1
        for horizon in fam["holding_horizons_minutes"]:
            bars = int(horizon) // 5
            exit_idx = entry_idx + bars
            delayed_entry = entry_idx + 1
            delayed_exit = delayed_entry + bars
            if exit_idx >= len(g):
                continue
            entry = float(g.iloc[entry_idx]["open"])
            exit_ = float(g.iloc[exit_idx]["open"])
            gross = side * (exit_ / entry - 1.0) * 10000.0
            delayed = None
            if delayed_exit < len(g):
                de = float(g.iloc[delayed_entry]["open"])
                dx = float(g.iloc[delayed_exit]["open"])
                delayed = side * (dx / de - 1.0) * 10000.0
            rows.append({"session": s, "side": side, "horizon": int(horizon), "gross_bps": gross, "delayed_gross_bps": delayed})
    return pd.DataFrame(rows)


def metric(g: pd.DataFrame) -> tuple[bool, dict]:
    if g.empty:
        return False, {"trades": 0, "reasons": ["NO_TRADES"]}
    gross = g["gross_bps"].astype(float)
    delayed = g["delayed_gross_bps"].dropna().astype(float)
    reasons = []
    net2 = float((gross - COST_REF).mean())
    net3 = float((gross - COST_STRESS).mean())
    dnet = float((delayed - COST_REF).mean()) if len(delayed) else None
    if len(g) < MIN_TRADES: reasons.append("MIN_TRADES")
    if net2 <= 0.25: reasons.append("REFERENCE_COST_EDGE")
    if net3 <= 0: reasons.append("STRESS_COST")
    if len(delayed) < MIN_TRADES or dnet is None or dnet <= 0: reasons.append("DELAYED_ENTRY")
    sides = {}
    for side, sg in g.groupby("side"):
        sides[int(side)] = {"trades": int(len(sg)), "net2": float((sg["gross_bps"] - COST_REF).mean())}
    if set(sides) != {-1, 1} or any(v["trades"] < MIN_SIDE or v["net2"] <= 0 for v in sides.values()):
        reasons.append("SIDE_STABILITY")
    tmp = g.copy(); tmp["half"] = tmp["session"].map(half_bucket)
    buckets = {b: {"trades": int(len(bg)), "net2": float((bg["gross_bps"] - COST_REF).mean())} for b, bg in tmp.groupby("half")}
    eligible = [v for v in buckets.values() if v["trades"] >= MIN_BUCKET]
    if len(eligible) < 2 or any(v["net2"] <= 0 for v in eligible): reasons.append("CALENDAR_HALF_STABILITY")
    pos = gross[gross > 0].sort_values(ascending=False)
    ps = float(pos.sum()); top5 = float(pos.head(5).sum()/ps) if ps > 0 else 1.0
    if top5 > MAX_TOP5: reasons.append("CONCENTRATION")
    return not reasons, {"trades": int(len(g)), "net2": net2, "net3": net3, "delayed_net2": dnet, "side_metrics": sides, "half_metrics": buckets, "top5_positive_share": top5, "reasons": reasons}


def eval_family(sessions: dict[str, pd.DataFrame], fam: dict) -> dict:
    trades = build_trades(sessions, fam)
    cells = []
    q = 0
    for h in fam["holding_horizons_minutes"]:
        g = trades[trades["horizon"] == int(h)] if not trades.empty else trades
        ok, m = metric(g)
        cells.append({"horizon": int(h), "qualified": ok, "metrics": m})
        q += int(ok)
    return {"qualified_cells": q, "survives": q >= 2, "cells": cells}


def subset(sessions: dict[str, pd.DataFrame], y0: int, y1: int) -> dict[str, pd.DataFrame]:
    return {s: g for s, g in sessions.items() if y0 <= int(s[:4]) <= y1}


def run(contract: dict, sessions: dict[str, pd.DataFrame]) -> dict:
    if not contract.get("frozen_before_economics") or contract.get("h1_economics_read") is not False:
        raise RuntimeError("CONTRACT_NOT_FROZEN_OR_CONTAMINATED")
    disc_sessions = subset(sessions, 2022, 2024)
    rep_sessions = subset(sessions, 2020, 2021)
    rows = []
    replicated = []
    for fam in contract["families"]:
        disc = eval_family(disc_sessions, fam)
        rep = eval_family(rep_sessions, fam) if disc["survives"] else {"qualified_cells": 0, "survives": False, "cells": [], "not_run_reason": "DISCOVERY_REJECTED"}
        ok = bool(disc["survives"] and rep["survives"])
        rows.append({"family_id": fam["family_id"], "contract": fam, "discovery": disc, "replication": rep, "replicated": ok})
        if ok: replicated.append(fam["family_id"])
    survivors = sorted(replicated, key=lambda x: int(x[1:]))[:2]
    gen = contract["generation"]
    return {
        "schema": "gate_btc.b3.autonomous_generation_result.v1",
        "generation": gen,
        "status": f"SURVIVORS_READY_{gen.replace('-', '_')}" if survivors else f"CLOSED_NO_{gen.replace('-', '_')}_SURVIVOR",
        "survivors": survivors,
        "families": rows,
        "research_only": True, "shadow_only": True, "not_approved": True,
        "orders": 0, "real_capital": 0, "engine_feed": False, "h1_economics_read": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    sessions = load_data(Path(args.csv))
    result = run(contract, sessions)
    p = Path(args.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"generation": result["generation"], "status": result["status"], "survivors": result["survivors"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
