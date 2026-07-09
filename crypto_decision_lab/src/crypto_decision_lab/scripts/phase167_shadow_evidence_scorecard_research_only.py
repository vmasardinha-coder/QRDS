from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase166_shadow_score_requirement_registry_research_only import (
    build_shadow_score_requirement_registry,
)

READY_GATE = "PHASE167_SHADOW_EVIDENCE_SCORECARD_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

SAMPLE_EVIDENCE_INPUT = {
    "candidate_id": "research_candidate_only",
    "evidence_quality_score": 0.92,
    "evidence_quality_label": "HIGH_RESEARCH_ONLY",
    "replay_validity_status": "REPLAY_VALIDITY_BATCH_READY_RESEARCH_ONLY_UNVALIDATED",
    "shadow_evidence_replay_status": "SHADOW_EVIDENCE_REPLAY_BATCH_READY_RESEARCH_ONLY_BLOCKED",
}

def score_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    quality = float(payload.get("evidence_quality_score", 0.0))
    replay_ready = "READY_RESEARCH_ONLY" in str(payload.get("replay_validity_status", ""))
    evidence_replay_blocked = "BLOCKED" in str(payload.get("shadow_evidence_replay_status", ""))

    descriptive_score = round(
        min(1.0, max(0.0, quality)) * 0.7
        + (0.2 if replay_ready else 0.0)
        + (0.1 if evidence_replay_blocked else 0.0),
        4,
    )

    return {
        "candidate_id": payload.get("candidate_id", "unknown_research_candidate"),
        "scorecard_name": "shadow_evidence_scorecard_research_only",
        "descriptive_score": descriptive_score,
        "score_label": "EVIDENCE_READY_RESEARCH_ONLY" if descriptive_score >= 0.85 else "EVIDENCE_INCOMPLETE_RESEARCH_ONLY",
        "score_is_signal": False,
        "score_is_recommendation": False,
        "valid_for_decision": False,
        "decision": None,
        "recommendation": None,
        "trading_signal": None,
        "allocation": None,
        "order_payload": None,
        "safe_apply_payload": None,
        "canonical_data_writes": 0,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_shadow_evidence_scorecard(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_shadow_score_requirement_registry(project_root)
    scorecard = score_evidence(SAMPLE_EVIDENCE_INPUT)

    null_outputs_ok = (
        scorecard["decision"] is None
        and scorecard["recommendation"] is None
        and scorecard["trading_signal"] is None
        and scorecard["allocation"] is None
        and scorecard["order_payload"] is None
        and scorecard["safe_apply_payload"] is None
    )

    scorecard_pass = (
        registry["registry_pass"] is True
        and scorecard["descriptive_score"] >= 0.0
        and scorecard["descriptive_score"] <= 1.0
        and scorecard["score_is_signal"] is False
        and scorecard["score_is_recommendation"] is False
        and scorecard["valid_for_decision"] is False
        and null_outputs_ok is True
        and scorecard["canonical_data_writes"] == 0
        and scorecard["operational_effect"] == "NONE_RESEARCH_ONLY"
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scorecard_name": "shadow_evidence_scorecard_research_only",
        "source_registry_gate": registry["gate"],
        "source_registry_pass": registry["registry_pass"],
        "sample_input": SAMPLE_EVIDENCE_INPUT,
        "scorecard": scorecard,
        "null_outputs_ok": null_outputs_ok,
        "scorecard_pass": scorecard_pass,
        "shadow_score_status": "SHADOW_EVIDENCE_SCORECARD_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase167(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase167_shadow_evidence_scorecard_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_shadow_evidence_scorecard()
    (out / "phase167_shadow_evidence_scorecard.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["scorecard_pass"], "scorecard_result": result, **LOCKS}

def main() -> int:
    result = build_phase167()
    scorecard_result = result["scorecard_result"]
    scorecard = scorecard_result["scorecard"]

    print(result["gate"])
    print("Scorecard pass:", scorecard_result["scorecard_pass"])
    print("Descriptive score:", scorecard["descriptive_score"])
    print("Score label:", scorecard["score_label"])
    print("Score is signal:", scorecard["score_is_signal"])
    print("Score is recommendation:", scorecard["score_is_recommendation"])
    print("Valid for decision:", scorecard["valid_for_decision"])
    print("Null outputs ok:", scorecard_result["null_outputs_ok"])
    print("Shadow score status:", scorecard_result["shadow_score_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("canonical_data_writes: 0")

    return 0 if scorecard_result["scorecard_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
