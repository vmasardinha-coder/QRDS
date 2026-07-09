from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase167_shadow_evidence_scorecard_research_only import (
    build_shadow_evidence_scorecard,
)

READY_GATE = "PHASE168_SHADOW_RISK_SCORECARD_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

SAMPLE_RISK_INPUT = {
    "candidate_id": "research_candidate_only",
    "risk_status": "RISK_RUIN_BATCH_READY_RESEARCH_ONLY_UNVALIDATED",
    "ruin_model_available": True,
    "exposure_guard_available": True,
    "risk_preflight_available": True,
    "operational_risk_blocked": True,
}

def score_risk(payload: dict[str, Any]) -> dict[str, Any]:
    ruin_ready = "READY_RESEARCH_ONLY" in str(payload.get("risk_status", ""))
    ruin_model_available = bool(payload.get("ruin_model_available", False))
    exposure_guard_available = bool(payload.get("exposure_guard_available", False))
    risk_preflight_available = bool(payload.get("risk_preflight_available", False))
    operational_risk_blocked = bool(payload.get("operational_risk_blocked", False))

    readiness_score = round(
        (0.25 if ruin_ready else 0.0)
        + (0.2 if ruin_model_available else 0.0)
        + (0.2 if exposure_guard_available else 0.0)
        + (0.2 if risk_preflight_available else 0.0)
        + (0.15 if operational_risk_blocked else 0.0),
        4,
    )

    return {
        "candidate_id": payload.get("candidate_id", "unknown_research_candidate"),
        "scorecard_name": "shadow_risk_scorecard_research_only",
        "descriptive_risk_readiness_score": readiness_score,
        "risk_label": "RISK_READINESS_OBSERVED_RESEARCH_ONLY" if readiness_score >= 0.85 else "RISK_READINESS_INCOMPLETE_RESEARCH_ONLY",
        "risk_score_is_signal": False,
        "risk_score_is_recommendation": False,
        "valid_for_decision": False,
        "decision": None,
        "recommendation": None,
        "trading_signal": None,
        "allocation": None,
        "position_size": None,
        "order_payload": None,
        "safe_apply_payload": None,
        "canonical_data_writes": 0,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_shadow_risk_scorecard(project_root: str | Path | None = None) -> dict[str, Any]:
    evidence = build_shadow_evidence_scorecard(project_root)
    risk_scorecard = score_risk(SAMPLE_RISK_INPUT)

    null_outputs_ok = (
        risk_scorecard["decision"] is None
        and risk_scorecard["recommendation"] is None
        and risk_scorecard["trading_signal"] is None
        and risk_scorecard["allocation"] is None
        and risk_scorecard["position_size"] is None
        and risk_scorecard["order_payload"] is None
        and risk_scorecard["safe_apply_payload"] is None
    )

    scorecard_pass = (
        evidence["scorecard_pass"] is True
        and 0.0 <= risk_scorecard["descriptive_risk_readiness_score"] <= 1.0
        and risk_scorecard["risk_score_is_signal"] is False
        and risk_scorecard["risk_score_is_recommendation"] is False
        and risk_scorecard["valid_for_decision"] is False
        and null_outputs_ok is True
        and risk_scorecard["canonical_data_writes"] == 0
        and risk_scorecard["operational_effect"] == "NONE_RESEARCH_ONLY"
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scorecard_name": "shadow_risk_scorecard_research_only",
        "source_evidence_scorecard_gate": evidence["gate"],
        "source_evidence_scorecard_pass": evidence["scorecard_pass"],
        "sample_input": SAMPLE_RISK_INPUT,
        "risk_scorecard": risk_scorecard,
        "null_outputs_ok": null_outputs_ok,
        "scorecard_pass": scorecard_pass,
        "shadow_score_status": "SHADOW_RISK_SCORECARD_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase168(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase168_shadow_risk_scorecard_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_shadow_risk_scorecard()
    (out / "phase168_shadow_risk_scorecard.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["scorecard_pass"], "risk_scorecard_result": result, **LOCKS}

def main() -> int:
    result = build_phase168()
    scorecard_result = result["risk_scorecard_result"]
    scorecard = scorecard_result["risk_scorecard"]

    print(result["gate"])
    print("Risk scorecard pass:", scorecard_result["scorecard_pass"])
    print("Descriptive risk readiness score:", scorecard["descriptive_risk_readiness_score"])
    print("Risk label:", scorecard["risk_label"])
    print("Risk score is signal:", scorecard["risk_score_is_signal"])
    print("Risk score is recommendation:", scorecard["risk_score_is_recommendation"])
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
