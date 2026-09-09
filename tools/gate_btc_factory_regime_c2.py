#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "tools" / "gate_btc_factory_regime_c2_prereg.json"
CLARIFY = ROOT / "tools" / "gate_btc_factory_regime_c2_clarification_freeze.json"
CANONICAL = ROOT / "migration" / "canonical" / "delta" / "scripts" / "00_run_delta_v11.py"
DELTA_CFG = ROOT / "migration" / "canonical" / "delta" / "config_delta_v11.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_contract() -> tuple[dict[str, Any], dict[str, Any]]:
    p_raw = PREREG.read_bytes()
    c_raw = CLARIFY.read_bytes()
    p = json.loads(p_raw)
    c = json.loads(c_raw)
    assert p["generated_before_results"] is True
    assert p["predecessor_result_credit"] == 0
    assert p["source_contract"]["funding_forbidden"] is True
    assert p["source_contract"]["fred_macro_forbidden"] is True
    assert p["safety"]["ORDERS"] == 0 and p["safety"]["REAL_CAPITAL"] == 0
    assert p["safety"]["ENGINE_FEED"] is False and p["safety"]["FAIL_CLOSED"] is True
    assert c["generated_before_results"] is True
    assert c["clarifications_only_no_parameter_change"] is True
    p["_sha256"] = sha256_bytes(p_raw)
    c["_sha256"] = sha256_bytes(c_raw)
    return p, c


def load_canonical_module():
    spec = importlib.util.spec_from_file_location("delta_canonical_for_regime_c2", CANONICAL)
    if spec is None or spec.loader is None:
        raise RuntimeError("REGIME_C2_CANONICAL_IMPORT_FAIL")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_inputs() -> pd.DataFrame:
    cfg = json.loads(DELTA_CFG.read_text(encoding="utf-8"))
    dates = pd.date_range("2025-10-01", "2026-08-09", freq="D")
    rng = np.random.default_rng(20260909)
    cycle = np.sin(np.linspace(0, 10 * np.pi, len(dates)))
    shock = np.zeros(len(dates))
    shock[[65, 142, 219, 276]] = [-0.09, -0.07, -0.11, -0.08]
    market = 0.0003 + 0.0045 * cycle + shock + rng.normal(0, 0.011, len(dates))
    rows: list[dict[str, Any]] = []
    for i, sym in enumerate(cfg["universe"]):
        beta = 0.55 + 0.035 * (i % 10)
        regime_loading = 0.004 * np.sin(np.linspace(0, (6 + i % 3) * np.pi, len(dates)))
        idio = rng.normal(0, 0.009 + 0.00035 * (i % 6), len(dates))
        rets = beta * market + regime_loading + idio
        px = 100.0 * np.exp(np.cumsum(rets))
        for d, close in zip(dates, px):
            rows.append({"date": d, "symbol": sym, "close": float(close), "source": "fixture"})
    return pd.DataFrame(rows)


def public_crypto(prereg: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    mod = load_canonical_module()
    cfg = json.loads(DELTA_CFG.read_text(encoding="utf-8"))
    start = pd.Timestamp(cfg["warmup_start"])
    end = pd.Timestamp(prereg["historical_cutoff_exclusive"]) - pd.Timedelta(days=1)
    session = requests.Session()
    session.headers.update({"User-Agent": "GATE-BTC-Factory-Regime-C2/1.0"})
    frames: list[pd.DataFrame] = []
    failures: list[dict[str, str]] = []
    quality: list[dict[str, Any]] = []
    for sym in cfg["universe"]:
        try:
            frame = mod.fetch_okx_candles(session, sym, start, end)
            x = frame[["date", "symbol", "close"]].copy()
            if x.duplicated(["date", "symbol"]).any():
                raise RuntimeError("duplicate date-symbol")
            frames.append(x)
            quality.append({"symbol": sym, "rows": int(len(x)), "start": str(x["date"].min()), "end": str(x["date"].max())})
        except Exception as exc:
            failures.append({"symbol": sym, "error": str(exc)})
    if len(frames) < int(prereg["minimum_loaded_assets"]):
        raise RuntimeError(f"REGIME_C2_SOURCE_MIN_ASSETS_FAIL loaded={len(frames)} failures={failures}")
    out = pd.concat(frames, ignore_index=True)
    manifest = {
        "source": "canonical_delta_okx_fetch_okx_candles_only",
        "start": str(start.date()),
        "end": str(end.date()),
        "loaded_assets": len(frames),
        "quality": quality,
        "failures": failures,
        "funding_called": False,
        "fred_called": False,
    }
    return out, manifest


def panelize(raw: pd.DataFrame, prereg: dict[str, Any]) -> pd.DataFrame:
    x = raw.copy()
    x["date"] = pd.to_datetime(x["date"], errors="raise").dt.normalize()
    x = x[x["date"] < pd.Timestamp(prereg["historical_cutoff_exclusive"])]
    x = x.sort_values(["date", "symbol"])
    if x.duplicated(["date", "symbol"]).any():
        raise RuntimeError("REGIME_C2_DUPLICATE_DATE_SYMBOL")
    p = x.pivot(index="date", columns="symbol", values="close").sort_index()
    if "BTC" not in p.columns or p.shape[1] < int(prereg["minimum_loaded_assets"]):
        raise RuntimeError("REGIME_C2_INSUFFICIENT_UNIVERSE")
    if (p <= 0).any().any():
        raise RuntimeError("REGIME_C2_NONPOSITIVE_PRICE")
    return p


def max_drawdown(r: pd.Series) -> float:
    nav = (1.0 + r.fillna(0.0)).cumprod()
    if nav.empty:
        return 0.0
    return float((nav / nav.cummax() - 1.0).min())


def metrics(r: pd.Series) -> dict[str, float]:
    r = r.dropna()
    n = int(len(r))
    total = float((1.0 + r).prod() - 1.0) if n else 0.0
    vol = float(r.std(ddof=1)) if n > 1 else 0.0
    sharpe = float(r.mean() / vol * math.sqrt(365.0)) if vol > 0 else 0.0
    return {"n": n, "total_return": total, "sharpe": sharpe, "max_drawdown": max_drawdown(r) if n else 0.0}


def mean_pairwise_corr(ret: pd.DataFrame, window: int) -> pd.Series:
    cols = list(ret.columns)
    pair_series = [ret[a].rolling(window, min_periods=window).corr(ret[b]) for a, b in itertools.combinations(cols, 2)]
    if not pair_series:
        return pd.Series(index=ret.index, dtype=float)
    return pd.concat(pair_series, axis=1).mean(axis=1, skipna=True)


def family_state(prices: pd.DataFrame, family: str, cfg: dict[str, Any]) -> pd.Series:
    ret = prices.pct_change(fill_method=None)
    alts = [c for c in prices.columns if c != "BTC"]
    btc = prices["BTC"]

    if family == "REGIME_C2_CORRELATION_STRUCTURE":
        corr = mean_pairwise_corr(ret[alts], int(cfg["corr_window"]))
        q = corr.shift(1).rolling(int(cfg["quantile_window"]), min_periods=max(20, int(cfg["quantile_window"]) // 2)).quantile(float(cfg["corr_quantile"]))
        trend = btc.pct_change(int(cfg["btc_trend_window"]), fill_method=None)
        return ((trend > 0.0) & (corr <= q)).astype(float)

    if family == "REGIME_C2_RELATIVE_STRENGTH_BREADTH":
        w = int(cfg["return_window"])
        rr = prices.pct_change(w, fill_method=None)
        alt_rr = rr[alts]
        available = alt_rr.notna().sum(axis=1)
        outperform = alt_rr.gt(rr["BTC"], axis=0).sum(axis=1)
        breadth = outperform / available.replace(0, np.nan)
        return (breadth >= float(cfg["breadth_threshold"])).astype(float)

    if family == "REGIME_C2_DOWNSIDE_PARTICIPATION":
        w = int(cfg["participation_window"])
        alt_ret = ret[alts]
        available = alt_ret.notna().sum(axis=1)
        frac_negative = alt_ret.lt(0).sum(axis=1) / available.replace(0, np.nan)
        btc_down = ret["BTC"].lt(0)
        down_count = btc_down.astype(float).rolling(w, min_periods=1).sum()
        down_sum = frac_negative.where(btc_down).rolling(w, min_periods=1).sum()
        participation = down_sum / down_count.replace(0, np.nan)
        trend = btc.pct_change(int(cfg["btc_trend_window"]), fill_method=None)
        enough = down_count >= int(cfg["minimum_btc_down_observations"])
        return (enough & (participation <= float(cfg["participation_threshold"])) & (trend > 0.0)).astype(float)

    if family == "REGIME_C2_SHOCK_RECOVERY":
        shock_ret = btc.pct_change(int(cfg["shock_window"]), fill_method=None)
        alt_recovery = prices[alts].pct_change(int(cfg["recovery_window"]), fill_method=None).mean(axis=1, skipna=True)
        state = 0.0
        out: list[float] = []
        for sret, aret in zip(shock_ret, alt_recovery):
            if pd.notna(sret) and float(sret) <= float(cfg["shock_threshold"]):
                state = 0.0
            elif state == 0.0 and pd.notna(aret) and float(aret) >= float(cfg["recovery_threshold"]):
                state = 1.0
            out.append(state)
        return pd.Series(out, index=prices.index, dtype=float)

    raise ValueError(f"unknown family {family}")


def strategy_returns(prices: pd.DataFrame, state: pd.Series, switch_cost_bps: float) -> pd.Series:
    ret = prices.pct_change(fill_method=None)
    alt = ret.drop(columns=["BTC"], errors="ignore").mean(axis=1, skipna=True)
    defensive = 0.50 * ret["BTC"].fillna(0.0)
    applied = state.shift(1)
    gross = applied * alt + (1.0 - applied) * defensive
    switches = applied.diff().abs().fillna(0.0)
    return gross - switches * (switch_cost_bps / 10000.0)


def passes(m: dict[str, float], gates: dict[str, Any]) -> bool:
    return bool(
        m["n"] >= int(gates["min_observations_each_block"])
        and m["total_return"] > 0.0
        and m["sharpe"] >= float(gates["min_sharpe"])
        and m["max_drawdown"] >= float(gates["max_drawdown_floor"])
    )


def evaluate(prices: pd.DataFrame, prereg: dict[str, Any]) -> dict[str, Any]:
    disc_end = pd.Timestamp(prereg["discovery_end_inclusive"])
    rep_start = pd.Timestamp(prereg["replication_start_inclusive"])
    gates = prereg["gates"]
    cost = float(prereg["economic_mapping"]["switch_cost_bps"])
    result: dict[str, Any] = {
        "schema": "qrds.factory.regime_c2_result.v1",
        "families": {},
        "all_passers": [],
        "survivors_to_freeze": [],
        "predecessor_result_credit": 0,
        "h1_economics_read": False,
        "partial_prospective_economics_read": False,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
    }
    survivor_rows: list[dict[str, Any]] = []
    for fam, spec in prereg["families"].items():
        variants = [("central", spec["central"])] + [(f"neighbor_{i+1}", x) for i, x in enumerate(spec["neighbors"])]
        rows: list[dict[str, Any]] = []
        central_disc = False
        central_rep = False
        neighbor_disc = False
        passing_variants = 0
        central_rep_sharpe = float("-inf")
        for label, vcfg in variants:
            state = family_state(prices, fam, vcfg)
            rr = strategy_returns(prices, state, cost)
            dm = metrics(rr[rr.index <= disc_end])
            rm = metrics(rr[rr.index >= rep_start])
            dp = passes(dm, gates)
            rp = passes(rm, gates)
            passing_variants += int(dp and rp)
            if label == "central":
                central_disc = dp
                central_rep = rp
                central_rep_sharpe = rm["sharpe"]
            else:
                neighbor_disc = neighbor_disc or dp
            rows.append({"variant": label, "config": vcfg, "discovery": dm, "replication": rm, "discovery_pass": dp, "replication_pass": rp})
        survivor = central_disc and neighbor_disc and central_rep
        state_name = "SURVIVOR_REPLICATED" if survivor else ("REJECTED_FAILED_REPLICATION" if central_disc and neighbor_disc else "REJECTED_DISCOVERY")
        if survivor:
            result["all_passers"].append(fam)
            survivor_rows.append({"family": fam, "passing_variants": passing_variants, "central_replication_sharpe": central_rep_sharpe})
        result["families"][fam] = {"state": state_name, "variants": rows}

    survivor_rows.sort(key=lambda x: (-x["passing_variants"], -x["central_replication_sharpe"], x["family"]))
    cap = int(gates["max_survivors_to_freeze"])
    result["survivors_to_freeze"] = [x["family"] for x in survivor_rows[:cap]]
    result["status"] = "SURVIVORS_READY_FOR_FREEZE" if result["survivors_to_freeze"] else "CLOSED_NULL"
    result["comparison_capital_brl"] = int(prereg["capital_comparison_brl"])
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fixture", "public"], default="fixture")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    prereg, clarify = load_contract()
    if args.mode == "fixture":
        raw = fixture_inputs()
        source_manifest = {"source": "fixture", "funding_called": False, "fred_called": False}
    else:
        raw, source_manifest = public_crypto(prereg)

    prices = panelize(raw, prereg)
    result = evaluate(prices, prereg)
    result["mode"] = args.mode
    result["source_manifest"] = source_manifest
    result["prereg_sha256"] = prereg["_sha256"]
    result["clarification_sha256"] = clarify["_sha256"]
    result["research_only"] = True
    result["shadow_only"] = True
    result["not_approved"] = True

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"mode": args.mode, "status": result["status"], "all_passers": result["all_passers"], "survivors_to_freeze": result["survivors_to_freeze"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
