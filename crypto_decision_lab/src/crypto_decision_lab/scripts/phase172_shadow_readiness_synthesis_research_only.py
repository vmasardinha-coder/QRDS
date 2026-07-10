from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase171_shadow_readiness_requirement_registry_research_only import (
    build_shadow_readiness_requirement_registry,
)

READY_GATE = "PHASE172_SHADOW_READINESS_SYNTHESIS_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def synthesize_shadow_readiness(registry: dict[str, Any]) -> dict[str, Any]:
    registry_ready = registry["registry_pass"] is True
    source_score_ready = registry["source_shadow_score_pass"] is True
    source_score_blocked = "BLOCKED" in str(registry["source_shadow_score_status"])

    readiness_score = round(
        (0.4 if registry_ready else 0.0)
        + (0.35 if source_score_ready else 0.0)
        + (0.25 if source_score_blocked else 0.0),
        4,
    )

    return {
        "synthesis_name": "shadow_readiness_synthesis_research_only",
        "readiness_score": readiness_score,
        "readiness_label": "READINESS_OBSERVED_BUT_BLOCKED_RESEARCH_ONLY"
        if readiness_score >= 0.85
        else "READINESS_INCOMPLETE_RESEARCH_ONLY",
        "readiness_is_approval": False,
        "readiness_is_signal": False,
        "readiness_is_recommendation": False,
        "readiness_is_allocation": False,
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

def build_shadow_readiness_synthesis(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_shadow_readiness_requirement_registry(project_root)
    synthesis = synthesize_shadow_readiness(registry)

    null_outputs_ok = (
        synthesis["decision"] is None
        and synthesis["recommendation"] is None
        and synthesis["trading_signal"] is None
        and synthesis["allocation"] is None
        and synthesis["position_size"] is None
        and synthesis["order_payload"] is None
        and synthesis["safe_apply_payload"] is None
    )

    synthesis_pass = (
        registry["registry_pass"] is True
        and 0.0 <= synthesis["readiness_score"] <= 1.0
        and synthesis["readiness_is_approval"] is False
        and synthesis["readiness_is_signal"] is False
        and synthesis["readiness_is_recommendation"] is False
        and synthesis["readiness_is_allocation"] is False
        and synthesis["valid_for_decision"] is False
        and synthesis["promotion_allowed"] is False
        and null_outputs_ok is True
        and synthesis["canonical_data_writes"] == 0
        and synthesis["operational_effect"] == "NONE_RESEARCH_ONLY"
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "synthesis_name": "shadow_readiness_synthesis_research_only",
        "source_registry_gate": registry["gate"],
        "source_registry_pass": registry["registry_pass"],
        "synthesis": synthesis,
        "null_outputs_ok": null_outputs_ok,
        "synthesis_pass": synthesis_pass,
        "shadow_readiness_status": "SHADOW_READINESS_SYNTHESIS_CANDIDATE_RESEARCH_ONLY_BLOCKED",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase172(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase172_shadow_readiness_synthesis_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_shadow_readiness_synthesis()
    (out / "phase172_shadow_readiness_synthesis.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["synthesis_pass"], "synthesis_result": result, **LOCKS}

def main() -> int:
    result = build_phase172()
    synthesis_result = result["synthesis_result"]
    synthesis = synthesis_result["synthesis"]

    print(result["gate"])
    print("Synthesis pass:", synthesis_result["synthesis_pass"])
    print("Readiness score:", synthesis["readiness_score"])
    print("Readiness label:", synthesis["readiness_label"])
    print("Readiness is approval:", synthesis["readiness_is_approval"])
    print("Readiness is signal:", synthesis["readiness_is_signal"])
    print("Readiness is recommendation:", synthesis["readiness_is_recommendation"])
    print("Valid for decision:", synthesis["valid_for_decision"])
    print("Promotion allowed:", synthesis["promotion_allowed"])
    print("Null outputs ok:", synthesis_result["null_outputs_ok"])
    print("Shadow readiness status:", synthesis_result["shadow_readiness_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("canonical_data_writes: 0")

    return 0 if synthesis_result["synthesis_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
