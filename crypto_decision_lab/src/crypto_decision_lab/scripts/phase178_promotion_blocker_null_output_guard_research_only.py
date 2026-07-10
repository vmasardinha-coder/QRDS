from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE178_PROMOTION_BLOCKER_NULL_OUTPUT_GUARD_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

PHASE177_ARTIFACT = Path(
    "artifacts/phase177_promotion_blocker_reason_map_research_only/"
    "phase177_promotion_blocker_reason_map.json"
)

NULL_OUTPUT_TEMPLATE = {
    "decision": None,
    "recommendation": None,
    "trading_signal": None,
    "allocation": None,
    "position_size": None,
    "order_payload": None,
    "safe_apply_payload": None,
    "promotion_payload": None,
    "approval_payload": None,
    "operational_decision_payload": None,
    "valid_for_decision": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
    "operational_effect": "NONE_RESEARCH_ONLY",
}

def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def build_promotion_blocker_null_output_guard(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()
    reason_map = _load_json(root / PHASE177_ARTIFACT)

    guarded_output = dict(NULL_OUTPUT_TEMPLATE)

    null_fields = [
        "decision",
        "recommendation",
        "trading_signal",
        "allocation",
        "position_size",
        "order_payload",
        "safe_apply_payload",
        "promotion_payload",
        "approval_payload",
        "operational_decision_payload",
    ]

    non_null_outputs = [field for field in null_fields if guarded_output.get(field) is not None]

    guard_pass = (
        reason_map["reason_map_pass"] is True
        and reason_map["promotion_allowed"] is False
        and reason_map["decision_layer_allowed"] is False
        and reason_map["shadow_decision_allowed"] is False
        and reason_map["canonical_data_writes"] == 0
        and non_null_outputs == []
        and guarded_output["valid_for_decision"] is False
        and guarded_output["promotion_allowed"] is False
        and guarded_output["canonical_data_writes"] == 0
        and guarded_output["operational_effect"] == "NONE_RESEARCH_ONLY"
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "guard_name": "promotion_blocker_null_output_guard_research_only",
        "artifact_based_guard": True,
        "source_reason_map_gate": reason_map["gate"],
        "source_reason_map_pass": reason_map["reason_map_pass"],
        "guarded_output": guarded_output,
        "null_fields": null_fields,
        "non_null_outputs": non_null_outputs,
        "null_outputs_ok": non_null_outputs == [],
        "guard_pass": guard_pass,
        "promotion_blocker_status": "PROMOTION_BLOCKER_NULL_OUTPUT_GUARD_CANDIDATE_RESEARCH_ONLY_BLOCKED",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase178(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase178_promotion_blocker_null_output_guard_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_promotion_blocker_null_output_guard()
    (out / "phase178_promotion_blocker_null_output_guard.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["guard_pass"], "guard_result": result, **LOCKS}

def main() -> int:
    result = build_phase178()
    guard = result["guard_result"]

    print(result["gate"])
    print("Guard pass:", guard["guard_pass"])
    print("Artifact based guard:", guard["artifact_based_guard"])
    print("Null outputs ok:", guard["null_outputs_ok"])
    print("Non-null outputs:", guard["non_null_outputs"])
    print("Promotion blocker status:", guard["promotion_blocker_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if guard["guard_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
