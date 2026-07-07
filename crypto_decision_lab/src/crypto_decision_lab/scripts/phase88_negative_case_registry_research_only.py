from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase87_replay_evidence_threshold_registry_research_only import (
    evaluate_replay_evidence_thresholds,
)

READY_GATE = "PHASE88_NEGATIVE_CASE_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

NEGATIVE_CASES = [
    {
        "case_id": "NEG_SAMPLE_TOO_SMALL",
        "description": "Active paper observations below minimum evidence threshold.",
        "summary": {
            "row_count": 10,
            "invalid_row_count": 0,
            "active_paper_observation_count": 10,
            "outlier_count": 0,
            "asset_abs_pnl_concentration": 0.10,
            "drawdown_like_paper_pnl_sequence": False,
        },
        "expected_status": "INSUFFICIENT_SAMPLE_RESEARCH_ONLY",
        "must_not_infer_edge": True,
    },
    {
        "case_id": "NEG_INVALID_ROWS",
        "description": "Invalid rows present in replay evidence.",
        "summary": {
            "row_count": 50,
            "invalid_row_count": 1,
            "active_paper_observation_count": 40,
            "outlier_count": 0,
            "asset_abs_pnl_concentration": 0.10,
            "drawdown_like_paper_pnl_sequence": False,
        },
        "expected_status": "NEEDS_REVIEW_RESEARCH_ONLY",
        "must_not_infer_edge": True,
    },
    {
        "case_id": "NEG_CONCENTRATION_TOO_HIGH",
        "description": "Paper PnL is too concentrated in one asset or source.",
        "summary": {
            "row_count": 60,
            "invalid_row_count": 0,
            "active_paper_observation_count": 50,
            "outlier_count": 1,
            "asset_abs_pnl_concentration": 0.80,
            "drawdown_like_paper_pnl_sequence": False,
        },
        "expected_status": "NEEDS_REVIEW_RESEARCH_ONLY",
        "must_not_infer_edge": True,
    },
    {
        "case_id": "NEG_OUTLIER_DOMINATED",
        "description": "Too many outliers relative to active paper observations.",
        "summary": {
            "row_count": 60,
            "invalid_row_count": 0,
            "active_paper_observation_count": 40,
            "outlier_count": 10,
            "asset_abs_pnl_concentration": 0.20,
            "drawdown_like_paper_pnl_sequence": False,
        },
        "expected_status": "NEEDS_REVIEW_RESEARCH_ONLY",
        "must_not_infer_edge": True,
    },
    {
        "case_id": "NEG_DRAWDOWN_LIKE_WARNING",
        "description": "Thresholds may pass, but drawdown-like paper sequence requires human review.",
        "summary": {
            "row_count": 80,
            "invalid_row_count": 0,
            "active_paper_observation_count": 60,
            "outlier_count": 1,
            "asset_abs_pnl_concentration": 0.20,
            "drawdown_like_paper_pnl_sequence": True,
        },
        "expected_status": "RESEARCH_CANDIDATE_THRESHOLD_PASS_DESCRIPTIVE_ONLY",
        "expected_warning": "drawdown_like_sequence_requires_human_review",
        "must_not_infer_edge": True,
    },
]

def evaluate_negative_case(case: dict[str, Any]) -> dict[str, Any]:
    evaluation = evaluate_replay_evidence_thresholds(case["summary"])
    expected_status = case["expected_status"]
    expected_warning = case.get("expected_warning")

    errors: list[str] = []

    if evaluation["threshold_status"] != expected_status:
        errors.append("threshold_status_mismatch")

    if expected_warning and expected_warning not in evaluation.get("warnings", []):
        errors.append("expected_warning_missing")

    if evaluation.get("edge_validated") is not False:
        errors.append("edge_validated_not_false")

    if evaluation.get("decision_layer_allowed") is not False:
        errors.append("decision_layer_allowed_not_false")

    if evaluation.get("shadow_decision_allowed") is not False:
        errors.append("shadow_decision_allowed_not_false")

    if evaluation.get("safe_apply_allowed") is not False:
        errors.append("safe_apply_allowed_not_false")

    if evaluation.get("promotion_allowed") is not False:
        errors.append("promotion_allowed_not_false")

    if evaluation.get("canonical_data_writes") != 0:
        errors.append("canonical_data_writes_not_zero")

    return {
        "case_id": case["case_id"],
        "description": case["description"],
        "expected_status": expected_status,
        "actual_status": evaluation["threshold_status"],
        "expected_warning": expected_warning,
        "warnings": evaluation.get("warnings", []),
        "blockers": evaluation.get("blockers", []),
        "negative_case_passed": len(errors) == 0,
        "errors": errors,
        "must_not_infer_edge": True,
        "human_review_required": True,
        **LOCKS,
    }

def build_negative_case_registry() -> dict[str, Any]:
    results = [evaluate_negative_case(case) for case in NEGATIVE_CASES]
    failing = [item for item in results if item["negative_case_passed"] is not True]

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "negative_case_registry_descriptive_only": True,
        "case_count": len(results),
        "failing_case_count": len(failing),
        "registry_status": "PASS_RESEARCH_ONLY" if not failing else "NEEDS_REVIEW_RESEARCH_ONLY",
        "cases": results,
        "human_review_required": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        "focused_tests_required": True,
        **LOCKS,
    }

def render_negative_case_registry_html(registry: dict[str, Any]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{case['case_id']}</td>"
        f"<td>{case['actual_status']}</td>"
        f"<td>{case['negative_case_passed']}</td>"
        f"<td>{', '.join(case['blockers'])}</td>"
        f"<td>{', '.join(case['warnings'])}</td>"
        "</tr>"
        for case in registry["cases"]
    )

    return f"""
<html>
<head>
  <meta charset="utf-8">
  <title>QRDS Negative Case Registry</title>
  <style>
    body{{font-family:system-ui;background:#07111f;color:#e7edf8;padding:32px}}
    .badge{{display:inline-block;padding:6px 10px;border:1px solid #28415f;border-radius:999px;margin:4px}}
    table{{border-collapse:collapse;background:#101f35;width:100%}}
    th,td{{border:1px solid #28415f;padding:10px;text-align:left;vertical-align:top}}
  </style>
</head>
<body>
  <h1>QRDS Negative Case Registry</h1>
  <p>{READY_GATE}</p>
  <p class="badge">Registry status: {registry["registry_status"]}</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">negative_case_registry_descriptive_only: True</p>
  <p class="badge">Edge: False</p>
  <p class="badge">Shadow decision allowed: False</p>
  <p class="badge">Decision layer allowed: False</p>
  <p class="badge">Promotion allowed: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>
  <p class="badge">Full suite: SKIPPED_LOCAL_ECONOMICAL</p>

  <h2>Negative Cases</h2>
  <table>
    <thead>
      <tr><th>Case</th><th>Status</th><th>Passed</th><th>Blockers</th><th>Warnings</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>Boundary</h2>
  <p>This registry is descriptive research only. Negative cases prevent false confidence.
  They do not validate edge, generate signals, recommendations, allocations, shadow decisions,
  operational decisions, promotion, safe-apply or canonical writes.</p>
</body>
</html>
"""

def build_phase88(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = Path.cwd()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase88_negative_case_registry_research_only"
    out.mkdir(parents=True, exist_ok=True)

    registry = build_negative_case_registry()

    (out / "phase88_negative_case_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase88_negative_case_registry.html").write_text(
        render_negative_case_registry_html(registry),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": registry["registry_status"] == "PASS_RESEARCH_ONLY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "negative_case_registry": registry,
        **LOCKS,
    }

def main() -> int:
    result = build_phase88()
    registry = result["negative_case_registry"]

    print("QRDS Phase 88 • Negative Case Registry Research-Only")
    print(result["gate"])
    print("Registry status:", registry["registry_status"])
    print("Case count:", registry["case_count"])
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
