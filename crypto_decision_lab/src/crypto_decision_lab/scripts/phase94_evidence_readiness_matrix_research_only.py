from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE94_EVIDENCE_READINESS_MATRIX_RESEARCH_ONLY_READY_RESEARCH_ONLY"

LOCKS = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
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

MATRIX = [
    {"dimension": "artifact_presence", "status": "READY_RESEARCH_ONLY", "promotion_weight": 0},
    {"dimension": "focused_tests", "status": "READY_RESEARCH_ONLY", "promotion_weight": 0},
    {"dimension": "negative_cases", "status": "READY_RESEARCH_ONLY", "promotion_weight": 0},
    {"dimension": "false_positive_guard", "status": "READY_RESEARCH_ONLY", "promotion_weight": 0},
    {"dimension": "thresholds", "status": "DESCRIPTIVE_ONLY", "promotion_weight": 0},
    {"dimension": "human_review", "status": "REQUIRED_RESEARCH_ONLY", "promotion_weight": 0},
    {"dimension": "operational_edge", "status": "NOT_VALIDATED_BLOCKED", "promotion_weight": 0},
]

def build_matrix() -> dict[str, Any]:
    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "matrix_name": "evidence_readiness_matrix",
        "readiness_for_operations": "BLOCKED_RESEARCH_ONLY",
        "descriptive_only": True,
        "matrix": MATRIX,
        "promotion_score": 0,
        "promotion_effect": "NONE_RESEARCH_ONLY",
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def render_markdown(matrix: dict[str, Any]) -> str:
    rows = "\n".join(
        f"| {item['dimension']} | {item['status']} | {item['promotion_weight']} |"
        for item in matrix["matrix"]
    )
    return f"""# Evidence Readiness Matrix Research-Only

Gate: `{READY_GATE}`

Readiness for operations: BLOCKED_RESEARCH_ONLY  
Promotion score: 0  
Promotion effect: NONE_RESEARCH_ONLY

| Dimension | Status | Promotion Weight |
|---|---:|---:|
{rows}

This matrix is descriptive only and cannot promote any strategy, edge, signal, recommendation, allocation, decision, safe-apply action or canonical write.
"""

def build_phase94(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase94_evidence_readiness_matrix_research_only"
    out.mkdir(parents=True, exist_ok=True)
    matrix = build_matrix()
    (out / "phase94_evidence_readiness_matrix.json").write_text(json.dumps(matrix, indent=2, sort_keys=True), encoding="utf-8")
    (out / "phase94_evidence_readiness_matrix.md").write_text(render_markdown(matrix), encoding="utf-8")
    return {"gate": READY_GATE, "ready": True, "matrix": matrix, **LOCKS}

def main() -> int:
    result = build_phase94()
    print(result["gate"])
    print("Readiness for operations: BLOCKED_RESEARCH_ONLY")
    print("Promotion score: 0")
    print("Promotion effect: NONE_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
