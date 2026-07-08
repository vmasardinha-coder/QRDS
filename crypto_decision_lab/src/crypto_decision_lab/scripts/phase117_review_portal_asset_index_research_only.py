from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase114_replay_evidence_export_review_portal_stub_research_only import build_phase114
from crypto_decision_lab.scripts.phase116_export_review_runbook_research_only import build_phase116

READY_GATE = "PHASE117_REVIEW_PORTAL_ASSET_INDEX_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_asset_index(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()

    portal = build_phase114(root / "artifacts" / "phase114_replay_evidence_export_review_portal_stub_research_only")
    runbook = build_phase116(root / "artifacts" / "phase116_export_review_runbook_research_only")

    assets = [
        {
            "asset_id": "review_portal_html",
            "phase": 114,
            "path": "artifacts/phase114_replay_evidence_export_review_portal_stub_research_only/phase114_replay_evidence_export_review_portal_stub.html",
            "asset_type": "html",
            "required": True,
            "operational_effect": "NONE_RESEARCH_ONLY",
        },
        {
            "asset_id": "review_portal_json",
            "phase": 114,
            "path": "artifacts/phase114_replay_evidence_export_review_portal_stub_research_only/phase114_replay_evidence_export_review_portal_stub.json",
            "asset_type": "json",
            "required": True,
            "operational_effect": "NONE_RESEARCH_ONLY",
        },
        {
            "asset_id": "export_review_runbook_md",
            "phase": 116,
            "path": "artifacts/phase116_export_review_runbook_research_only/phase116_export_review_runbook.md",
            "asset_type": "markdown",
            "required": True,
            "operational_effect": "NONE_RESEARCH_ONLY",
        },
        {
            "asset_id": "export_review_runbook_json",
            "phase": 116,
            "path": "artifacts/phase116_export_review_runbook_research_only/phase116_export_review_runbook.json",
            "asset_type": "json",
            "required": True,
            "operational_effect": "NONE_RESEARCH_ONLY",
        },
    ]

    missing = [asset for asset in assets if not (root / asset["path"]).exists()]

    index_pass = (
        portal["ready"] is True
        and runbook["ready"] is True
        and len(missing) == 0
        and all(asset["operational_effect"] == "NONE_RESEARCH_ONLY" for asset in assets)
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "asset_index_name": "review_portal_asset_index_research_only",
        "source_portal_gate": portal["gate"],
        "source_runbook_gate": runbook["gate"],
        "assets": assets,
        "asset_count": len(assets),
        "missing_assets": missing,
        "asset_index_pass": index_pass,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase117(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase117_review_portal_asset_index_research_only"
    out.mkdir(parents=True, exist_ok=True)

    index = build_asset_index()
    (out / "phase117_review_portal_asset_index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": index["asset_index_pass"], "asset_index": index, **LOCKS}

def main() -> int:
    result = build_phase117()
    index = result["asset_index"]

    print(result["gate"])
    print("Asset index pass:", index["asset_index_pass"])
    print("Asset count:", index["asset_count"])
    print("Missing assets:", index["missing_assets"])
    print("Approval effect:", index["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if index["asset_index_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
