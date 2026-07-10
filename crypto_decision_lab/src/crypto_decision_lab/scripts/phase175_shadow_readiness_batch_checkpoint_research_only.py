from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE175_SHADOW_READINESS_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

ARTIFACT_PATHS = {
    "phase171": Path("artifacts/phase171_shadow_readiness_requirement_registry_research_only/phase171_shadow_readiness_requirement_registry.json"),
    "phase172": Path("artifacts/phase172_shadow_readiness_synthesis_research_only/phase172_shadow_readiness_synthesis.json"),
    "phase173": Path("artifacts/phase173_shadow_readiness_explanation_research_only/phase173_shadow_readiness_explanation.json"),
    "phase174": Path("artifacts/phase174_shadow_readiness_preflight_research_only/phase174_shadow_readiness_preflight.json"),
}

def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def build_checkpoint(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()

    registry = _load_json(root / ARTIFACT_PATHS["phase171"])
    synthesis_result = _load_json(root / ARTIFACT_PATHS["phase172"])
    explanation_result = _load_json(root / ARTIFACT_PATHS["phase173"])
    preflight = _load_json(root / ARTIFACT_PATHS["phase174"])

    synthesis = synthesis_result["synthesis"]
    explanation = explanation_result["explanation"]

    checks = [
        {"id": "PHASE171_SHADOW_READINESS_REQUIREMENT_REGISTRY", "status": registry["registry_pass"]},
        {"id": "PHASE172_SHADOW_READINESS_SYNTHESIS", "status": synthesis_result["synthesis_pass"]},
        {"id": "PHASE173_SHADOW_READINESS_EXPLANATION", "status": explanation_result["explanation_pass"]},
        {"id": "PHASE174_SHADOW_READINESS_PREFLIGHT", "status": preflight["preflight_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        registry["approval_effect"] == "NONE_RESEARCH_ONLY"
        and synthesis_result["approval_effect"] == "NONE_RESEARCH_ONLY"
        and explanation_result["approval_effect"] == "NONE_RESEARCH_ONLY"
        and preflight["approval_effect"] == "NONE_RESEARCH_ONLY"
        and preflight["boundaries_ok"] is True
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
        and preflight["readiness_is_approval"] is False
        and preflight["readiness_is_signal"] is False
        and preflight["readiness_is_recommendation"] is False
        and preflight["valid_for_decision"] is False
        and synthesis_result["null_outputs_ok"] is True
        and explanation_result["null_outputs_ok"] is True
        and registry["canonical_data_writes"] == 0
        and synthesis_result["canonical_data_writes"] == 0
        and explanation_result["canonical_data_writes"] == 0
        and preflight["canonical_data_writes"] == 0
        and synthesis["canonical_data_writes"] == 0
        and explanation["canonical_data_writes"] == 0
    )

    checkpoint_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "shadow_readiness_batch_checkpoint_171_175_fast_artifact_based",
        "phase_batch": [171, 172, 173, 174, 175],
        "artifact_based_checkpoint": True,
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "readiness_score": synthesis["readiness_score"],
        "readiness_label": synthesis["readiness_label"],
        "reason_count": explanation["reason_count"],
        "checkpoint_pass": checkpoint_pass,
        "checkpoint_status": "PASS_RESEARCH_ONLY" if checkpoint_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "shadow_readiness_status": "SHADOW_READINESS_BATCH_READY_RESEARCH_ONLY_BLOCKED",
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

def build_phase175(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase175_shadow_readiness_batch_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    checkpoint = build_checkpoint()
    (out / "phase175_shadow_readiness_batch_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": checkpoint["checkpoint_pass"], "checkpoint": checkpoint, **LOCKS}

def main() -> int:
    result = build_phase175()
    checkpoint = result["checkpoint"]

    print(result["gate"])
    print("Checkpoint pass:", checkpoint["checkpoint_pass"])
    print("Checkpoint status:", checkpoint["checkpoint_status"])
    print("Artifact based checkpoint:", checkpoint["artifact_based_checkpoint"])
    print("Failed checks:", checkpoint["failed_checks"])
    print("Boundaries ok:", checkpoint["boundaries_ok"])
    print("Readiness score:", checkpoint["readiness_score"])
    print("Readiness label:", checkpoint["readiness_label"])
    print("Reason count:", checkpoint["reason_count"])
    print("Readiness is approval:", checkpoint["readiness_is_approval"])
    print("Readiness is signal:", checkpoint["readiness_is_signal"])
    print("Readiness is recommendation:", checkpoint["readiness_is_recommendation"])
    print("Valid for decision:", checkpoint["valid_for_decision"])
    print("Shadow readiness status:", checkpoint["shadow_readiness_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("canonical_data_writes: 0")

    return 0 if checkpoint["checkpoint_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
