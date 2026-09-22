#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def top5_positive_share(gross):
    pos = sorted((x for x in gross if x > 0), reverse=True)
    total = sum(pos)
    return 1.0 if total <= 0 else sum(pos[:5]) / total


def collect_trigger_outcomes(records: list[dict]) -> dict[str, dict[int, list[dict]]]:
    out: dict[str, dict[int, list[dict]]] = {}
    for rec in sorted(records, key=lambda x: str(x.get("session", ""))):
        for fam in rec.get("family_observations", []):
            if fam.get("state") != "TRIGGER":
                continue
            fid = str(fam["family_id"])
            for row in fam.get("outcomes", []):
                h = int(row["horizon_minutes"])
                out.setdefault(fid, {}).setdefault(h, []).append({
                    "session": rec.get("session"),
                    "gross_bps": float(row["gross_bps"]),
                    "net_ref_2bps": float(row["net_ref_2bps"]),
                    "net_stress_3bps": float(row["net_stress_3bps"]),
                    "delayed_net_ref_2bps": None if row.get("delayed_net_ref_2bps") is None else float(row["delayed_net_ref_2bps"]),
                })
    return out


def eval_cell(rows: list[dict], prereg: dict) -> dict:
    n = int(prereg["fixed_forward_checkpoint"]["trigger_observations_per_horizon"])
    if len(rows) < n:
        return {"state": "AWAITING_FORWARD_TRIGGERS", "trigger_count": len(rows), "checkpoint_n": n}
    fixed = rows[:n]
    gross = [x["gross_bps"] for x in fixed]
    net_ref = [x["net_ref_2bps"] for x in fixed]
    net_stress = [x["net_stress_3bps"] for x in fixed]
    delayed = [x["delayed_net_ref_2bps"] for x in fixed if x["delayed_net_ref_2bps"] is not None]
    gates = prereg["cell_gates"]
    metrics = {
        "checkpoint_n": n,
        "mean_net_reference_bps": mean(net_ref),
        "mean_net_stress_bps": mean(net_stress),
        "delayed_count": len(delayed),
        "mean_delayed_net_reference_bps": mean(delayed),
        "top5_positive_gross_share": top5_positive_share(gross),
        "first_session": fixed[0]["session"],
        "checkpoint_session": fixed[-1]["session"],
    }
    reasons = []
    if metrics["mean_net_reference_bps"] <= float(gates["minimum_mean_net_reference_bps_exclusive"]):
        reasons.append("REFERENCE_COST_EDGE")
    if metrics["mean_net_stress_bps"] <= float(gates["minimum_mean_net_stress_bps_exclusive"]):
        reasons.append("STRESS_COST")
    if len(delayed) < n or metrics["mean_delayed_net_reference_bps"] is None or metrics["mean_delayed_net_reference_bps"] <= float(gates["minimum_mean_delayed_net_reference_bps_exclusive"]):
        reasons.append("DELAYED_ENTRY")
    if metrics["top5_positive_gross_share"] > float(gates["maximum_top5_positive_gross_share_inclusive"]):
        reasons.append("CONCENTRATION")
    return {
        "state": "REJECTED_FORWARD_SCREEN" if reasons else "PASS_FORWARD_SCREEN",
        "trigger_count_total_seen": len(rows),
        "checkpoint_frozen": True,
        "metrics": metrics,
        "reasons": reasons,
    }


def adjudicate(manifest: dict, records: list[dict], prereg: dict) -> dict:
    outcomes = collect_trigger_outcomes(records)
    horizons = [int(x) for x in prereg["fixed_forward_checkpoint"]["holding_horizons_minutes"]]
    need_pass = int(prereg["fixed_forward_checkpoint"]["minimum_passing_horizons_for_candidate"])
    need_reject = int(prereg["fixed_forward_checkpoint"]["minimum_rejected_horizons_for_terminal_null"])
    rows = []
    counts = {}
    for entry in sorted(manifest.get("active_families") or [], key=lambda x: int(str(x["contract"]["family_id"])[1:])):
        fid = str(entry["contract"]["family_id"])
        cells = {str(h): eval_cell(outcomes.get(fid, {}).get(h, []), prereg) for h in horizons}
        passed = sum(c["state"] == "PASS_FORWARD_SCREEN" for c in cells.values())
        rejected = sum(c["state"] == "REJECTED_FORWARD_SCREEN" for c in cells.values())
        if passed >= need_pass:
            state = "CANDIDATE_READY_FORWARD_SCREEN"
        elif rejected >= need_reject:
            state = "EXPERIMENTAL_TERMINAL_NULL"
        else:
            state = "CONTINUE_EXPERIMENTAL_SHADOW"
        counts[state] = counts.get(state, 0) + 1
        rows.append({
            "family_id": fid,
            "state": state,
            "pass_horizons": passed,
            "rejected_horizons": rejected,
            "cells": cells,
            "survivor_credit": 0,
            "survivor_promotion_authority": False,
            "orders": 0,
            "real_capital": 0,
        })
    return {
        "schema": "gate_btc_2.factory_item3d_forward_adjudication.v1",
        "status": "FORWARD_ADJUDICATION_ACTIVE" if records else "WAIT_FORWARD_LEDGER",
        "population_count": len(rows),
        "ledger_session_count": len(records),
        "family_state_counts": counts,
        "families": rows,
        "historical_credit": 0,
        "retroactive_credit": 0,
        "survivor_credit": 0,
        "survivor_promotion_authority": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital": 0,
        "no_backfill": True,
        "no_retune": True,
    }


def self_test():
    p = {
        "fixed_forward_checkpoint": {"trigger_observations_per_horizon": 60, "holding_horizons_minutes": [30, 60, 120], "minimum_passing_horizons_for_candidate": 2, "minimum_rejected_horizons_for_terminal_null": 2},
        "cell_gates": {"minimum_mean_net_reference_bps_exclusive": 0.25, "minimum_mean_net_stress_bps_exclusive": 0.0, "minimum_mean_delayed_net_reference_bps_exclusive": 0.0, "maximum_top5_positive_gross_share_inclusive": 0.40},
    }
    good = [{"session": f"S{i:03d}", "gross_bps": 5.0 + (i % 3), "net_ref_2bps": 3.0 + (i % 3), "net_stress_3bps": 2.0 + (i % 3), "delayed_net_ref_2bps": 2.0 + (i % 2)} for i in range(60)]
    bad = [{**x, "gross_bps": 1.0, "net_ref_2bps": -1.0, "net_stress_3bps": -2.0, "delayed_net_ref_2bps": -1.0} for x in good]
    assert eval_cell(good, p)["state"] == "PASS_FORWARD_SCREEN"
    assert eval_cell(bad, p)["state"] == "REJECTED_FORWARD_SCREEN"
    assert eval_cell(good[:59], p)["state"] == "AWAITING_FORWARD_TRIGGERS"
    print("ITEM3D_SELF_TEST=PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime-root")
    ap.add_argument("--prereg")
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test(); return 0
    if not args.runtime_root or not args.prereg or not args.out:
        raise SystemExit("runtime-root, prereg and out are required")
    root = Path(args.runtime_root)
    prereg = load(Path(args.prereg))
    if prereg.get("status") != "PREREGISTERED_BEFORE_FIRST_FORWARD_ADJUDICATION":
        raise RuntimeError("ITEM3D_PREREG_MISMATCH")
    manifest_path = root / prereg["population"]["activation_manifest"]
    if not manifest_path.exists():
        result = {"schema": "gate_btc_2.factory_item3d_forward_adjudication.v1", "status": "WAIT_ACTIVATION_MANIFEST", "population_count": 0, "ledger_session_count": 0, "family_state_counts": {}, "families": [], "survivor_credit": 0, "survivor_promotion_authority": False, "engine_feed": False, "orders": 0, "real_capital": 0, "no_backfill": True, "no_retune": True}
        dump(Path(args.out), result); return 0
    manifest = load(manifest_path)
    ledger = root / prereg["population"]["ledger_root"]
    records = []
    if ledger.exists():
        for path in sorted(ledger.glob("*.json")):
            rec = load(path)
            if rec.get("schema") == "gate_btc_2.factory_item3c_forward_session.v1" and rec.get("session") == path.stem and rec.get("record_sha256"):
                records.append(rec)
    result = adjudicate(manifest, records, prereg)
    dump(Path(args.out), result)
    print(json.dumps({"status": result["status"], "population": result["population_count"], "sessions": result["ledger_session_count"], "states": result["family_state_counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
