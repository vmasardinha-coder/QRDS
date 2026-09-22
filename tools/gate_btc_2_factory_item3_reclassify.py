#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

HARD_REASONS = {
    "REFERENCE_COST_EDGE", "STRESS_COST", "DELAYED_ENTRY", "SIDE_STABILITY", "CONCENTRATION"
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def calendar_reason_is_soft(metrics: dict) -> bool:
    halves = metrics.get("half_metrics") or {}
    eligible = [v for v in halves.values() if int(v.get("trades", 0)) >= 15]
    return len(eligible) < 2


def classify_cell(cell: dict) -> tuple[str, list[str]]:
    m = cell.get("metrics") or {}
    reasons = list(m.get("reasons") or [])
    if cell.get("qualified") is True and not reasons:
        return "QUALIFIED", reasons
    if not reasons:
        return "UNCLASSIFIED", reasons
    hard = []
    soft = []
    for r in reasons:
        if r == "CALENDAR_HALF_STABILITY":
            (soft if calendar_reason_is_soft(m) else hard).append(r)
        elif r in {"NO_TRADES", "MIN_TRADES"}:
            soft.append(r)
        elif r in HARD_REASONS:
            hard.append(r)
        else:
            hard.append(r)
    if hard:
        return "HARD_REJECT", reasons
    if soft:
        return "SOFT_INSUFFICIENT", reasons
    return "UNCLASSIFIED", reasons


def classify_family(fam: dict) -> dict:
    disc = fam.get("discovery") or {}
    cells = disc.get("cells") or []
    cell_rows = []
    for c in cells:
        cls, reasons = classify_cell(c)
        cell_rows.append({
            "horizon": c.get("horizon"),
            "class": cls,
            "reasons": reasons,
            "trades": int((c.get("metrics") or {}).get("trades", 0)),
            "net2": (c.get("metrics") or {}).get("net2"),
            "net3": (c.get("metrics") or {}).get("net3"),
            "delayed_net2": (c.get("metrics") or {}).get("delayed_net2"),
        })
    soft_or_pass = sum(x["class"] in {"SOFT_INSUFFICIENT", "QUALIFIED"} for x in cell_rows)
    hard = sum(x["class"] == "HARD_REJECT" for x in cell_rows)
    unclassified = sum(x["class"] == "UNCLASSIFIED" for x in cell_rows)
    if len(cell_rows) >= 2 and soft_or_pass >= 2:
        status = "INCONCLUSIVE_BUT_FORWARD_SAFE"
        exp = True
    elif hard > 0:
        status = "VALID_SCIENTIFIC_REJECTION"
        exp = False
    elif unclassified > 0 or not cell_rows:
        status = "REVIEW_REQUIRED"
        exp = False
    else:
        status = "VALID_SCIENTIFIC_REJECTION"
        exp = False
    return {
        "classification": status,
        "experimental_shadow_eligible": exp,
        "soft_or_qualified_cells": soft_or_pass,
        "hard_reject_cells": hard,
        "cells": cell_rows,
    }


def generation_results(results_dir: Path):
    for p in sorted(results_dir.glob("gate_btc_b3_h*_h*_result.json")):
        try:
            j = load(p)
        except Exception:
            continue
        for fam in j.get("families") or []:
            yield p, fam


def map_requalification(req_dir: Path) -> dict[str, dict]:
    out = {}
    qpath = req_dir / "QUEUE.json"
    if not qpath.exists():
        return out
    q = load(qpath)
    results_dir = req_dir / "results"
    for row in q.get("families") or []:
        fid = row.get("original_family_id")
        names = []
        ns = row.get("new_namespace", "")
        if ns:
            names.append(ns.replace("::", "__") + ".json")
        rp = row.get("result_path")
        if rp:
            names.append(Path(rp).name)
        result = None
        for name in names:
            p = results_dir / name
            if p.exists():
                result = load(p)
                break
        out[fid] = {"queue": row, "result": result}
    return out


def classify_grammar_007(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    j = load(path)
    rows = []
    for c in j.get("cases") or []:
        term = c.get("terminal_status", "")
        rows.append({
            "id": c.get("case_id"),
            "terminal_status": term,
            "classification": "VALID_SCIENTIFIC_REJECTION" if term.startswith("REJECTED_") else "REVIEW_REQUIRED",
            "experimental_shadow_eligible": False,
        })
    return {"exists": True, "status": j.get("status"), "cases": rows}


def classify_grammar_008(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    j = load(path)
    rows = []
    for c in j.get("cases") or []:
        term = c.get("terminal_status", "")
        if term.startswith("REJECTED_"):
            cls = "VALID_SCIENTIFIC_REJECTION"
        elif term.startswith("INELIGIBLE_PREREG_UNDERSPECIFIED"):
            cls = "INVALID_SCIENCE_OR_DATA"
        else:
            cls = "REVIEW_REQUIRED"
        rows.append({
            "id": c.get("candidate_id"),
            "terminal_status": term,
            "classification": cls,
            "experimental_shadow_eligible": False,
        })
    return {"exists": True, "status": j.get("status"), "cases": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime-root", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()

    rr = Path(args.runtime_root)
    contract = load(Path(args.contract))
    if contract.get("status_name") != "EXPERIMENTAL_PROSPECTIVE_SHADOW":
        raise SystemExit("ITEM2_CONTRACT_MISMATCH")

    auto = rr / "runtime" / "autonomous_science"
    fac = rr / "runtime" / "factory_autonomy"
    req = map_requalification(fac / "invalidated_requalification")

    families = []
    current_by_class = Counter()
    reason_counter = Counter()
    requal_used = 0
    for src, fam in generation_results(auto / "results"):
        fid = fam.get("family_id")
        basis = fam
        basis_name = "ORIGINAL_AUTONOMOUS_RESULT"
        rq = req.get(fid)
        if rq and rq.get("result"):
            r = rq["result"]
            basis = {
                "family_id": fid,
                "contract": fam.get("contract"),
                "discovery": r.get("discovery") or {},
                "replication": r.get("replication") or {},
            }
            basis_name = "LATEST_REQUALIFICATION_RESULT"
            requal_used += 1
        c = classify_family(basis)
        for cell in c["cells"]:
            reason_counter.update(cell["reasons"])
        current_by_class[c["classification"]] += 1
        families.append({
            "family_id": fid,
            "generation_result": src.name,
            "evidence_basis": basis_name,
            "feature": (fam.get("contract") or {}).get("feature"),
            "direction": (fam.get("contract") or {}).get("direction"),
            "decision_window_minutes": (fam.get("contract") or {}).get("decision_window_minutes"),
            "abs_z_threshold": (fam.get("contract") or {}).get("abs_z_threshold"),
            "standardization_lookback_sessions": (fam.get("contract") or {}).get("standardization_lookback_sessions", 20),
            **c,
        })

    eligible = [x for x in families if x["experimental_shadow_eligible"]]
    g7 = classify_grammar_007(fac / "GRAMMAR_007_PEARSON_HISTORICAL_EVAL_RUNTIME.json")
    g8 = classify_grammar_008(fac / "GRAMMAR_008_INDUSTRIAL_HISTORICAL_EVAL_RUNTIME.json")

    queue_path = fac / "invalidated_requalification" / "QUEUE.json"
    q = load(queue_path) if queue_path.exists() else {}
    out = {
        "schema": "gate_btc_2.factory_item3_reclassification.v1",
        "item": 3,
        "policy": {
            "survivor_standard_changed": False,
            "no_retune": True,
            "no_backfill": True,
            "same_hypothesis_clean_rejection_rescued": False,
            "experimental_lane_credit": 0,
            "experimental_lane_promotion_authority": False,
            "family_admission_rule": "AT_LEAST_TWO_FROZEN_HORIZON_CELLS_ARE_QUALIFIED_OR_FAIL_ONLY_FOR_EVIDENCE_SUFFICIENCY; HARD_ECONOMIC_OR_ROBUSTNESS_REJECTION_IS_NOT_RESCUED",
            "soft_reason_semantics": {
                "NO_TRADES": "EVIDENCE_INSUFFICIENT",
                "MIN_TRADES": "EVIDENCE_INSUFFICIENT",
                "CALENDAR_HALF_STABILITY": "SOFT_ONLY_WHEN_FEWER_THAN_TWO_HALF_BUCKETS_HAVE_AT_LEAST_15_TRADES"
            },
            "hard_reasons": sorted(HARD_REASONS)
        },
        "autonomous_base": {
            "families_scanned": len(families),
            "latest_requalification_results_used": requal_used,
            "classification_counts": dict(sorted(current_by_class.items())),
            "experimental_shadow_eligible_count": len(eligible),
            "experimental_shadow_eligible_ids": [x["family_id"] for x in eligible],
            "reason_counts": dict(sorted(reason_counter.items())),
            "families": families
        },
        "invalidated_requalification_queue": {
            "affected_family_count": q.get("affected_family_count"),
            "green_source_family_count": q.get("green_source_family_count"),
            "v3_scope_authorized": q.get("v3_scope_authorized"),
            "completed_family_count": q.get("completed_family_count"),
            "waiting_source_count": q.get("waiting_source_count"),
            "queue_label_scientific_rejection_is_not_used_as_sufficient_proof": True
        },
        "grammar_007": g7,
        "grammar_008": g8,
        "next_step": "BIND_FORWARD_SOURCE_AND_ACTIVATE_ALL_ELIGIBLE_IDS_AS_ZERO_CREDIT_EXPERIMENTAL_PROSPECTIVE_SHADOW_WITHOUT_CHERRY_PICKING",
        "safety": {
            "research_only": True,
            "shadow_only": True,
            "engine_feed": False,
            "orders": 0,
            "real_capital": 0,
            "no_backfill": True,
            "no_retune": True
        }
    }

    op = Path(args.out_json)
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# GATE BTC 2.0 — Factory Item 3 reclassification",
        "",
        f"Autonomous families scanned: **{len(families)}**",
        f"Latest requalification evidence used: **{requal_used}** families",
        f"Experimental-shadow eligible under frozen Item-2 semantics: **{len(eligible)}**",
        "",
        "## Classification counts",
    ]
    for k, v in sorted(current_by_class.items()):
        lines.append(f"- `{k}`: {v}")
    lines += [
        "",
        "## 512-family question",
        f"The canonical requalification queue reports `green_source_family_count={q.get('green_source_family_count')}` and `v3_scope_authorized={q.get('v3_scope_authorized')}`. Item 3 does not trust the queue's terminal label alone; each latest result is re-read from its actual cell evidence.",
        "",
        "## Admission rule",
        "A frozen family is eligible for the experimental lane only when at least two of its three frozen horizon cells are already qualified or fail solely because the evidence is insufficient (`NO_TRADES`, `MIN_TRADES`, or calendar-half insufficiency caused by fewer than two adequately populated half-year buckets). Any hard cost/robustness rejection prevents rescue of that cell. No parameter, sign, threshold, horizon, lookback or cost is changed.",
        "",
        "## Grammar 007/008",
        f"- Grammar 007 cases: {len(g7.get('cases', []))}; historical rejects remain terminal under the same hypothesis.",
        f"- Grammar 008 cases: {len(g8.get('cases', []))}; clean discovery rejects remain terminal; underspecified preregistrations remain invalid until a materially distinct complete preregistration exists.",
        "",
        "## Next mechanical step",
        "Bind a prospectively valid B3 M5 source and activate **all** eligible frozen IDs as `EXPERIMENTAL_PROSPECTIVE_SHADOW` together, avoiding post-result cherry-picking. D0 must be the first observation after merged activation; historical credit remains zero."
    ]
    Path(args.out_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"families_scanned": len(families), "eligible": len(eligible), "counts": dict(current_by_class)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
