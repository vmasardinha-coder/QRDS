from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase106_replay_evidence_query_export_manifest_research_only import (
    build_export_manifest,
)

READY_GATE = "PHASE107_REPLAY_EVIDENCE_QUERY_EXPORT_DRY_RUN_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_export_dry_run(project_root: str | Path | None = None) -> dict[str, Any]:
    manifest = build_export_manifest(project_root)

    export_attempts = []
    for target in manifest["export_targets"]:
        export_attempts.append({
            "target": target["name"],
            "format": target["format"],
            "allowed": target["allowed"],
            "dry_run_status": "EXPORT_DRY_RUN_ALLOWED_RESEARCH_ONLY" if target["allowed"] else "EXPORT_BLOCKED_RESEARCH_ONLY",
            "writes_canonical_data": False,
            "generates_signal": False,
            "generates_allocation": False,
        })

    blocked = [item for item in export_attempts if item["allowed"] is False]
    allowed = [item for item in export_attempts if item["allowed"] is True]

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dry_run_name": "replay_evidence_query_export_dry_run_106_107",
        "source_manifest_gate": manifest["gate"],
        "source_manifest_pass": manifest["export_manifest_pass"],
        "export_attempts": export_attempts,
        "allowed_export_count": len(allowed),
        "blocked_export_count": len(blocked),
        "dry_run_pass": (
            manifest["export_manifest_pass"] is True
            and len(allowed) == 3
            and len(blocked) == 2
            and all(item["writes_canonical_data"] is False for item in export_attempts)
            and all(item["generates_signal"] is False for item in export_attempts)
            and all(item["generates_allocation"] is False for item in export_attempts)
        ),
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def render_markdown(dry_run: dict[str, Any]) -> str:
    rows = "\n".join(
        f"| {item['target']} | {item['format']} | {item['allowed']} | {item['dry_run_status']} |"
        for item in dry_run["export_attempts"]
    )

    return f"""# Replay Evidence Query Export Dry-Run Research-Only

Gate: `{READY_GATE}`

Source manifest: `{dry_run['source_manifest_gate']}`

| Target | Format | Allowed | Status |
|---|---:|---:|---|
{rows}

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

def build_phase107(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase107_replay_evidence_query_export_dry_run_research_only"
    out.mkdir(parents=True, exist_ok=True)

    dry_run = build_export_dry_run()
    (out / "phase107_replay_evidence_query_export_dry_run.json").write_text(
        json.dumps(dry_run, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase107_replay_evidence_query_export_dry_run.md").write_text(
        render_markdown(dry_run),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": dry_run["dry_run_pass"],
        "dry_run": dry_run,
        **LOCKS,
    }

def main() -> int:
    result = build_phase107()
    dry_run = result["dry_run"]

    print(result["gate"])
    print("Export dry run pass:", dry_run["dry_run_pass"])
    print("Allowed export count:", dry_run["allowed_export_count"])
    print("Blocked export count:", dry_run["blocked_export_count"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if dry_run["dry_run_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
