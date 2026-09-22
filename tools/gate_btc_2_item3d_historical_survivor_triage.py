#!/usr/bin/env python3
"""Item 3D historical-survivor triage.

Consumes only existing Item 3 reclassification evidence and emits a descriptive
historical candidate/watch ranking. It does not alter prospective Item 3C
collection, does not promote to H1/H31 survivor, and has zero trading authority.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

HARD_REASONS = {
    "CONCENTRATION",
    "DELAYED_ENTRY",
    "REFERENCE_COST_EDGE",
    "SIDE_STABILITY",
    "STRESS_COST",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _family_id(row: dict[str, Any]) -> str:
    for k in ("family_id", "id", "family"):
        if k in row:
            return str(row[k])
    raise KeyError("family id missing")


def _rows(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    nested = runtime.get("autonomous_base", {}).get("families")
    if isinstance(nested, list):
        return [x for x in nested if isinstance(x, dict)]
    for key in ("families", "family_results", "results", "reclassification_results"):
        v = runtime.get(key)
        if isinstance(v, list):
            return [x for x in v if isinstance(x, dict)]
    return []


def _cells(row: dict[str, Any]) -> list[dict[str, Any]]:
    v = row.get("cells") or row.get("horizon_cells")
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []


def _qualified_cells(row: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in _cells(row) if c.get("class") == "QUALIFIED" or c.get("qualified") is True]


def _qualified_count(row: dict[str, Any]) -> int:
    return len(_qualified_cells(row))


def _reasons(row: dict[str, Any]) -> list[str]:
    vals: list[str] = []
    for c in _cells(row):
        v = c.get("reasons")
        if isinstance(v, list):
            vals.extend(str(x) for x in v)
        elif isinstance(v, str):
            vals.append(v)
    for k in ("reasons", "rejection_reasons", "failure_reasons", "reason_codes"):
        v = row.get(k)
        if isinstance(v, list):
            vals.extend(str(x) for x in v)
        elif isinstance(v, str):
            vals.append(v)
    return sorted(set(vals))


def _min_metric(cells: list[dict[str, Any]], key: str) -> float | None:
    vals = [float(c[key]) for c in cells if isinstance(c.get(key), (int, float))]
    return min(vals) if vals else None


def _sum_metric(cells: list[dict[str, Any]], key: str) -> float | None:
    vals = [float(c[key]) for c in cells if isinstance(c.get(key), (int, float))]
    return sum(vals) if vals else None


def classify(runtime: dict[str, Any]) -> dict[str, Any]:
    base = runtime.get("autonomous_base", {})
    ids = base.get("experimental_shadow_eligible_ids")
    if not isinstance(ids, list):
        ids = runtime.get("experimental_shadow_eligible_ids")
    if not isinstance(ids, list):
        raise ValueError("experimental_shadow_eligible_ids missing")
    eligible = {str(x) for x in ids}
    if len(eligible) != 580:
        raise ValueError(f"expected 580 eligible families, got {len(eligible)}")

    source_rows = {_family_id(r): r for r in _rows(runtime)}
    out = []
    missing_detail = 0
    for fid in sorted(eligible):
        r = source_rows.get(fid, {})
        if not r:
            missing_detail += 1
        qc = _qualified_cells(r)
        q = len(qc)
        reasons = _reasons(r)
        hard = sorted(HARD_REASONS.intersection(reasons))
        label = "HISTORICAL_SURVIVOR_CANDIDATE" if (not hard and q >= 2) else "HISTORICAL_WATCH"
        out.append({
            "family_id": fid,
            "label": label,
            "feature": r.get("feature"),
            "direction": r.get("direction"),
            "decision_window_minutes": r.get("decision_window_minutes"),
            "abs_z_threshold": r.get("abs_z_threshold"),
            "standardization_lookback_sessions": r.get("standardization_lookback_sessions"),
            "evidence_basis": r.get("evidence_basis"),
            "qualified_horizon_cell_count": q,
            "qualified_horizons": [c.get("horizon") for c in qc],
            "hard_reasons": hard,
            "all_reasons": reasons,
            "reference_cost_edge": _min_metric(qc, "net2"),
            "stress_cost_edge": _min_metric(qc, "net3"),
            "delayed_entry_edge": _min_metric(qc, "delayed_net2"),
            "trade_count": _sum_metric(qc, "trades"),
            "historical_detail_available": bool(r),
            "prospective_survivor_credit": 0,
            "promotion_authority": False,
        })

    def key(x: dict[str, Any]):
        def nk(v: float | None) -> tuple[int, float]:
            return (1, 0.0) if v is None else (0, -v)
        return (
            -x["qualified_horizon_cell_count"],
            nk(x["reference_cost_edge"]),
            nk(x["stress_cost_edge"]),
            nk(x["delayed_entry_edge"]),
            nk(x["trade_count"]),
            x["family_id"],
        )

    out.sort(key=key)
    for i, row in enumerate(out, 1):
        row["rank"] = i

    counts: dict[str, int] = {}
    for r in out:
        counts[r["label"]] = counts.get(r["label"], 0) + 1

    candidates = [r for r in out if r["label"] == "HISTORICAL_SURVIVOR_CANDIDATE"]
    return {
        "schema": "gate_btc_2.factory_item3d_historical_survivor_triage.v1",
        "status": "HISTORICAL_TRIAGE_COMPLETE" if missing_detail == 0 else "HISTORICAL_TRIAGE_PARTIAL_SOURCE_DETAIL",
        "population_count": 580,
        "historical_survivor_candidate_count": len(candidates),
        "family_state_counts": counts,
        "missing_historical_detail_count": missing_detail,
        "top_candidate_ids": [r["family_id"] for r in candidates[:50]],
        "families": out,
        "all_580_remain_forward_active": True,
        "prospective_survivor_credit": 0,
        "survivor_promotion_authority": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital": 0,
        "no_retune": True,
        "no_backfill": True,
        "h1_h31_runtime_mutation": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    result = classify(_load(Path(args.runtime)))
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "population": result["population_count"],
        "candidate_count": result["historical_survivor_candidate_count"],
        "counts": result["family_state_counts"],
        "missing_detail": result["missing_historical_detail_count"],
        "top_candidate_ids": result["top_candidate_ids"][:20],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
