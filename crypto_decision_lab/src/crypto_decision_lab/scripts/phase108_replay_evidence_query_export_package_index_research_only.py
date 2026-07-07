from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase106_replay_evidence_query_export_manifest_research_only import build_export_manifest
from crypto_decision_lab.scripts.phase107_replay_evidence_query_export_dry_run_research_only import build_export_dry_run

READY_GATE = "PHASE108_REPLAY_EVIDENCE_QUERY_EXPORT_PACKAGE_INDEX_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_package_index(project_root: str | Path | None = None) -> dict[str, Any]:
    manifest = build_export_manifest(project_root)
    dry_run = build_export_dry_run(project_root)

    package_items = [
        {
            "id": "EXPORT_MANIFEST",
            "gate": manifest["gate"],
            "status": "PASS_RESEARCH_ONLY" if manifest["export_manifest_pass"] else "NEEDS_REVIEW_RESEARCH_ONLY",
            "source_phase": 106,
        },
        {
            "id": "EXPORT_DRY_RUN",
            "gate": dry_run["gate"],
            "status": "PASS_RESEARCH_ONLY" if dry_run["dry_run_pass"] else "NEEDS_REVIEW_RESEARCH_ONLY",
            "source_phase": 107,
        },
    ]

    failed = [item for item in package_items if item["status"] != "PASS_RESEARCH_ONLY"]

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "package_index_name": "replay_evidence_query_export_package_index_106_108",
        "package_items": package_items,
        "failed_items": failed,
        "allowed_export_count": dry_run["allowed_export_count"],
        "blocked_export_count": dry_run["blocked_export_count"],
        "blocked_exports": [
            item["target"]
            for item in dry_run["export_attempts"]
            if item["allowed"] is False
        ],
        "package_index_pass": len(failed) == 0 and dry_run["blocked_export_count"] == 2,
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def render_markdown(package_index: dict[str, Any]) -> str:
    rows = "\n".join(
        f"| {item['id']} | {item['source_phase']} | {item['status']} | {item['gate']} |"
        for item in package_index["package_items"]
    )
    blocked = ", ".join(package_index["blocked_exports"])

    return f"""# Replay Evidence Query Export Package Index Research-Only

Gate: `{READY_GATE}`

| Item | Source Phase | Status | Gate |
|---|---:|---:|---|
{rows}

Blocked exports: {blocked}

Locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- decision_layer_allowed: False
- trading_signal_generated: False
- allocation_generated: False
- safe_apply_allowed: False
- promotion_allowed: False
- canonical_data_writes: 0
"""

def build_phase108(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase108_replay_evidence_query_export_package_index_research_only"
    out.mkdir(parents=True, exist_ok=True)

    package_index = build_package_index()
    (out / "phase108_replay_evidence_query_export_package_index.json").write_text(
        json.dumps(package_index, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase108_replay_evidence_query_export_package_index.md").write_text(
        render_markdown(package_index),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": package_index["package_index_pass"],
        "package_index": package_index,
        **LOCKS,
    }

def main() -> int:
    result = build_phase108()
    package_index = result["package_index"]

    print(result["gate"])
    print("Package index pass:", package_index["package_index_pass"])
    print("Allowed export count:", package_index["allowed_export_count"])
    print("Blocked export count:", package_index["blocked_export_count"])
    print("Blocked exports:", package_index["blocked_exports"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if package_index["package_index_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
