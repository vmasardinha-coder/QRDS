from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase171_shadow_readiness_requirement_registry_research_only import build_shadow_readiness_requirement_registry
from crypto_decision_lab.scripts.phase172_shadow_readiness_synthesis_research_only import build_shadow_readiness_synthesis
from crypto_decision_lab.scripts.phase173_shadow_readiness_explanation_research_only import build_shadow_readiness_explanation

READY_GATE = "PHASE174_SHADOW_READINESS_PREFLIGHT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_shadow_readiness_preflight(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_shadow_readiness_requirement_registry(project_root)
    synthesis_result = build_shadow_readiness_synthesis(project_root)
    explanation_result = build_shadow_readiness_explanation(project_root)

    synthesis = synthesis_result["synthesis"]
    explanation = explanation_result["explanation"]

    checks = [
        {"id": "PHASE171_SHADOW_READINESS_REQUIREMENT_REGISTRY", "status": registry["registry_pass"]},
        {"id": "PHASE172_SHADOW_READINESS_SYNTHESIS", "status": synthesis_result["synthesis_pass"]},
        {"id": "PHASE173_SHADOW_READINESS_EXPLANATION", "status": explanation_result["explanation_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        registry["approval_effect"] == "NONE_RESEARCH_ONLY"
        and synthesis_result["approval_effect"] == "NONE_RESEARCH_ONLY"
        and explanation_result["approval_effect"] == "NONE_RESEARCH_ONLY"
        and synthesis["readiness_is_approval"] is False
        and synthesis["readiness_is_signal"] is False
        and synthesis["readiness_is_recommendation"] is False
        and synthesis["readiness_is_allocation"] is False
        and synthesis["valid_for_decision"] is False
        and synthesis["promotion_allowed"] is False
        and explanation["explanation_is_approval"] is False
        and explanation["explanation_is_signal"] is False
        and explanation["explanation_is_recommendation"] is False
        and explanation["explanation_is_allocation"] is False
        and explanation["valid_for_decision"] is False
        and explanation["promotion_allowed"] is False
        and synthesis_result["null_outputs_ok"] is True
        and explanation_result["null_outputs_ok"] is True
        and registry["canonical_data_writes"] == 0
        and synthesis_result["canonical_data_writes"] == 0
        and explanation_result["canonical_data_writes"] == 0
        and synthesis["canonical_data_writes"] == 0
        and explanation["canonical_data_writes"] == 0
    )

    preflight_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preflight_name": "shadow_readiness_preflight_research_only",
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "readiness_score": synthesis["readiness_score"],
        "readiness_label": synthesis["readiness_label"],
        "reason_count": explanation["reason_count"],
        "preflight_pass": preflight_pass,
        "preflight_status": "PASS_RESEARCH_ONLY" if preflight_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "shadow_readiness_status": "SHADOW_READINESS_PREFLIGHT_CANDIDATE_RESEARCH_ONLY_BLOCKED",
        "readiness_is_approval": False,
        "readiness_is_signal": False,
        "readiness_is_recommendation": False,
        "readiness_is_allocation": False,
        "valid_for_decision": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase174(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase174_shadow_readiness_preflight_research_only"
    out.mkdir(parents=True, exist_ok=True)

    preflight = build_shadow_readiness_preflight()
    (out / "phase174_shadow_readiness_preflight.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": preflight["preflight_pass"], "preflight": preflight, **LOCKS}

def main() -> int:
    result = build_phase174()
    preflight = result["preflight"]

    print(result["gate"])
    print("Preflight pass:", preflight["preflight_pass"])
    print("Preflight status:", preflight["preflight_status"])
    print("Failed checks:", preflight["failed_checks"])
    print("Boundaries ok:", preflight["boundaries_ok"])
    print("Readiness score:", preflight["readiness_score"])
    print("Readiness label:", preflight["readiness_label"])
    print("Reason count:", preflight["reason_count"])
    print("Readiness is approval:", preflight["readiness_is_approval"])
    print("Readiness is signal:", preflight["readiness_is_signal"])
    print("Readiness is recommendation:", preflight["readiness_is_recommendation"])
    print("Valid for decision:", preflight["valid_for_decision"])
    print("Shadow readiness status:", preflight["shadow_readiness_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("canonical_data_writes: 0")

    return 0 if preflight["preflight_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
