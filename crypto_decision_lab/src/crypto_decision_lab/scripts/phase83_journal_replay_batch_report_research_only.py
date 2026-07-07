from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase79_journal_replay_batch_loader_research_only import (
    SAMPLE_BATCH,
    validate_batch_payload,
)
from crypto_decision_lab.scripts.phase72_journal_replay_dry_run_engine_research_only import (
    replay_batch_dry_run,
)
from crypto_decision_lab.scripts.phase73_journal_replay_aggregate_metrics_research_only import (
    aggregate_replay_metrics,
)
from crypto_decision_lab.scripts.phase74_journal_replay_distribution_diagnostics_research_only import (
    replay_distribution_diagnostics,
)
from crypto_decision_lab.scripts.phase75_journal_replay_quality_flags_research_only import (
    compute_quality_flags,
)
from crypto_decision_lab.scripts.phase76_journal_replay_evidence_scorecard_v2_research_only import (
    build_evidence_scorecard,
)

READY_GATE = "PHASE83_JOURNAL_REPLAY_BATCH_REPORT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_batch_report(payload: dict[str, Any]) -> dict[str, Any]:
    validation = validate_batch_payload(payload)
    entries = payload.get("entries") if isinstance(payload.get("entries"), list) else []

    replay = replay_batch_dry_run(entries)
    metrics = aggregate_replay_metrics(replay)
    diagnostics = replay_distribution_diagnostics(replay)
    quality = compute_quality_flags(metrics, diagnostics)
    scorecard = build_evidence_scorecard(replay, metrics, diagnostics, quality)

    has_validation_errors = validation.get("batch_valid_for_replay_loader") is not True
    has_invalid_entries = int(validation.get("invalid_entry_count", 0)) > 0

    report_status = (
        "NEEDS_REVIEW_RESEARCH_ONLY"
        if has_validation_errors or has_invalid_entries
        else "DESCRIPTIVE_REPORT_READY_RESEARCH_ONLY"
    )

    return {
        "batch_id": payload.get("batch_id"),
        "report_status": report_status,
        "batch_report_descriptive_only": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "batch_validation": validation,
        "replay_summary": {
            "dry_run_only": replay.get("dry_run_only"),
            "row_count": replay.get("row_count"),
            "valid_row_count": replay.get("valid_row_count"),
            "invalid_row_count": replay.get("invalid_row_count"),
            "active_paper_observation_count": replay.get("active_paper_observation_count"),
            "total_paper_pnl": replay.get("total_paper_pnl"),
        },
        "aggregate_metrics": {
            "metrics_descriptive_only": metrics.get("metrics_descriptive_only"),
            "total_paper_pnl": metrics.get("total_paper_pnl"),
            "avg_paper_return_pct": metrics.get("avg_paper_return_pct"),
            "win_rate_descriptive_only": metrics.get("win_rate_descriptive_only"),
            "wins": metrics.get("wins"),
            "losses": metrics.get("losses"),
            "flats": metrics.get("flats"),
            "by_asset": metrics.get("by_asset"),
        },
        "distribution_diagnostics": {
            "distribution_diagnostics_descriptive_only": diagnostics.get("distribution_diagnostics_descriptive_only"),
            "mean_paper_return_pct": diagnostics.get("mean_paper_return_pct"),
            "median_paper_return_pct": diagnostics.get("median_paper_return_pct"),
            "drawdown_like_paper_pnl_sequence": diagnostics.get("drawdown_like_paper_pnl_sequence"),
            "outlier_count": diagnostics.get("outlier_count"),
            "asset_abs_pnl_concentration": diagnostics.get("asset_abs_pnl_concentration"),
        },
        "quality_flags": quality,
        "evidence_scorecard": scorecard,
        "human_review_required": True,
        "loader_execution_allowed": False,
        "replay_execution_allowed": False,
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
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def render_batch_report_html(report: dict[str, Any]) -> str:
    blockers = report["evidence_scorecard"].get("blockers_to_edge", [])
    blocker_rows = "".join(f"<li>{item}</li>" for item in blockers)

    by_asset = report["aggregate_metrics"].get("by_asset", []) or []
    asset_rows = "".join(
        "<tr>"
        f"<td>{row.get('asset')}</td>"
        f"<td>{row.get('row_count')}</td>"
        f"<td>{row.get('active_paper_observation_count')}</td>"
        f"<td>{row.get('total_paper_pnl')}</td>"
        f"<td>{row.get('avg_paper_return_pct')}</td>"
        "</tr>"
        for row in by_asset
    ) or "<tr><td colspan='5'>No asset rows.</td></tr>"

    return f"""
<html>
<head>
  <meta charset="utf-8">
  <title>QRDS Journal Replay Batch Report</title>
  <style>
    body{{font-family:system-ui;background:#07111f;color:#e7edf8;padding:32px}}
    table{{border-collapse:collapse;width:100%;background:#101f35}}
    th,td{{border:1px solid #28415f;padding:10px;text-align:left;vertical-align:top}}
    .badge{{display:inline-block;padding:6px 10px;border:1px solid #28415f;border-radius:999px;margin:4px}}
  </style>
</head>
<body>
  <h1>QRDS Journal Replay Batch Report</h1>
  <p>{READY_GATE}</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">batch_report_descriptive_only: True</p>
  <p class="badge">loader_execution_allowed: False</p>
  <p class="badge">replay_execution_allowed: False</p>
  <p class="badge">Edge: False</p>
  <p class="badge">Shadow decision allowed: False</p>
  <p class="badge">Decision layer allowed: False</p>
  <p class="badge">Promotion allowed: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>

  <h2>Batch</h2>
  <p>batch_id: {report.get("batch_id")}</p>
  <p>report_status: {report.get("report_status")}</p>
  <p>human_review_required: True</p>

  <h2>Replay Summary</h2>
  <p>row_count: {report["replay_summary"].get("row_count")}</p>
  <p>valid_row_count: {report["replay_summary"].get("valid_row_count")}</p>
  <p>invalid_row_count: {report["replay_summary"].get("invalid_row_count")}</p>
  <p>active_paper_observation_count: {report["replay_summary"].get("active_paper_observation_count")}</p>

  <h2>Evidence Status</h2>
  <p>{report["evidence_scorecard"].get("evidence_status")}</p>
  <ul>{blocker_rows}</ul>

  <h2>By Asset</h2>
  <table>
    <thead><tr><th>Asset</th><th>Rows</th><th>Active</th><th>Total PnL</th><th>Avg Return %</th></tr></thead>
    <tbody>{asset_rows}</tbody>
  </table>

  <h2>Boundary</h2>
  <p>This report is descriptive research only. It does not validate edge, generate signals,
  recommendations, allocations, shadow decisions, operational decisions, promotion, safe-apply or canonical writes.</p>
</body>
</html>
"""

def write_batch_report(output_dir: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_batch_report(payload)
    batch_id = str(report.get("batch_id") or "unknown_batch").replace("/", "_")
    (out / f"{batch_id}_batch_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / f"{batch_id}_batch_report.html").write_text(
        render_batch_report_html(report),
        encoding="utf-8",
    )
    return report

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase83(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase83_journal_replay_batch_report_research_only"
    out.mkdir(parents=True, exist_ok=True)

    report = write_batch_report(out, SAMPLE_BATCH)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_batch_report": report,
        **LOCKS,
    }

    (out / "phase83_journal_replay_batch_report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(render_batch_report_html(report), encoding="utf-8")

    project_out = project / "docs" / "reports" / "journal_replay"
    project_out.mkdir(parents=True, exist_ok=True)
    write_batch_report(project_out, SAMPLE_BATCH)
    (project_out / "phase83_journal_replay_batch_report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (project_out / "phase83_journal_replay_batch_report.html").write_text(
        render_batch_report_html(report),
        encoding="utf-8",
    )

    return result

def main() -> int:
    result = build_phase83()
    print("QRDS Phase 83 • Journal Replay Batch Report Research-Only")
    print(result["gate"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
