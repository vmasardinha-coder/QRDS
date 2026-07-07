from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase96_replay_evidence_artifact_inventory_research_only import build_inventory
from crypto_decision_lab.scripts.phase97_replay_evidence_artifact_integrity_digest_research_only import build_digest

READY_GATE = "PHASE98_REPLAY_EVIDENCE_DRIFT_SENTINEL_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_drift_sentinel(project_root: str | Path | None = None) -> dict[str, Any]:
    inventory = build_inventory(project_root)
    digest = build_digest(project_root)

    inventory_phases = [entry["phase"] for entry in inventory["entries"]]
    digest_phases = [entry["phase"] for entry in digest["entries"]]

    phase_alignment_ok = inventory_phases == digest_phases[: len(inventory_phases)]
    inventory_ok = inventory["inventory_pass"] is True
    digest_ok = digest["digest_pass"] is True
    combined_digest_present = isinstance(digest.get("combined_sha256"), str) and len(digest["combined_sha256"]) == 64

    drift_findings = []
    if not inventory_ok:
        drift_findings.append("inventory_needs_review")
    if not digest_ok:
        drift_findings.append("digest_needs_review")
    if not phase_alignment_ok:
        drift_findings.append("phase_alignment_mismatch")
    if not combined_digest_present:
        drift_findings.append("combined_digest_missing_or_invalid")

    drift_status = "NO_DRIFT_RESEARCH_ONLY" if not drift_findings else "NEEDS_REVIEW_RESEARCH_ONLY"

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sentinel_name": "replay_evidence_drift_sentinel_84_97",
        "inventory_gate": inventory["gate"],
        "digest_gate": digest["gate"],
        "inventory_phase_start": inventory["phase_start"],
        "inventory_phase_end": inventory["phase_end"],
        "digest_phase_start": digest["phase_start"],
        "digest_phase_end": digest["phase_end"],
        "inventory_pass": inventory_ok,
        "digest_pass": digest_ok,
        "phase_alignment_ok": phase_alignment_ok,
        "combined_digest_present": combined_digest_present,
        "combined_sha256": digest["combined_sha256"],
        "drift_findings": drift_findings,
        "drift_status": drift_status,
        "sentinel_pass": drift_status == "NO_DRIFT_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase98(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase98_replay_evidence_drift_sentinel_research_only"
    out.mkdir(parents=True, exist_ok=True)

    sentinel = build_drift_sentinel()
    (out / "phase98_replay_evidence_drift_sentinel.json").write_text(
        json.dumps(sentinel, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": sentinel["sentinel_pass"],
        "sentinel": sentinel,
        **LOCKS,
    }

def main() -> int:
    result = build_phase98()
    sentinel = result["sentinel"]

    print(result["gate"])
    print("Sentinel pass:", sentinel["sentinel_pass"])
    print("Drift status:", sentinel["drift_status"])
    print("Drift findings:", sentinel["drift_findings"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if sentinel["sentinel_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
