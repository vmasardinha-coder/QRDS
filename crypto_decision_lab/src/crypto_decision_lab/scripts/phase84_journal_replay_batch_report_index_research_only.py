from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase79_journal_replay_batch_loader_research_only import SAMPLE_BATCH
from crypto_decision_lab.scripts.phase83_journal_replay_batch_report_research_only import (
    write_batch_report,
)

READY_GATE = "PHASE84_JOURNAL_REPLAY_BATCH_REPORT_INDEX_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

REQUIRED_REPORT_FLAGS = {
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

def validate_batch_report_for_index(report: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    if not report.get("batch_id"):
        errors.append("missing:batch_id")
    if report.get("human_review_required") is not True:
        errors.append("human_review_required_must_be_true")
    if report.get("batch_report_descriptive_only") is not True:
        errors.append("batch_report_must_be_descriptive_only")

    for key, expected in REQUIRED_REPORT_FLAGS.items():
        if report.get(key) != expected:
            errors.append(f"safety_flag_mismatch:{key}")

    return {
        "report_valid_for_research_index": len(errors) == 0,
        "errors": errors,
        "batch_id": report.get("batch_id"),
        "report_status": report.get("report_status"),
        "human_review_required": True,
        "loader_execution_allowed": False,
        "replay_execution_allowed": False,
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "safe_apply_allowed": False,
        "promotion_allowed": False,
        "canonical_data_writes": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def _entry(path: Path, report: dict[str, Any]) -> dict[str, Any]:
    replay = report.get("replay_summary", {}) or {}
    scorecard = report.get("evidence_scorecard", {}) or {}
    validation = validate_batch_report_for_index(report)

    return {
        "batch_id": report.get("batch_id"),
        "path": str(path),
        "report_status": report.get("report_status"),
        "row_count": replay.get("row_count", 0),
        "valid_row_count": replay.get("valid_row_count", 0),
        "invalid_row_count": replay.get("invalid_row_count", 0),
        "active_paper_observation_count": replay.get("active_paper_observation_count", 0),
        "evidence_status": scorecard.get("evidence_status"),
        "human_review_required": report.get("human_review_required"),
        "validation": validation,
    }

def build_batch_report_index(report_dir: str | Path) -> dict[str, Any]:
    base = Path(report_dir)
    base.mkdir(parents=True, exist_ok=True)

    entries = []
    invalid_entries = []

    for path in sorted(base.glob("*_batch_report.json")):
        if path.name.startswith("phase83_"):
            continue

        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            report = {
                "batch_id": path.stem,
                "report_status": "NEEDS_REVIEW_RESEARCH_ONLY",
                "human_review_required": True,
                "batch_report_descriptive_only": True,
                "read_error": str(exc),
                **REQUIRED_REPORT_FLAGS,
            }

        item = _entry(path, report)
        entries.append(item)

        if item["validation"]["report_valid_for_research_index"] is not True:
            invalid_entries.append(item)

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "batch_report_index_descriptive_only": True,
        "report_count": len(entries),
        "invalid_index_entry_count": len(invalid_entries),
        "entries": entries,
        "invalid_index_entries": invalid_entries,
        "index_valid_for_research_only": len(invalid_entries) == 0,
        "human_review_required": True,
        "loader_execution_allowed": False,
        "replay_execution_allowed": False,
        **LOCKS,
    }

def render_batch_report_index_html(index: dict[str, Any]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{entry['batch_id']}</td>"
        f"<td>{entry['report_status']}</td>"
        f"<td>{entry['row_count']}</td>"
        f"<td>{entry['active_paper_observation_count']}</td>"
        f"<td>{entry['evidence_status']}</td>"
        f"<td>{entry['human_review_required']}</td>"
        f"<td>{entry['validation']['report_valid_for_research_index']}</td>"
        "</tr>"
        for entry in index["entries"]
    ) or "<tr><td colspan='7'>No batch reports found.</td></tr>"

    return f"""
<html>
<head>
  <meta charset="utf-8">
  <title>QRDS Journal Replay Batch Report Index</title>
  <style>
    body{{font-family:system-ui;background:#07111f;color:#e7edf8;padding:32px}}
    table{{border-collapse:collapse;width:100%;background:#101f35}}
    th,td{{border:1px solid #28415f;padding:10px;text-align:left;vertical-align:top}}
    .badge{{display:inline-block;padding:6px 10px;border:1px solid #28415f;border-radius:999px;margin:4px}}
  </style>
</head>
<body>
  <h1>QRDS Journal Replay Batch Report Index</h1>
  <p>{READY_GATE}</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">batch_report_index_descriptive_only: True</p>
  <p class="badge">loader_execution_allowed: False</p>
  <p class="badge">replay_execution_allowed: False</p>
  <p class="badge">Edge: False</p>
  <p class="badge">Shadow decision allowed: False</p>
  <p class="badge">Decision layer allowed: False</p>
  <p class="badge">Promotion allowed: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>

  <h2>Summary</h2>
  <p>report_count: {index["report_count"]}</p>
  <p>invalid_index_entry_count: {index["invalid_index_entry_count"]}</p>
  <p>index_valid_for_research_only: {index["index_valid_for_research_only"]}</p>

  <h2>Batch Reports</h2>
  <table>
    <thead>
      <tr>
        <th>Batch ID</th><th>Status</th><th>Rows</th><th>Active</th>
        <th>Evidence</th><th>Human Review</th><th>Index Valid</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>Boundary</h2>
  <p>This index is descriptive research only. It does not validate edge, generate signals,
  recommendations, allocations, shadow decisions, operational decisions, promotion, safe-apply or canonical writes.</p>
</body>
</html>
"""

def write_batch_report_index(report_dir: str | Path) -> dict[str, Any]:
    base = Path(report_dir)
    index = build_batch_report_index(base)
    (base / "batch_report_index.json").write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    (base / "batch_report_index.html").write_text(render_batch_report_index_html(index), encoding="utf-8")
    return index

def build_phase84(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = Path.cwd()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase84_journal_replay_batch_report_index_research_only"
    out.mkdir(parents=True, exist_ok=True)

    write_batch_report(out, SAMPLE_BATCH)
    index = write_batch_report_index(out)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_batch_report_index": index,
        **LOCKS,
    }

    (out / "phase84_journal_replay_batch_report_index.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(render_batch_report_index_html(index), encoding="utf-8")
    return result

def main() -> int:
    result = build_phase84()
    print("QRDS Phase 84 • Journal Replay Batch Report Index Research-Only")
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
