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
PREREG = ROOT / "tools" / "gate_btc_factory_delta_c2_prereg.json"
CANONICAL = ROOT / "migration" / "canonical" / "delta" / "scripts" / "00_run_delta_v11.py"


def load_prereg() -> dict[str, Any]:
    p = json.loads(PREREG.read_text(encoding="utf-8"))
    assert p["generated_before_results"] is True
    assert p["lineage"]["predecessor_result_credit"] == 0
    s = p["safety"]
    assert s["ORDERS"] == 0 and s["REAL_CAPITAL"] == 0
    assert s["ENGINE_FEED"] is False and s["NO_BACKFILL"] is True
    assert s["NO_RETUNE"] is True and s["FAIL_CLOSED"] is True
    return p


def load_canonical_module():
    spec = importlib.util.spec_from_file_location("delta_canonical_for_factory_c2", CANONICAL)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import canonical Delta collector")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = json.loads((ROOT / "migration" / "canonical" / "delta" / "config_delta_v11.json").read_text(encoding="utf-8"))
    dates = pd.date_range("2025-10-01", "2026-08-09", freq="D")
    rng = np.random.default_rng(20260909)
    market = rng.normal(0.0002, 0.018, len(dates))
    ohlc_rows: list[dict[str, Any]] = []
    funding_rows: list[dict[str, Any]] = []
    for i, sym in enumerate(cfg["universe"]):
        idio = rng.normal(0, 0.011 + i * 0.00025, len(dates))
        drift = (i - len(cfg["universe"]) / 2) * 0.000012
        rets = market * (0.72 + 0.025 * (i % 6)) + idio + drift
        px = 100 * np.exp(np.cumsum(rets))
        vol_noise = rng.lognormal(mean=0.0, sigma=0.35, size=len(dates))
        volume = (1_000_000 + 120_000 * i) * vol_noise * (1.0 + np.abs(rets) * 8.0)
        fund_base = 0.00002 * np.tanh(pd.Series(rets).rolling(7, min_periods=1).mean().to_numpy() * 100)
        for j, (d, close, vv) in enumerate(zip(dates, px, volume)):
            ohlc_rows.append({"date": d, "symbol": sym, "close": float(close), "volume": float(vv)})
            for hour in (0, 8, 16):
                ts = pd.Timestamp(d).tz_localize("UTC") + pd.Timedelta(hours=hour)
                fr = float(fund_base[j] + rng.normal(0, 0.00001))
                funding_rows.append({"date": d, "symbol": sym, "funding_rate": fr, "funding_time_utc": ts.isoformat()})
    return pd.DataFrame(ohlc_rows), pd.DataFrame(funding_rows)


def public_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    mod = load_canonical_module()
    ohlc, funding, quality, failures = mod.collect_public_data()
    if int((quality["ohlc_rows"] > 0).sum()) < 12:
        raise RuntimeError("DELTA_C2_SOURCE_MIN_ASSETS_FAIL")
    if int((quality["funding_events"] > 0).sum()) < 12:
        raise RuntimeError("DELTA_C2_FUNDING_MIN_ASSETS_FAIL")
    if not failures.empty:
        material = failures[failures["layer"].isin(["ohlc", "funding"])]
        failed_assets = set(material["symbol"].astype(str))
        good_ohlc = set(quality.loc[quality["ohlc_rows"] > 0, "symbol"].astype(str))
        good_funding = set(quality.loc[quality["funding_events"] > 0, "symbol"].astype(str))
        if len(good_ohlc & good_funding) < 12 or len(failed_assets) >= len(quality) - 11:
            raise RuntimeError("DELTA_C2_MATERIAL_SOURCE_FAILURE")
    cols = ["date", "symbol", "close", "volume"]
    return ohlc[cols].copy(), funding[["date", "symbol", "funding_rate", "funding_time_utc"]].copy()


def validate_and_panelize(
    ohlc: pd.DataFrame, funding: pd.DataFrame, cutoff: str
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    x = ohlc.copy()
    x["date"] = pd.to_datetime(x["date"]).dt.normalize()
    x = x[x["date"] < pd.Timestamp(cutoff)].sort_values(["date", "symbol"])
    if x.duplicated(["date", "symbol"]).any():
        raise RuntimeError("DELTA_C2_DUPLICATE_OHLC_DATE_SYMBOL")
    if (x["volume"] <= 0).any() or x[["close", "volume"]].isna().any().any():
        raise RuntimeError("DELTA_C2_INVALID_OHLC_OR_VOLUME")

    f = funding.copy()
    f["funding_time_utc"] = pd.to_datetime(f["funding_time_utc"], utc=True, errors="coerce")
    if f["funding_time_utc"].isna().any():
        raise RuntimeError("DELTA_C2_INVALID_FUNDING_TIMESTAMP")
    f["date"] = f["funding_time_utc"].dt.tz_convert(None).dt.normalize()
    f = f[f["date"] < pd.Timestamp(cutoff)].sort_values(["funding_time_utc", "symbol"])
    if f.duplicated(["funding_time_utc", "symbol"]).any():
        raise RuntimeError("DELTA_C2_DUPLICATE_FUNDING_EVENT")
    if f["funding_rate"].isna().any():
        raise RuntimeError("DELTA_C2_INVALID_FUNDING_RATE")

    prices = x.pivot(index="date", columns="symbol", values="close").sort_index()
    volumes = x.pivot(index="date", columns="symbol", values="volume").sort_index()
    if "BTC" not in prices.columns or prices.shape[1] < 12:
        raise RuntimeError("DELTA_C2_INSUFFICIENT_UNIVERSE")
    if set(prices.columns) != set(volumes.columns):
        raise RuntimeError("DELTA_C2_PRICE_VOLUME_IDENTITY_MISMATCH")

    # Funding is aggregated by the exact UTC event date. No interpolation or forward fill.
    funding_daily = f.groupby(["date", "symbol"], as_index=False)["funding_rate"].sum().pivot(
        index="date", columns="symbol", values="funding_rate"
    ).sort_index()
    funding_daily = funding_daily.reindex(index=prices.index, columns=prices.columns)
    return prices, volumes, funding_daily


def cross_z(s: pd.Series) -> pd.Series:
    x = s.astype(float).replace([np.inf, -np.inf], np.nan)
    mu = x.mean(skipna=True)
    sd = x.std(skipna=True, ddof=0)
    if not np.isfinite(sd) or sd <= 0:
        return pd.Series(np.nan, index=s.index, dtype=float)
    return (x - mu) / sd


def feature_frames(
    prices: pd.DataFrame, volumes: pd.DataFrame, funding_daily: pd.DataFrame, cfg: dict[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    lb = int(cfg.get("price_lookback", 14))
    mom = prices.pct_change(lb)
    fund_days = int(cfg.get("funding_days", 7))
    # min_periods=1 does not invent events: NaN days contribute zero to the sum only
    # after at least one actual funding observation exists in the trailing window.
    event_seen = funding_daily.notna().rolling(fund_days, min_periods=1).sum()
    fund = funding_daily.fillna(0.0).rolling(fund_days, min_periods=1).sum().where(event_seen > 0)
    short = int(cfg.get("volume_short_days", 7))
    long = int(cfg.get("volume_long_days", 30))
    short_mean = volumes.rolling(short, min_periods=short).mean()
    long_mean = volumes.rolling(long, min_periods=long).mean()
    vol_ratio = (short_mean / long_mean).where((short_mean > 0) & (long_mean > 0))
    return mom, fund, np.log(vol_ratio)


def score_for_date(
    family: str,
    cfg: dict[str, Any],
    d: pd.Timestamp,
    prices: pd.DataFrame,
    volumes: pd.DataFrame,
    funding_daily: pd.DataFrame,
) -> tuple[pd.Series, dict[str, pd.Series]]:
    mom, fund, log_vr = feature_frames(prices, volumes, funding_daily, cfg)
    pz = cross_z(mom.loc[d])
    fz = cross_z(fund.loc[d])
    vz = cross_z(log_vr.loc[d])
    if family == "DELTA_C2_FUNDING_DIVERGENCE":
        score = pz - float(cfg["funding_weight"]) * fz
    elif family == "DELTA_C2_VOLUME_CONFIRMATION":
        score = pz + float(cfg["volume_weight"]) * vz
    elif family == "DELTA_C2_PRICE_VOLUME_DIVERGENCE":
        disagree = np.sign(pz) != np.sign(vz)
        score = pz.where(~disagree, pz - float(cfg["divergence_penalty"]) * vz.abs())
    elif family == "DELTA_C2_FUNDING_VOLUME_CONSENSUS":
        score = pz - float(cfg["funding_weight"]) * fz + float(cfg["volume_weight"]) * vz
    elif family == "DELTA_C2_FUNDING_EXTREMES":
        score = pz
    else:
        raise RuntimeError(f"unknown family {family}")
    return score, {"price_z": pz, "funding_z": fz, "volume_z": vz, "funding_raw": fund.loc[d]}


def equal_side_weights(score: pd.Series, top_n: int, bottom_n: int) -> pd.Series:
    s = score.drop(labels=["BTC"], errors="ignore").dropna()
    if len(s) < top_n + bottom_n:
        return pd.Series(dtype=float)
    top = s.nlargest(top_n).index
    bot = s.nsmallest(bottom_n).index
    w = pd.Series(0.0, index=score.index)
    w.loc[top] = 0.70 / len(top)
    w.loc[bot] = -0.30 / len(bot)
    return w


def funding_extreme_weights(
    score: pd.Series, funding_raw: pd.Series, q: float, top_n: int, bottom_n: int
) -> pd.Series:
    base = score.drop(labels=["BTC"], errors="ignore").dropna()
    fr = funding_raw.reindex(base.index).dropna()
    base = base.reindex(fr.index).dropna()
    if len(base) < top_n + bottom_n:
        return pd.Series(dtype=float)
    lo = float(fr.quantile(q))
    hi = float(fr.quantile(1.0 - q))
    long_pool = base[fr <= hi]
    short_pool = base[fr >= lo]
    if len(long_pool) < top_n or len(short_pool) < bottom_n:
        return pd.Series(dtype=float)
    top = long_pool.nlargest(top_n).index
    bot = short_pool.nsmallest(bottom_n).index
    if set(top) & set(bot):
        return pd.Series(dtype=float)
    w = pd.Series(0.0, index=score.index)
    w.loc[top] = 0.70 / len(top)
    w.loc[bot] = -0.30 / len(bot)
    return w


def run_variant(
    prices: pd.DataFrame,
    volumes: pd.DataFrame,
    funding_daily: pd.DataFrame,
    family: str,
    cfg: dict[str, Any],
    prereg: dict[str, Any],
) -> tuple[pd.Series, pd.DataFrame]:
    ret = prices.pct_change()
    fee = float(prereg["execution"]["fee_bps_per_turnover_unit"]) / 10000.0
    reb = int(prereg["execution"]["rebalance_days"])
    top_n = int(prereg["execution"]["top_n"])
    bottom_n = int(prereg["execution"]["bottom_n"])
    held = pd.Series(0.0, index=prices.columns)
    out: list[float] = []
    audit: list[dict[str, Any]] = []

    for i, d in enumerate(prices.index):
        # Today's close-to-close return is earned only by weights already held before today's close.
        day_ret = ret.loc[d].fillna(0.0) if i > 0 else pd.Series(0.0, index=prices.columns)
        pnl = float((held * day_ret).sum())
        next_weights = held.copy()
        turnover = 0.0
        if i % reb == 0:
            score, feats = score_for_date(family, cfg, d, prices.loc[:d], volumes.loc[:d], funding_daily.loc[:d])
            if family == "DELTA_C2_FUNDING_EXTREMES":
                next_weights = funding_extreme_weights(
                    score, feats["funding_raw"], float(cfg["exclusion_quantile"]), top_n, bottom_n
                )
            else:
                next_weights = equal_side_weights(score, top_n, bottom_n)
            if next_weights.empty:
                next_weights = pd.Series(0.0, index=prices.columns)
            next_weights = next_weights.reindex(prices.columns, fill_value=0.0)
            turnover = float((next_weights - held).abs().sum())
            pnl -= fee * turnover
        out.append(pnl)
        audit.append({"date": str(pd.Timestamp(d).date()), "turnover": turnover, "gross_long_next": float(next_weights.clip(lower=0).sum()), "gross_short_next": float(-next_weights.clip(upper=0).sum())})
        held = next_weights
    return pd.Series(out, index=prices.index, name=family), pd.DataFrame(audit)


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


def passes(m: dict[str, float], gates: dict[str, Any]) -> bool:
    return bool(
        m["n"] >= int(gates["min_observations_each_block"])
        and m["total_return"] > 0
        and m["sharpe"] >= float(gates["min_sharpe"])
        and m["max_drawdown"] >= float(gates["max_drawdown_floor"])
    )


def evaluate(
    prices: pd.DataFrame, volumes: pd.DataFrame, funding_daily: pd.DataFrame, prereg: dict[str, Any]
) -> dict[str, Any]:
    disc_end = pd.Timestamp(prereg["discovery_end_inclusive"])
    rep_start = pd.Timestamp(prereg["replication_start_inclusive"])
    gates = prereg["gates"]
    result: dict[str, Any] = {
        "schema": "qrds.factory.delta_c2_result.v1",
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
    ranked: list[tuple[str, int, float]] = []
    for fam, spec in prereg["families"].items():
        variants = [("central", spec["central"])] + [(f"neighbor_{i+1}", x) for i, x in enumerate(spec["neighbors"])]
        rows = []
        central_rep_pass = False
        central_rep_sharpe = float("-inf")
        central_disc_pass = False
        discovery_neighbor_pass = False
        passing_variants = 0
        for label, cfg in variants:
            rr, _audit = run_variant(prices, volumes, funding_daily, fam, cfg, prereg)
            dm = metrics(rr[rr.index <= disc_end])
            rm = metrics(rr[rr.index >= rep_start])
            dp, rp = passes(dm, gates), passes(rm, gates)
            if dp and rp:
                passing_variants += 1
            if label == "central":
                central_disc_pass = dp
                central_rep_pass = rp
                central_rep_sharpe = rm["sharpe"]
            else:
                discovery_neighbor_pass = discovery_neighbor_pass or dp
            rows.append({"variant": label, "config": cfg, "discovery": dm, "replication": rm, "discovery_pass": dp, "replication_pass": rp})
        survivor = central_disc_pass and discovery_neighbor_pass and central_rep_pass
        state = "SURVIVOR_REPLICATED" if survivor else ("REJECTED_FAILED_REPLICATION" if central_disc_pass and discovery_neighbor_pass else "REJECTED_DISCOVERY")
        result["families"][fam] = {"state": state, "variants": rows, "passing_predeclared_variant_count": passing_variants}
        if survivor:
            result["all_passers"].append(fam)
            ranked.append((fam, passing_variants, central_rep_sharpe))
    ranked.sort(key=lambda x: (-x[1], -x[2], x[0]))
    cap = int(gates["max_survivors_to_freeze"])
    result["survivors_to_freeze"] = [x[0] for x in ranked[:cap]]
    result["status"] = "SURVIVORS_READY_FOR_FREEZE" if result["survivors_to_freeze"] else "CLOSED_NULL"
    result["comparison_capital_brl"] = int(prereg["capital_comparison_brl"])
    return result


def source_sha(ohlc: pd.DataFrame, funding: pd.DataFrame) -> str:
    h = hashlib.sha256()
    h.update(ohlc.sort_values(["date", "symbol"]).to_csv(index=False).encode())
    h.update(funding.sort_values(["funding_time_utc", "symbol"]).to_csv(index=False).encode())
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fixture", "public"], default="fixture")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    prereg = load_prereg()
    raw_ohlc, raw_funding = fixture_data() if args.mode == "fixture" else public_data()
    prices, volumes, funding_daily = validate_and_panelize(raw_ohlc, raw_funding, prereg["historical_cutoff_exclusive"])
    result = evaluate(prices, volumes, funding_daily, prereg)
    result["mode"] = args.mode
    result["source_ohlc_rows"] = int(len(raw_ohlc))
    result["source_funding_events"] = int(len(raw_funding))
    result["source_sha256"] = source_sha(raw_ohlc, raw_funding)
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "all_passers": result["all_passers"], "survivors_to_freeze": result["survivors_to_freeze"], "mode": args.mode}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
