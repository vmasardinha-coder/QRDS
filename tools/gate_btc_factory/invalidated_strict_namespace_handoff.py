#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from tools.gate_btc_factory import invalidated_family_requalification_runner as runner

STRICT_NAMESPACE = "RQ_STRICT_FORWARD_UNSEEN_2025_2026_V2"
STRICT_PREFIX = "WIN_M5_STRICT_FORWARD_UNSEEN_2025_2026_BATCH_"
CONTAMINATED_V1_NAMESPACE = "RQ_FORWARD_UNSEEN_2025_2026_V1"
CONTAMINATED_V1_PREFIX = "WIN_M5_FORWARD_UNSEEN_2025_2026_BATCH_"
HOLDOUT_START = "2025-01-01"
CUTOFF_EXCLUSIVE = "2026-08-10"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def contaminated_v1_gate_names(source_gates_dir: Path | None) -> list[str]:
    """Return superseded V1 gates that overlap the original 2020-2024 evaluator.

    They are retained on the runtime branch as immutable audit evidence, but they
    are never eligible for new scientific credit.  The defect is mechanical: the
    gate claimed unseen temporal holdout semantics while its discovery window
    started in 2024.
    """
    if source_gates_dir is None or not source_gates_dir.is_dir():
        return []
    names = []
    for path in sorted(source_gates_dir.glob(f"{CONTAMINATED_V1_PREFIX}*.json")):
        gate = _load(path)
        windows = gate.get("windows") or {}
        discovery = windows.get("discovery") or {}
        start = str(discovery.get("start") or "")
        mode = str((gate.get("source") or {}).get("independence_mode") or "")
        if gate.get("evaluation_namespace") == CONTAMINATED_V1_NAMESPACE and (
            start < HOLDOUT_START or mode == "TEMPORAL_HOLDOUT_NOT_READ_BY_ORIGINAL_2020_2024_EVALUATOR"
        ):
            names.append(path.name)
    return names


def strict_scoped_sources(source_gates_dir: Path | None, runtime_dir: Path):
    if source_gates_dir is None or not source_gates_dir.is_dir():
        return []
    repo_root = runtime_dir.parents[2]
    out = []
    for path in sorted(source_gates_dir.glob(f"{STRICT_PREFIX}*.json")):
        gate = _load(path)
        if gate.get("evaluation_namespace") != STRICT_NAMESPACE:
            raise RuntimeError(f"STRICT_NAMESPACE_MISMATCH:{path.name}")
        windows = gate.get("windows") or {}
        discovery = windows.get("discovery") or {}
        replication = windows.get("replication") or {}
        if str(discovery.get("start") or "") < HOLDOUT_START:
            raise RuntimeError(f"STRICT_DISCOVERY_PRE_HOLDOUT:{path.name}")
        if str(replication.get("start") or "") < HOLDOUT_START:
            raise RuntimeError(f"STRICT_REPLICATION_PRE_HOLDOUT:{path.name}")
        if str(discovery.get("end") or "9999") >= CUTOFF_EXCLUSIVE:
            raise RuntimeError(f"STRICT_DISCOVERY_AFTER_CUTOFF:{path.name}")
        if str(replication.get("end") or "9999") >= CUTOFF_EXCLUSIVE:
            raise RuntimeError(f"STRICT_REPLICATION_AFTER_CUTOFF:{path.name}")
        rel = str(gate.get("dataset_relative_path") or "")
        dataset = repo_root / rel if rel else None
        green, reason = runner.validate_source_gate(gate, dataset)
        if not green:
            raise RuntimeError(f"STRICT_GATE_NOT_GREEN:{path.name}:{reason}")
        out.append((gate, dataset))
    if out:
        ids = [fid for gate, _ in out for fid in gate.get("family_ids") or []]
        if len(out) != 12 or len(ids) != 768 or len(set(ids)) != 768:
            raise RuntimeError(f"STRICT_SCOPE_INCOMPLETE:gates={len(out)}:ids={len(ids)}:unique={len(set(ids))}")
    return out


def prepare_existing(existing: dict | None, strict_sources) -> tuple[dict | None, int]:
    """Remove scientific credit from the known contaminated V1 namespace only.

    Valid discovery-only 2025 terminal rejections remain immutable and terminal.
    Contaminated V1 result files and attempt counters are also preserved; only
    their terminal scientific credit is revoked.  This happens even when no
    strict V2 source is currently green, so lack of a replacement source can
    never make an invalid result look completed.
    """
    if existing is None:
        return None, 0
    strict_by_family = {}
    for gate, _ in strict_sources:
        for fid in gate.get("family_ids") or []:
            strict_by_family[fid] = gate
    prepared = copy.deepcopy(existing)
    invalidated = 0
    for row in prepared.get("families") or []:
        fid = row.get("original_family_id")
        old_ns = str(row.get("new_namespace") or "")
        if row.get("status") in runner.TERMINAL and old_ns == f"{CONTAMINATED_V1_NAMESPACE}::{fid}":
            row["status"] = "WAITING_SOURCE_QUALIFICATION"
            row["source_gate_status"] = "INVALIDATED_2024_OVERLAP_AWAITING_STRICT_V2"
            invalidated += 1
            continue
        # A strict V2 gate may execute an unresolved row, but it must never
        # reopen a terminal result from the valid 2025-only discovery namespace.
        gate = strict_by_family.get(fid)
        wanted_ns = f"{STRICT_NAMESPACE}::{fid}"
        if gate is not None and row.get("status") not in runner.TERMINAL and old_ns != wanted_ns:
            row["source_gate_status"] = "STRICT_V2_SOURCE_AVAILABLE"
    return prepared, invalidated


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root-cause", type=Path, required=True)
    ap.add_argument("--policy", type=Path, required=True)
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--source-gates-dir", type=Path)
    ap.add_argument("--runtime-dir", type=Path, required=True)
    ap.add_argument("--existing", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ns = ap.parse_args()

    root = _load(ns.root_cause)
    policy = _load(ns.policy)
    existing = _load(ns.existing) if ns.existing and ns.existing.is_file() else None
    contaminated_gates = contaminated_v1_gate_names(ns.source_gates_dir)
    strict_sources = strict_scoped_sources(ns.source_gates_dir, ns.runtime_dir)
    prepared, invalidated_v1 = prepare_existing(existing, strict_sources)

    queue = runner.run_all(
        root,
        policy,
        ns.results_dir,
        gate=None,
        dataset=None,
        runtime_dir=ns.runtime_dir,
        existing=prepared,
        scoped_sources=strict_sources,
    )
    queue["authoritative_replay_namespace"] = STRICT_NAMESPACE
    queue["strict_source_gate_count"] = len(strict_sources)
    queue["strict_source_gate_green"] = bool(strict_sources)
    queue["contaminated_v1_credit_invalidated_count"] = invalidated_v1
    queue["contaminated_v1_gate_count"] = len(contaminated_gates)
    queue["contaminated_v1_gates_authoritative"] = False
    runner.dump(ns.output, queue)
    print(json.dumps({
        "strict_gate_count": len(strict_sources),
        "strict_gate_green": bool(strict_sources),
        "contaminated_v1_credit_invalidated": invalidated_v1,
        "contaminated_v1_gate_count": len(contaminated_gates),
        "completed": queue.get("completed_family_count", 0),
        "waiting_source": queue.get("waiting_source_count", 0),
        "survivors": queue.get("survivor_count", 0),
        "orders": 0,
        "real_capital": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
