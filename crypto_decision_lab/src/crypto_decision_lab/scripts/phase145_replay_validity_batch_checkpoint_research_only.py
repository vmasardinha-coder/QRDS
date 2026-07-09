from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase141_replay_validity_requirement_registry_research_only import build_replay_validity_requirement_registry
from crypto_decision_lab.scripts.phase142_backtest_window_integrity_check_research_only import build_backtest_window_integrity_check
from crypto_decision_lab.scripts.phase143_replay_leakage_guard_research_only import build_replay_leakage_guard
from crypto_decision_lab.scripts.phase144_replay_validity_preflight_research_only import build_replay_validity_preflight

READY_GATE = "PHASE145_REPLAY_VALIDITY_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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
    registry = build_replay_validity_requirement_registry(project_root)
    window = build_backtest_window_integrity_check(project_root)
    leakage = build_replay_leakage_guard(project_root)
    preflight = build_replay_validity_preflight(project_root)

    checks = [
        {"id": "PHASE141_REPLAY_VALIDITY_REQUIREMENT_REGISTRY", "status": registry["registry_pass"]},
        {"id": "PHASE142_BACKTEST_WINDOW_INTEGRITY_CHECK", "status": window["check_pass"]},
        {"id": "PHASE143_REPLAY_LEAKAGE_GUARD", "status": leakage["guard_pass"]},
        {"id": "PHASE144_REPLAY_VALIDITY_PREFLIGHT", "status": preflight["preflight_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        registry["approval_effect"] == "NONE_RESEARCH_ONLY"
        and window["approval_effect"] == "NONE_RESEARCH_ONLY"
        and leakage["approval_effect"] == "NONE_RESEARCH_ONLY"
        and preflight["approval_effect"] == "NONE_RESEARCH_ONLY"
        and preflight["boundaries_ok"] is True
        and preflight["edge_validated"] is False
        and preflight["edge_operationally_validated"] is False
        and preflight["decision_layer_allowed"] is False
        and preflight["trading_signal_generated"] is False
        and preflight["allocation_generated"] is False
        and preflight["canonical_data_writes"] == 0
    )

    checkpoint_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "replay_validity_batch_checkpoint_141_145",
        "phase_batch": [141, 142, 143, 144, 145],
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "checkpoint_pass": checkpoint_pass,
        "checkpoint_status": "PASS_RESEARCH_ONLY" if checkpoint_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "replay_validity_status": "REPLAY_VALIDITY_BATCH_READY_RESEARCH_ONLY_UNVALIDATED",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase145(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase145_replay_validity_batch_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    checkpoint = build_checkpoint()
    (out / "phase145_replay_validity_batch_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": checkpoint["checkpoint_pass"], "checkpoint": checkpoint, **LOCKS}

def main() -> int:
    result = build_phase145()
    checkpoint = result["checkpoint"]

    print(result["gate"])
    print("Checkpoint pass:", checkpoint["checkpoint_pass"])
    print("Checkpoint status:", checkpoint["checkpoint_status"])
    print("Failed checks:", checkpoint["failed_checks"])
    print("Boundaries ok:", checkpoint["boundaries_ok"])
    print("Replay validity status:", checkpoint["replay_validity_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge validated: False")
    print("Edge operationally validated: False")
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
