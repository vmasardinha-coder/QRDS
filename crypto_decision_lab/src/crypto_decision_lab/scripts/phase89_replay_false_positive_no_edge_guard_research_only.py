from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase87_replay_evidence_threshold_registry_research_only import (
    evaluate_replay_evidence_thresholds,
)
from crypto_decision_lab.scripts.phase88_negative_case_registry_research_only import (
    build_negative_case_registry,
)

READY_GATE = "PHASE89_REPLAY_FALSE_POSITIVE_NO_EDGE_GUARD_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

FORBIDDEN_ESCALATIONS = [
    "EDGE_VALIDATED",
    "EDGE_OPERATIONALLY_VALIDATED",
    "TRADING_SIGNAL",
    "RECOMMENDATION",
    "ALLOCATION",
    "SHADOW_DECISION",
    "DECISION_LAYER",
    "OPERATIONAL_DECISION",
    "SAFE_APPLY",
    "PROMOTION",
    "CANONICAL_WRITE",
]

ALLOWED_INTERPRETATIONS = [
    "INSUFFICIENT_EVIDENCE_RESEARCH_ONLY",
    "NEEDS_REVIEW_RESEARCH_ONLY",
    "RESEARCH_CANDIDATE_DESCRIPTIVE_ONLY",
    "NO_EDGE_VALIDATED_RESEARCH_ONLY",
]

def guard_replay_false_positive(evidence: dict[str, Any]) -> dict[str, Any]:
    threshold = evaluate_replay_evidence_thresholds(evidence)
    negative_registry = build_negative_case_registry()

    errors: list[str] = []
    warnings: list[str] = []

    threshold_status = threshold["threshold_status"]

    if threshold_status == "RESEARCH_CANDIDATE_THRESHOLD_PASS_DESCRIPTIVE_ONLY":
        interpretation = "RESEARCH_CANDIDATE_DESCRIPTIVE_ONLY"
        warnings.append("threshold_pass_is_not_edge_validation")
    elif threshold_status == "INSUFFICIENT_SAMPLE_RESEARCH_ONLY":
        interpretation = "INSUFFICIENT_EVIDENCE_RESEARCH_ONLY"
    else:
        interpretation = "NEEDS_REVIEW_RESEARCH_ONLY"

    if negative_registry.get("registry_status") != "PASS_RESEARCH_ONLY":
        errors.append("negative_case_registry_not_passing")

    for key, expected in LOCKS.items():
        if key in threshold and threshold.get(key) != expected:
            errors.append(f"threshold_lock_mismatch:{key}")

    if interpretation not in ALLOWED_INTERPRETATIONS:
        errors.append("interpretation_not_allowed")

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "false_positive_guard_descriptive_only": True,
        "guard_status": "PASS_RESEARCH_ONLY" if not errors else "NEEDS_REVIEW_RESEARCH_ONLY",
        "interpretation": interpretation,
        "threshold_status": threshold_status,
        "threshold_blockers": threshold.get("blockers", []),
        "threshold_warnings": threshold.get("warnings", []),
        "guard_warnings": warnings,
        "guard_errors": errors,
        "negative_case_registry_status": negative_registry.get("registry_status"),
        "forbidden_escalations": FORBIDDEN_ESCALATIONS,
        "allowed_interpretations": ALLOWED_INTERPRETATIONS,
        "threshold_pass_does_not_validate_edge": True,
        "human_review_required": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        "focused_tests_required": True,
        **LOCKS,
    }

def render_false_positive_guard_html(report: dict[str, Any]) -> str:
    errors = "".join(f"<li>{item}</li>" for item in report["guard_errors"]) or "<li>No errors.</li>"
    warnings = "".join(f"<li>{item}</li>" for item in report["guard_warnings"]) or "<li>No warnings.</li>"
    forbidden = "".join(f"<li>{item}</li>" for item in report["forbidden_escalations"])

    return f"""
<html>
<head>
  <meta charset="utf-8">
  <title>QRDS Replay False Positive / No-Edge Guard</title>
  <style>
    body{{font-family:system-ui;background:#07111f;color:#e7edf8;padding:32px}}
    .badge{{display:inline-block;padding:6px 10px;border:1px solid #28415f;border-radius:999px;margin:4px}}
    table{{border-collapse:collapse;background:#101f35;width:100%}}
    th,td{{border:1px solid #28415f;padding:10px;text-align:left;vertical-align:top}}
  </style>
</head>
<body>
  <h1>QRDS Replay False Positive / No-Edge Guard</h1>
  <p>{READY_GATE}</p>
  <p class="badge">Guard status: {report["guard_status"]}</p>
  <p class="badge">Interpretation: {report["interpretation"]}</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">false_positive_guard_descriptive_only: True</p>
  <p class="badge">Edge: False</p>
  <p class="badge">Shadow decision allowed: False</p>
  <p class="badge">Decision layer allowed: False</p>
  <p class="badge">Promotion allowed: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>
  <p class="badge">Full suite: SKIPPED_LOCAL_ECONOMICAL</p>

  <h2>Guard Warnings</h2>
  <ul>{warnings}</ul>

  <h2>Guard Errors</h2>
  <ul>{errors}</ul>

  <h2>Forbidden Escalations</h2>
  <ul>{forbidden}</ul>

  <h2>Boundary</h2>
  <p>This guard is descriptive research only. A threshold pass, positive replay result, or clean negative-case registry
  does not validate edge, generate signals, recommendations, allocations, shadow decisions, operational decisions,
  promotion, safe-apply or canonical writes.</p>
</body>
</html>
"""

def build_phase89(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = Path.cwd()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase89_replay_false_positive_no_edge_guard_research_only"
    out.mkdir(parents=True, exist_ok=True)

    sample_evidence = {
        "row_count": 80,
        "invalid_row_count": 0,
        "active_paper_observation_count": 60,
        "outlier_count": 2,
        "asset_abs_pnl_concentration": 0.25,
        "drawdown_like_paper_pnl_sequence": False,
    }

    guard = guard_replay_false_positive(sample_evidence)

    (out / "phase89_replay_false_positive_no_edge_guard.json").write_text(
        json.dumps(guard, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase89_replay_false_positive_no_edge_guard.html").write_text(
        render_false_positive_guard_html(guard),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": guard["guard_status"] == "PASS_RESEARCH_ONLY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "false_positive_guard": guard,
        **LOCKS,
    }

def main() -> int:
    result = build_phase89()
    guard = result["false_positive_guard"]

    print("QRDS Phase 89 • Replay False Positive / No-Edge Guard Research-Only")
    print(result["gate"])
    print("Guard status:", guard["guard_status"])
    print("Interpretation:", guard["interpretation"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")
    print("Full suite: SKIPPED_LOCAL_ECONOMICAL")
    return 0 if result["ready"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
