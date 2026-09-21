import json
import math
import os
import time
from pathlib import Path

import ccxt
import numpy as np
import pandas as pd

RESEARCH_ONLY = True
SHADOW_ONLY = True
ROUNDTRIP_COST = 0.002  # 20 bps total, deliberately conservative for event comparison
HORIZON = 24
SINCE_ISO = "2025-06-01T00:00:00Z"
SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]
OUTDIR = Path(__file__).with_name("runtime")
OUTDIR.mkdir(parents=True, exist_ok=True)


def fetch_ohlcv(exchange, symbol, since_ms):
    rows = []
    cursor = since_ms
    now = exchange.milliseconds()
    while cursor < now:
        batch = exchange.fetch_ohlcv(symbol, timeframe="1h", since=cursor, limit=300)
        if not batch:
            break
        if rows and batch[0][0] <= rows[-1][0]:
            batch = [r for r in batch if r[0] > rows[-1][0]]
        if not batch:
            break
        rows.extend(batch)
        cursor = batch[-1][0] + 3600_000
        if len(batch) < 300:
            break
        time.sleep(exchange.rateLimit / 1000.0)
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.drop_duplicates("date").set_index("date").sort_index()
    return df[["open", "high", "low", "close", "volume"]].astype(float)


def ema(s, span):
    return s.ewm(span=span, adjust=False, min_periods=span).mean()


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(df, n=14):
    prev = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev).abs(),
        (df["low"] - prev).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False, min_periods=n).mean()


def forward_return(df, h=HORIZON):
    return df["close"].shift(-h) / df["close"] - 1.0


def event_stats(signal, fwd, oos_mask, cost=ROUNDTRIP_COST):
    x = fwd[signal & oos_mask].dropna()
    n = int(x.size)
    if n == 0:
        return {"n": 0, "mean": None, "mean_net": None, "median": None, "hit_rate": None, "t_stat": None}
    mean = float(x.mean())
    sd = float(x.std(ddof=1)) if n > 1 else float("nan")
    t = mean / (sd / math.sqrt(n)) if n > 1 and sd > 0 else None
    return {
        "n": n,
        "mean": mean,
        "mean_net": mean - cost,
        "median": float(x.median()),
        "hit_rate": float((x > 0).mean()),
        "t_stat": None if t is None or not np.isfinite(t) else float(t),
    }


def evidence_label(s):
    if s["n"] < 30 or s["mean_net"] is None:
        return "INSUFFICIENT"
    if s["mean_net"] > 0 and (s["t_stat"] or 0) >= 1.96:
        return "POSITIVE_OOS"
    if s["mean_net"] > 0:
        return "WEAK_POSITIVE_OOS"
    return "NO_POSITIVE_OOS"


def build_signals(df):
    c = df["close"]
    sma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std(ddof=0)
    r14 = rsi(c, 14)

    # 1) volatility-band mean reversion: preregistered, no hyperopt values imported.
    band_mr = (c < sma20 - 2.0 * std20) & (r14 < 35)
    band_mr = band_mr & ~band_mr.shift(1).fillna(False)

    # 2) multi-horizon MA lattice: fixed log-like horizons.
    e8, e16, e32, e64 = [ema(c, n) for n in (8, 16, 32, 64)]
    lattice_state = (e8 > e16) & (e16 > e32) & (e32 > e64)
    ma_lattice = lattice_state & ~lattice_state.shift(1).fillna(False)

    # 3) volatility geometry: prior compression -> current expansion + upper Donchian location.
    a = atr(df, 14)
    kcw = (4.0 * a / c).replace([np.inf, -np.inf], np.nan)
    hi20 = df["high"].rolling(20).max()
    lo20 = df["low"].rolling(20).min()
    dpos = ((c - lo20) / (hi20 - lo20)).replace([np.inf, -np.inf], np.nan)
    q20 = kcw.rolling(120, min_periods=60).quantile(0.20)
    med = kcw.rolling(120, min_periods=60).median()
    was_compressed = kcw.shift(24) < q20.shift(24)
    vol_geom = was_compressed & (kcw > med) & (dpos > 0.70)
    vol_geom = vol_geom & ~vol_geom.shift(1).fillna(False)

    # 4) candlestick event family: scale-invariant bullish events, tested as a cluster.
    body = (df["close"] - df["open"]).abs()
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    lower = np.minimum(df["open"], df["close"]) - df["low"]
    upper = df["high"] - np.maximum(df["open"], df["close"])
    hammer = (lower > 2.0 * body) & (upper < body) & (body / rng < 0.45)
    bull_engulf = (
        (df["close"] > df["open"]) &
        (df["close"].shift(1) < df["open"].shift(1)) &
        (df["open"] <= df["close"].shift(1)) &
        (df["close"] >= df["open"].shift(1))
    )
    high_wave_bull = (df["close"] > df["open"]) & (body / rng < 0.25) & (lower / rng > 0.25) & (upper / rng > 0.25)
    candle_event = hammer | bull_engulf | high_wave_bull
    candle_event = candle_event & ~candle_event.shift(1).fillna(False)

    return {
        "volatility_band_mean_reversion": band_mr.fillna(False),
        "multi_horizon_ma_lattice": ma_lattice.fillna(False),
        "volatility_geometry_ratio": vol_geom.fillna(False),
        "candlestick_pattern_event": candle_event.fillna(False),
    }


def btc_regime_gate(btc):
    # Strict PIT alignment: only a completed 4h bar is used, then shifted one 4h bar before ffill.
    b4 = btc.resample("4h", label="right", closed="right").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna()
    state = b4["close"] > b4["close"].rolling(20).mean()
    return state.shift(1).reindex(btc.index, method="ffill").fillna(False)


def informative_gate_stats(asset, btc_gate, oos_mask):
    fast = ema(asset["close"], 20)
    slow = ema(asset["close"], 50)
    cross = (fast > slow) & (fast.shift(1) <= slow.shift(1))
    gate = btc_gate.reindex(asset.index).fillna(False)
    fwd = forward_return(asset)
    base = event_stats(cross.fillna(False), fwd, oos_mask)
    gated = event_stats((cross & gate).fillna(False), fwd, oos_mask)
    delta = None
    if base["mean_net"] is not None and gated["mean_net"] is not None:
        delta = gated["mean_net"] - base["mean_net"]
    return {"base": base, "gated": gated, "delta_mean_net": delta,
            "evidence": "POSITIVE_INCREMENTAL_OOS" if delta is not None and delta > 0 and gated["n"] >= 20 else "NO_CONFIRMED_INCREMENT"}


def seasonality_stats(df, split1, split2):
    # Train selects hours; validation must be positive; test is untouched final readout.
    fwd6 = df["close"].shift(-6) / df["close"] - 1.0
    hours = pd.Series(df.index.hour, index=df.index)
    train = df.index < split1
    valid = (df.index >= split1) & (df.index < split2)
    test = df.index >= split2
    train_means = pd.DataFrame({"hour": hours[train], "ret": fwd6[train]}).dropna().groupby("hour")["ret"].mean()
    selected = list(train_means.sort_values(ascending=False).head(6).index.astype(int))
    sig = hours.isin(selected)
    val_s = event_stats(sig, fwd6, valid, cost=ROUNDTRIP_COST)
    test_s = event_stats(sig, fwd6, test, cost=ROUNDTRIP_COST)
    val_pass = val_s["mean_net"] is not None and val_s["mean_net"] > 0
    label = evidence_label(test_s) if val_pass else "FAILED_VALIDATION"
    return {"selected_hours_utc": selected, "validation": val_s, "test": test_s, "evidence": label}


def main():
    assert RESEARCH_ONLY and SHADOW_ONLY
    ex = ccxt.okx({"enableRateLimit": True})
    since = ex.parse8601(SINCE_ISO)
    data = {}
    for symbol in SYMBOLS:
        print(f"fetching {symbol}", flush=True)
        data[symbol] = fetch_ohlcv(ex, symbol, since)
        if len(data[symbol]) < 2000:
            raise RuntimeError(f"insufficient data for {symbol}: {len(data[symbol])}")

    common_end = min(df.index.max() for df in data.values())
    common_start = max(df.index.min() for df in data.values())
    for s in data:
        data[s] = data[s].loc[common_start:common_end].copy()

    n = len(data["BTC/USDT"])
    split1 = data["BTC/USDT"].index[int(n * 0.60)]
    split2 = data["BTC/USDT"].index[int(n * 0.80)]
    oos_start = data["BTC/USDT"].index[int(n * 0.70)]

    results = {
        "policy": {"RESEARCH_ONLY": True, "SHADOW_ONLY": True, "factory_modified": False},
        "dataset": {"exchange": "OKX", "timeframe": "1h", "symbols": SYMBOLS, "start": str(common_start), "end": str(common_end), "roundtrip_cost": ROUNDTRIP_COST},
        "families": {},
        "informative_pair_regime_gate": {},
        "intraday_time_seasonality": {},
    }

    for symbol, df in data.items():
        fwd = forward_return(df)
        oos = df.index >= oos_start
        for family, signal in build_signals(df).items():
            s = event_stats(signal, fwd, oos)
            results["families"].setdefault(family, {})[symbol] = {**s, "evidence": evidence_label(s)}
        results["intraday_time_seasonality"][symbol] = seasonality_stats(df, split1, split2)

    gate = btc_regime_gate(data["BTC/USDT"])
    for symbol in [s for s in SYMBOLS if s != "BTC/USDT"]:
        oos = data[symbol].index >= oos_start
        results["informative_pair_regime_gate"][symbol] = informative_gate_stats(data[symbol], gate, oos)

    # Aggregate family evidence without ranking or optimization.
    for family, per_symbol in results["families"].items():
        positive = sum(1 for v in per_symbol.values() if v["evidence"] in {"POSITIVE_OOS", "WEAK_POSITIVE_OOS"})
        strong = sum(1 for v in per_symbol.values() if v["evidence"] == "POSITIVE_OOS")
        results["families"][family]["_aggregate"] = {"positive_symbols": positive, "strong_symbols": strong, "tested_symbols": len(SYMBOLS)}

    out_json = OUTDIR / "candidate_family_test_results.json"
    out_json.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Freqtrade candidate-family isolated test — first preregistered battery",
        "",
        f"Dataset: OKX 1h, {common_start} to {common_end}; cost={ROUNDTRIP_COST:.2%} round-trip.",
        "Factory impact: NONE. RESEARCH_ONLY=true; SHADOW_ONLY=true.",
        "",
        "## Fixed-family OOS event tests",
        "",
        "| Family | Symbol | N | Mean net | Hit | t-stat | Evidence |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for family, per_symbol in results["families"].items():
        for symbol, v in per_symbol.items():
            if symbol.startswith("_"):
                continue
            mn = "NA" if v["mean_net"] is None else f"{v['mean_net']:.3%}"
            hit = "NA" if v["hit_rate"] is None else f"{v['hit_rate']:.1%}"
            ts = "NA" if v["t_stat"] is None else f"{v['t_stat']:.2f}"
            lines.append(f"| {family} | {symbol} | {v['n']} | {mn} | {hit} | {ts} | {v['evidence']} |")

    lines += ["", "## Informative BTC regime gate", "", "| Symbol | Base N | Base net | Gated N | Gated net | Delta | Evidence |", "|---|---:|---:|---:|---:|---:|---|"]
    for symbol, v in results["informative_pair_regime_gate"].items():
        b, g = v["base"], v["gated"]
        fmt = lambda x: "NA" if x is None else f"{x:.3%}"
        lines.append(f"| {symbol} | {b['n']} | {fmt(b['mean_net'])} | {g['n']} | {fmt(g['mean_net'])} | {fmt(v['delta_mean_net'])} | {v['evidence']} |")

    lines += ["", "## Intraday UTC seasonality", "", "| Symbol | Selected train hours | Validation net | Test net | Test N | Evidence |", "|---|---|---:|---:|---:|---|"]
    for symbol, v in results["intraday_time_seasonality"].items():
        fmt = lambda x: "NA" if x is None else f"{x:.3%}"
        lines.append(f"| {symbol} | {','.join(map(str, v['selected_hours_utc']))} | {fmt(v['validation']['mean_net'])} | {fmt(v['test']['mean_net'])} | {v['test']['n']} | {v['evidence']} |")

    lines += ["", "## Interpretation contract", "", "- These are screening results, not survivors and not Factory families.", "- No source-reported hyperopt parameters or performance claims were used.", "- Positive OOS evidence only qualifies a family for a deeper isolated POC.", "- No result is allowed to modify or feed the active Factory automatically."]
    (OUTDIR / "candidate_family_test_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
