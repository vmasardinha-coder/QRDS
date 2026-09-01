#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.gate_btc_factory.autonomous_family_evaluator import load_data, eval_family

SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "engine_feed": False,
    "orders": 0,
    "real_capital": 0,
    "no_retune": True,
    "no_backfill": True,
    "no_counter_reset": True,
    "fail_closed": True,
    "h1_economics_read": False,
}

TERMINAL = {"SCIENTIFIC_REJECTION", "VALID_SURVIVOR_READY_FOR_SEPARATE_PROSPECTIVE"}


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"EXPECTED_OBJECT:{path}")
    return obj


def dump(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def family_contracts(results_dir: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for p in sorted(results_dir.glob("gate_btc_b3_h*_h*_result.json")):
        d = load(p)
        for fam in d.get("families") or []:
            fid = str(fam.get("family_id") or "")
            contract = fam.get("contract")
            if fid.startswith("H") and isinstance(contract, dict):
                prior = out.get(fid)
                if prior is not None and prior != contract:
                    raise RuntimeError(f"CONFLICTING_FROZEN_CONTRACT:{fid}")
                out[fid] = copy.deepcopy(contract)
    return out


def validate_root(root: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    if root.get("root_cause_classification") != "SOURCE_DATA_GAP":
        raise RuntimeError("ROOT_CAUSE_NOT_SOURCE_DATA_GAP")
    if root.get("root_cause_unresolved") is True:
        raise RuntimeError("ROOT_CAUSE_UNRESOLVED")
    hist = root.get("historical_integrity_status")
    required = (policy.get("trigger") or {}).get("historical_result_status")
    if required and hist != required:
        raise RuntimeError(f"HISTORICAL_STATUS_MISMATCH:{hist}:{required}")
    ids = list((root.get("affected_scope") or {}).get("family_ids") or [])
    count = int((root.get("affected_scope") or {}).get("family_count", len(ids)))
    if count != len(ids) or count == 0:
        raise RuntimeError("AFFECTED_SCOPE_INVALID")
    if len(set(ids)) != len(ids):
        raise RuntimeError("AFFECTED_SCOPE_DUPLICATE_IDS")
    return ids


def validate_source_gate(gate: dict[str, Any], dataset: Path | None) -> tuple[bool, str]:
    required_true = [
        "qualified",
        "free_or_official_auditable",
        "publication_semantics_proven",
        "revision_semantics_proven",
        "identity_qa_pass",
        "schema_qa_pass",
        "point_in_time_valid",
        "independent_unseen_evaluation_data",
        "no_historical_backfill_credit",
    ]
    for key in required_true:
        if gate.get(key) is not True:
            return False, f"SOURCE_GATE_NOT_GREEN:{key}"
    if gate.get("economics_pre_read") is not False:
        return False, "SOURCE_GATE_ECONOMICS_PRE_READ_FORBIDDEN"
    if gate.get("evaluation_namespace") in (None, ""):
        return False, "SOURCE_GATE_NAMESPACE_MISSING"
    windows = gate.get("windows") or {}
    for name in ("discovery", "replication"):
        w = windows.get(name) or {}
        if not w.get("start") or not w.get("end"):
            return False, f"SOURCE_GATE_WINDOW_MISSING:{name}"
        if str(w["start"]) > str(w["end"]):
            return False, f"SOURCE_GATE_WINDOW_INVALID:{name}"
    d, r = windows["discovery"], windows["replication"]
    if not (str(d["end"]) < str(r["start"]) or str(r["end"]) < str(d["start"])):
        return False, "SOURCE_GATE_WINDOWS_OVERLAP"
    if dataset is None or not dataset.is_file():
        return False, "SOURCE_GATE_DATASET_NOT_MATERIALIZED"
    expected = gate.get("dataset_sha256")
    if not expected or sha256(dataset) != expected:
        return False, "SOURCE_GATE_DATASET_HASH_MISMATCH"
    return True, "SOURCE_GATE_GREEN"


def load_scoped_sources(source_gates_dir: Path | None, runtime_dir: Path) -> list[tuple[dict[str, Any], Path | None]]:
    """Load independently qualified source gates without requiring every affected family to share one gate.

    Each scoped gate must explicitly list ``family_ids``. The dataset path remains repository-relative,
    preserving the same hash/PIT/source checks as the legacy global gate. A malformed or red scoped gate
    is isolated to its declared families and can never green another family.
    """
    if source_gates_dir is None or not source_gates_dir.is_dir():
        return []
    repo_root = runtime_dir.parents[2]
    out: list[tuple[dict[str, Any], Path | None]] = []
    seen_scope: set[tuple[str, str]] = set()
    for path in sorted(source_gates_dir.glob("*.json")):
        gate = load(path)
        ids = gate.get("family_ids")
        if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not x.startswith("H") for x in ids):
            continue
        gate_id = str(gate.get("source_gate_id") or path.stem)
        for fid in ids:
            key = (gate_id, fid)
            if key in seen_scope:
                raise RuntimeError(f"DUPLICATE_SCOPED_SOURCE_GATE_IDENTITY:{gate_id}:{fid}")
            seen_scope.add(key)
        rel = str(gate.get("dataset_relative_path") or "")
        dataset = repo_root / rel if rel else None
        out.append((gate, dataset))
    return out


def select_source_for_family(
    fid: str,
    global_gate: dict[str, Any] | None,
    global_dataset: Path | None,
    scoped_sources: list[tuple[dict[str, Any], Path | None]],
) -> tuple[dict[str, Any] | None, Path | None, str]:
    reasons: list[str] = []
    for gate, dataset in scoped_sources:
        ids = gate.get("family_ids") or []
        if fid not in ids:
            continue
        green, reason = validate_source_gate(gate, dataset)
        if green:
            return gate, dataset, "SOURCE_GATE_GREEN_SCOPED"
        reasons.append(f"{gate.get('source_gate_id') or 'SCOPED'}:{reason}")
    if global_gate is not None:
        green, reason = validate_source_gate(global_gate, global_dataset)
        if green:
            return global_gate, global_dataset, "SOURCE_GATE_GREEN_GLOBAL"
        reasons.append(f"GLOBAL:{reason}")
    if reasons:
        return None, None, "SOURCE_GATE_NOT_GREEN_FOR_FAMILY:" + "|".join(reasons)
    return None, None, "SOURCE_GATE_ABSENT_FOR_FAMILY"


def subset_date(sessions: dict[str, Any], start: str, end: str) -> dict[str, Any]:
    return {k: v for k, v in sessions.items() if start <= k <= end}


def prereg_for(fid: str, contract: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    c = copy.deepcopy(contract)
    if c.get("family_id") != fid:
        raise RuntimeError(f"FAMILY_IDENTITY_MISMATCH:{fid}")
    ns = f"{gate['evaluation_namespace']}::{fid}"
    return {
        "schema": "qrds.factory.invalidated_family_rerun_prereg.v1",
        "namespace": ns,
        "original_family_id": fid,
        "historical_family_mutated": False,
        "grammar_contract": c,
        "grammar_contract_mode": "EXACT_FROZEN_ORIGINAL",
        "source_gate_id": gate.get("source_gate_id"),
        "dataset_sha256": gate.get("dataset_sha256"),
        "windows": copy.deepcopy(gate.get("windows")),
        "economics_read_before_freeze": False,
        "historical_observations_credited": 0,
        "same_historical_window_rerun": False,
        "safety": dict(SAFETY),
    }


def evaluate_one(prereg: dict[str, Any], sessions: dict[str, Any]) -> dict[str, Any]:
    w = prereg["windows"]
    disc_s = subset_date(sessions, str(w["discovery"]["start"]), str(w["discovery"]["end"]))
    rep_s = subset_date(sessions, str(w["replication"]["start"]), str(w["replication"]["end"]))
    if not disc_s or not rep_s:
        return {
            "schema": "qrds.factory.invalidated_family_rerun_result.v1",
            "namespace": prereg["namespace"],
            "original_family_id": prereg["original_family_id"],
            "status": "INCONCLUSIVE_INSUFFICIENT_ELIGIBLE_UNSEEN_DATA",
            "survives": False,
            "scientific_rejection": False,
            "discovery_sessions": len(disc_s),
            "replication_sessions": len(rep_s),
            "safety": dict(SAFETY),
        }
    contract = prereg["grammar_contract"]
    disc = eval_family(disc_s, contract)
    rep = eval_family(rep_s, contract) if disc["survives"] else {
        "qualified_cells": 0,
        "survives": False,
        "cells": [],
        "not_run_reason": "DISCOVERY_REJECTED",
    }
    survives = bool(disc["survives"] and rep["survives"])
    status = "VALID_SURVIVOR_READY_FOR_SEPARATE_PROSPECTIVE" if survives else "SCIENTIFIC_REJECTION"
    return {
        "schema": "qrds.factory.invalidated_family_rerun_result.v1",
        "namespace": prereg["namespace"],
        "original_family_id": prereg["original_family_id"],
        "status": status,
        "survives": survives,
        "scientific_rejection": not survives,
        "discovery": disc,
        "replication": rep,
        "historical_result_rewritten": False,
        "historical_observations_credited": 0,
        "safety": dict(SAFETY),
    }


def build_queue(root: dict[str, Any], policy: dict[str, Any], results_dir: Path, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    ids = validate_root(root, policy)
    contracts = family_contracts(results_dir)
    missing = [fid for fid in ids if fid not in contracts]
    if missing:
        raise RuntimeError(f"MISSING_FROZEN_CONTRACTS:{len(missing)}:{missing[:5]}")
    prev = {x["original_family_id"]: x for x in (existing or {}).get("families", [])}
    families = []
    for fid in ids:
        old = prev.get(fid) or {}
        families.append({
            "original_family_id": fid,
            "new_namespace": old.get("new_namespace"),
            "status": old.get("status", "WAITING_SOURCE_QUALIFICATION"),
            "attempts": int(old.get("attempts", 0)),
            "result_path": old.get("result_path"),
            "prospective_candidate_path": old.get("prospective_candidate_path"),
            "source_gate_id": old.get("source_gate_id"),
            "source_gate_status": old.get("source_gate_status"),
        })
    return {
        "schema": "qrds.factory.invalidated_family_requalification_queue.v1",
        "mode": "AFFECTED_FAMILIES_INDEPENDENT_SOURCE_GATES",
        "affected_family_count": len(ids),
        "queued_family_count": len(families),
        "families": families,
        "safety": dict(SAFETY),
        "updated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def run_all(root: dict[str, Any], policy: dict[str, Any], results_dir: Path, gate: dict[str, Any] | None,
            dataset: Path | None, runtime_dir: Path, existing: dict[str, Any] | None = None,
            scoped_sources: list[tuple[dict[str, Any], Path | None]] | None = None) -> dict[str, Any]:
    queue = build_queue(root, policy, results_dir, existing)
    scoped_sources = scoped_sources or []
    contracts = family_contracts(results_dir)
    session_cache: dict[str, dict[str, Any]] = {}

    for row in queue["families"]:
        if row.get("status") in TERMINAL:
            continue
        fid = row["original_family_id"]
        selected_gate, selected_dataset, gate_reason = select_source_for_family(
            fid, gate, dataset, scoped_sources
        )
        row["source_gate_status"] = gate_reason
        if selected_gate is None or selected_dataset is None:
            row["status"] = "WAITING_SOURCE_QUALIFICATION"
            continue
        row["source_gate_id"] = selected_gate.get("source_gate_id")
        cache_key = str(selected_dataset.resolve()) + ":" + str(selected_gate.get("dataset_sha256"))
        if cache_key not in session_cache:
            session_cache[cache_key] = load_data(selected_dataset)
        sessions = session_cache[cache_key]
        prereg = prereg_for(fid, contracts[fid], selected_gate)
        ns = prereg["namespace"].replace("::", "__")
        pdir = runtime_dir / "preregistrations"
        rdir = runtime_dir / "results"
        cdir = runtime_dir / "prospective_candidates"
        prereg_path = pdir / f"{ns}.json"
        result_path = rdir / f"{ns}.json"
        dump(prereg_path, prereg)
        result = evaluate_one(prereg, sessions)
        dump(result_path, result)
        row["new_namespace"] = prereg["namespace"]
        row["attempts"] = int(row.get("attempts", 0)) + 1
        row["status"] = result["status"]
        row["result_path"] = str(result_path)
        if result.get("survives") is True:
            candidate = {
                "schema": "qrds.factory.requalified_survivor_prospective_candidate.v1",
                "namespace": prereg["namespace"],
                "original_family_id": fid,
                "mode": "SEPARATE_FORWARD_ONLY_SHADOW_LEDGER",
                "pattern": "H31_STYLE_SEPARATE_PROSPECTIVE",
                "start_clock": "FIRST_ELIGIBLE_OBSERVATION_AFTER_VALID_FREEZE",
                "historical_observations_credited": 0,
                "backfill": False,
                "h1_dependency": "NONE_FOR_BINDING",
                "h1_economics_read": False,
                "paper_or_real_orders_authorized": False,
                "safety": dict(SAFETY),
            }
            cpath = cdir / f"{ns}.json"
            dump(cpath, candidate)
            row["prospective_candidate_path"] = str(cpath)

    queue["completed_family_count"] = sum(1 for x in queue["families"] if x["status"] in TERMINAL)
    queue["survivor_count"] = sum(1 for x in queue["families"] if x["status"] == "VALID_SURVIVOR_READY_FOR_SEPARATE_PROSPECTIVE")
    queue["inconclusive_count"] = sum(1 for x in queue["families"] if str(x["status"]).startswith("INCONCLUSIVE"))
    queue["waiting_source_count"] = sum(1 for x in queue["families"] if x["status"] == "WAITING_SOURCE_QUALIFICATION")
    queue["green_source_family_count"] = sum(1 for x in queue["families"] if str(x.get("source_gate_status", "")).startswith("SOURCE_GATE_GREEN"))
    queue["scoped_source_gate_count"] = len(scoped_sources)
    global_green, global_reason = validate_source_gate(gate or {}, dataset)
    queue["source_gate_status"] = global_reason
    queue["source_gate_green"] = global_green
    queue["updated_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return queue


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root-cause", type=Path, required=True)
    ap.add_argument("--policy", type=Path, required=True)
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--source-gate", type=Path)
    ap.add_argument("--source-gates-dir", type=Path)
    ap.add_argument("--dataset", type=Path)
    ap.add_argument("--existing", type=Path)
    ap.add_argument("--runtime-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ns = ap.parse_args()
    root = load(ns.root_cause)
    policy = load(ns.policy)
    gate = load(ns.source_gate) if ns.source_gate and ns.source_gate.is_file() else None
    existing = load(ns.existing) if ns.existing and ns.existing.is_file() else None
    scoped_sources = load_scoped_sources(ns.source_gates_dir, ns.runtime_dir)
    out = run_all(root, policy, ns.results_dir, gate, ns.dataset, ns.runtime_dir, existing, scoped_sources)
    dump(ns.output, out)
    print(f"AFFECTED_FAMILIES={out['affected_family_count']}")
    print(f"SOURCE_GATE={out['source_gate_status']}")
    print(f"GREEN_SOURCE_FAMILIES={out.get('green_source_family_count', 0)}")
    print(f"WAITING_SOURCE={out.get('waiting_source_count', 0)}")
    print(f"COMPLETED={out.get('completed_family_count', 0)}")
    print(f"SURVIVORS={out.get('survivor_count', 0)}")
    print("ORDERS=0")
    print("REAL_CAPITAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
