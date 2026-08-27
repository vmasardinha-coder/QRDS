from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd

import gate_btc_b3_h30_h39_cross_asset as b3
from gate_btc_b3_h140_h149_source_probe import get_year as get_ptax_year
from gate_btc_b3_h150_h159_focus_source_qa import CUTOFF, INDICATORS, fetch_indicator

OUT = Path("artifacts/b3_h150_h159_focus_join_qa.json")
THRESHOLD = 0.90
PRIMARY_BASE = 0


def annual_year(v: object) -> int | None:
    s = str(v or "").strip()
    return int(s) if len(s) == 4 and s.isdigit() else None


def focus_maps() -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    for indicator in INDICATORS:
        _raw, obj = fetch_indicator(indicator)
        rows = [r for r in obj["payload"]["value"] if r.get("baseCalculo") == PRIMARY_BASE]
        by_date: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            d = str(r.get("Data") or "")[:10]
            if d:
                by_date[d].append(r)
        chosen: dict[str, dict] = {}
        for d, rr in by_date.items():
            y0 = date.fromisoformat(d).year
            candidates = [(annual_year(r.get("DataReferencia")), r) for r in rr]
            candidates = [(y, r) for y, r in candidates if y is not None and y >= y0]
            if not candidates:
                continue
            y = min(y for y, _r in candidates)
            exact = [r for yy, r in candidates if yy == y]
            if len(exact) == 1:
                chosen[d] = exact[0]
        out[indicator] = chosen
    return out


def ptax_close_dates() -> set[str]:
    rows = []
    for y in range(2020, 2027):
        part, _meta = get_ptax_year(y)
        rows.extend(part)
    df = pd.DataFrame(rows)
    if df.empty or "dataHoraCotacao" not in df:
        return set()
    ts = pd.to_datetime(df["dataHoraCotacao"], errors="coerce")
    return set(ts.dropna().dt.date.astype(str))


def exact_prior_pairs(sessions: dict) -> list[tuple[str, str]]:
    ordered = sorted(sessions)
    return [(ordered[i], ordered[i - 1]) for i in range(1, len(ordered))]


def ok_num(row: dict | None, field: str) -> bool:
    if row is None:
        return False
    try:
        return pd.notna(float(row.get(field)))
    except (TypeError, ValueError):
        return False


def evaluate_sample(name: str, sessions: dict, focus: dict[str, dict[str, dict]], ptax_dates: set[str]) -> dict:
    pairs = exact_prior_pairs(sessions)
    total = len(pairs)
    counts = defaultdict(int)
    miss_examples: dict[str, list[dict]] = defaultdict(list)

    def record(key: str, passed: bool, d: str, p: str) -> None:
        if passed:
            counts[key] += 1
        elif len(miss_examples[key]) < 5:
            miss_examples[key].append({"signal_session": d, "required_focus_date": p})

    for d, p in pairs:
        s = focus["Selic"].get(p)
        i = focus["IPCA"].get(p)
        fx = focus["Câmbio"].get(p)
        gdp = focus["PIB Total"].get(p)

        med_s = ok_num(s, "Mediana")
        med_i = ok_num(i, "Mediana")
        med_fx = ok_num(fx, "Mediana")
        med_gdp = ok_num(gdp, "Mediana")
        std_s = ok_num(s, "DesvioPadrao")
        std_i = ok_num(i, "DesvioPadrao")
        rng_s = ok_num(s, "Minimo") and ok_num(s, "Maximo")
        rng_i = ok_num(i, "Minimo") and ok_num(i, "Maximo")
        same_si_horizon = med_s and med_i and str(s.get("DataReferencia")) == str(i.get("DataReferencia"))
        ptax = p in ptax_dates

        record("selic_median", med_s, d, p)
        record("ipca_median", med_i, d, p)
        record("fx_median", med_fx, d, p)
        record("gdp_median", med_gdp, d, p)
        record("selic_std", std_s, d, p)
        record("ipca_std", std_i, d, p)
        record("selic_range", rng_s, d, p)
        record("ipca_range", rng_i, d, p)
        record("four_medians", med_s and med_i and med_fx and med_gdp, d, p)
        record("selic_ipca_same_horizon", same_si_horizon, d, p)
        record("fx_plus_ptax", med_fx and ptax, d, p)
        record("ptax_close", ptax, d, p)

    def metric(key: str) -> dict:
        joined = counts[key]
        return {
            "eligible_sessions": total,
            "joined_sessions": joined,
            "coverage": joined / total if total else 0.0,
            "passes_90pct": bool(total and joined / total >= THRESHOLD),
            "missing_examples": miss_examples[key],
        }

    inputs = {k: metric(k) for k in (
        "selic_median", "ipca_median", "fx_median", "gdp_median",
        "selic_std", "ipca_std", "selic_range", "ipca_range",
        "four_medians", "selic_ipca_same_horizon", "fx_plus_ptax", "ptax_close",
    )}

    selic_disp = "selic_std" if inputs["selic_std"]["passes_90pct"] else "selic_range"
    ipca_disp = "ipca_std" if inputs["ipca_std"]["passes_90pct"] else "ipca_range"
    family_input = {
        "H150": "selic_median",
        "H151": "ipca_median",
        "H152": "fx_median",
        "H153": "gdp_median",
        "H154": selic_disp,
        "H155": ipca_disp,
        "H156": "four_medians",
        "H157": "selic_ipca_same_horizon",
        "H158": "fx_plus_ptax",
        "H159": "four_medians",
    }
    families = {
        fam: {
            "selected_input_gate": key,
            "coverage": inputs[key]["coverage"],
            "passes_90pct": inputs[key]["passes_90pct"],
        }
        for fam, key in family_input.items()
    }
    return {
        "sample": name,
        "eligible_sessions": total,
        "lag_rule": "signal session D requires an observed Focus row dated exactly the immediately preceding frozen B3 session P; no carry/forward-fill",
        "inputs": inputs,
        "dispersion_selection": {
            "H154": selic_disp,
            "H155": ipca_disp,
            "rule": "prefer DesvioPadrao when it independently passes >=90%; otherwise use preregistered exact Maximo-Minimo range only when that range independently passes >=90%",
        },
        "families": families,
        "all_families_pass": all(x["passes_90pct"] for x in families.values()),
    }


def main() -> int:
    focus = focus_maps()
    ptax_dates = ptax_close_dates()
    ds, dcov = b3.sample(["2024_26"], 5)
    rs, rcov = b3.sample(["2020_22", "2022_24"], 15)

    discovery = evaluate_sample("DISCOVERY_2024_26_M5", ds, focus, ptax_dates)
    replication = evaluate_sample("REPLICATION_2020_24_M15", rs, focus, ptax_dates)
    ready = discovery["all_families_pass"] and replication["all_families_pass"]
    report = {
        "schema": "qrds.b3_h150_h159.focus_exact_prior_session_join_qa.v1",
        "cutoff_exclusive": CUTOFF,
        "coverage_threshold": THRESHOLD,
        "coverage_definition": "canonical H130 precedent: joined eligible frozen B3 sessions divided by eligible frozen B3 sessions; H150 applies stricter exact-previous-session source-date matching because forward-fill is forbidden",
        "b3_response_source_repo": b3.SOURCE_REPO,
        "b3_response_source_commit": b3.SOURCE_COMMIT,
        "discovery_sync_sessions": len(ds),
        "replication_sync_sessions": len(rs),
        "discovery_median_common_bar_coverage": float(pd.Series(dcov).median()) if dcov else 0.0,
        "replication_median_common_bar_coverage": float(pd.Series(rcov).median()) if rcov else 0.0,
        "discovery": discovery,
        "replication": replication,
        "status": "JOIN_QA_PASS_ECONOMICS_STILL_NOT_RUN" if ready else "DATA_GAP_CAUSAL_JOIN_COVERAGE",
        "economics_executed": False,
        "h1_economics_read": False,
        "survivor_partial_economics_read": False,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "not_approved": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "discovery_all_families_pass": discovery["all_families_pass"],
        "replication_all_families_pass": replication["all_families_pass"],
        "discovery_sessions": len(ds),
        "replication_sessions": len(rs),
    }, sort_keys=True))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
