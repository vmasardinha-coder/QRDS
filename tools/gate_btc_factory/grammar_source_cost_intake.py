#!/usr/bin/env python3
"""Transport immutable Grammar Scout preregistrations into source/cost qualification intake.

This is plumbing only. It never qualifies a source, fixes costs, reads outcomes/economics,
allocates an existing H id, or starts historical testing. It makes the cumulative
preregistration ledger visible to the next scientific gate without depending on the
incremental handoff batch from the current run.
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

# The frozen Source/Cost 006 protocol can only adjudicate granularity when these
# semantics already exist in the preregistration. Never infer them from source data.
REQUIRED_FROZEN_SEMANTICS = ("feature", "window", "lookback", "target")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _has_complete_frozen_semantics(d: dict) -> bool:
    semantics = d.get("frozen_semantics")
    if not isinstance(semantics, dict):
        return False
    return all(k in semantics and semantics[k] not in (None, "", [], {}) for k in REQUIRED_FROZEN_SEMANTICS)


def build(prereg_dir: Path) -> dict:
    rows = []
    seen_signatures = set()
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
            if not sig or sig in seen_signatures:
                raise ValueError(f"FAIL_CLOSED: missing/duplicate grammar signature: {path}")
            seen_signatures.add(sig)
            semantics_ready = _has_complete_frozen_semantics(d)
            status = "QUEUED_FOR_SOURCE_COST_QUALIFICATION" if semantics_ready else "BLOCKED_PREREG_SEMANTICS_UNDECIDABLE"
            next_stage = (
                "QUALIFY_SOURCE_AND_COST_BEFORE_EXISTING_FACTORY"
                if semantics_ready
                else "SEPARATE_SEMANTIC_PREREGISTRATION_REQUIRED_BEFORE_SOURCE_COST"
            )
            row = {
                "family_id": d.get("family_id"),
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
                row["frozen_semantics"] = d["frozen_semantics"]
            else:
                row["blocker_reason"] = "SOURCE_COST_PROTOCOL_REQUIRES_ALREADY_FROZEN_FEATURE_WINDOW_LOOKBACK_TARGET"
            rows.append(row)
    return {
        "schema": "qrds.factory.grammar_source_cost_intake_runtime.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "CUMULATIVE_PREREG_TO_SOURCE_COST_GATE_ONLY",
        "transported_count": len(rows),
        "semantic_ready_count": sum(x["semantic_preregistration_complete"] for x in rows),
        "blocked_semantics_count": sum(not x["semantic_preregistration_complete"] for x in rows),
        "families": rows,
        "next_stage": "SOURCE_COST_QUALIFICATION_THEN_EXISTING_FACTORY",
        "safety": SAFETY,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg-dir", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = build(Path(args.prereg_dir))
    Path(args.output).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "transported_count": out["transported_count"],
        "semantic_ready_count": out["semantic_ready_count"],
        "blocked_semantics_count": out["blocked_semantics_count"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
