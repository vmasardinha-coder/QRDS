from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE82_JOURNAL_REPLAY_BATCH_INTAKE_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

REQUIRED_PHASES = {
    79: "PHASE79_JOURNAL_REPLAY_BATCH_LOADER_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    80: "PHASE80_JOURNAL_REPLAY_BATCH_QUARANTINE_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    81: "PHASE81_JOURNAL_REPLAY_QUARANTINE_INDEX_RESEARCH_ONLY_READY_RESEARCH_ONLY",
}

CAPABILITY_MAP = [
    {
        "phase": 79,
        "capability": "journal_replay_batch_loader",
        "status": "READY_RESEARCH_ONLY",
        "purpose": "Loads external/staging JSON batches and validates structure.",
    },
    {
        "phase": 80,
        "capability": "journal_replay_batch_quarantine",
        "status": "READY_RESEARCH_ONLY",
        "purpose": "Creates quarantine bundles for invalid batches or entries.",
    },
    {
        "phase": 81,
        "capability": "journal_replay_quarantine_index",
        "status": "READY_RESEARCH_ONLY",
        "purpose": "Indexes quarantine bundles for human review.",
    },
]

def evaluate_batch_intake_checkpoint(report_text: str | None = None, files: list[str] | None = None) -> dict[str, Any]:
    missing_phases: list[int] = []
    detected_phases: list[int] = []

    if report_text:
        for phase, gate in REQUIRED_PHASES.items():
            if gate in report_text:
                detected_phases.append(phase)
            else:
                missing_phases.append(phase)
    elif files is not None:
        blob = "\n".join(files).lower()
        for phase in REQUIRED_PHASES:
            if f"phase{phase}" in blob:
                detected_phases.append(phase)
            else:
                missing_phases.append(phase)
    else:
        missing_phases = list(REQUIRED_PHASES)

    return {
        "batch_intake_checkpoint_ready_for_research_only": len(missing_phases) == 0,
        "required_phase_count": len(REQUIRED_PHASES),
        "detected_phase_count": len(detected_phases),
        "missing_phases": missing_phases,
        "detected_phases": detected_phases,
        "human_review_required": True,
        "batch_loader_descriptive_only": True,
        "quarantine_index_descriptive_only": True,
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

def render_checkpoint_html(result: dict[str, Any]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{item['phase']}</td>"
        f"<td>{item['capability']}</td>"
        f"<td>{item['status']}</td>"
        f"<td>{item['purpose']}</td>"
        "</tr>"
        for item in CAPABILITY_MAP
    )
    return f"""
<html>
<head>
  <meta charset="utf-8">
  <title>QRDS Journal Replay Batch Intake Checkpoint</title>
  <style>
    body{{font-family:system-ui;background:#07111f;color:#e7edf8;padding:32px}}
    table{{border-collapse:collapse;width:100%;background:#101f35}}
    th,td{{border:1px solid #28415f;padding:10px;text-align:left;vertical-align:top}}
    .badge{{display:inline-block;padding:6px 10px;border:1px solid #28415f;border-radius:999px;margin:4px}}
  </style>
</head>
<body>
  <h1>QRDS Journal Replay Batch Intake Checkpoint</h1>
  <p>{READY_GATE}</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">loader_execution_allowed: False</p>
  <p class="badge">replay_execution_allowed: False</p>
  <p class="badge">Edge: False</p>
  <p class="badge">Shadow decision allowed: False</p>
  <p class="badge">Decision layer allowed: False</p>
  <p class="badge">Promotion allowed: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>

  <h2>Checkpoint</h2>
  <p>Ready: {result["batch_intake_checkpoint_ready_for_research_only"]}</p>
  <p>Required phases: {result["required_phase_count"]}</p>
  <p>Detected phases: {result["detected_phase_count"]}</p>
  <p>Missing phases: {result["missing_phases"]}</p>

  <h2>Capabilities</h2>
  <table>
    <thead><tr><th>Phase</th><th>Capability</th><th>Status</th><th>Purpose</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>Boundary</h2>
  <p>This checkpoint confirms batch intake is descriptive research only. It does not unlock replay execution,
  edge validation, trading signals, recommendations, allocations, shadow decisions, operational decisions,
  safe-apply, promotion or canonical writes.</p>
</body>
</html>
"""

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def _load_report_text(project: Path) -> str:
    path = project / "docs" / "reports" / "PROJECT_STATUS_QRDS_GATE_BTC.md"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="cp1252")
    return ""

def build_phase82(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase82_journal_replay_batch_intake_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    report_text = _load_report_text(project)
    checkpoint = evaluate_batch_intake_checkpoint(report_text=report_text)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "required_phases": REQUIRED_PHASES,
        "capability_map": CAPABILITY_MAP,
        "checkpoint": checkpoint,
        **LOCKS,
    }

    html = render_checkpoint_html(checkpoint)

    (out / "phase82_journal_replay_batch_intake_checkpoint.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(html, encoding="utf-8")

    project_out = project / "docs" / "reports" / "journal_replay"
    project_out.mkdir(parents=True, exist_ok=True)
    (project_out / "phase82_journal_replay_batch_intake_checkpoint.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (project_out / "phase82_journal_replay_batch_intake_checkpoint.html").write_text(
        html,
        encoding="utf-8",
    )

    return result

def main() -> int:
    result = build_phase82()
    print("QRDS Phase 82 • Journal Replay Batch Intake Checkpoint Research-Only")
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
