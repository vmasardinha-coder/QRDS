#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

import gate_btc_b3_h30_h39_cross_asset as b3
from gate_btc_b3_h140_h149_source_probe import get_year as get_ptax_year
from gate_btc_b3_h150_h159_focus_source_qa import CUTOFF, INDICATORS, fetch_indicator

FAMS = tuple(f"H{i}" for i in range(150, 160))
ASSETS = ("WIN", "WDO")
HOLDS = (60, 120)
GEN = "H150_H159_V1"
PRIMARY_BASE = 0
ROLL = 20


def finite(x: object) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def sgn(x: float) -> int:
    return 1 if x > 0 else -1 if x < 0 else 0


def annual_year(v: object) -> int | None:
    s = str(v or "").strip()
    return int(s) if len(s) == 4 and s.isdigit() else None


def selected_focus(indicator: str) -> pd.DataFrame:
    _raw, obj = fetch_indicator(indicator)
    rows = [r for r in obj["payload"]["value"] if r.get("baseCalculo") == PRIMARY_BASE]
    by_date: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        d = str(r.get("Data") or "")[:10]
        if d:
            by_date[d].append(r)
    chosen = []
    for d, rr in sorted(by_date.items()):
        y0 = pd.Timestamp(d).year
        cand = [(annual_year(r.get("DataReferencia")), r) for r in rr]
        cand = [(y, r) for y, r in cand if y is not None and y >= y0]
        if not cand:
            continue
        y = min(y for y, _r in cand)
        exact = [r for yy, r in cand if yy == y]
        if len(exact) != 1:
            continue
        r = exact[0]
        chosen.append({
            "date": d,
            "ref": str(r.get("DataReferencia")),
            "median": pd.to_numeric(r.get("Mediana"), errors="coerce"),
            "std": pd.to_numeric(r.get("DesvioPadrao"), errors="coerce"),
            "min": pd.to_numeric(r.get("Minimo"), errors="coerce"),
            "max": pd.to_numeric(r.get("Maximo"), errors="coerce"),
        })
    x = pd.DataFrame(chosen)
    if x.empty:
        raise RuntimeError(f"ZERO_SELECTED_FOCUS:{indicator}")
    x["date"] = pd.to_datetime(x["date"]).dt.strftime("%Y-%m-%d")
    return x.sort_values("date").drop_duplicates("date").reset_index(drop=True)


def add_revision_z(df: pd.DataFrame, value_col: str, prefix: str) -> pd.DataFrame:
    x = df.copy().sort_values("date").reset_index(drop=True)
    same_ref = x["ref"].eq(x["ref"].shift(1))
    rev = x[value_col].diff().where(same_ref)
    scale = rev.abs().shift(1).rolling(ROLL, min_periods=ROLL).median().replace(0, np.nan)
    x[f"rev_{prefix}"] = rev
    x[f"z_{prefix}"] = rev / scale
    return x


def ptax_closes() -> pd.DataFrame:
    rows = []
    for y in range(2020, 2027):
        part, _meta = get_ptax_year(y)
        rows.extend(part)
    x = pd.DataFrame(rows)
    if x.empty:
        raise RuntimeError("ZERO_PTAX_ROWS")
    x["timestamp"] = pd.to_datetime(x["dataHoraCotacao"], errors="raise")
    x["date"] = x["timestamp"].dt.strftime("%Y-%m-%d")
    x["buy"] = pd.to_numeric(x["cotacaoCompra"], errors="raise")
    x["sell"] = pd.to_numeric(x["cotacaoVenda"], errors="raise")
    x["mid"] = (x["buy"] + x["sell"]) / 2.0
    x = x[x["date"] < CUTOFF].sort_values("timestamp")
    return x.groupby("date", as_index=False).tail(1)[["date", "mid"]].sort_values("date").reset_index(drop=True)


def feature_table(join_qa_path: str) -> tuple[pd.DataFrame, dict]:
    jq = json.loads(Path(join_qa_path).read_text(encoding="utf-8"))
    if jq.get("status") != "JOIN_QA_PASS_ECONOMICS_STILL_NOT_RUN":
        raise RuntimeError(f"JOIN_QA_NOT_READY:{jq.get('status')}")
    if jq.get("economics_executed") is not False or jq.get("h1_economics_read") is not False:
        raise RuntimeError("JOIN_QA_SAFETY_MISMATCH")

    raw = {ind: selected_focus(ind) for ind in INDICATORS}
    short = {"Selic": "selic", "IPCA": "ipca", "Câmbio": "fx", "PIB Total": "gdp"}
    pieces = []
    for ind, p in short.items():
        x = add_revision_z(raw[ind], "median", p)
        x = x.rename(columns={
            "ref": f"ref_{p}", "median": f"median_{p}", "std": f"std_{p}",
            "min": f"min_{p}", "max": f"max_{p}", f"rev_{p}": f"rev_{p}", f"z_{p}": f"z_{p}",
        })
        keep = ["date", f"ref_{p}", f"median_{p}", f"std_{p}", f"min_{p}", f"max_{p}", f"rev_{p}", f"z_{p}"]
        pieces.append(x[keep])

    f = pieces[0]
    for x in pieces[1:]:
        f = f.merge(x, on="date", how="outer")
    f = f.sort_values("date").reset_index(drop=True)

    # H154/H155 selection was frozen by the green pre-economics join artifact.
    disp_sel = jq["discovery"]["dispersion_selection"]
    selic_field = "std_selic" if disp_sel["H154"] == "selic_std" else None
    ipca_field = "std_ipca" if disp_sel["H155"] == "ipca_std" else None
    if selic_field is None:
        f["disp_selic"] = f["max_selic"] - f["min_selic"]
    else:
        f["disp_selic"] = f[selic_field]
    if ipca_field is None:
        f["disp_ipca"] = f["max_ipca"] - f["min_ipca"]
    else:
        f["disp_ipca"] = f[ipca_field]

    for p in ("selic", "ipca"):
        same_ref = f[f"ref_{p}"].eq(f[f"ref_{p}"].shift(1))
        rev = f[f"disp_{p}"].diff().where(same_ref)
        scale = rev.abs().shift(1).rolling(ROLL, min_periods=ROLL).median().replace(0, np.nan)
        f[f"rev_disp_{p}"] = rev
        f[f"z_disp_{p}"] = rev / scale

    same_si = f["ref_selic"].eq(f["ref_ipca"])
    f["real_rate"] = (f["median_selic"] - f["median_ipca"]).where(same_si)
    same_real_ref = same_si & same_si.shift(1, fill_value=False) & f["ref_selic"].eq(f["ref_selic"].shift(1))
    rr = f["real_rate"].diff().where(same_real_ref)
    rrscale = rr.abs().shift(1).rolling(ROLL, min_periods=ROLL).median().replace(0, np.nan)
    f["rev_real_rate"] = rr
    f["z_real_rate"] = rr / rrscale

    ptax = ptax_closes()
    f = f.merge(ptax.rename(columns={"mid": "ptax_mid"}), on="date", how="left")
    f["fx_ptax_gap"] = f["median_fx"] - f["ptax_mid"]
    same_fx_ref = f["ref_fx"].eq(f["ref_fx"].shift(1))
    gaprev = f["fx_ptax_gap"].diff().where(same_fx_ref)
    gapscale = gaprev.abs().shift(1).rolling(ROLL, min_periods=ROLL).median().replace(0, np.nan)
    f["rev_fx_ptax_gap"] = gaprev
    f["z_fx_ptax_gap"] = gaprev / gapscale

    return f.set_index("date", drop=False), jq


def emit(R, fam, s, g, asset, side, param, bar, i=-1, window=None):
    suffix = f"|w{window}" if window else ""
    for h in HOLDS:
        b3.add(R, fam, s, g, asset, int(side), i, h, f"{param}{suffix}", bar)


def macro_residuals(ss: dict, feat: pd.DataFrame, asset: str, windows=(60, 120)) -> dict:
    ordered = sorted(ss)
    hist: list[dict] = []
    out = {}
    for j in range(2, len(ordered)):
        signal = ordered[j]
        target = ordered[j - 1]
        macro_date = ordered[j - 2]
        row = feat.loc[macro_date] if macro_date in feat.index else None
        g = ss[target]
        if row is None or g.empty:
            continue
        x = np.array([row.get("z_selic"), row.get("z_ipca"), row.get("z_fx"), row.get("z_gdp")], dtype=float)
        y = (float(g.iloc[-1][f"close_{asset}"]) / float(g.iloc[0][f"open_{asset}"]) - 1.0) * 1e4
        if not np.isfinite(x).all() or not finite(y):
            continue
        for w in windows:
            prior = hist[-w:]
            if len(prior) < w:
                continue
            X = np.array([r["x"] for r in prior], dtype=float)
            Y = np.array([r["y"] for r in prior], dtype=float)
            if len(X) != w or not np.isfinite(X).all() or not np.isfinite(Y).all():
                continue
            A = np.c_[np.ones(w), X]
            beta = np.linalg.lstsq(A, Y, rcond=None)[0]
            resid_hist = Y - A @ beta
            sd = float(np.std(resid_hist, ddof=0))
            if sd <= 0:
                continue
            resid = float(y - np.r_[1.0, x] @ beta)
            out[(signal, w)] = resid / sd
        hist.append({"x": x, "y": float(y)})
    return out


def gen(ss: dict, bar: int, feat: pd.DataFrame) -> pd.DataFrame:
    R = []
    ordered = sorted(ss)
    prev = {ordered[i]: ordered[i - 1] for i in range(1, len(ordered))}
    residuals = {a: macro_residuals(ss, feat, a) for a in ASSETS}

    simple = {
        "H150": "z_selic",
        "H151": "z_ipca",
        "H152": "z_fx",
        "H153": "z_gdp",
        "H154": "z_disp_selic",
        "H155": "z_disp_ipca",
        "H157": "z_real_rate",
    }
    for s, g in ss.items():
        p = prev.get(s)
        if p is None or p not in feat.index:
            continue
        r = feat.loc[p]
        for fam, col in simple.items():
            v = r.get(col)
            if not finite(v):
                continue
            v = float(v)
            for th in (1.0, 1.5):
                if abs(v) < th:
                    continue
                side = sgn(v)
                for a in ASSETS:
                    emit(R, fam, s, g, a, side, f"z{th}_same", bar)
                    emit(R, fam, s, g, a, -side, f"z{th}_inverse", bar)

        # H156: fixed four-vote breadth from the four standardized median revisions.
        vote_vals = [r.get("z_selic"), r.get("z_ipca"), r.get("z_fx"), r.get("z_gdp")]
        if all(finite(v) for v in vote_vals):
            votes = [sgn(float(v)) if abs(float(v)) >= 1.0 else 0 for v in vote_vals]
            pos, neg = sum(v > 0 for v in votes), sum(v < 0 for v in votes)
            aligned = max(pos, neg)
            if aligned >= 3:
                vote_side = 1 if pos > neg else -1
                for q in (3, 4):
                    if aligned >= q:
                        for a in ASSETS:
                            emit(R, "H156", s, g, a, vote_side, f"{q}of4_vote", bar)
                            emit(R, "H156", s, g, a, -vote_side, f"{q}of4_inverse", bar)

        # H158: both preregistered convergence/divergence mappings, with WIN exact inverse.
        z = r.get("z_fx_ptax_gap")
        if finite(z):
            z = float(z)
            for th in (1.0, 1.5):
                if abs(z) < th:
                    continue
                side = sgn(z)
                emit(R, "H158", s, g, "WDO", side, f"z{th}_divergence", bar)
                emit(R, "H158", s, g, "WDO", -side, f"z{th}_convergence", bar)
                emit(R, "H158", s, g, "WIN", -side, f"z{th}_inverse_divergence", bar)
                emit(R, "H158", s, g, "WIN", side, f"z{th}_inverse_convergence", bar)

        # H159: residual is from prior completed session, trained only on earlier
        # completed sessions; decision occurs after current first 30 minutes.
        n = max(2, 30 // bar)
        if len(g) > n:
            for a in ASSETS:
                move = (float(g.iloc[n - 1][f"close_{a}"]) / float(g.iloc[0][f"open_{a}"]) - 1.0) * 1e4
                mside = sgn(move)
                if not mside:
                    continue
                for w in (60, 120):
                    rz = residuals[a].get((s, w))
                    if not finite(rz):
                        continue
                    for th in (1.5, 2.0):
                        if abs(float(rz)) >= th:
                            emit(R, "H159", s, g, a, mside, f"resid{th}_cont", bar, n - 1, w)
                            emit(R, "H159", s, g, a, -mside, f"resid{th}_meanrev", bar, n - 1, w)
    return pd.DataFrame(R)


def summ(t: pd.DataFrame, fam: str) -> tuple[dict, list[dict]]:
    qualified = []
    cells = []
    if t.empty:
        return {"qualified_cells": 0, "surviving_legs": [], "survives": False, "qualified": []}, cells
    qf = t[t.family == fam]
    for (a, p, h), g in qf.groupby(["asset", "param", "horizon"]):
        ok, reasons, metrics = b3.metric(g, *b3.COST[a])
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


def main(join_qa: str, out: str, ledger: str, cells: str, manifest: str, sample_loader=None) -> None:
    sample_loader = sample_loader or b3.sample
    feat, jq = feature_table(join_qa)
    ds, dc = sample_loader(["2024_26"], 5)
    rs, rc = sample_loader(["2020_22", "2022_24"], 15)
    D = gen(ds, 5, feat)
    R = gen(rs, 15, feat)

    discovery, replication, cell_rows = {}, {}, []
    for fam in FAMS:
        a, x = summ(D, fam)
        z, y = summ(R, fam)
        discovery[fam], replication[fam] = a, z
        cell_rows += [{**v, "sample": "DISCOVERY"} for v in x]
        cell_rows += [{**v, "sample": "REPLICATION"} for v in y]

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

    status = "SURVIVORS_READY_FOR_SEPARATE_PROSPECTIVE" if survivors else "CLOSED_NO_H150_H159_SURVIVOR"
    result = {
        "schema": "gate_btc.b3.h150_h159.economics.v1",
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
        "join_qa_schema": jq["schema"],
        "join_qa_status": jq["status"],
        "discovery_sync_sessions": len(ds),
        "replication_sync_sessions": len(rs),
        "discovery_median_common_bar_coverage": float(np.median(dc)) if dc else 0.0,
        "replication_median_common_bar_coverage": float(np.median(rc)) if rc else 0.0,
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
                "h1_economics_read": False, "orders": 0, "capital": 0,
                "engine_feed": False, "not_approved": True,
            }, sort_keys=True) + "\n")
    pd.DataFrame(cell_rows).to_csv(cells, index=False)
    manifest_payload = {
        "schema": "qrds.b3.h150_h159.manifest.v1",
        "cutoff_exclusive": CUTOFF,
        "focus_primary_base_calculo": PRIMARY_BASE,
        "focus_revision_scale": "median(abs(revision)) over 20 completed prior observations; full 20 required; no cross-horizon revision",
        "causal_lag": "exact immediately preceding frozen B3 session Focus date; no carry/forward-fill",
        "h159_causality": "residual of prior completed session using macro state from one session earlier; fit only on earlier completed valid observations",
        "h158_ptax": "official H140 PTAX source contract; exact prior-session PTAX date",
        "dispersion_selection_discovery": jq["discovery"]["dispersion_selection"],
        "dispersion_selection_replication": jq["replication"]["dispersion_selection"],
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
    p.add_argument("--join-qa", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--cells", required=True)
    p.add_argument("--manifest", required=True)
    a = p.parse_args()
    main(a.join_qa, a.out, a.ledger, a.cells, a.manifest)
