from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase123_portal_link_smoke_test_research_only import build_link_smoke_test

READY_GATE = "PHASE124_ONE_COMMAND_REVIEW_PORTAL_RUNNER_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

RUNNER_SCRIPT_PATH = "tools/run_review_portal_research_only.ps1"
SERVE_SCRIPT_PATH = "tools/serve_review_portal_research_only.ps1"

RUNNER_SCRIPT = r'''param(
  [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$serveScript = Join-Path $root "tools\serve_review_portal_research_only.ps1"
$portalIndex = Join-Path $root "artifacts\phase114_replay_evidence_export_review_portal_stub_research_only\index.html"

if (-not (Test-Path $serveScript)) {
  Write-Host "Serve script not found. Run Phase 122 first." -ForegroundColor Red
  exit 1
}

if (-not (Test-Path $portalIndex)) {
  Write-Host "Portal index not found. Run Phase 121 first." -ForegroundColor Red
  exit 1
}

Write-Host ""
Write-Host "QRDS one-command review portal runner"
Write-Host "Research-only mode"
Write-Host "Operational: BLOCKED_RESEARCH_ONLY"
Write-Host "Edge: False"
Write-Host "Decision layer allowed: False"
Write-Host "trading_signal_generated: False"
Write-Host "allocation_generated: False"
Write-Host "safe_apply_allowed: False"
Write-Host "canonical_data_writes: 0"
Write-Host ""
Write-Host "Open:"
Write-Host "  http://localhost:$Port/index.html"
Write-Host ""

& $serveScript -Port $Port
'''

def build_runner(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()
    smoke = build_link_smoke_test(root)

    runner_path = root / RUNNER_SCRIPT_PATH
    runner_path.parent.mkdir(parents=True, exist_ok=True)
    runner_path.write_text(RUNNER_SCRIPT, encoding="utf-8")

    serve_path = root / SERVE_SCRIPT_PATH
    portal_index = root / "artifacts" / "phase114_replay_evidence_export_review_portal_stub_research_only" / "index.html"

    runner_text = runner_path.read_text(encoding="utf-8") if runner_path.exists() else ""

    runner_pass = (
        smoke["link_smoke_pass"] is True
        and runner_path.exists()
        and serve_path.exists()
        and portal_index.exists()
        and "http://localhost:$Port/index.html" in runner_text
        and "BLOCKED_RESEARCH_ONLY" in runner_text
        and "canonical_data_writes: 0" in runner_text
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runner_name": "one_command_review_portal_runner_research_only",
        "runner_script_path": RUNNER_SCRIPT_PATH,
        "serve_script_path": SERVE_SCRIPT_PATH,
        "local_index_url": "http://localhost:8765/index.html",
        "source_link_smoke_gate": smoke["gate"],
        "source_link_smoke_pass": smoke["link_smoke_pass"],
        "runner_pass": runner_pass,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase124(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase124_one_command_review_portal_runner_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_runner()
    (out / "phase124_one_command_review_portal_runner.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["runner_pass"], "runner": result, **LOCKS}

def main() -> int:
    result = build_phase124()
    runner = result["runner"]

    print(result["gate"])
    print("Runner pass:", runner["runner_pass"])
    print("Runner script:", runner["runner_script_path"])
    print("Serve script:", runner["serve_script_path"])
    print("Local index URL:", runner["local_index_url"])
    print("Approval effect:", runner["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if runner["runner_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
