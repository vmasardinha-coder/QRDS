from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase166_shadow_score_requirement_registry_research_only import build_shadow_score_requirement_registry
from crypto_decision_lab.scripts.phase167_shadow_evidence_scorecard_research_only import build_shadow_evidence_scorecard
from crypto_decision_lab.scripts.phase168_shadow_risk_scorecard_research_only import build_shadow_risk_scorecard
from crypto_decision_lab.scripts.phase169_shadow_score_preflight_research_only import build_shadow_score_preflight

READY_GATE = "PHASE170_SHADOW_SCORE_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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
    registry = build_shadow_score_requirement_registry(project_root)
    evidence = build_shadow_evidence_scorecard(project_root)
    risk = build_shadow_risk_scorecard(project_root)
    preflight = build_shadow_score_preflight(project_root)

    checks = [
        {"id": "PHASE166_SHADOW_SCORE_REQUIREMENT_REGISTRY", "status": registry["registry_pass"]},
        {"id": "PHASE167_SHADOW_EVIDENCE_SCORECARD", "status": evidence["scorecard_pass"]},
        {"id": "PHASE168_SHADOW_RISK_SCORECARD", "status": risk["scorecard_pass"]},
        {"id": "PHASE169_SHADOW_SCORE_PREFLIGHT", "status": preflight["preflight_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    evidence_scorecard = evidence["scorecard"]
    risk_scorecard = risk["risk_scorecard"]

    boundaries_ok = (
        registry["approval_effect"] == "NONE_RESEARCH_ONLY"
        and evidence["approval_effect"] == "NONE_RESEARCH_ONLY"
        and risk["approval_effect"] == "NONE_RESEARCH_ONLY"
        and preflight["approval_effect"] == "NONE_RESEARCH_ONLY"
        and preflight["boundaries_ok"] is True
        and evidence_scorecard["score_is_signal"] is False
        and evidence_scorecard["score_is_recommendation"] is False
        and evidence_scorecard["valid_for_decision"] is False
        and risk_scorecard["risk_score_is_signal"] is False
        and risk_scorecard["risk_score_is_recommendation"] is False
        and risk_scorecard["valid_for_decision"] is False
        and preflight["score_is_signal"] is False
        and preflight["score_is_recommendation"] is False
        and preflight["valid_for_decision"] is False
        and evidence["null_outputs_ok"] is True
        and risk["null_outputs_ok"] is True
        and registry["canonical_data_writes"] == 0
        and evidence["canonical_data_writes"] == 0
        and risk["canonical_data_writes"] == 0
        and preflight["canonical_data_writes"] == 0
        and evidence_scorecard["canonical_data_writes"] == 0
        and risk_scorecard["canonical_data_writes"] == 0
    )

    checkpoint_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "shadow_score_batch_checkpoint_166_170",
        "phase_batch": [166, 167, 168, 169, 170],
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "descriptive_scores": preflight["descriptive_scores"],
        "checkpoint_pass": checkpoint_pass,
        "checkpoint_status": "PASS_RESEARCH_ONLY" if checkpoint_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "shadow_score_status": "SHADOW_SCORE_BATCH_READY_RESEARCH_ONLY_BLOCKED",
        "score_is_signal": False,
        "score_is_recommendation": False,
        "valid_for_decision": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase170(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase170_shadow_score_batch_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    checkpoint = build_checkpoint()
    (out / "phase170_shadow_score_batch_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": checkpoint["checkpoint_pass"], "checkpoint": checkpoint, **LOCKS}

def main() -> int:
    result = build_phase170()
    checkpoint = result["checkpoint"]

    print(result["gate"])
    print("Checkpoint pass:", checkpoint["checkpoint_pass"])
    print("Checkpoint status:", checkpoint["checkpoint_status"])
    print("Failed checks:", checkpoint["failed_checks"])
    print("Boundaries ok:", checkpoint["boundaries_ok"])
    print("Evidence score:", checkpoint["descriptive_scores"]["evidence_score"])
    print("Risk readiness score:", checkpoint["descriptive_scores"]["risk_readiness_score"])
    print("Combined descriptive score:", checkpoint["descriptive_scores"]["combined_descriptive_score"])
    print("Score is signal:", checkpoint["score_is_signal"])
    print("Score is recommendation:", checkpoint["score_is_recommendation"])
    print("Valid for decision:", checkpoint["valid_for_decision"])
    print("Shadow score status:", checkpoint["shadow_score_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("canonical_data_writes: 0")

    return 0 if checkpoint["checkpoint_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
