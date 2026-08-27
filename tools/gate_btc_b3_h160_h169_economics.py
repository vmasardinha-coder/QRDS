#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import gate_btc_b3_h30_h39_cross_asset as b3
import gate_btc_b3_h160_h169_nyfed_source_qa as src

FAMS = tuple(f"H{i}" for i in range(160, 170))
ASSETS = ("WIN", "WDO")
HOLDS = (60, 120)
CUTOFF = "2026-08-10"
GEN = "H160_H169_V1"
LEVEL_WINDOW = 60
CHANGE_WINDOW = 20
COVERAGE_MIN = 0.90

SERIES_COLS = {
    "SOFR": ("percentRate", "volumeInBillions", "percentPercentile1", "percentPercentile99"),
    "BGCR": ("percentRate",),
    "TGCR": ("percentRate",),
    "EFFR": ("percentRate", "volumeInBillions", "percentPercentile1", "percentPercentile99"),
    "OBFR": ("percentRate",),
}

FAMILY_INPUTS = {
    "H160": ("z_h160",),
    "H161": ("z_h161",),
    "H162": ("z_h162",),
    "H163": ("z_h163",),
    "H164": ("z_h164",),
    "H165": ("z_h165",),
    "H166": ("z_h166",),
    "H167": ("z_h167",),
    "H168": ("z_h160", "z_h161", "z_h162"),
    "H169": ("z_h160", "z_h161", "z_h162", "z_h163", "z_h164"),
}


def finite(x: object) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def sgn(x: float) -> int:
    return 1 if x > 0 else -1 if x < 0 else 0


def _rolling_mad(values: np.ndarray) -> float:
    med = float(np.median(values))
    return float(np.median(np.abs(values - med)))


def robust_level_z(series: pd.Series, window: int = LEVEL_WINDOW) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    prior = s.shift(1)
    center = prior.rolling(window, min_periods=window).median()
    scale = prior.rolling(window, min_periods=window).apply(_rolling_mad, raw=True).replace(0, np.nan)
    return (s - center) / scale


def abs_change_z(series: pd.Series, window: int = CHANGE_WINDOW, log_change: bool = False) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if log_change:
        s = s.where(s > 0)
        change = np.log(s).diff()
    else:
        change = s.diff()
    scale = change.abs().shift(1).rolling(window, min_periods=window).median().replace(0, np.nan)
    return change / scale


def nyfed_frame() -> tuple[pd.DataFrame, dict]:
    pieces = []
    evidence = {}
    for name, (group, slug) in src.SERIES.items():
        meta = src.fetch_one(name, group, slug)
        qa = src.qa_series(name, meta)
        failures = []
        if qa["missing_required_schema_fields"] or qa["duplicate_effective_dates"]:
            failures.append("schema_or_dupes")
        if any(qa["block_counts"][b] < 200 for b in src.BLOCKS):
            failures.append("coverage")
        if qa["missing_required_values"].get("percentRate", 0) or qa["missing_required_values"].get("volumeInBillions", 0):
            failures.append("rate_or_volume_missing")
        if failures:
            raise RuntimeError(f"SOURCE_QA_NOT_READY:{name}:{','.join(failures)}")
        evidence[name] = qa
        rows = pd.DataFrame(meta["rows"])
        rows["date"] = pd.to_datetime(rows["effectiveDate"], errors="raise").dt.normalize()
        if rows["date"].duplicated().any():
            raise RuntimeError(f"DUPLICATE_SOURCE_DATE:{name}")
        keep = ["date"]
        rename = {}
        for col in SERIES_COLS[name]:
            if col not in rows.columns:
                raise RuntimeError(f"MISSING_SOURCE_FIELD:{name}:{col}")
            rows[col] = pd.to_numeric(rows[col], errors="coerce")
            keep.append(col)
            rename[col] = f"{name.lower()}_{col}"
        pieces.append(rows[keep].rename(columns=rename))

    f = pieces[0]
    for x in pieces[1:]:
        f = f.merge(x, on="date", how="outer", validate="one_to_one")
    f = f[f["date"] < pd.Timestamp(CUTOFF)].sort_values("date").reset_index(drop=True)

    f["h160"] = f["sofr_percentRate"] - f["effr_percentRate"]
    f["h161"] = f["bgcr_percentRate"] - f["tgcr_percentRate"]
    f["h162"] = f["obfr_percentRate"] - f["effr_percentRate"]
    f["z_h160"] = robust_level_z(f["h160"])
    f["z_h161"] = robust_level_z(f["h161"])
    f["z_h162"] = robust_level_z(f["h162"])

    f["z_h163"] = abs_change_z(f["sofr_volumeInBillions"])
    f["z_h164"] = abs_change_z(f["effr_volumeInBillions"])

    f["sofr_width"] = f["sofr_percentPercentile99"] - f["sofr_percentPercentile1"]
    f["effr_width"] = f["effr_percentPercentile99"] - f["effr_percentPercentile1"]
    f["z_h165"] = abs_change_z(f["sofr_width"])
    f["z_h166"] = abs_change_z(f["effr_width"])

    ratio = f["sofr_volumeInBillions"] / f["effr_volumeInBillions"].replace(0, np.nan)
    f["volume_ratio"] = ratio
    f["z_h167"] = abs_change_z(ratio, log_change=True)
    return f, evidence


def causal_join(feat: pd.DataFrame, sessions) -> tuple[dict, dict]:
    ordered = sorted(sessions)
    dates = feat["date"].to_numpy(dtype="datetime64[ns]")
    joined = {}
    source_dates = {}
    for i in range(1, len(ordered)):
        signal = ordered[i]
        prior_b3 = pd.Timestamp(ordered[i - 1]).normalize()
        pos = int(np.searchsorted(dates, np.datetime64(prior_b3), side="left")) - 1
        if pos < 0:
            continue
        row = feat.iloc[pos]
        if not (row["date"] < prior_b3):
            raise RuntimeError("CAUSAL_JOIN_NOT_STRICT_PRIOR")
        joined[signal] = row
        source_dates[signal] = row["date"].date().isoformat()
    return joined, source_dates


def coverage_gate(feat: pd.DataFrame, sessions, sample_name: str) -> tuple[dict, dict]:
    ordered = sorted(sessions)
    joined, source_dates = causal_join(feat, ordered)
    eligible = max(0, len(ordered) - 1)
    family = {}
    failed = []
    for fam, cols in FAMILY_INPUTS.items():
        valid = 0
        for s in ordered[1:]:
            row = joined.get(s)
            if row is not None and all(finite(row.get(c)) for c in cols):
                valid += 1
        cov = valid / eligible if eligible else 0.0
        family[fam] = {
            "eligible_sessions": eligible,
            "finite_causal_sessions": valid,
            "coverage": cov,
            "required_inputs": list(cols),
            "strict_source_date_before_prior_b3_session": True,
        }
        if cov < COVERAGE_MIN:
            failed.append(fam)
    if failed:
        raise RuntimeError(f"CAUSAL_COVERAGE_FAIL:{sample_name}:{','.join(failed)}")
    return family, source_dates


def emit(rows, fam, session, g, asset, side, param, bar, i=-1, window=None):
    suffix = f"|w{window}" if window else ""
    for h in HOLDS:
        b3.add(rows, fam, session, g, asset, int(side), i, h, f"{param}{suffix}", bar)


def residuals_h169(ss: dict, join: dict, asset: str, windows=(60, 120)) -> dict:
    ordered = sorted(ss)
    hist = []
    out = {}
    for i in range(1, len(ordered)):
        signal = ordered[i]
        target = ordered[i - 1]
        row = join.get(target)
        g = ss[target]
        if row is None or g.empty:
            continue
        x = np.array([row.get("z_h160"), row.get("z_h161"), row.get("z_h162"), row.get("z_h163"), row.get("z_h164")], dtype=float)
        y = (float(g.iloc[-1][f"close_{asset}"]) / float(g.iloc[0][f"open_{asset}"]) - 1.0) * 1e4
        if not np.isfinite(x).all() or not finite(y):
            continue
        for w in windows:
            prior = hist[-w:]
            if len(prior) != w:
                continue
            X = np.array([r["x"] for r in prior], dtype=float)
            Y = np.array([r["y"] for r in prior], dtype=float)
            if not np.isfinite(X).all() or not np.isfinite(Y).all():
                continue
            A = np.c_[np.ones(w), X]
            beta = np.linalg.lstsq(A, Y, rcond=None)[0]
            fitted_resid = Y - A @ beta
            sd = float(np.std(fitted_resid, ddof=0))
            if sd <= 0 or not finite(sd):
                continue
            target_resid = float(y - np.r_[1.0, x] @ beta)
            out[(signal, w)] = target_resid / sd
        hist.append({"x": x, "y": float(y)})
    return out


def gen(ss: dict, bar: int, feat: pd.DataFrame) -> pd.DataFrame:
    rows = []
    join, _source_dates = causal_join(feat, ss.keys())
    resids = {a: residuals_h169(ss, join, a) for a in ASSETS}
    simple = {
        "H160": "z_h160", "H161": "z_h161", "H162": "z_h162",
        "H163": "z_h163", "H164": "z_h164", "H165": "z_h165",
        "H166": "z_h166", "H167": "z_h167",
    }
    for s, g in ss.items():
        row = join.get(s)
        if row is None:
            continue
        for fam, col in simple.items():
            z = row.get(col)
            if not finite(z):
                continue
            z = float(z)
            for th in (1.0, 1.5):
                if abs(z) < th:
                    continue
                stress = sgn(z)
                emit(rows, fam, s, g, "WDO", stress, f"z{th}_stress", bar)
                emit(rows, fam, s, g, "WDO", -stress, f"z{th}_inverse", bar)
                emit(rows, fam, s, g, "WIN", -stress, f"z{th}_riskoff", bar)
                emit(rows, fam, s, g, "WIN", stress, f"z{th}_inverse", bar)

        votes_raw = [row.get("z_h160"), row.get("z_h161"), row.get("z_h162")]
        if all(finite(v) for v in votes_raw):
            votes = [sgn(float(v)) if abs(float(v)) >= 1.0 else 0 for v in votes_raw]
            pos, neg = sum(v > 0 for v in votes), sum(v < 0 for v in votes)
            aligned = max(pos, neg)
            if aligned >= 2 and pos != neg:
                stress = 1 if pos > neg else -1
                for q in (2, 3):
                    if aligned >= q:
                        emit(rows, "H168", s, g, "WDO", stress, f"{q}of3_stress", bar)
                        emit(rows, "H168", s, g, "WDO", -stress, f"{q}of3_inverse", bar)
                        emit(rows, "H168", s, g, "WIN", -stress, f"{q}of3_riskoff", bar)
                        emit(rows, "H168", s, g, "WIN", stress, f"{q}of3_inverse", bar)

        n = max(2, 30 // bar)
        if len(g) > n:
            for a in ASSETS:
                move = (float(g.iloc[n - 1][f"close_{a}"]) / float(g.iloc[0][f"open_{a}"]) - 1.0) * 1e4
                move_side = sgn(move)
                if not move_side:
                    continue
                for w in (60, 120):
                    rz = resids[a].get((s, w))
                    if not finite(rz):
                        continue
                    for th in (1.5, 2.0):
                        if abs(float(rz)) >= th:
                            emit(rows, "H169", s, g, a, move_side, f"resid{th}_cont", bar, n - 1, w)
                            emit(rows, "H169", s, g, a, -move_side, f"resid{th}_meanrev", bar, n - 1, w)
    return pd.DataFrame(rows)


def summarize(t: pd.DataFrame, fam: str) -> tuple[dict, list[dict]]:
    qualified = []
    cells = []
    if t.empty:
        return {"qualified_cells": 0, "surviving_legs": [], "survives": False, "qualified": []}, cells
    qf = t[t.family == fam]
    for (asset, param, horizon), g in qf.groupby(["asset", "param", "horizon"]):
        ok, reasons, metrics = b3.metric(g, *b3.COST[asset])
        cells.append(dict(family=fam, asset=asset, param=param, horizon=int(horizon), qualified=ok, reasons="|".join(reasons), **metrics))
        if ok:
            qualified.append((asset, param, int(horizon)))
    legs = []
    for asset in ASSETS:
        q = [x for x in qualified if x[0] == asset]
        if len(q) >= 2 and (len({x[1] for x in q}) >= 2 or len({x[2] for x in q}) >= 2):
            legs.append(asset)
    return {
        "qualified_cells": len(qualified),
        "surviving_legs": legs,
        "survives": bool(legs),
        "qualified": sorted(f"{a}|{p}|{h}" for a, p, h in qualified),
    }, cells


def main(out: str, ledger: str, cells: str, manifest: str, sample_loader=None) -> None:
    sample_loader = sample_loader or b3.sample
    feat, source_evidence = nyfed_frame()
    ds, dc = sample_loader(["2024_26"], 5)
    rs, rc = sample_loader(["2020_22", "2022_24"], 15)

    discovery_coverage, _ = coverage_gate(feat, ds.keys(), "DISCOVERY")
    replication_coverage, _ = coverage_gate(feat, rs.keys(), "REPLICATION")

    D = gen(ds, 5, feat)
    R = gen(rs, 15, feat)
    discovery, replication, cell_rows = {}, {}, []
    for fam in FAMS:
        dsum, dcells = summarize(D, fam)
        rsum, rcells = summarize(R, fam)
        discovery[fam], replication[fam] = dsum, rsum
        cell_rows += [{**v, "sample": "DISCOVERY"} for v in dcells]
        cell_rows += [{**v, "sample": "REPLICATION"} for v in rcells]

    candidates = [f for f in FAMS if discovery[f]["survives"]]
    replicated = [f for f in candidates if replication[f]["survives"]]
    survivors = replicated[:2]
    states = {}
    for f in FAMS:
        if f in survivors:
            states[f] = "SURVIVOR_REPLICATED"
        elif f in replicated:
            states[f] = "REPLICATED_NOT_SELECTED_CAP2"
        elif f in candidates:
            states[f] = "REJECTED_FAILED_REPLICATION"
        else:
            states[f] = "REJECTED_DISCOVERY"

    status = "SURVIVORS_READY_FOR_SEPARATE_PROSPECTIVE" if survivors else "CLOSED_NO_H160_H169_SURVIVOR"
    result = {
        "schema": "gate_btc.b3.h160_h169.economics.v1",
        "generation": GEN,
        "status": status,
        "cutoff_exclusive": CUTOFF,
        "states": states,
        "discovery": discovery,
        "replication": replication,
        "discovery_candidates": candidates,
        "independently_replicated": replicated,
        "survivors": survivors,
        "survivor_cap": 2,
        "survivor_cap_rule": "lowest frozen family_id order among independently replicated families; no economics-based ranking",
        "causal_coverage_minimum": COVERAGE_MIN,
        "discovery_causal_coverage": discovery_coverage,
        "replication_causal_coverage": replication_coverage,
        "discovery_sync_sessions": len(ds),
        "replication_sync_sessions": len(rs),
        "discovery_median_common_bar_coverage": float(np.median(dc)) if dc else 0.0,
        "replication_median_common_bar_coverage": float(np.median(rc)) if rc else 0.0,
        "source_series_qa": {k: {"rate_raw_sha256": v["rate_raw_sha256"], "volume_raw_sha256": v["volume_raw_sha256"], "rows": v["rows"]} for k, v in source_evidence.items()},
        "h1_economics_read": False,
        "survivor_partial_economics_read": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "engine_feed": False,
        "not_approved": True,
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with Path(ledger).open("w", encoding="utf-8") as fh:
        for fam in FAMS:
            fh.write(json.dumps({
                "family": fam, "generation": GEN, "state": states[fam],
                "discovery": discovery[fam], "replication": replication[fam],
                "h1_economics_read": False, "survivor_partial_economics_read": False,
                "orders": 0, "capital": 0, "engine_feed": False, "not_approved": True,
            }, sort_keys=True) + "\n")
    pd.DataFrame(cell_rows).to_csv(cells, index=False)
    manifest_payload = {
        "schema": "qrds.b3.h160_h169.manifest.v1",
        "cutoff_exclusive": CUTOFF,
        "official_source": "Federal Reserve Bank of New York Markets Data API",
        "rate_volume_join": "exact effectiveDate only",
        "causal_lag": "signal D uses latest NY Fed effectiveDate strictly before immediately prior completed B3 session P",
        "level_standardization": "current level minus median(previous 60), divided by unscaled MAD(previous 60 around own median); full 60 required",
        "change_standardization": "prescribed change divided by median(abs(previous 20 prescribed changes)); full 20 required",
        "h169": "prior completed same-asset session return on five causally lagged states; OLS intercept; exact 60/120 prior finite rows; residual/population-residual-sd; current decision after first 30m",
        "h1_economics_read": False,
        "survivor_partial_economics_read": False,
        "orders": 0,
        "capital": 0,
        "engine_feed": False,
        "not_approved": True,
    }
    Path(manifest).write_text(json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "states": states, "survivors": survivors, "replicated": replicated}, sort_keys=True))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--cells", required=True)
    p.add_argument("--manifest", required=True)
    a = p.parse_args()
    main(a.out, a.ledger, a.cells, a.manifest)
