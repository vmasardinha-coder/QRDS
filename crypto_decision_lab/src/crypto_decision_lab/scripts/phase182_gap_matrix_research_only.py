from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE182_GAP_MATRIX_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

PHASE181_ARTIFACT = Path(
    "artifacts/phase181_gap_requirement_registry_research_only/"
    "phase181_gap_requirement_registry.json"
)

FORBIDDEN_OUTPUT_BY_GAP = {
    "operational_validation_gap": "operational_decision_payload",
    "decision_layer_gap": "decision_layer_output",
    "shadow_decision_gap": "shadow_decision_output",
    "safe_apply_gap": "safe_apply_payload",
    "canonical_write_gap": "canonical_write_payload",
}

def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def build_gap_matrix(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()
    registry = _load_json(root / PHASE181_ARTIFACT)

    rows = []
    for item in registry["requirements"]:
        gap_id = item["requirement_id"]
        rows.append(
            {
                "gap_id": gap_id,
                "gap_type": item["gap_type"],
                "description": item["description"],
                "required_before_promotion": item["required_before_promotion"],
                "currently_satisfied": item["currently_satisfied"],
                "blocks_promotion": True,
                "forbidden_output": FORBIDDEN_OUTPUT_BY_GAP[gap_id],
                "operational_effect": "NONE_RESEARCH_ONLY",
            }
        )

    invalid_rows = [
        row
        for row in rows
        if row["gap_type"] != "PROMOTION_BLOCKING_GAP_RESEARCH_ONLY"
        or row["required_before_promotion"] is not True
        or row["currently_satisfied"] is not False
        or row["blocks_promotion"] is not True
        or row["operational_effect"] != "NONE_RESEARCH_ONLY"
    ]

    matrix_pass = (
        registry["gap_registry_pass"] is True
        and len(rows) == 5
        and len(invalid_rows) == 0
        and registry["promotion_allowed"] is False
        and registry["decision_layer_allowed"] is False
        and registry["shadow_decision_allowed"] is False
        and registry["safe_apply_allowed"] is False
        and registry["canonical_data_writes"] == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "matrix_name": "evidence_to_promotion_gap_matrix_research_only",
        "artifact_based_matrix": True,
        "source_gap_registry_gate": registry["gate"],
        "source_gap_registry_pass": registry["gap_registry_pass"],
        "rows": rows,
        "row_count": len(rows),
        "invalid_row_count": len(invalid_rows),
        "gap_matrix_pass": matrix_pass,
        "gap_status": "GAP_MATRIX_CANDIDATE_RESEARCH_ONLY_BLOCKED",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "valid_for_decision": False,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase182(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase182_gap_matrix_research_only"
    out.mkdir(parents=True, exist_ok=True)

    matrix = build_gap_matrix()
    (out / "phase182_gap_matrix.json").write_text(
        json.dumps(matrix, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": matrix["gap_matrix_pass"], "matrix": matrix, **LOCKS}

def main() -> int:
    result = build_phase182()
    matrix = result["matrix"]

    print(result["gate"])
    print("Gap matrix pass:", matrix["gap_matrix_pass"])
    print("Artifact based matrix:", matrix["artifact_based_matrix"])
    print("Row count:", matrix["row_count"])
    print("Invalid row count:", matrix["invalid_row_count"])
    print("Gap status:", matrix["gap_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if matrix["gap_matrix_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
