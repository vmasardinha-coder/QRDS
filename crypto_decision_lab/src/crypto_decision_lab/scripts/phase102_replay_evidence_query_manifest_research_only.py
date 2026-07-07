from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase101_replay_evidence_query_index_research_only import build_query_index

READY_GATE = "PHASE102_REPLAY_EVIDENCE_QUERY_MANIFEST_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

QUERY_ROUTES = [
    {"route": "by_phase", "description": "Find evidence artifacts by phase number.", "allowed": True},
    {"route": "by_tag", "description": "Find evidence artifacts by descriptive tag.", "allowed": True},
    {"route": "by_checkpoint", "description": "Find checkpoint artifacts and summaries.", "allowed": True},
    {"route": "by_review_status", "description": "Find NEEDS_REVIEW or indexed artifacts.", "allowed": True},
    {"route": "decision_query", "description": "Blocked: cannot ask evidence layer for trade decisions.", "allowed": False},
    {"route": "signal_query", "description": "Blocked: cannot ask evidence layer for signals.", "allowed": False},
    {"route": "allocation_query", "description": "Blocked: cannot ask evidence layer for allocations.", "allowed": False},
]

def build_query_manifest(project_root: str | Path | None = None) -> dict[str, Any]:
    index = build_query_index(project_root)

    tag_counts: dict[str, int] = {}
    for entry in index["entries"]:
        for tag in entry["tags"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    blocked_routes = [route for route in QUERY_ROUTES if route["allowed"] is False]

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_name": "replay_evidence_query_manifest_84_101",
        "source_index_gate": index["gate"],
        "source_index_pass": index["query_index_pass"],
        "phase_start": index["phase_start"],
        "phase_end": index["phase_end"],
        "phase_count": index["phase_count"],
        "query_routes": QUERY_ROUTES,
        "blocked_routes": blocked_routes,
        "tag_counts": dict(sorted(tag_counts.items())),
        "manifest_pass": index["query_index_pass"] is True and len(blocked_routes) == 3,
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase102(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase102_replay_evidence_query_manifest_research_only"
    out.mkdir(parents=True, exist_ok=True)

    manifest = build_query_manifest()
    (out / "phase102_replay_evidence_query_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": manifest["manifest_pass"],
        "manifest": manifest,
        **LOCKS,
    }

def main() -> int:
    result = build_phase102()
    manifest = result["manifest"]

    print(result["gate"])
    print("Manifest pass:", manifest["manifest_pass"])
    print("Source index pass:", manifest["source_index_pass"])
    print("Blocked routes:", [route["route"] for route in manifest["blocked_routes"]])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if manifest["manifest_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
