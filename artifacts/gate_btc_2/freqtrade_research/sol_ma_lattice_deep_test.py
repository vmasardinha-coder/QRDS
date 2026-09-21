# RESEARCH_ONLY=true
# SHADOW_ONLY=true
# Isolated deep test for SOL multi-horizon MA lattice.
# No Factory integration, no live orders, no capital.

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen, Request

import numpy as np
import pandas as pd

OUT = Path(__file__).with_name("runtime_sol_ma_lattice")
OUT.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://www.okx.com/api/v5/market/history-candles"
INST = "SOL-USDT"
BAR = "1H"
ROUND_TRIP_COSTS = [0.001, 0.002, 0.004, 0.006]
LATTICES = {
    "6_12_24_48": [6, 12, 24, 48],
    "8_16_32_64": [8, 16, 32, 64],
    "12_24_48_96": [12, 24, 48, 96],
}
HOLD_HOURS = [12, 24, 48]


def fetch_history(max_pages: int = 80) -> pd.DataFrame:
    rows = []
    after = None
    for _ in range(max_pages):
        params = {"instId": INST, "bar": BAR, "limit": "100"}
        if after is not None:
            params["after"] = str(after)
        req = Request(BASE_URL + "?" + urlencode(params), headers={"User-Agent": "qrds-research/1.0"})
        with urlopen(req, timeout=20) as r:
            payload = json.loads(r.read().decode("utf-8"))
        data = payload.get("data", [])
        if not data:
            break
        rows.extend(data)
        oldest = min(int(x[0]) for x in data)
        if after == oldest:
            break
        after = oldest
        time.sleep(0.05)
    if not rows:
        raise RuntimeError("no OHLCV fetched")
    cols = ["ts", "open", "high", "low", "close", "volume", "volCcy", "volCcyQuote", "confirm"]
    df = pd.DataFrame(rows, columns=cols)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ts"] = pd.to_datetime(pd.to_numeric(df["ts"]), unit="ms", utc=True)
    return df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)


def ordered_state(df: pd.DataFrame, periods: list[int]) -> pd.Series:
    emas = [df["close"].ewm(span=p, adjust=False, min_periods=p).mean() for p in periods]
    ordered = pd.Series(True, index=df.index)
    for a, b in zip(emas[:-1], emas[1:]):
        ordered &= a > b
    return ordered


def trade_returns(df: pd.DataFrame, state: pd.Series, hold: int, cost: float, mode: str) -> list[float]:
    rets = []
    i = 0
    n = len(df)
    while i + hold < n:
        trigger = bool(state.iloc[i])
        if mode == "fresh_state":
            trigger = trigger and (i == 0 or not bool(state.iloc[i - 1]))
        elif mode == "reenter_when_flat":
            trigger = trigger
        else:
            raise ValueError(mode)
        if trigger:
            entry = float(df["close"].iloc[i])
            exit_ = float(df["close"].iloc[i + hold])
            rets.append(exit_ / entry - 1.0 - cost)
            i += hold
        else:
            i += 1
    return rets


def equity_stats(rets: list[float]) -> dict:
    if not rets:
        return {"n": 0, "mean": None, "median": None, "win_rate": None, "total_return": None, "max_dd": None, "profit_factor": None}
    arr = np.asarray(rets, dtype=float)
    eq = np.cumprod(1.0 + arr)
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1.0
    gross_profit = arr[arr > 0].sum()
    gross_loss = -arr[arr < 0].sum()
    pf = None if gross_loss == 0 else float(gross_profit / gross_loss)
    return {
        "n": int(len(arr)), "mean": float(arr.mean()), "median": float(np.median(arr)),
        "win_rate": float((arr > 0).mean()), "total_return": float(eq[-1] - 1.0),
        "max_dd": float(dd.min()), "profit_factor": pf,
    }


def walk_forward_slices(n: int) -> list[tuple[int, int]]:
    out = []
    for a in [0.45, 0.55, 0.65, 0.75, 0.85]:
        s, e = int(n * a), min(n, int(n * (a + 0.10)))
        if e - s >= 200:
            out.append((s, e))
    return out


def main() -> None:
    df = fetch_history()
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(), "research_only": True,
        "shadow_only": True, "factory_touched": False, "instrument": INST, "bar": BAR,
        "rows": len(df), "start": df["ts"].min().isoformat(), "end": df["ts"].max().isoformat(),
        "entry_modes": ["fresh_state", "reenter_when_flat"], "lattices": {},
    }
    slices = walk_forward_slices(len(df))
    for name, periods in LATTICES.items():
        state = ordered_state(df, periods)
        lattice = {"periods": periods, "modes": {}}
        for mode in report["entry_modes"]:
            mode_obj = {"holds": {}}
            for hold in HOLD_HOURS:
                hold_obj = {"costs": {}, "walk_forward": []}
                for cost in ROUND_TRIP_COSTS:
                    hold_obj["costs"][str(cost)] = equity_stats(trade_returns(df, state, hold, cost, mode))
                for s, e in slices:
                    sub = df.iloc[s:e].reset_index(drop=True)
                    sub_state = state.iloc[s:e].reset_index(drop=True)
                    stats = equity_stats(trade_returns(sub, sub_state, hold, 0.002, mode))
                    hold_obj["walk_forward"].append({"start": sub["ts"].iloc[0].isoformat(), "end": sub["ts"].iloc[-1].isoformat(), **stats})
                mode_obj["holds"][str(hold)] = hold_obj
            lattice["modes"][mode] = mode_obj
        report["lattices"][name] = lattice

    (OUT / "sol_ma_lattice_deep_test.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# SOL MA lattice deep research", "", f"Rows: {len(df)} | {report['start']} -> {report['end']}", "", "RESEARCH_ONLY=true; SHADOW_ONLY=true; Factory untouched.", ""]
    for name, lattice in report["lattices"].items():
        lines += [f"## {name}", ""]
        for mode, mode_obj in lattice["modes"].items():
            lines.append(f"### {mode}")
            for hold, obj in mode_obj["holds"].items():
                base = obj["costs"]["0.002"]
                wf = obj["walk_forward"]
                wf_pos = sum(1 for x in wf if x["mean"] is not None and x["mean"] > 0)
                lines.append(f"- hold {hold}h @0.20%: n={base['n']}, mean={base['mean']}, total={base['total_return']}, maxDD={base['max_dd']}, PF={base['profit_factor']}, WF positive={wf_pos}/{len(wf)}")
            lines.append("")
    (OUT / "sol_ma_lattice_deep_test.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
