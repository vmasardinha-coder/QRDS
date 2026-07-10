from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase172_shadow_readiness_synthesis_research_only import (
    build_shadow_readiness_synthesis,
)

READY_GATE = "PHASE173_SHADOW_READINESS_EXPLANATION_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def explain_shadow_readiness(synthesis_result: dict[str, Any]) -> dict[str, Any]:
    synthesis = synthesis_result["synthesis"]

    reasons = [
        "Shadow readiness is observed from the research-only score and readiness chain.",
        "Readiness remains blocked because operational validation is not present.",
        "The score is descriptive and cannot be interpreted as approval.",
        "No trading signal, recommendation, allocation, order payload, or safe-apply payload is allowed.",
        "Promotion to the decision layer remains disabled.",
    ]

    return {
        "explanation_name": "shadow_readiness_explanation_research_only",
        "readiness_score_seen": synthesis["readiness_score"],
        "readiness_label_seen": synthesis["readiness_label"],
        "explanation_reasons": reasons,
        "reason_count": len(reasons),
        "explanation_is_approval": False,
        "explanation_is_signal": False,
        "explanation_is_recommendation": False,
        "explanation_is_allocation": False,
        "valid_for_decision": False,
        "decision": None,
        "recommendation": None,
        "trading_signal": None,
        "allocation": None,
        "position_size": None,
        "order_payload": None,
        "safe_apply_payload": None,
        "promotion_allowed": False,
        "canonical_data_writes": 0,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_shadow_readiness_explanation(project_root: str | Path | None = None) -> dict[str, Any]:
    synthesis_result = build_shadow_readiness_synthesis(project_root)
    explanation = explain_shadow_readiness(synthesis_result)

    null_outputs_ok = (
        explanation["decision"] is None
        and explanation["recommendation"] is None
        and explanation["trading_signal"] is None
        and explanation["allocation"] is None
        and explanation["position_size"] is None
        and explanation["order_payload"] is None
        and explanation["safe_apply_payload"] is None
    )

    explanation_pass = (
        synthesis_result["synthesis_pass"] is True
        and explanation["reason_count"] == 5
        and explanation["explanation_is_approval"] is False
        and explanation["explanation_is_signal"] is False
        and explanation["explanation_is_recommendation"] is False
        and explanation["explanation_is_allocation"] is False
        and explanation["valid_for_decision"] is False
        and explanation["promotion_allowed"] is False
        and null_outputs_ok is True
        and explanation["canonical_data_writes"] == 0
        and explanation["operational_effect"] == "NONE_RESEARCH_ONLY"
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "explanation_name": "shadow_readiness_explanation_research_only",
        "source_synthesis_gate": synthesis_result["gate"],
        "source_synthesis_pass": synthesis_result["synthesis_pass"],
        "explanation": explanation,
        "null_outputs_ok": null_outputs_ok,
        "explanation_pass": explanation_pass,
        "shadow_readiness_status": "SHADOW_READINESS_EXPLANATION_CANDIDATE_RESEARCH_ONLY_BLOCKED",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase173(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase173_shadow_readiness_explanation_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_shadow_readiness_explanation()
    (out / "phase173_shadow_readiness_explanation.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["explanation_pass"], "explanation_result": result, **LOCKS}

def main() -> int:
    result = build_phase173()
    explanation_result = result["explanation_result"]
    explanation = explanation_result["explanation"]

    print(result["gate"])
    print("Explanation pass:", explanation_result["explanation_pass"])
    print("Reason count:", explanation["reason_count"])
    print("Readiness score seen:", explanation["readiness_score_seen"])
    print("Explanation is approval:", explanation["explanation_is_approval"])
    print("Explanation is signal:", explanation["explanation_is_signal"])
    print("Explanation is recommendation:", explanation["explanation_is_recommendation"])
    print("Valid for decision:", explanation["valid_for_decision"])
    print("Promotion allowed:", explanation["promotion_allowed"])
    print("Null outputs ok:", explanation_result["null_outputs_ok"])
    print("Shadow readiness status:", explanation_result["shadow_readiness_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("canonical_data_writes: 0")

    return 0 if explanation_result["explanation_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
