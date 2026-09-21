# RESEARCH_ONLY=true
# SHADOW_ONLY=true
# Frozen generalization test: same alt EMA20/50 signal, same 48h hold,
# same BTC 12h/SMA20 gate, same costs across all assets. No per-asset retune.

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

OUT = Path(__file__).with_name("runtime_multi_alt_btc_gate")
OUT.mkdir(parents=True, exist_ok=True)
BASE_URL = "https://www.okx.com/api/v5/market/history-candles"
BAR = "1H"
MAX_PAGES = 80
ALTS = ["ETH-USDT", "SOL-USDT", "DOGE-USDT", "ADA-USDT", "LINK-USDT", "AVAX-USDT", "DOT-USDT", "LTC-USDT"]
HOLD = 48
COST = 0.002
BTC_GATE_HOURS = 12
BTC_GATE_SMA = 20


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
    if not rows:
        raise RuntimeError(f"no OHLCV fetched for {inst}")
    cols = ["ts", "open", "high", "low", "close", "volume", "volCcy", "volCcyQuote", "confirm"]
    df = pd.DataFrame(rows, columns=cols)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ts"] = pd.to_datetime(pd.to_numeric(df["ts"]), unit="ms", utc=True)
    return df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)


def base_signal(df: pd.DataFrame) -> pd.Series:
    e20 = df["close"].ewm(span=20, adjust=False, min_periods=20).mean()
    e50 = df["close"].ewm(span=50, adjust=False, min_periods=50).mean()
    state = e20 > e50
    return state & ~state.shift(1, fill_value=False)


def btc_gate_for(alt: pd.DataFrame, btc: pd.DataFrame) -> pd.Series:
    b = btc.set_index("ts")["close"].resample(f"{BTC_GATE_HOURS}h", label="right", closed="right").last().dropna()
    ma = b.rolling(BTC_GATE_SMA, min_periods=BTC_GATE_SMA).mean()
    state = (b > ma).rename("gate")
    return pd.merge_asof(
        alt[["ts"]].sort_values("ts"), state.reset_index().sort_values("ts"),
        on="ts", direction="backward", allow_exact_matches=True,
    )["gate"].fillna(False).astype(bool)


def trade_returns(df: pd.DataFrame, signal: pd.Series) -> list[float]:
    out, i, n = [], 0, len(df)
    while i + HOLD < n:
        if bool(signal.iloc[i]):
            out.append(float(df["close"].iloc[i + HOLD] / df["close"].iloc[i] - 1.0 - COST))
            i += HOLD
        else:
            i += 1
    return out


def stats(rets: list[float]) -> dict:
    if not rets:
        return {"n": 0, "mean": None, "win_rate": None, "total_return": None, "max_dd": None, "profit_factor": None}
    a = np.asarray(rets, dtype=float)
    eq = np.cumprod(1 + a)
    dd = eq / np.maximum.accumulate(eq) - 1
    gp, gl = a[a > 0].sum(), -a[a < 0].sum()
    return {
        "n": int(len(a)),
        "mean": float(a.mean()),
        "win_rate": float((a > 0).mean()),
        "total_return": float(eq[-1] - 1),
        "max_dd": float(dd.min()),
        "profit_factor": None if gl == 0 else float(gp / gl),
    }


def wf_slices(n: int) -> list[tuple[int, int]]:
    out = []
    for a in [0.45, 0.55, 0.65, 0.75, 0.85]:
        s, e = int(n * a), min(n, int(n * (a + 0.10)))
        if e - s >= 200:
            out.append((s, e))
    return out


def main() -> None:
    btc = fetch("BTC-USDT")
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "shadow_only": True,
        "factory_touched": False,
        "frozen_rule": {
            "alt_signal": "fresh EMA20 > EMA50 crossover on 1h close",
            "hold_hours": HOLD,
            "round_trip_cost": COST,
            "btc_gate": f"BTC {BTC_GATE_HOURS}h close > SMA{BTC_GATE_SMA}",
            "per_asset_retune": False,
        },
        "assets": {},
    }
    for inst in ALTS:
        alt = fetch(inst)
        start, end = max(alt.ts.min(), btc.ts.min()), min(alt.ts.max(), btc.ts.max())
        a = alt[(alt.ts >= start) & (alt.ts <= end)].reset_index(drop=True)
        b = btc[(btc.ts >= start) & (btc.ts <= end)].reset_index(drop=True)
        base = base_signal(a)
        gate = btc_gate_for(a, b)
        ungated = stats(trade_returns(a, base))
        gated = stats(trade_returns(a, base & gate))
        wf = []
        for s, e in wf_slices(len(a)):
            sub = a.iloc[s:e].reset_index(drop=True)
            bs = base.iloc[s:e].reset_index(drop=True)
            gs = gate.iloc[s:e].reset_index(drop=True)
            ub, gb = stats(trade_returns(sub, bs)), stats(trade_returns(sub, bs & gs))
            delta = None if ub["mean"] is None or gb["mean"] is None else gb["mean"] - ub["mean"]
            wf.append({"start": sub.ts.iloc[0].isoformat(), "end": sub.ts.iloc[-1].isoformat(), "ungated": ub, "gated": gb, "delta_mean": delta})
        deltas = [x["delta_mean"] for x in wf if x["delta_mean"] is not None]
        report["assets"][inst] = {
            "rows": len(a), "start": start.isoformat(), "end": end.isoformat(),
            "ungated": ungated, "gated": gated,
            "delta_mean": None if ungated["mean"] is None or gated["mean"] is None else gated["mean"] - ungated["mean"],
            "delta_total": None if ungated["total_return"] is None or gated["total_return"] is None else gated["total_return"] - ungated["total_return"],
            "walk_forward": wf,
            "wf_delta_positive": sum(d > 0 for d in deltas),
            "wf_delta_count": len(deltas),
        }
    valid = [v for v in report["assets"].values() if v["delta_mean"] is not None]
    report["panel"] = {
        "assets_tested": len(valid),
        "positive_delta_mean": sum(v["delta_mean"] > 0 for v in valid),
        "positive_gated_mean": sum(v["gated"]["mean"] is not None and v["gated"]["mean"] > 0 for v in valid),
        "positive_gated_pf_gt_1": sum(v["gated"]["profit_factor"] is not None and v["gated"]["profit_factor"] > 1 for v in valid),
        "wf_majority_positive_delta": sum(v["wf_delta_count"] >= 3 and v["wf_delta_positive"] > v["wf_delta_count"] / 2 for v in valid),
    }
    (OUT / "multi_alt_btc_regime_gate_test.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Multi-alt BTC regime gate generalization", "", "RESEARCH_ONLY=true; SHADOW_ONLY=true; Factory untouched.", "", f"Frozen: EMA20/50 1h fresh crossover; hold={HOLD}h; cost={COST:.3%}; gate=BTC {BTC_GATE_HOURS}h > SMA{BTC_GATE_SMA}.", ""]
    for inst, x in report["assets"].items():
        u, g = x["ungated"], x["gated"]
        lines.append(f"- {inst}: base n={u['n']} mean={u['mean']} PF={u['profit_factor']} total={u['total_return']} | gated n={g['n']} mean={g['mean']} PF={g['profit_factor']} total={g['total_return']} | delta_mean={x['delta_mean']} | WF delta+={x['wf_delta_positive']}/{x['wf_delta_count']}")
    lines += ["", f"Panel: {report['panel']}"]
    (OUT / "multi_alt_btc_regime_gate_test.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
