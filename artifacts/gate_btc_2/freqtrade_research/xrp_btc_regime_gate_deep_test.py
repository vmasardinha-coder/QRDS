# RESEARCH_ONLY=true
# SHADOW_ONLY=true
# Isolated confirmatory test for XRP base signal conditioned by BTC regime.
# No Factory integration, no live orders, no capital.

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

OUT = Path(__file__).with_name("runtime_xrp_btc_gate")
OUT.mkdir(parents=True, exist_ok=True)
BASE_URL = "https://www.okx.com/api/v5/market/history-candles"
BAR = "1H"
MAX_PAGES = 80
COSTS = [0.001, 0.002, 0.004]
HOLD_HOURS = [12, 24, 48]


def fetch(inst: str) -> pd.DataFrame:
    rows, after = [], None
    for _ in range(MAX_PAGES):
        params = {"instId": inst, "bar": BAR, "limit": "100"}
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
    cols = ["ts", "open", "high", "low", "close", "volume", "volCcy", "volCcyQuote", "confirm"]
    df = pd.DataFrame(rows, columns=cols)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ts"] = pd.to_datetime(pd.to_numeric(df["ts"]), unit="ms", utc=True)
    return df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)


def resample_close(df: pd.DataFrame, hours: int) -> pd.Series:
    s = df.set_index("ts")["close"].resample(f"{hours}h", label="right", closed="right").last().dropna()
    return s


def align_regime(xrp: pd.DataFrame, btc: pd.DataFrame, hours: int, sma: int) -> pd.Series:
    btc_tf = resample_close(btc, hours)
    ma = btc_tf.rolling(sma, min_periods=sma).mean()
    state = (btc_tf > ma).rename("gate")
    aligned = pd.merge_asof(
        xrp[["ts"]].sort_values("ts"),
        state.reset_index().sort_values("ts"),
        on="ts", direction="backward", allow_exact_matches=True,
    )["gate"]
    return aligned.fillna(False).astype(bool)


def base_signal(df: pd.DataFrame) -> pd.Series:
    e20 = df["close"].ewm(span=20, adjust=False, min_periods=20).mean()
    e50 = df["close"].ewm(span=50, adjust=False, min_periods=50).mean()
    return (e20 > e50) & ~(e20 > e50).shift(1, fill_value=False)


def trade_returns(df: pd.DataFrame, signal: pd.Series, hold: int, cost: float) -> list[float]:
    out, i, n = [], 0, len(df)
    while i + hold < n:
        if bool(signal.iloc[i]):
            out.append(float(df["close"].iloc[i + hold] / df["close"].iloc[i] - 1.0 - cost))
            i += hold
        else:
            i += 1
    return out


def stats(rets: list[float]) -> dict:
    if not rets:
        return {"n": 0, "mean": None, "median": None, "win_rate": None, "total_return": None, "max_dd": None, "profit_factor": None}
    a = np.asarray(rets)
    eq = np.cumprod(1 + a)
    dd = eq / np.maximum.accumulate(eq) - 1
    gp, gl = a[a > 0].sum(), -a[a < 0].sum()
    return {
        "n": int(len(a)), "mean": float(a.mean()), "median": float(np.median(a)),
        "win_rate": float((a > 0).mean()), "total_return": float(eq[-1] - 1),
        "max_dd": float(dd.min()), "profit_factor": None if gl == 0 else float(gp / gl),
    }


def slices(n: int) -> list[tuple[int, int]]:
    out = []
    for a in [0.45, 0.55, 0.65, 0.75, 0.85]:
        s, e = int(n * a), min(n, int(n * (a + 0.10)))
        if e - s >= 200:
            out.append((s, e))
    return out


def main() -> None:
    xrp, btc = fetch("XRP-USDT"), fetch("BTC-USDT")
    start = max(xrp.ts.min(), btc.ts.min())
    end = min(xrp.ts.max(), btc.ts.max())
    xrp = xrp[(xrp.ts >= start) & (xrp.ts <= end)].reset_index(drop=True)
    btc = btc[(btc.ts >= start) & (btc.ts <= end)].reset_index(drop=True)
    base = base_signal(xrp)
    gates = {
        "btc_4h_sma20": align_regime(xrp, btc, 4, 20),
        "btc_4h_sma50": align_regime(xrp, btc, 4, 50),
        "btc_12h_sma20": align_regime(xrp, btc, 12, 20),
        "btc_12h_sma50": align_regime(xrp, btc, 12, 50),
    }
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(), "research_only": True,
        "shadow_only": True, "factory_touched": False, "rows": len(xrp),
        "start": start.isoformat(), "end": end.isoformat(), "holds": {},
    }
    wf_slices = slices(len(xrp))
    for hold in HOLD_HOURS:
        hobj = {"base": {}, "gates": {}}
        for cost in COSTS:
            hobj["base"][str(cost)] = stats(trade_returns(xrp, base, hold, cost))
        for gname, gate in gates.items():
            sig = base & gate
            gobj = {"costs": {}, "walk_forward": []}
            for cost in COSTS:
                gobj["costs"][str(cost)] = stats(trade_returns(xrp, sig, hold, cost))
            for s, e in wf_slices:
                sub = xrp.iloc[s:e].reset_index(drop=True)
                bs = base.iloc[s:e].reset_index(drop=True)
                gs = gate.iloc[s:e].reset_index(drop=True)
                bstat = stats(trade_returns(sub, bs, hold, 0.002))
                gstat = stats(trade_returns(sub, bs & gs, hold, 0.002))
                delta = None if bstat["mean"] is None or gstat["mean"] is None else gstat["mean"] - bstat["mean"]
                gobj["walk_forward"].append({"start": sub.ts.iloc[0].isoformat(), "end": sub.ts.iloc[-1].isoformat(), "base": bstat, "gated": gstat, "delta_mean": delta})
            hobj["gates"][gname] = gobj
        report["holds"][str(hold)] = hobj
    (OUT / "xrp_btc_regime_gate_deep_test.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# XRP BTC regime-gate deep research", "", f"Rows: {len(xrp)} | {start} -> {end}", "", "RESEARCH_ONLY=true; SHADOW_ONLY=true; Factory untouched.", ""]
    for hold, hobj in report["holds"].items():
        b = hobj["base"]["0.002"]
        lines += [f"## hold {hold}h", f"- base @0.20%: n={b['n']}, mean={b['mean']}, total={b['total_return']}, maxDD={b['max_dd']}, PF={b['profit_factor']}"]
        for name, g in hobj["gates"].items():
            s = g["costs"]["0.002"]
            deltas = [x["delta_mean"] for x in g["walk_forward"] if x["delta_mean"] is not None]
            pos = sum(d > 0 for d in deltas)
            lines.append(f"- {name}: n={s['n']}, mean={s['mean']}, delta={None if s['mean'] is None or b['mean'] is None else s['mean']-b['mean']}, total={s['total_return']}, maxDD={s['max_dd']}, PF={s['profit_factor']}, WF delta positive={pos}/{len(deltas)}")
        lines.append("")
    (OUT / "xrp_btc_regime_gate_deep_test.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
