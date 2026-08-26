#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import gate_btc_b3_h30_h39_cross_asset as b

FAMS = tuple(f"H{i}" for i in range(130, 140))
ASSETS = ("WIN", "WDO")
HOLDS = (60, 120)
CUTOFF = "2026-08-10"
GEN = "H130_H139_V1"
EXPECTED_NODE_SHA256 = "9cf3dd950e696a9e6033c777d75298463c8e9b148dce8f29ea9e531b9619bd02"
NODE_COLS = ("nominal2Y", "nominal5Y", "nominal8Y", "real5Y", "real10Y")


def finite(x):
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def load_nodes(path: str, qa_path: str) -> tuple[pd.DataFrame, dict]:
    qa = json.loads(Path(qa_path).read_text(encoding="utf-8"))
    if qa.get("status") != "SOURCE_QA_READY_STRATIFIED":
        raise RuntimeError(f"SOURCE_QA_NOT_READY:{qa.get('status')}")
    if qa.get("derived_node_csv_sha256") != EXPECTED_NODE_SHA256:
        raise RuntimeError("FROZEN_NODE_HASH_MISMATCH")
    if qa.get("cutoff_exclusive") != CUTOFF:
        raise RuntimeError("CUTOFF_MISMATCH")
    if qa.get("economics_run") is not False or qa.get("h1_economics_read") is not False:
        raise RuntimeError("SOURCE_QA_SAFETY_MISMATCH")
    n = pd.read_csv(path)
    need = {"date", *NODE_COLS}
    if not need.issubset(n.columns):
        raise RuntimeError("NODE_SCHEMA_MISMATCH")
    n["date"] = pd.to_datetime(n["date"], errors="raise").dt.normalize()
    if n["date"].duplicated().any():
        raise RuntimeError("DUPLICATE_NODE_DATE")
    n = n[n["date"] < pd.Timestamp(CUTOFF)].sort_values("date").reset_index(drop=True)
    for c in NODE_COLS:
        n[c] = pd.to_numeric(n[c], errors="coerce")
    n["nominal_slope"] = n.nominal8Y - n.nominal2Y
    n["nominal_curve"] = 2.0 * n.nominal5Y - n.nominal2Y - n.nominal8Y
    n["real_slope"] = n.real10Y - n.real5Y
    n["breakeven_proxy"] = n.nominal5Y - n.real5Y
    raw = ["nominal_slope", "nominal_curve", "real_slope", "nominal5Y", "real5Y", "breakeven_proxy"]
    for c in raw:
        d = n[c].diff()
        scale = d.abs().shift(1).rolling(20, min_periods=15).median().replace(0, np.nan)
        n[f"d_{c}"] = d
        n[f"z_{c}"] = d / scale
    # Frozen before economics: sovereign stress index is an equal-weight mean of
    # standardized nominal5Y, real5Y, nominal-slope and cash-breakeven changes.
    zcols = ["z_nominal5Y", "z_real5Y", "z_nominal_slope", "z_breakeven_proxy"]
    n["stress_z"] = n[zcols].mean(axis=1, skipna=False)
    return n, qa


def causal_join(nodes: pd.DataFrame, sessions) -> tuple[dict, dict]:
    dates = nodes.date.to_numpy()
    joined = {}
    stale = 0
    missing = 0
    for s in sorted(sessions):
        sd = pd.Timestamp(s).normalize()
        pos = int(np.searchsorted(dates, np.datetime64(sd), side="left")) - 1
        if pos < 0:
            missing += 1
            continue
        row = nodes.iloc[pos]
        age = int((sd - row.date).days)
        if age < 1 or age > 5:
            stale += 1
            continue
        joined[s] = row
    total = len(sessions)
    return joined, {
        "eligible_sessions": total,
        "joined_sessions": len(joined),
        "coverage": len(joined) / total if total else 0.0,
        "missing_prior_source": missing,
        "stale_over_5_calendar_days": stale,
        "strict_prior_date": True,
    }


def emit(R, fam, s, g, asset, side, param, bar, i=-1, window=None):
    suffix = f"|w{window}" if window else ""
    for h in HOLDS:
        b.add(R, fam, s, g, asset, int(side), i, h, f"{param}{suffix}", bar)


def _sgn(v):
    return 1 if v > 0 else -1 if v < 0 else 0


def h139_residuals(ss, join, windows=(60, 120)):
    ordered = sorted(ss)
    hist = []
    out = {}
    for s in ordered:
        g = ss[s]
        row = join.get(s)
        if row is None or g.empty:
            continue
        y = (float(g.iloc[-1].close_WIN) / float(g.iloc[0].open_WIN) - 1.0) * 1e4
        x = np.array([row.get("z_nominal5Y"), row.get("z_real5Y"), row.get("z_nominal_slope")], dtype=float)
        for w in windows:
            prior = hist[-w:]
            if len(prior) < max(45, int(w * 0.75)):
                continue
            X = np.array([r["x"] for r in prior], dtype=float)
            Y = np.array([r["y"] for r in prior], dtype=float)
            good = np.isfinite(X).all(1) & np.isfinite(Y)
            if good.sum() < max(45, int(w * 0.75)):
                continue
            A = np.c_[np.ones(good.sum()), X[good]]
            beta = np.linalg.lstsq(A, Y[good], rcond=None)[0]
            resid_hist = Y[good] - A @ beta
            sd = float(np.std(resid_hist, ddof=0))
            if sd <= 0 or not np.isfinite(x).all():
                continue
            resid = float(y - np.r_[1.0, x] @ beta)
            out[(s, w)] = resid / sd
        hist.append({"x": x, "y": y})
    return out


def gen(ss, bar, nodes):
    join, coverage = causal_join(nodes, ss.keys())
    R = []
    residuals = h139_residuals(ss, join)
    for s, g in ss.items():
        r = join.get(s)
        if r is None:
            continue
        vals = {
            "H130": r.get("z_nominal_slope"),
            "H131": r.get("z_nominal_curve"),
            "H132": r.get("z_real_slope"),
            "H133": r.get("z_nominal5Y"),
            "H134": r.get("z_real5Y"),
            "H135": r.get("z_breakeven_proxy"),
        }
        for fam, v in vals.items():
            if not finite(v):
                continue
            v = float(v)
            for th in (1.0, 1.5):
                if abs(v) < th:
                    continue
                sg = _sgn(v)
                for a in ASSETS:
                    emit(R, fam, s, g, a, sg, f"z{th}_same", bar)
                    emit(R, fam, s, g, a, -sg, f"z{th}_inverse", bar)
        # H136 exact state mapping frozen now, pre-result: nominal-slope sign is
        # the primary state direction; real-slope sign labels the four-state cell;
        # each mapping is paired with its exact inverse.
        ns, rs = r.get("z_nominal_slope"), r.get("z_real_slope")
        if finite(ns) and finite(rs):
            ns, rs = float(ns), float(rs)
            for th in (0.75, 1.0):
                if abs(ns) >= th and abs(rs) >= th:
                    side = _sgn(ns)
                    state = f"n{_sgn(ns):+d}_r{_sgn(rs):+d}_t{th}"
                    for a in ASSETS:
                        emit(R, "H136", s, g, a, side, state + "_map", bar)
                        emit(R, "H136", s, g, a, -side, state + "_inverse", bar)
        # H137 aligned four-vote breadth. Positive aligned state is frozen as
        # stress: short WIN / long WDO; negative aligned state reverses it.
        vote_vals = [r.get("z_nominal5Y"), r.get("z_real5Y"), r.get("z_nominal_slope"), r.get("z_breakeven_proxy")]
        if all(finite(v) for v in vote_vals):
            signs = [_sgn(float(v)) if abs(float(v)) >= 1.0 else 0 for v in vote_vals]
            pos, neg = sum(v > 0 for v in signs), sum(v < 0 for v in signs)
            aligned = max(pos, neg)
            if aligned >= 3:
                stress = 1 if pos > neg else -1
                for q in (3, 4):
                    if aligned >= q:
                        win_side, wdo_side = -stress, stress
                        emit(R, "H137", s, g, "WIN", win_side, f"{q}of4_derisk", bar)
                        emit(R, "H137", s, g, "WIN", -win_side, f"{q}of4_inverse", bar)
                        emit(R, "H137", s, g, "WDO", wdo_side, f"{q}of4_defensive", bar)
                        emit(R, "H137", s, g, "WDO", -wdo_side, f"{q}of4_inverse", bar)
        # H138 persistence uses the pre-result equal-weight stress_z defined above.
        ix = int(r.name)
        if ix >= 1:
            prev = nodes.iloc[ix - 1]
            pz, cz = prev.get("stress_z"), r.get("stress_z")
            if finite(pz) and finite(cz) and _sgn(float(pz)) == _sgn(float(cz)) and _sgn(float(cz)):
                for th in (0.75, 1.0):
                    if abs(float(cz)) >= th:
                        side = _sgn(float(cz))
                        for a in ASSETS:
                            emit(R, "H138", s, g, a, side, f"persist{th}_cont", bar)
                            emit(R, "H138", s, g, a, -side, f"persist{th}_fade", bar)
        # H139: decision only after first 30 minutes; residual was computed from
        # completed-session information only. Current first-30m sign chooses
        # continuation vs mean-reversion mapping.
        n = max(2, 30 // bar)
        if len(g) > n:
            move = (float(g.iloc[n - 1].close_WIN) / float(g.iloc[0].open_WIN) - 1.0) * 1e4
            move_side = _sgn(move)
            if move_side:
                for w in (60, 120):
                    z = residuals.get((s, w))
                    if not finite(z):
                        continue
                    for th in (1.5, 2.0):
                        if abs(float(z)) >= th:
                            emit(R, "H139", s, g, "WIN", move_side, f"resid{th}_cont", bar, n - 1, w)
                            emit(R, "H139", s, g, "WIN", -move_side, f"resid{th}_meanrev", bar, n - 1, w)
    return pd.DataFrame(R), coverage


def summ(t, fam):
    qualified, cells = [], []
    if t.empty:
        return {"qualified_cells": 0, "surviving_legs": [], "survives": False, "qualified": []}, cells
    qf = t[t.family == fam]
    for (a, p, h), g in qf.groupby(["asset", "param", "horizon"]):
        ok, reasons, metrics = b.metric(g, *b.COST[a])
        cells.append(dict(family=fam, asset=a, param=p, horizon=int(h), qualified=ok, reasons="|".join(reasons), **metrics))
        if ok:
            qualified.append((a, p, int(h)))
    legs = []
    for a in ASSETS:
        z = [x for x in qualified if x[0] == a]
        if len(z) >= 2 and (len({x[1] for x in z}) >= 2 or len({x[2] for x in z}) >= 2):
            legs.append(a)
    return {
        "qualified_cells": len(qualified),
        "surviving_legs": legs,
        "survives": bool(legs),
        "qualified": sorted(f"{a}|{p}|{h}" for a, p, h in qualified),
    }, cells


def main(nodes_path, qa_path, out, ledger, cells, manifest, sample_loader=None):
    sample_loader = sample_loader or b.sample
    nodes, qa = load_nodes(nodes_path, qa_path)
    ds, dc = sample_loader(["2024_26"], 5)
    rs, rc = sample_loader(["2020_22", "2022_24"], 15)
    D, dcover = gen(ds, 5, nodes)
    R, rcover = gen(rs, 15, nodes)
    ready = dcover["coverage"] >= 0.90 and rcover["coverage"] >= 0.90
    discovery, replication, states, cell_rows = {}, {}, {}, []
    unavailable = {"qualified_cells": 0, "surviving_legs": [], "survives": False, "qualified": [], "evaluation": "NOT_RUN_DATA_GAP_COVERAGE"}
    for fam in FAMS:
        if not ready:
            discovery[fam] = dict(unavailable)
            replication[fam] = dict(unavailable)
            states[fam] = "DATA_GAP_COVERAGE"
            continue
        a, x = summ(D, fam)
        z, y = summ(R, fam)
        discovery[fam], replication[fam] = a, z
        cell_rows += [{**v, "sample": "DISCOVERY"} for v in x] + [{**v, "sample": "REPLICATION"} for v in y]
        states[fam] = "SURVIVOR_REPLICATED" if a["survives"] and z["survives"] else "REJECTED_FAILED_REPLICATION" if a["survives"] else "REJECTED_DISCOVERY"
    survivors = [f for f in FAMS if states[f] == "SURVIVOR_REPLICATED"][:2]
    gaps = [f for f in FAMS if states[f] == "DATA_GAP_COVERAGE"]
    status = "SURVIVORS_READY_FOR_SEPARATE_PROSPECTIVE" if survivors else "DATA_GAP_H130_H139_COVERAGE" if len(gaps) == len(FAMS) else "CLOSED_NO_H130_H139_SURVIVOR"
    result = {
        "schema": "gate_btc.b3.h130_h139.economics.v1",
        "status": status,
        "cutoff_exclusive": CUTOFF,
        "source": {
            "provider": qa["provider"],
            "package_name": qa["package_name"],
            "resource_id": qa["resource_id"],
            "raw_sha256": qa["raw_sha256"],
            "derived_node_csv_sha256": qa["derived_node_csv_sha256"],
            "strict_prior_date": True,
            "stale_limit_calendar_days": 5,
        },
        "states": states,
        "discovery": discovery,
        "replication": replication,
        "survivors": survivors,
        "data_gap_families": gaps,
        "discovery_join": dcover,
        "replication_join": rcover,
        "discovery_sync_sessions": len(ds),
        "replication_sync_sessions": len(rs),
        "discovery_median_common_bar_coverage": float(np.median(dc)),
        "replication_median_common_bar_coverage": float(np.median(rc)),
        "h1_economics_read": False,
        "survivor_partial_economics_read": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "engine_feed": False,
        "not_approved": True,
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows = []
    for fam in FAMS:
        row = {"family": fam, "generation": GEN, "state": states[fam], "orders": 0, "capital": 0, "engine_feed": False, "not_approved": True}
        if states[fam] != "DATA_GAP_COVERAGE":
            row.update({"discovery": discovery[fam], "replication": replication[fam]})
        rows.append(row)
    Path(ledger).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    pd.DataFrame(cell_rows).to_csv(cells, index=False)
    manifest_payload = {
        "schema": "qrds.b3.h130_h139.manifest.v1",
        "cutoff_exclusive": CUTOFF,
        "node_hash_frozen": EXPECTED_NODE_SHA256,
        "source_raw_sha256": qa["raw_sha256"],
        "source_resource_id": qa["resource_id"],
        "discovery_join": dcover,
        "replication_join": rcover,
        "observed_fields": list(NODE_COLS),
        "derived_fields": ["nominal_slope", "nominal_curve", "real_slope", "breakeven_proxy", "stress_z"],
        "h1_economics_read": False,
        "survivor_partial_economics_read": False,
        "orders": 0,
        "capital": 0,
        "engine_feed": False,
        "not_approved": True,
    }
    Path(manifest).write_text(json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "states": states, "survivors": survivors, "data_gap_families": gaps}, sort_keys=True))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--nodes", required=True)
    p.add_argument("--source-qa", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--cells", required=True)
    p.add_argument("--manifest", required=True)
    a = p.parse_args()
    main(a.nodes, a.source_qa, a.out, a.ledger, a.cells, a.manifest)
