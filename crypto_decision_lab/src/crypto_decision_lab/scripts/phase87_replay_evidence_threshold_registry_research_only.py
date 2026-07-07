from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE87_REPLAY_EVIDENCE_THRESHOLD_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

THRESHOLD_REGISTRY = {
    "registry_name": "qrds_replay_evidence_threshold_registry_v1",
    "registry_descriptive_only": True,
    "minimum_active_paper_observations": 30,
    "maximum_invalid_row_rate": 0.0,
    "maximum_asset_abs_pnl_concentration": 0.45,
    "maximum_outlier_rate": 0.10,
    "drawdown_like_sequence_requires_review": True,
    "threshold_pass_does_not_validate_edge": True,
    "allowed_statuses": [
        "INSUFFICIENT_SAMPLE_RESEARCH_ONLY",
        "NEEDS_REVIEW_RESEARCH_ONLY",
        "RESEARCH_CANDIDATE_THRESHOLD_PASS_DESCRIPTIVE_ONLY",
    ],
    "forbidden_interpretations": [
        "EDGE_VALIDATED",
        "TRADING_SIGNAL",
        "RECOMMENDATION",
        "ALLOCATION",
        "SHADOW_DECISION",
        "OPERATIONAL_DECISION",
        "SAFE_APPLY",
        "PROMOTION",
        "CANONICAL_WRITE",
    ],
}

def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default

def evaluate_replay_evidence_thresholds(summary: dict[str, Any]) -> dict[str, Any]:
    row_count = int(_num(summary.get("row_count"), 0))
    invalid_row_count = int(_num(summary.get("invalid_row_count"), 0))
    active_count = int(_num(summary.get("active_paper_observation_count"), 0))
    outlier_count = int(_num(summary.get("outlier_count"), 0))

    invalid_rate = invalid_row_count / row_count if row_count else 0.0
    outlier_rate = outlier_count / active_count if active_count else 0.0
    concentration = _num(summary.get("asset_abs_pnl_concentration"), 0.0)
    drawdown_like = bool(summary.get("drawdown_like_paper_pnl_sequence", False))

    blockers: list[str] = []
    warnings: list[str] = []

    if active_count < THRESHOLD_REGISTRY["minimum_active_paper_observations"]:
        blockers.append("minimum_active_paper_observations_not_met")

    if invalid_rate > THRESHOLD_REGISTRY["maximum_invalid_row_rate"]:
        blockers.append("invalid_row_rate_above_threshold")

    if concentration > THRESHOLD_REGISTRY["maximum_asset_abs_pnl_concentration"]:
        blockers.append("asset_abs_pnl_concentration_above_threshold")

    if outlier_rate > THRESHOLD_REGISTRY["maximum_outlier_rate"]:
        blockers.append("outlier_rate_above_threshold")

    if drawdown_like and THRESHOLD_REGISTRY["drawdown_like_sequence_requires_review"]:
        warnings.append("drawdown_like_sequence_requires_human_review")

    if blockers:
        threshold_status = "INSUFFICIENT_SAMPLE_RESEARCH_ONLY" if "minimum_active_paper_observations_not_met" in blockers else "NEEDS_REVIEW_RESEARCH_ONLY"
    else:
        threshold_status = "RESEARCH_CANDIDATE_THRESHOLD_PASS_DESCRIPTIVE_ONLY"

    return {
        "threshold_status": threshold_status,
        "threshold_registry": THRESHOLD_REGISTRY,
        "row_count": row_count,
        "invalid_row_count": invalid_row_count,
        "invalid_row_rate": invalid_rate,
        "active_paper_observation_count": active_count,
        "outlier_count": outlier_count,
        "outlier_rate": outlier_rate,
        "asset_abs_pnl_concentration": concentration,
        "drawdown_like_paper_pnl_sequence": drawdown_like,
        "blockers": blockers,
        "warnings": warnings,
        "human_review_required": True,
        "threshold_pass_does_not_validate_edge": True,
        **LOCKS,
    }

def render_threshold_registry_html(result: dict[str, Any]) -> str:
    blockers = "".join(f"<li>{item}</li>" for item in result.get("blockers", [])) or "<li>No blockers.</li>"
    warnings = "".join(f"<li>{item}</li>" for item in result.get("warnings", [])) or "<li>No warnings.</li>"

    return f"""
<html>
<head>
  <meta charset="utf-8">
  <title>QRDS Replay Evidence Threshold Registry</title>
  <style>
    body{{font-family:system-ui;background:#07111f;color:#e7edf8;padding:32px}}
    .badge{{display:inline-block;padding:6px 10px;border:1px solid #28415f;border-radius:999px;margin:4px}}
    table{{border-collapse:collapse;background:#101f35;width:100%}}
    th,td{{border:1px solid #28415f;padding:10px;text-align:left}}
  </style>
</head>
<body>
  <h1>QRDS Replay Evidence Threshold Registry</h1>
  <p>{READY_GATE}</p>
  <p class="badge">Threshold status: {result["threshold_status"]}</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">registry_descriptive_only: True</p>
  <p class="badge">Edge: False</p>
  <p class="badge">Shadow decision allowed: False</p>
  <p class="badge">Decision layer allowed: False</p>
  <p class="badge">Promotion allowed: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>
  <p class="badge">Full suite: SKIPPED_LOCAL_ECONOMICAL</p>

  <h2>Thresholds</h2>
  <table>
    <tr><th>Minimum active observations</th><td>{THRESHOLD_REGISTRY["minimum_active_paper_observations"]}</td></tr>
    <tr><th>Maximum invalid row rate</th><td>{THRESHOLD_REGISTRY["maximum_invalid_row_rate"]}</td></tr>
    <tr><th>Maximum asset concentration</th><td>{THRESHOLD_REGISTRY["maximum_asset_abs_pnl_concentration"]}</td></tr>
    <tr><th>Maximum outlier rate</th><td>{THRESHOLD_REGISTRY["maximum_outlier_rate"]}</td></tr>
  </table>

  <h2>Evaluation</h2>
  <p>active_paper_observation_count: {result["active_paper_observation_count"]}</p>
  <p>invalid_row_rate: {result["invalid_row_rate"]}</p>
  <p>outlier_rate: {result["outlier_rate"]}</p>
  <p>asset_abs_pnl_concentration: {result["asset_abs_pnl_concentration"]}</p>

  <h2>Blockers</h2>
  <ul>{blockers}</ul>

  <h2>Warnings</h2>
  <ul>{warnings}</ul>

  <h2>Boundary</h2>
  <p>This registry is descriptive research only. Passing thresholds does not validate edge,
  generate signals, recommendations, allocations, shadow decisions, operational decisions,
  promotion, safe-apply or canonical writes.</p>
</body>
</html>
"""

def build_phase87(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = Path.cwd()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase87_replay_evidence_threshold_registry_research_only"
    out.mkdir(parents=True, exist_ok=True)

    sample_summary = {
        "row_count": 60,
        "invalid_row_count": 0,
        "active_paper_observation_count": 48,
        "outlier_count": 2,
        "asset_abs_pnl_concentration": 0.35,
        "drawdown_like_paper_pnl_sequence": False,
    }

    evaluation = evaluate_replay_evidence_thresholds(sample_summary)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "threshold_registry": THRESHOLD_REGISTRY,
        "sample_threshold_evaluation": evaluation,
        "human_review_required": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        "focused_tests_required": True,
        **LOCKS,
    }

    (out / "phase87_replay_evidence_threshold_registry.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase87_replay_evidence_threshold_registry.html").write_text(
        render_threshold_registry_html(evaluation),
        encoding="utf-8",
    )

    return result

def main() -> int:
    result = build_phase87()
    evaluation = result["sample_threshold_evaluation"]

    print("QRDS Phase 87 • Replay Evidence Threshold Registry Research-Only")
    print(result["gate"])
    print("Threshold status:", evaluation["threshold_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")
    print("Full suite: SKIPPED_LOCAL_ECONOMICAL")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
