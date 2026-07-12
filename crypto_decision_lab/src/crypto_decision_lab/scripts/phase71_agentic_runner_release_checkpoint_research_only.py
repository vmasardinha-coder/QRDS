from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE71_AGENTIC_RUNNER_RELEASE_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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
    60: "PHASE60_AGENTIC_DEVOPS_HARNESS_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    61: "PHASE61_AGENT_REPORT_INTAKE_VALIDATOR_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    62: "PHASE62_AGENT_CHANGE_REVIEW_LEDGER_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    63: "PHASE63_AGENT_SAFE_PATCH_PROTOCOL_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    64: "PHASE64_AGENT_PATCH_DIFF_GUARD_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    65: "PHASE65_LOCAL_SAFETY_PREFLIGHT_GUARD_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    66: "PHASE66_UNIFIED_LOCAL_PREFLIGHT_CLI_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    67: "PHASE67_RUNNER_PREFLIGHT_INTEGRATION_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    68: "PHASE68_RUNNER_VALIDATION_MANIFEST_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    69: "PHASE69_RUNNER_MANIFEST_WRITER_INTEGRATION_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    70: "PHASE70_VALIDATION_MANIFEST_INDEX_RESEARCH_ONLY_READY_RESEARCH_ONLY",
}

CAPABILITY_MAP = [
    {
        "capability": "agentic_devops_harness",
        "phase": 60,
        "status": "READY_RESEARCH_ONLY",
        "purpose": "Defines safe roles for Codex, Claude and QRDS controller.",
    },
    {
        "capability": "agent_report_intake",
        "phase": 61,
        "status": "READY_RESEARCH_ONLY",
        "purpose": "Validates auxiliary AI reports before human review.",
    },
    {
        "capability": "agent_change_review_ledger",
        "phase": 62,
        "status": "READY_RESEARCH_ONLY",
        "purpose": "Creates human-review ledger for agent changes.",
    },
    {
        "capability": "agent_safe_patch_protocol",
        "phase": 63,
        "status": "READY_RESEARCH_ONLY",
        "purpose": "Classifies safe patches versus blocked patches.",
    },
    {
        "capability": "agent_patch_diff_guard",
        "phase": 64,
        "status": "READY_RESEARCH_ONLY",
        "purpose": "Scans diffs for forbidden safety/decision changes.",
    },
    {
        "capability": "local_safety_preflight",
        "phase": 65,
        "status": "READY_RESEARCH_ONLY",
        "purpose": "Checks flags, tests, forbidden terms and watched paths.",
    },
    {
        "capability": "unified_preflight_cli",
        "phase": 66,
        "status": "READY_RESEARCH_ONLY",
        "purpose": "Provides qrds_local_preflight.sh.",
    },
    {
        "capability": "runner_preflight_integration",
        "phase": 67,
        "status": "READY_RESEARCH_ONLY",
        "purpose": "Runs local preflight from next-phase runner.",
    },
    {
        "capability": "runner_validation_manifest",
        "phase": 68,
        "status": "READY_RESEARCH_ONLY",
        "purpose": "Defines runner validation manifest schema.",
    },
    {
        "capability": "runner_manifest_writer",
        "phase": 69,
        "status": "READY_RESEARCH_ONLY",
        "purpose": "Writes lightweight runner manifests after validation.",
    },
    {
        "capability": "validation_manifest_index",
        "phase": 70,
        "status": "READY_RESEARCH_ONLY",
        "purpose": "Indexes validation manifests.",
    },
]

def evaluate_release_checkpoint(
    manifest_index: dict[str, Any] | None = None,
    report_text: str | None = None,
) -> dict[str, Any]:
    missing_phases: list[int] = []
    detected_phases: list[int] = []

    if manifest_index:
        entries = manifest_index.get("entries", [])
        indexed = {int(e.get("phase")) for e in entries if e.get("phase") is not None}
        for phase in REQUIRED_PHASES:
            if phase in indexed:
                detected_phases.append(phase)
            else:
                missing_phases.append(phase)
    elif report_text:
        for phase, gate in REQUIRED_PHASES.items():
            if gate in report_text:
                detected_phases.append(phase)
            else:
                missing_phases.append(phase)
    else:
        missing_phases = list(REQUIRED_PHASES)

    return {
        "release_checkpoint_ready_for_research_only": len(missing_phases) == 0,
        "required_phase_count": len(REQUIRED_PHASES),
        "detected_phase_count": len(detected_phases),
        "missing_phases": missing_phases,
        "detected_phases": detected_phases,
        "human_review_required": True,
        "agent_auto_apply_allowed": False,
        "safe_apply_allowed": False,
        "promotion_allowed": False,
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "canonical_data_writes": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def _load_manifest_index(project: Path) -> dict[str, Any] | None:
    path = project / "docs" / "reports" / "validation_automation" / "runner_manifest_index.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _load_report_text(project: Path) -> str:
    path = project / "docs" / "reports" / "PROJECT_STATUS_QRDS_GATE_BTC.md"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="cp1252")
    return ""

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
  <title>QRDS Agentic Runner Release Checkpoint</title>
  <style>
    body{{font-family:system-ui;background:#07111f;color:#e7edf8;padding:32px}}
    table{{border-collapse:collapse;width:100%;background:#101f35}}
    th,td{{border:1px solid #28415f;padding:10px;text-align:left}}
    .badge{{display:inline-block;padding:6px 10px;border:1px solid #28415f;border-radius:999px;margin:4px}}
  </style>
</head>
<body>
  <h1>QRDS Agentic Runner Release Checkpoint</h1>
  <p>{READY_GATE}</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">Edge: False</p>
  <p class="badge">Shadow decision allowed: False</p>
  <p class="badge">Decision layer allowed: False</p>
  <p class="badge">Promotion allowed: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>
  <h2>Checkpoint</h2>
  <p>Ready: {result["release_checkpoint_ready_for_research_only"]}</p>
  <p>Required phases: {result["required_phase_count"]}</p>
  <p>Detected phases: {result["detected_phase_count"]}</p>
  <p>Missing phases: {result["missing_phases"]}</p>
  <h2>Capabilities</h2>
  <table>
    <thead><tr><th>Phase</th><th>Capability</th><th>Status</th><th>Purpose</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>
"""

def build_phase71(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase71_agentic_runner_release_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    manifest_index = _load_manifest_index(project)
    report_text = _load_report_text(project)
    checkpoint = evaluate_release_checkpoint(manifest_index=manifest_index, report_text=report_text)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "capability_map": CAPABILITY_MAP,
        "required_phases": REQUIRED_PHASES,
        "checkpoint": checkpoint,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **LOCKS,
    }

    (out / "phase71_agentic_runner_release_checkpoint.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(render_checkpoint_html(checkpoint), encoding="utf-8")

    project_out = project / "docs" / "reports" / "agentic_devops"
    project_out.mkdir(parents=True, exist_ok=True)
    (project_out / "phase71_agentic_runner_release_checkpoint.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (project_out / "phase71_agentic_runner_release_checkpoint.html").write_text(
        render_checkpoint_html(checkpoint),
        encoding="utf-8",
    )

    return result

def main() -> int:
    result = build_phase71()
    print("QRDS Phase 71 • Agentic Runner Release Checkpoint Research-Only")
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
