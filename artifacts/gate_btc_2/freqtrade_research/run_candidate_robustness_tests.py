import json
from pathlib import Path

import ccxt
import numpy as np
import pandas as pd

from run_candidate_family_tests import (
    RESEARCH_ONLY, SHADOW_ONLY, ROUNDTRIP_COST, SINCE_ISO, SYMBOLS,
    fetch_ohlcv, ema, forward_return, event_stats, btc_regime_gate,
)

OUTDIR = Path(__file__).with_name("runtime_robustness")
OUTDIR.mkdir(parents=True, exist_ok=True)


def lattice_signal(df, horizons):
    es = [ema(df["close"], h) for h in horizons]
    state = pd.Series(True, index=df.index)
    for a, b in zip(es[:-1], es[1:]):
        state &= a > b
    return (state & ~state.shift(1).fillna(False)).fillna(False)


def candlestick_components(df):
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
    return {
        "hammer": (hammer & ~hammer.shift(1).fillna(False)).fillna(False),
        "bullish_engulfing": (bull_engulf & ~bull_engulf.shift(1).fillna(False)).fillna(False),
        "high_wave_bull": (high_wave_bull & ~high_wave_bull.shift(1).fillna(False)).fillna(False),
    }


def ref_gate(btc, hours, sma_n):
    rule = f"{hours}h"
    b = btc.resample(rule, label="right", closed="right").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna()
    state = b["close"] > b["close"].rolling(sma_n).mean()
    return state.shift(1).reindex(btc.index, method="ffill").fillna(False)


def half_masks(index, oos_start):
    oos_idx = index[index >= oos_start]
    mid = oos_idx[len(oos_idx) // 2]
    return (index >= oos_start) & (index < mid), index >= mid


def cost_stats(signal, fwd, mask):
    out = {}
    for cost in (0.001, 0.002, 0.004):
        out[f"cost_{int(cost*10000)}bps"] = event_stats(signal, fwd, mask, cost=cost)
    return out


def main():
    assert RESEARCH_ONLY and SHADOW_ONLY
    ex = ccxt.okx({"enableRateLimit": True})
    since = ex.parse8601(SINCE_ISO)
    data = {s: fetch_ohlcv(ex, s, since) for s in SYMBOLS}
    start = max(d.index.min() for d in data.values())
    end = min(d.index.max() for d in data.values())
    data = {s: d.loc[start:end].copy() for s, d in data.items()}
    n = len(data["BTC/USDT"])
    oos_start = data["BTC/USDT"].index[int(n * 0.70)]

    results = {
        "policy": {"RESEARCH_ONLY": True, "SHADOW_ONLY": True, "factory_modified": False},
        "dataset": {"exchange": "OKX", "timeframe": "1h", "start": str(start), "end": str(end)},
        "ma_lattice": {}, "xrp_btc_regime_gate": {}, "sol_candlestick": {},
    }

    # A) MA lattice: three preregistered horizon ladders, three forward horizons,
    # cost sensitivity, and two untouched OOS subperiods.
    ladders = {
        "fast_6_12_24_48": (6, 12, 24, 48),
        "base_8_16_32_64": (8, 16, 32, 64),
        "slow_12_24_48_96": (12, 24, 48, 96),
    }
    for symbol in ["ETH/USDT", "SOL/USDT", "XRP/USDT", "BTC/USDT"]:
        df = data[symbol]
        oos = df.index >= oos_start
        h1, h2 = half_masks(df.index, oos_start)
        results["ma_lattice"][symbol] = {}
        for lname, horizons in ladders.items():
            sig = lattice_signal(df, horizons)
            item = {"horizons": horizons, "horizons_forward": {}}
            for fh in (12, 24, 48):
                fwd = forward_return(df, fh)
                item["horizons_forward"][str(fh)] = event_stats(sig, fwd, oos, cost=ROUNDTRIP_COST)
            fwd24 = forward_return(df, 24)
            item["cost_sensitivity_24h"] = cost_stats(sig, fwd24, oos)
            item["oos_half_1_24h"] = event_stats(sig, fwd24, h1, cost=ROUNDTRIP_COST)
            item["oos_half_2_24h"] = event_stats(sig, fwd24, h2, cost=ROUNDTRIP_COST)
            results["ma_lattice"][symbol][lname] = item

    # B) XRP reference-regime gate: keep base alpha fixed; perturb only the
    # reference timeframe/lookback to test whether the incremental effect is structural.
    xrp = data["XRP/USDT"]
    fast, slow = ema(xrp["close"], 20), ema(xrp["close"], 50)
    cross = ((fast > slow) & (fast.shift(1) <= slow.shift(1))).fillna(False)
    fwd = forward_return(xrp, 24)
    oos = xrp.index >= oos_start
    base = event_stats(cross, fwd, oos, cost=ROUNDTRIP_COST)
    results["xrp_btc_regime_gate"]["base"] = base
    for name, hours, sma_n in [
        ("4h_sma20", 4, 20), ("4h_sma50", 4, 50), ("12h_sma20", 12, 20), ("12h_sma50", 12, 50)
    ]:
        gate = ref_gate(data["BTC/USDT"], hours, sma_n).reindex(xrp.index).fillna(False)
        gated = event_stats(cross & gate, fwd, oos, cost=ROUNDTRIP_COST)
        delta = None if base["mean_net"] is None or gated["mean_net"] is None else gated["mean_net"] - base["mean_net"]
        results["xrp_btc_regime_gate"][name] = {"gated": gated, "delta_mean_net": delta}

    # C) SOL candlesticks: split the cluster into components and horizons.
    sol = data["SOL/USDT"]
    oos = sol.index >= oos_start
    h1, h2 = half_masks(sol.index, oos_start)
    for pname, sig in candlestick_components(sol).items():
        results["sol_candlestick"][pname] = {}
        for fh in (12, 24, 48):
            results["sol_candlestick"][pname][f"fwd_{fh}h"] = event_stats(sig, forward_return(sol, fh), oos, cost=ROUNDTRIP_COST)
        results["sol_candlestick"][pname]["oos_half_1_24h"] = event_stats(sig, forward_return(sol, 24), h1, cost=ROUNDTRIP_COST)
        results["sol_candlestick"][pname]["oos_half_2_24h"] = event_stats(sig, forward_return(sol, 24), h2, cost=ROUNDTRIP_COST)

    (OUTDIR / "robustness_results.json").write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Freqtrade candidate robustness — isolated second stage", "",
        f"Dataset: OKX 1h, {start} to {end}",
        "Factory impact: NONE. RESEARCH_ONLY=true; SHADOW_ONLY=true.", "",
        "## MA lattice — 24h base-cost view", "",
        "| Symbol | Ladder | N | Net 24h | t-stat | Half1 net | Half2 net | 10bps | 40bps |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    def pct(v): return "NA" if v is None else f"{v:.3%}"
    def ts(v): return "NA" if v is None else f"{v:.2f}"
    for sym, ladd in results["ma_lattice"].items():
        for lname, v in ladd.items():
            b = v["horizons_forward"]["24"]
            c10 = v["cost_sensitivity_24h"]["cost_10bps"]
            c40 = v["cost_sensitivity_24h"]["cost_40bps"]
            lines.append(f"| {sym} | {lname} | {b['n']} | {pct(b['mean_net'])} | {ts(b['t_stat'])} | {pct(v['oos_half_1_24h']['mean_net'])} | {pct(v['oos_half_2_24h']['mean_net'])} | {pct(c10['mean_net'])} | {pct(c40['mean_net'])} |")

    lines += ["", "## XRP — BTC regime-gate robustness", "", "| Gate | N | Gated net | Delta vs base |", "|---|---:|---:|---:|"]
    for name, v in results["xrp_btc_regime_gate"].items():
        if name == "base":
            continue
        lines.append(f"| {name} | {v['gated']['n']} | {pct(v['gated']['mean_net'])} | {pct(v['delta_mean_net'])} |")
    lines.append(f"\nBase XRP cross: N={base['n']}, net={pct(base['mean_net'])}.")

    lines += ["", "## SOL — candlestick component robustness", "", "| Pattern | N24 | Net12 | Net24 | Net48 | Half1 24h | Half2 24h |", "|---|---:|---:|---:|---:|---:|---:|"]
    for name, v in results["sol_candlestick"].items():
        lines.append(f"| {name} | {v['fwd_24h']['n']} | {pct(v['fwd_12h']['mean_net'])} | {pct(v['fwd_24h']['mean_net'])} | {pct(v['fwd_48h']['mean_net'])} | {pct(v['oos_half_1_24h']['mean_net'])} | {pct(v['oos_half_2_24h']['mean_net'])} |")

    lines += ["", "## Contract", "", "These are robustness screens only. No result is promoted to the active Factory."]
    (OUTDIR / "robustness_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
