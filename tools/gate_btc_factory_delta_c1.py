#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "tools" / "gate_btc_factory_delta_c1_prereg.json"
CANONICAL = ROOT / "migration" / "canonical" / "delta" / "scripts" / "00_run_delta_v11.py"


def load_prereg() -> dict[str, Any]:
    p = json.loads(PREREG.read_text(encoding="utf-8"))
    assert p["generated_before_results"] is True
    assert p["safety"]["ORDERS"] == 0 and p["safety"]["REAL_CAPITAL"] == 0
    assert p["safety"]["ENGINE_FEED"] is False and p["safety"]["NO_BACKFILL"] is True
    return p


def load_canonical_module():
    spec = importlib.util.spec_from_file_location("delta_canonical_for_factory", CANONICAL)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import canonical Delta collector")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_ohlc() -> pd.DataFrame:
    cfg = json.loads((ROOT / "migration" / "canonical" / "delta" / "config_delta_v11.json").read_text(encoding="utf-8"))
    dates = pd.date_range("2025-10-01", "2026-08-09", freq="D")
    rng = np.random.default_rng(20260824)
    market = rng.normal(0.0002, 0.018, len(dates))
    rows = []
    for i, sym in enumerate(cfg["universe"]):
        idio = rng.normal(0, 0.012 + i * 0.0002, len(dates))
        drift = (i - len(cfg["universe"]) / 2) * 0.00001
        rets = market * (0.75 + 0.02 * (i % 5)) + idio + drift
        px = 100 * np.exp(np.cumsum(rets))
        for d, close in zip(dates, px):
            rows.append({"date": d, "symbol": sym, "close": float(close)})
    return pd.DataFrame(rows)


def public_ohlc() -> pd.DataFrame:
    mod = load_canonical_module()
    ohlc, _funding, quality, _failures = mod.collect_public_data()
    if int((quality["ohlc_rows"] > 0).sum()) < 12:
        raise RuntimeError("DELTA_C1_SOURCE_MIN_ASSETS_FAIL")
    out = ohlc[["date", "symbol", "close"]].copy()
    out["date"] = pd.to_datetime(out["date"]).dt.normalize()
    return out


def panelize(ohlc: pd.DataFrame, cutoff: str) -> pd.DataFrame:
    x = ohlc.copy()
    x["date"] = pd.to_datetime(x["date"]).dt.normalize()
    x = x[x["date"] < pd.Timestamp(cutoff)].sort_values(["date", "symbol"])
    if x.duplicated(["date", "symbol"]).any():
        raise RuntimeError("DELTA_C1_DUPLICATE_DATE_SYMBOL")
    p = x.pivot(index="date", columns="symbol", values="close").sort_index()
    if "BTC" not in p.columns or p.shape[1] < 12:
        raise RuntimeError("DELTA_C1_INSUFFICIENT_UNIVERSE")
    return p


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


def equal_side_weights(score: pd.Series, top_n: int, bottom_n: int, gross_long: float, gross_short: float) -> pd.Series:
    s = score.dropna().drop(labels=["BTC"], errors="ignore")
    if len(s) < top_n + bottom_n:
        return pd.Series(dtype=float)
    top = s.nlargest(top_n).index
    bot = s.nsmallest(bottom_n).index
    w = pd.Series(0.0, index=score.index)
    w.loc[top] = gross_long / len(top)
    w.loc[bot] = -gross_short / len(bot)
    return w


def inverse_vol_weights(score: pd.Series, vol: pd.Series, top_n: int, bottom_n: int) -> pd.Series:
    s = score.dropna().drop(labels=["BTC"], errors="ignore")
    if len(s) < top_n + bottom_n:
        return pd.Series(dtype=float)
    top = s.nlargest(top_n).index
    bot = s.nsmallest(bottom_n).index
    w = pd.Series(0.0, index=score.index)
    for names, gross, sign in ((top, 0.70, 1.0), (bot, 0.30, -1.0)):
        inv = 1.0 / vol.reindex(names).replace(0, np.nan)
        inv = inv.replace([np.inf, -np.inf], np.nan).dropna()
        if inv.empty:
            return pd.Series(dtype=float)
        w.loc[inv.index] = sign * gross * inv / inv.sum()
    return w


def rolling_beta(ret: pd.DataFrame, window: int) -> pd.DataFrame:
    btc = ret["BTC"]
    out = pd.DataFrame(index=ret.index, columns=ret.columns, dtype=float)
    var = btc.rolling(window).var()
    for c in ret.columns:
        out[c] = ret[c].rolling(window).cov(btc) / var
    return out


def run_variant(prices: pd.DataFrame, family: str, cfg: dict[str, Any], prereg: dict[str, Any]) -> pd.Series:
    ret = prices.pct_change()
    lb = int(cfg["lookback"])
    score = prices.pct_change(lb)
    betas = rolling_beta(ret, int(cfg.get("beta_window", 60))) if family == "DELTA_C1_BETA_NEUTRAL" else None
    vol = ret.rolling(int(cfg.get("vol_window", 20))).std()
    top_n = int(prereg["execution"]["top_n"])
    bottom_n = int(prereg["execution"]["bottom_n"])
    fee = float(prereg["execution"]["fee_bps_per_turnover_unit"]) / 10000.0
    reb = int(cfg["rebalance_days"])
    weights = pd.Series(0.0, index=prices.columns)
    prev = weights.copy()
    out = []
    for i, d in enumerate(prices.index):
        if i == 0:
            out.append(np.nan)
            continue
        if i % reb == 0:
            sc = score.loc[d].copy()
            if family == "DELTA_C1_BETA_NEUTRAL":
                b = betas.loc[d]
                sc = sc - b * float(sc.get("BTC", 0.0))
                weights = equal_side_weights(sc, top_n, bottom_n, 0.50, 0.50)
            elif family == "DELTA_C1_REGIME":
                trend_w = int(cfg["trend_window"])
                vol_w = int(cfg["vol_window"])
                if i < max(trend_w, vol_w) + 1:
                    weights = pd.Series(0.0, index=prices.columns)
                else:
                    btc_trend = prices["BTC"].iloc[i] / prices["BTC"].iloc[i - trend_w] - 1.0
                    btc_vol = ret["BTC"].iloc[max(1, i - vol_w + 1): i + 1].std()
                    long_gross, short_gross = ((0.70, 0.30) if btc_trend > 0 and btc_vol < 0.05 else (0.40, 0.20))
                    weights = equal_side_weights(sc, top_n, bottom_n, long_gross, short_gross)
            elif family == "DELTA_C1_RISK_BUDGET":
                weights = inverse_vol_weights(sc, vol.loc[d], top_n, bottom_n)
            else:
                weights = equal_side_weights(sc, top_n, bottom_n, float(cfg.get("gross_long", 0.70)), float(cfg.get("gross_short", 0.30)))
            if weights.empty:
                weights = pd.Series(0.0, index=prices.columns)
            weights = weights.reindex(prices.columns, fill_value=0.0)
        day_ret = ret.loc[d].fillna(0.0)
        turnover = float((weights - prev).abs().sum())
        out.append(float((weights * day_ret).sum()) - fee * turnover)
        prev = weights.copy()
    return pd.Series(out, index=prices.index, name=family)


def passes(m: dict[str, float], gates: dict[str, Any]) -> bool:
    return bool(m["n"] >= int(gates["min_observations_each_block"]) and m["total_return"] > 0 and m["sharpe"] >= float(gates["min_sharpe"]) and m["max_drawdown"] >= float(gates["max_drawdown_floor"]))


def evaluate(prices: pd.DataFrame, prereg: dict[str, Any]) -> dict[str, Any]:
    disc_end = pd.Timestamp(prereg["discovery_end_inclusive"])
    rep_start = pd.Timestamp(prereg["replication_start_inclusive"])
    gates = prereg["gates"]
    result: dict[str, Any] = {"schema": "qrds.factory.delta_c1_result.v1", "families": {}, "survivors": [], "h1_economics_read": False, "partial_prospective_economics_read": False, "orders": 0, "real_capital": 0, "engine_feed": False}
    for fam, spec in prereg["families"].items():
        variants = [("central", spec["central"])] + [(f"neighbor_{i+1}", x) for i, x in enumerate(spec["neighbors"])]
        rows = []
        central_rep_pass = False
        discovery_neighbor_pass = False
        central_disc_pass = False
        for label, cfg in variants:
            rr = run_variant(prices, fam, cfg, prereg)
            dm = metrics(rr[rr.index <= disc_end])
            rm = metrics(rr[rr.index >= rep_start])
            dp, rp = passes(dm, gates), passes(rm, gates)
            if label == "central":
                central_disc_pass, central_rep_pass = dp, rp
            else:
                discovery_neighbor_pass = discovery_neighbor_pass or dp
            rows.append({"variant": label, "config": cfg, "discovery": dm, "replication": rm, "discovery_pass": dp, "replication_pass": rp})
        survivor = central_disc_pass and discovery_neighbor_pass and central_rep_pass
        state = "SURVIVOR_REPLICATED" if survivor else ("REJECTED_FAILED_REPLICATION" if central_disc_pass and discovery_neighbor_pass else "REJECTED_DISCOVERY")
        result["families"][fam] = {"state": state, "variants": rows}
        if survivor:
            result["survivors"].append(fam)
    result["status"] = "SURVIVORS_READY_FOR_FREEZE" if result["survivors"] else "CLOSED_NULL"
    result["comparison_capital_brl"] = int(prereg["capital_comparison_brl"])
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fixture", "public"], default="fixture")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    prereg = load_prereg()
    raw = fixture_ohlc() if args.mode == "fixture" else public_ohlc()
    prices = panelize(raw, prereg["historical_cutoff_exclusive"])
    result = evaluate(prices, prereg)
    result["mode"] = args.mode
    result["source_rows"] = int(len(raw))
    result["source_sha256"] = hashlib.sha256(raw.sort_values(["date", "symbol"]).to_csv(index=False).encode()).hexdigest()
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "survivors": result["survivors"], "mode": args.mode}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
