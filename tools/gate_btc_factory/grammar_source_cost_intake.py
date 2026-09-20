#!/usr/bin/env python3
"""Transport immutable Grammar Scout preregistrations into source/cost qualification intake.

Separate semantic preregistrations may supply feature/window/lookback/target for legacy
preregistrations, but only when identity matches exactly and each semantic artifact proves
it was frozen outcome-blind before Source/Cost qualification. No outcomes/economics are read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "NO_RETUNE": True,
    "NO_BACKFILL": True,
    "NO_COUNTER_RESET": True,
    "FAIL_CLOSED": True,
    "H1_H31_UNTOUCHED": True,
}

REQUIRED_FROZEN_SEMANTICS = ("feature", "window", "lookback", "target")
SEMANTIC_SCHEMA = "qrds.factory.grammar_semantic_prereg.v1"
SEMANTIC_GLOB = "GRAMMAR_*_SEMANTIC_PREREG.v1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _has_complete_frozen_semantics_value(semantics: object) -> bool:
    if not isinstance(semantics, dict):
        return False
    return all(k in semantics and semantics[k] not in (None, "", [], {}) for k in REQUIRED_FROZEN_SEMANTICS)


def _has_complete_frozen_semantics(d: dict) -> bool:
    return _has_complete_frozen_semantics_value(d.get("frozen_semantics"))


def _semantic_paths(path: Path | None) -> list[Path]:
    if path is None:
        return []
    if path.match(SEMANTIC_GLOB):
        siblings = sorted(path.parent.glob(SEMANTIC_GLOB))
        if path not in siblings:
            siblings.append(path)
            siblings.sort()
        return siblings
    return [path]


def _semantic_index(path: Path | None) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    seen_signatures: set[str] = set()
    for semantic_path in _semantic_paths(path):
        d = load(semantic_path)
        if d.get("schema") != SEMANTIC_SCHEMA:
            raise ValueError("FAIL_CLOSED: unexpected semantic prereg schema")
        if d.get("frozen_before_source_cost") is not True or d.get("outcome_blind") is not True:
            raise ValueError("FAIL_CLOSED: semantic prereg not frozen outcome-blind before source/cost")
        if d.get("economics_read") is not False or d.get("historical_testing_started") is not False:
            raise ValueError("FAIL_CLOSED: semantic prereg already opened economics/history")
        safety = d.get("safety")
        if not isinstance(safety, dict) or any(safety.get(k) != v for k, v in SAFETY.items()):
            raise ValueError("FAIL_CLOSED: semantic prereg safety mismatch")
        semantic_sha = sha256(semantic_path)
        for raw in d.get("families", []):
            row = dict(raw)
            fid = row.get("family_id")
            sig = row.get("grammar_signature")
            if not fid or not sig or fid in rows or sig in seen_signatures:
                raise ValueError("FAIL_CLOSED: missing/duplicate semantic prereg identity")
            if not _has_complete_frozen_semantics(row):
                raise ValueError(f"FAIL_CLOSED: incomplete semantic prereg: {fid}")
            row["_semantic_prereg_path"] = str(semantic_path)
            row["_semantic_prereg_sha256"] = semantic_sha
            rows[fid] = row
            seen_signatures.add(sig)
    return rows


def build(prereg_dir: Path, semantic_prereg: Path | None = None) -> dict:
    rows = []
    seen_signatures = set()
    seen_family_ids = set()
    semantic_rows = _semantic_index(semantic_prereg)
    if prereg_dir.exists():
        for path in sorted(prereg_dir.glob("XAGRAMMAR_*.json")):
            d = load(path)
            if d.get("schema") != "qrds.factory.grammar_scout_separate_prereg.v1":
                raise ValueError(f"FAIL_CLOSED: unexpected prereg schema: {path}")
            if d.get("status") != "PREREGISTERED_AWAITING_SOURCE_COST_QUALIFICATION":
                raise ValueError(f"FAIL_CLOSED: unexpected prereg status: {path}")
            if d.get("economics_read") is not False or d.get("historical_testing_started") is not False:
                raise ValueError(f"FAIL_CLOSED: prereg already opened economics/history: {path}")
            if d.get("source_qualification_required") is not True or d.get("cost_applicability_required") is not True:
                raise ValueError(f"FAIL_CLOSED: source/cost gate missing: {path}")
            sig = d.get("grammar_signature")
            fid = d.get("family_id")
            if not sig or sig in seen_signatures or not fid or fid in seen_family_ids:
                raise ValueError(f"FAIL_CLOSED: missing/duplicate grammar identity: {path}")
            seen_signatures.add(sig)
            seen_family_ids.add(fid)

            semantics = d.get("frozen_semantics") if _has_complete_frozen_semantics(d) else None
            semantic_source = "ORIGINAL_PREREGISTRATION" if semantics is not None else None
            semantic_row = semantic_rows.get(fid)
            if semantic_row is not None:
                if semantic_row.get("grammar_signature") != sig or semantic_row.get("channel_id") != d.get("channel_id"):
                    raise ValueError(f"FAIL_CLOSED: semantic prereg identity mismatch: {fid}")
                separate_semantics = semantic_row["frozen_semantics"]
                if semantics is not None and semantics != separate_semantics:
                    raise ValueError(f"FAIL_CLOSED: conflicting frozen semantics: {fid}")
                semantics = separate_semantics
                semantic_source = "SEPARATE_OUTCOME_BLIND_SEMANTIC_PREREG_V1"

            semantics_ready = _has_complete_frozen_semantics_value(semantics)
            status = "QUEUED_FOR_SOURCE_COST_QUALIFICATION" if semantics_ready else "BLOCKED_PREREG_SEMANTICS_UNDECIDABLE"
            next_stage = (
                "QUALIFY_SOURCE_AND_COST_BEFORE_EXISTING_FACTORY"
                if semantics_ready
                else "SEPARATE_SEMANTIC_PREREGISTRATION_REQUIRED_BEFORE_SOURCE_COST"
            )
            row = {
                "family_id": fid,
                "grammar_signature": sig,
                "channel_id": d.get("channel_id"),
                "mechanism": d.get("mechanism"),
                "required_new_data": d.get("required_new_data", []),
                "official_free_source_candidates": d.get("official_free_source_candidates", []),
                "prereg_path": str(path),
                "prereg_sha256": sha256(path),
                "status": status,
                "semantic_preregistration_complete": semantics_ready,
                "required_frozen_semantics": list(REQUIRED_FROZEN_SEMANTICS),
                "source_qualified": False,
                "cost_applicability_proven": False,
                "economics_read": False,
                "historical_testing_started": False,
                "next_stage": next_stage,
            }
            if semantics_ready:
                row["frozen_semantics"] = semantics
                row["semantic_source"] = semantic_source
                if semantic_row is not None and semantic_source == "SEPARATE_OUTCOME_BLIND_SEMANTIC_PREREG_V1":
                    row["semantic_prereg_path"] = semantic_row["_semantic_prereg_path"]
                    row["semantic_prereg_sha256"] = semantic_row["_semantic_prereg_sha256"]
            else:
                row["blocker_reason"] = "SOURCE_COST_PROTOCOL_REQUIRES_ALREADY_FROZEN_FEATURE_WINDOW_LOOKBACK_TARGET"
            rows.append(row)

    orphan_semantics = sorted(set(semantic_rows) - seen_family_ids)
    if orphan_semantics:
        raise ValueError(f"FAIL_CLOSED: semantic prereg family not present in immutable prereg ledger: {orphan_semantics}")

    return {
        "schema": "qrds.factory.grammar_source_cost_intake_runtime.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "CUMULATIVE_PREREG_TO_SOURCE_COST_GATE_ONLY",
        "transported_count": len(rows),
        "semantic_ready_count": sum(x["semantic_preregistration_complete"] for x in rows),
        "semantic_prereg_applied_count": sum(x.get("semantic_source") == "SEPARATE_OUTCOME_BLIND_SEMANTIC_PREREG_V1" for x in rows),
        "blocked_semantics_count": sum(not x["semantic_preregistration_complete"] for x in rows),
        "families": rows,
        "next_stage": "SOURCE_COST_QUALIFICATION_THEN_EXISTING_FACTORY",
        "safety": SAFETY,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg-dir", required=True)
    ap.add_argument("--semantic-prereg")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = build(Path(args.prereg_dir), Path(args.semantic_prereg) if args.semantic_prereg else None)
    Path(args.output).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "transported_count": out["transported_count"],
        "semantic_ready_count": out["semantic_ready_count"],
        "semantic_prereg_applied_count": out["semantic_prereg_applied_count"],
        "blocked_semantics_count": out["blocked_semantics_count"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
