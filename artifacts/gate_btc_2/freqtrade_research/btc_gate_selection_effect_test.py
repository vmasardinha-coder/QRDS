# RESEARCH_ONLY=true
# SHADOW_ONLY=true
# Frozen pooled selection-effect test for BTC 12h/SMA20 gate.
# Baseline events are selected first with 48h non-overlap, then split by gate state.
# No per-asset retune, no Factory integration, no live orders, no capital.

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

OUT = Path(__file__).with_name("runtime_btc_gate_selection_effect")
OUT.mkdir(parents=True, exist_ok=True)
BASE_URL = "https://www.okx.com/api/v5/market/history-candles"
BAR = "1H"
MAX_PAGES = 80
ASSETS = ["XRP-USDT", "ETH-USDT", "SOL-USDT", "DOGE-USDT", "ADA-USDT", "LINK-USDT", "AVAX-USDT", "DOT-USDT", "LTC-USDT"]
HOLD = 48
COST = 0.002
BTC_GATE_HOURS = 12
BTC_GATE_SMA = 20
N_PERM = 20000
SEED = 20260921


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


def gate_for(alt: pd.DataFrame, btc: pd.DataFrame) -> pd.Series:
    b = btc.set_index("ts")["close"].resample(f"{BTC_GATE_HOURS}h", label="right", closed="right").last().dropna()
    ma = b.rolling(BTC_GATE_SMA, min_periods=BTC_GATE_SMA).mean()
    state = (b > ma).rename("gate")
    return pd.merge_asof(
        alt[["ts"]].sort_values("ts"), state.reset_index().sort_values("ts"),
        on="ts", direction="backward", allow_exact_matches=True,
    )["gate"].fillna(False).astype(bool)


def baseline_trades(df: pd.DataFrame, signal: pd.Series, gate: pd.Series) -> list[dict]:
    out, i, n = [], 0, len(df)
    while i + HOLD < n:
        if bool(signal.iloc[i]):
            r = float(df["close"].iloc[i + HOLD] / df["close"].iloc[i] - 1.0 - COST)
            out.append({"ts": df["ts"].iloc[i].isoformat(), "ret": r, "accepted": bool(gate.iloc[i])})
            i += HOLD
        else:
            i += 1
    return out


def stats(vals: list[float]) -> dict:
    if not vals:
        return {"n": 0, "mean": None, "median": None, "win_rate": None, "profit_factor": None}
    a = np.asarray(vals, dtype=float)
    gp, gl = a[a > 0].sum(), -a[a < 0].sum()
    return {
        "n": int(len(a)), "mean": float(a.mean()), "median": float(np.median(a)),
        "win_rate": float((a > 0).mean()), "profit_factor": None if gl == 0 else float(gp / gl),
    }


def stratified_permutation(asset_rows: dict[str, list[dict]]) -> dict:
    rng = np.random.default_rng(SEED)
    accepted = [t["ret"] for rows in asset_rows.values() for t in rows if t["accepted"]]
    rejected = [t["ret"] for rows in asset_rows.values() for t in rows if not t["accepted"]]
    observed = float(np.mean(accepted) - np.mean(rejected))
    per_asset = {}
    arrays = []
    for asset, rows in asset_rows.items():
        vals = np.asarray([t["ret"] for t in rows], dtype=float)
        k = sum(t["accepted"] for t in rows)
        arrays.append((asset, vals, k))
        a = vals[[t["accepted"] for t in rows]]
        r = vals[[not t["accepted"] for t in rows]]
        per_asset[asset] = None if len(a) == 0 or len(r) == 0 else float(a.mean() - r.mean())
    null = np.empty(N_PERM, dtype=float)
    for j in range(N_PERM):
        acc_all, rej_all = [], []
        for _, vals, k in arrays:
            perm = rng.permutation(len(vals))
            acc_all.extend(vals[perm[:k]])
            rej_all.extend(vals[perm[k:]])
        null[j] = np.mean(acc_all) - np.mean(rej_all)
    p_one = float((1 + np.sum(null >= observed)) / (N_PERM + 1))
    return {
        "observed_delta_mean": observed,
        "one_sided_stratified_permutation_p": p_one,
        "null_mean": float(null.mean()),
        "null_sd": float(null.std(ddof=1)),
        "asset_deltas": per_asset,
        "assets_positive_delta": sum(v is not None and v > 0 for v in per_asset.values()),
        "assets_with_delta": sum(v is not None for v in per_asset.values()),
    }


def main() -> None:
    btc = fetch("BTC-USDT")
    rows_by_asset: dict[str, list[dict]] = {}
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "shadow_only": True,
        "factory_touched": False,
        "frozen_rule": {"hold_hours": HOLD, "cost": COST, "gate": "BTC 12h close > SMA20", "per_asset_retune": False},
        "assets": {},
    }
    for inst in ASSETS:
        alt = fetch(inst)
        start, end = max(alt.ts.min(), btc.ts.min()), min(alt.ts.max(), btc.ts.max())
        a = alt[(alt.ts >= start) & (alt.ts <= end)].reset_index(drop=True)
        b = btc[(btc.ts >= start) & (btc.ts <= end)].reset_index(drop=True)
        trades = baseline_trades(a, base_signal(a), gate_for(a, b))
        rows_by_asset[inst] = trades
        accepted = [t["ret"] for t in trades if t["accepted"]]
        rejected = [t["ret"] for t in trades if not t["accepted"]]
        sa, sr = stats(accepted), stats(rejected)
        report["assets"][inst] = {
            "all_n": len(trades), "accepted": sa, "rejected": sr,
            "delta_mean": None if sa["mean"] is None or sr["mean"] is None else sa["mean"] - sr["mean"],
        }
    all_acc = [t["ret"] for rows in rows_by_asset.values() for t in rows if t["accepted"]]
    all_rej = [t["ret"] for rows in rows_by_asset.values() for t in rows if not t["accepted"]]
    report["pooled"] = {
        "accepted": stats(all_acc), "rejected": stats(all_rej),
        "selection_effect": stratified_permutation(rows_by_asset),
    }
    (OUT / "btc_gate_selection_effect_test.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# BTC gate pooled selection-effect test", "", "RESEARCH_ONLY=true; SHADOW_ONLY=true; Factory untouched.", "", "Frozen: baseline 1h EMA20/50 fresh cross, 48h non-overlap, 0.20% round-trip cost; gate BTC 12h > SMA20.", ""]
    for asset, x in report["assets"].items():
        lines.append(f"- {asset}: accepted={x['accepted']} | rejected={x['rejected']} | delta_mean={x['delta_mean']}")
    lines += ["", f"Pooled accepted: {report['pooled']['accepted']}", f"Pooled rejected: {report['pooled']['rejected']}", f"Selection effect: {report['pooled']['selection_effect']}"]
    (OUT / "btc_gate_selection_effect_test.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
