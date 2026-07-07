from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE96_REPLAY_EVIDENCE_ARTIFACT_INVENTORY_RESEARCH_ONLY_READY_RESEARCH_ONLY"

PHASES = list(range(84, 96))

LOCKS = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
    "edge_operationally_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}

def build_inventory(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()

    script_dir = root / "src" / "crypto_decision_lab" / "scripts"
    test_dir = root / "tests" / "unit"
    doc_dir = root / "docs" / "reports" / "journal_replay"

    entries = []
    for phase in PHASES:
        script_matches = sorted(script_dir.glob(f"phase{phase}_*_research_only.py"))
        test_matches = sorted(test_dir.glob(f"test_phase{phase}_*_research_only.py"))
        doc_matches = sorted(doc_dir.glob(f"phase{phase}_*"))

        entries.append({
            "phase": phase,
            "script_count": len(script_matches),
            "test_count": len(test_matches),
            "doc_count": len(doc_matches),
            "script_files": [p.name for p in script_matches],
            "test_files": [p.name for p in test_matches],
            "doc_files": [p.name for p in doc_matches],
            "inventory_status": "PRESENT_RESEARCH_ONLY" if script_matches and test_matches else "NEEDS_REVIEW_RESEARCH_ONLY",
        })

    needs_review = [entry["phase"] for entry in entries if entry["inventory_status"] != "PRESENT_RESEARCH_ONLY"]

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "inventory_name": "replay_evidence_artifact_inventory_84_95",
        "phase_start": 84,
        "phase_end": 95,
        "phase_count": len(entries),
        "entries": entries,
        "needs_review_phases": needs_review,
        "inventory_pass": len(needs_review) == 0,
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase96(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase96_replay_evidence_artifact_inventory_research_only"
    out.mkdir(parents=True, exist_ok=True)

    inventory = build_inventory()
    (out / "phase96_replay_evidence_artifact_inventory.json").write_text(
        json.dumps(inventory, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": inventory["inventory_pass"],
        "inventory": inventory,
        **LOCKS,
    }

def main() -> int:
    result = build_phase96()
    inventory = result["inventory"]

    print(result["gate"])
    print("Inventory pass:", inventory["inventory_pass"])
    print("Needs review phases:", inventory["needs_review_phases"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if inventory["inventory_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
