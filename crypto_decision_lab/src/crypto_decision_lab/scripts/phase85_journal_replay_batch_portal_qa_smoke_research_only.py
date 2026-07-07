from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase84_journal_replay_batch_report_index_research_only import (
    READY_GATE as PHASE84_GATE,
    build_phase84,
)

READY_GATE = "PHASE85_JOURNAL_REPLAY_BATCH_PORTAL_QA_SMOKE_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

REQUIRED_PORTAL_FILES = [
    "phase84_journal_replay_batch_report_index.json",
    "batch_report_index.json",
    "batch_report_index.html",
    "index.html",
    "sample-batch-79_batch_report.json",
    "sample-batch-79_batch_report.html",
]

REQUIRED_HTML_MARKERS = [
    "QRDS Journal Replay Batch Report Index",
    "Operational: BLOCKED_RESEARCH_ONLY",
    "batch_report_index_descriptive_only: True",
    "loader_execution_allowed: False",
    "replay_execution_allowed: False",
    "Edge: False",
    "Shadow decision allowed: False",
    "Decision layer allowed: False",
    "Promotion allowed: False",
    "safe_apply_allowed: False",
    "canonical_data_writes: 0",
    "This index is descriptive research only",
]

FORBIDDEN_OPERATIONAL_MARKERS = [
    "BUY SIGNAL",
    "SELL SIGNAL",
    "EXECUTE ORDER",
    "LIVE TRADING",
    "decision_layer_allowed: True",
    "shadow_decision_allowed: True",
    "safe_apply_allowed: True",
    "promotion_allowed: True",
    "canonical_data_writes: 1",
    "edge_validated: True",
]

def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def qa_smoke_batch_portal(portal_dir: str | Path) -> dict[str, Any]:
    base = Path(portal_dir)
    errors: list[str] = []
    warnings: list[str] = []

    file_checks = []
    for name in REQUIRED_PORTAL_FILES:
        path = base / name
        exists = path.exists()
        file_checks.append({"file": name, "exists": exists})
        if not exists:
            errors.append(f"missing_file:{name}")

    html_checks = []
    html_path = base / "batch_report_index.html"
    html_text = html_path.read_text(encoding="utf-8") if html_path.exists() else ""

    for marker in REQUIRED_HTML_MARKERS:
        found = marker in html_text
        html_checks.append({"marker": marker, "found": found})
        if not found:
            errors.append(f"missing_html_marker:{marker}")

    forbidden_checks = []
    for marker in FORBIDDEN_OPERATIONAL_MARKERS:
        found = marker in html_text
        forbidden_checks.append({"marker": marker, "found": found})
        if found:
            errors.append(f"forbidden_operational_marker:{marker}")

    index_json_path = base / "batch_report_index.json"
    index_json = _read_json(index_json_path) if index_json_path.exists() else {}

    if index_json:
        if index_json.get("gate") != PHASE84_GATE:
            errors.append("index_gate_mismatch")
        if index_json.get("operational_status") != "BLOCKED_RESEARCH_ONLY":
            errors.append("operational_status_not_blocked")
        if index_json.get("edge_validated") is not False:
            errors.append("edge_validated_not_false")
        if index_json.get("shadow_decision_allowed") is not False:
            errors.append("shadow_decision_allowed_not_false")
        if index_json.get("decision_layer_allowed") is not False:
            errors.append("decision_layer_allowed_not_false")
        if index_json.get("safe_apply_allowed") is not False:
            errors.append("safe_apply_allowed_not_false")
        if index_json.get("promotion_allowed") is not False:
            errors.append("promotion_allowed_not_false")
        if index_json.get("canonical_data_writes") != 0:
            errors.append("canonical_data_writes_not_zero")
        if index_json.get("report_count", 0) < 1:
            warnings.append("no_batch_reports_indexed")

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "portal_qa_smoke_descriptive_only": True,
        "portal_dir": str(base),
        "qa_status": "PASS_RESEARCH_ONLY" if not errors else "NEEDS_REVIEW_RESEARCH_ONLY",
        "errors": errors,
        "warnings": warnings,
        "file_checks": file_checks,
        "html_checks": html_checks,
        "forbidden_checks": forbidden_checks,
        "human_review_required": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        "focused_tests_required": True,
        **LOCKS,
    }

def render_qa_smoke_html(report: dict[str, Any]) -> str:
    error_rows = "".join(f"<li>{item}</li>" for item in report["errors"]) or "<li>No errors.</li>"
    warning_rows = "".join(f"<li>{item}</li>" for item in report["warnings"]) or "<li>No warnings.</li>"
    file_rows = "".join(
        f"<tr><td>{item['file']}</td><td>{item['exists']}</td></tr>"
        for item in report["file_checks"]
    )

    return f"""
<html>
<head>
  <meta charset="utf-8">
  <title>QRDS Journal Replay Batch Portal QA Smoke</title>
  <style>
    body{{font-family:system-ui;background:#07111f;color:#e7edf8;padding:32px}}
    table{{border-collapse:collapse;width:100%;background:#101f35}}
    th,td{{border:1px solid #28415f;padding:10px;text-align:left;vertical-align:top}}
    .badge{{display:inline-block;padding:6px 10px;border:1px solid #28415f;border-radius:999px;margin:4px}}
  </style>
</head>
<body>
  <h1>QRDS Journal Replay Batch Portal QA Smoke</h1>
  <p>{READY_GATE}</p>
  <p class="badge">QA status: {report["qa_status"]}</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">Full suite: SKIPPED_LOCAL_ECONOMICAL</p>
  <p class="badge">Edge: False</p>
  <p class="badge">Shadow decision allowed: False</p>
  <p class="badge">Decision layer allowed: False</p>
  <p class="badge">Promotion allowed: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>

  <h2>Files</h2>
  <table>
    <thead><tr><th>File</th><th>Exists</th></tr></thead>
    <tbody>{file_rows}</tbody>
  </table>

  <h2>Errors</h2>
  <ul>{error_rows}</ul>

  <h2>Warnings</h2>
  <ul>{warning_rows}</ul>

  <h2>Boundary</h2>
  <p>This QA smoke is descriptive research only. It does not validate edge, generate signals,
  recommendations, allocations, shadow decisions, operational decisions, promotion, safe-apply or canonical writes.</p>
</body>
</html>
"""

def write_qa_smoke_report(output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    build_phase84(out)
    report = qa_smoke_batch_portal(out)

    (out / "phase85_journal_replay_batch_portal_qa_smoke.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase85_journal_replay_batch_portal_qa_smoke.html").write_text(
        render_qa_smoke_html(report),
        encoding="utf-8",
    )
    return report

def build_phase85(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = Path.cwd()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase85_journal_replay_batch_portal_qa_smoke_research_only"
    report = write_qa_smoke_report(out)
    return {
        "gate": READY_GATE,
        "ready": report["qa_status"] == "PASS_RESEARCH_ONLY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "qa_smoke_report": report,
        **LOCKS,
    }

def main() -> int:
    result = build_phase85()
    report = result["qa_smoke_report"]
    print("QRDS Phase 85 • Journal Replay Batch Portal QA Smoke Research-Only")
    print(result["gate"])
    print("QA status:", report["qa_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")
    print("Full suite: SKIPPED_LOCAL_ECONOMICAL")
    return 0 if report["qa_status"] == "PASS_RESEARCH_ONLY" else 2

if __name__ == "__main__":
    raise SystemExit(main())
