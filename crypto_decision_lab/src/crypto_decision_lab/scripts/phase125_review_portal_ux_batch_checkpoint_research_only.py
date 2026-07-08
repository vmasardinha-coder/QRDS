from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase121_review_portal_index_page_research_only import build_index_page
from crypto_decision_lab.scripts.phase122_serve_root_fix_research_only import build_serve_root_fix
from crypto_decision_lab.scripts.phase123_portal_link_smoke_test_research_only import build_link_smoke_test
from crypto_decision_lab.scripts.phase124_one_command_review_portal_runner_research_only import build_runner

READY_GATE = "PHASE125_REVIEW_PORTAL_UX_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_checkpoint(project_root: str | Path | None = None) -> dict[str, Any]:
    index = build_index_page(project_root)
    serve_fix = build_serve_root_fix(project_root)
    link_smoke = build_link_smoke_test(project_root)
    runner = build_runner(project_root)

    checks = [
        {"id": "PHASE121_REVIEW_PORTAL_INDEX_PAGE", "status": index["index_pass"]},
        {"id": "PHASE122_SERVE_ROOT_FIX", "status": serve_fix["serve_root_fix_pass"]},
        {"id": "PHASE123_PORTAL_LINK_SMOKE_TEST", "status": link_smoke["link_smoke_pass"]},
        {"id": "PHASE124_ONE_COMMAND_REVIEW_PORTAL_RUNNER", "status": runner["runner_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        index["approval_effect"] == "NONE_RESEARCH_ONLY"
        and serve_fix["approval_effect"] == "NONE_RESEARCH_ONLY"
        and link_smoke["approval_effect"] == "NONE_RESEARCH_ONLY"
        and runner["approval_effect"] == "NONE_RESEARCH_ONLY"
        and runner["canonical_data_writes"] == 0
        and runner["trading_signal_generated"] is False
        and runner["allocation_generated"] is False
        and runner["decision_layer_allowed"] is False
    )

    checkpoint_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "review_portal_ux_batch_checkpoint_121_125",
        "phase_batch": [121, 122, 123, 124, 125],
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "checkpoint_pass": checkpoint_pass,
        "checkpoint_status": "PASS_RESEARCH_ONLY" if checkpoint_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "local_index_url": "http://localhost:8765/index.html",
        "local_review_url": "http://localhost:8765/phase114_replay_evidence_export_review_portal_stub.html",
        "runner_script_path": "tools/run_review_portal_research_only.ps1",
        "serve_script_path": "tools/serve_review_portal_research_only.ps1",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase125(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase125_review_portal_ux_batch_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    checkpoint = build_checkpoint()
    (out / "phase125_review_portal_ux_batch_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": checkpoint["checkpoint_pass"],
        "checkpoint": checkpoint,
        **LOCKS,
    }

def main() -> int:
    result = build_phase125()
    checkpoint = result["checkpoint"]

    print(result["gate"])
    print("Checkpoint pass:", checkpoint["checkpoint_pass"])
    print("Checkpoint status:", checkpoint["checkpoint_status"])
    print("Failed checks:", checkpoint["failed_checks"])
    print("Boundaries ok:", checkpoint["boundaries_ok"])
    print("Local index URL:", checkpoint["local_index_url"])
    print("Runner script:", checkpoint["runner_script_path"])
    print("Approval effect:", checkpoint["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if checkpoint["checkpoint_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
