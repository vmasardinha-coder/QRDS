#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "research" / "factory_regime_c1_prereg.json"
CANONICAL = ROOT / "migration" / "canonical" / "delta" / "scripts" / "00_run_delta_v11.py"


def load_prereg() -> dict[str, Any]:
    p = json.loads(PREREG.read_text(encoding="utf-8"))
    assert p["generated_before_results"] is True
    assert p["safety"]["ORDERS"] == 0 and p["safety"]["REAL_CAPITAL"] == 0
    assert p["safety"]["ENGINE_FEED"] is False and p["safety"]["NO_BACKFILL"] is True
    assert p["source_contract"]["exploratory_bottom_probabilities_not_labels"] is True
    return p


def load_canonical_module():
    spec = importlib.util.spec_from_file_location("delta_canonical_for_regime", CANONICAL)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import canonical Delta collector")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = json.loads((ROOT / "migration" / "canonical" / "delta" / "config_delta_v11.json").read_text(encoding="utf-8"))
    dates = pd.date_range("2025-10-01", "2026-08-09", freq="D")
    rng = np.random.default_rng(20260825)
    cycle = np.sin(np.linspace(0, 9 * np.pi, len(dates)))
    market = 0.0002 + 0.006 * cycle + rng.normal(0, 0.012, len(dates))
    rows = []
    for i, sym in enumerate(cfg["universe"]):
        idio = rng.normal(0, 0.010 + 0.0003 * (i % 7), len(dates))
        beta = 0.65 + 0.03 * (i % 8)
        rets = beta * market + idio
        px = 100 * np.exp(np.cumsum(rets))
        for d, close in zip(dates, px):
            rows.append({"date": d, "symbol": sym, "close": float(close)})
    macro = pd.DataFrame({
        "date": dates,
        "DGS10": 4.2 + 0.35 * np.sin(np.linspace(0, 4 * np.pi, len(dates))) + rng.normal(0, 0.03, len(dates)),
        "DTWEXBGS": 120 + 4 * np.cos(np.linspace(0, 5 * np.pi, len(dates))) + rng.normal(0, 0.4, len(dates)),
    })
    return pd.DataFrame(rows), macro


def public_crypto() -> pd.DataFrame:
    mod = load_canonical_module()
    ohlc, _funding, quality, _failures = mod.collect_public_data()
    if int((quality["ohlc_rows"] > 0).sum()) < 12:
        raise RuntimeError("REGIME_C1_SOURCE_MIN_ASSETS_FAIL")
    x = ohlc[["date", "symbol", "close"]].copy()
    x["date"] = pd.to_datetime(x["date"]).dt.normalize()
    return x


def fetch_fred(series: str) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
    x = pd.read_csv(url)
    x.columns = ["date", series]
    x["date"] = pd.to_datetime(x["date"], errors="raise").dt.normalize()
    x[series] = pd.to_numeric(x[series], errors="coerce")
    return x.dropna().sort_values("date")


def public_macro() -> pd.DataFrame | None:
    try:
        a = fetch_fred("DGS10")
        b = fetch_fred("DTWEXBGS")
        return a.merge(b, on="date", how="outer").sort_values("date")
    except Exception:
        return None


def panelize(ohlc: pd.DataFrame, cutoff: str) -> pd.DataFrame:
    x = ohlc.copy()
    x["date"] = pd.to_datetime(x["date"]).dt.normalize()
    x = x[x["date"] < pd.Timestamp(cutoff)].sort_values(["date", "symbol"])
    if x.duplicated(["date", "symbol"]).any():
        raise RuntimeError("REGIME_C1_DUPLICATE_DATE_SYMBOL")
    p = x.pivot(index="date", columns="symbol", values="close").sort_index()
    if "BTC" not in p.columns or p.shape[1] < 12:
        raise RuntimeError("REGIME_C1_INSUFFICIENT_UNIVERSE")
    return p


def align_macro(macro: pd.DataFrame | None, index: pd.DatetimeIndex) -> pd.DataFrame | None:
    if macro is None:
        return None
    x = macro.copy().set_index("date").sort_index().reindex(index).ffill(limit=7)
    if not {"DGS10", "DTWEXBGS"}.issubset(x.columns):
        return None
    return x


def max_drawdown(r: pd.Series) -> float:
    nav = (1.0 + r.fillna(0.0)).cumprod()
    return float((nav / nav.cummax() - 1.0).min())


def metrics(r: pd.Series) -> dict[str, float]:
    r = r.dropna()
    n = int(len(r))
    total = float((1.0 + r).prod() - 1.0) if n else 0.0
    vol = float(r.std(ddof=1)) if n > 1 else 0.0
    sharpe = float(r.mean() / vol * math.sqrt(365.0)) if vol > 0 else 0.0
    return {"n": n, "total_return": total, "sharpe": sharpe, "max_drawdown": max_drawdown(r) if n else 0.0}


def lagged_quantile(s: pd.Series, window: int, q: float) -> pd.Series:
    return s.shift(1).rolling(window, min_periods=max(20, window // 2)).quantile(q)


def family_state(prices: pd.DataFrame, macro: pd.DataFrame | None, family: str, cfg: dict[str, Any]) -> pd.Series | None:
    ret = prices.pct_change()
    btc = prices["BTC"]
    if family == "REGIME_C1_TREND_DISPERSION":
        tw, dw = int(cfg["trend_window"]), int(cfg["dispersion_window"])
        trend = btc.pct_change(tw)
        dispersion = ret.drop(columns=["BTC"], errors="ignore").rolling(dw).std().mean(axis=1)
        gate = lagged_quantile(dispersion, 60, float(cfg["dispersion_quantile"]))
        return ((trend > float(cfg["trend_threshold"])) & (dispersion <= gate)).astype(float)
    if family == "REGIME_C1_VOLATILITY":
        fast = ret["BTC"].rolling(int(cfg["fast_vol"])).std()
        slow = ret["BTC"].rolling(int(cfg["slow_vol"])).std()
        return ((fast / slow) <= float(cfg["ratio_threshold"])).astype(float)
    if family == "REGIME_C1_RATES_FX":
        if macro is None:
            return None
        rw, fw = int(cfg["rates_window"]), int(cfg["fx_window"])
        rates = macro["DGS10"].diff(rw)
        fx = macro["DTWEXBGS"].pct_change(fw)
        return ((rates <= float(cfg["rates_threshold"])) & (fx <= float(cfg["fx_threshold"]))).astype(float)
    if family == "REGIME_C1_BREADTH":
        mw = int(cfg["ma_window"])
        ma = prices.rolling(mw).mean()
        breadth = (prices > ma).mean(axis=1)
        return (breadth >= float(cfg["breadth_threshold"])).astype(float)
    if family == "REGIME_C1_HYSTERESIS":
        tw = int(cfg["trend_window"])
        trend = btc.pct_change(tw)
        entry, exit_ = float(cfg["entry_threshold"]), float(cfg["exit_threshold"])
        persist = int(cfg["persistence_days"])
        state = 0.0
        enter_count = 0
        exit_count = 0
        out = []
        for val in trend:
            enter_count = enter_count + 1 if pd.notna(val) and val >= entry else 0
            exit_count = exit_count + 1 if pd.notna(val) and val <= exit_ else 0
            if state == 0.0 and enter_count >= persist:
                state = 1.0
                enter_count = 0
            elif state == 1.0 and exit_count >= persist:
                state = 0.0
                exit_count = 0
            out.append(state)
        return pd.Series(out, index=prices.index, dtype=float)
    raise ValueError(f"unknown family {family}")


def strategy_returns(prices: pd.DataFrame, state: pd.Series, switch_cost_bps: float) -> pd.Series:
    ret = prices.pct_change()
    alt = ret.drop(columns=["BTC"], errors="ignore").mean(axis=1)
    defensive = 0.50 * ret["BTC"].fillna(0.0)
    # State at completed close t is applied only to return t+1.
    applied = state.shift(1)
    gross = applied * alt + (1.0 - applied) * defensive
    switches = applied.diff().abs().fillna(0.0)
    return gross - switches * (switch_cost_bps / 10000.0)


def passes(m: dict[str, float], gates: dict[str, Any]) -> bool:
    return bool(m["n"] >= int(gates["min_observations_each_block"]) and m["total_return"] > 0 and m["sharpe"] >= float(gates["min_sharpe"]) and m["max_drawdown"] >= float(gates["max_drawdown_floor"]))


def evaluate(prices: pd.DataFrame, macro: pd.DataFrame | None, prereg: dict[str, Any]) -> dict[str, Any]:
    disc_end = pd.Timestamp(prereg["discovery_end_inclusive"])
    rep_start = pd.Timestamp(prereg["replication_start_inclusive"])
    gates = prereg["gates"]
    cost = float(prereg["economic_mapping"]["switch_cost_bps"])
    result: dict[str, Any] = {"schema": "qrds.factory.regime_c1_result.v1", "families": {}, "survivors": [], "data_gaps": [], "h1_economics_read": False, "partial_prospective_economics_read": False, "orders": 0, "real_capital": 0, "engine_feed": False}
    for fam, spec in prereg["families"].items():
        variants = [("central", spec["central"])] + [(f"neighbor_{i+1}", x) for i, x in enumerate(spec["neighbors"])]
        rows = []
        central_disc = False
        central_rep = False
        neighbor_disc = False
        unavailable = False
        for label, cfg in variants:
            state = family_state(prices, macro, fam, cfg)
            if state is None:
                unavailable = True
                break
            rr = strategy_returns(prices, state, cost)
            dm = metrics(rr[rr.index <= disc_end])
            rm = metrics(rr[rr.index >= rep_start])
            dp, rp = passes(dm, gates), passes(rm, gates)
            if label == "central":
                central_disc, central_rep = dp, rp
            else:
                neighbor_disc = neighbor_disc or dp
            rows.append({"variant": label, "config": cfg, "discovery": dm, "replication": rm, "discovery_pass": dp, "replication_pass": rp})
        if unavailable:
            state_name = "DATA_GAP"
            result["data_gaps"].append(fam)
        else:
            survivor = central_disc and neighbor_disc and central_rep
            state_name = "SURVIVOR_REPLICATED" if survivor else ("REJECTED_FAILED_REPLICATION" if central_disc and neighbor_disc else "REJECTED_DISCOVERY")
            if survivor:
                result["survivors"].append(fam)
        result["families"][fam] = {"state": state_name, "variants": rows}
    if result["survivors"]:
        result["status"] = "SURVIVORS_READY_FOR_FREEZE"
    elif len(result["data_gaps"]) == len(prereg["families"]):
        result["status"] = "DATA_BLOCKED"
    else:
        result["status"] = "CLOSED_NULL_WITH_DATA_GAPS" if result["data_gaps"] else "CLOSED_NULL"
    result["comparison_capital_brl"] = int(prereg["capital_comparison_brl"])
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fixture", "public"], default="fixture")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    prereg = load_prereg()
    if args.mode == "fixture":
        raw, macro_raw = fixture_inputs()
    else:
        raw, macro_raw = public_crypto(), public_macro()
    prices = panelize(raw, prereg["historical_cutoff_exclusive"])
    macro = align_macro(macro_raw, prices.index)
    result = evaluate(prices, macro, prereg)
    result["mode"] = args.mode
    result["macro_available"] = macro is not None
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "survivors": result["survivors"], "data_gaps": result["data_gaps"], "mode": args.mode}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
