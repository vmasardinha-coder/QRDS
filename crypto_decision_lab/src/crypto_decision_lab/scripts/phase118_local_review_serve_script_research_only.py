from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase117_review_portal_asset_index_research_only import build_asset_index

READY_GATE = "PHASE118_LOCAL_REVIEW_SERVE_SCRIPT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

SERVE_SCRIPT_PATH = "tools/serve_review_portal_research_only.ps1"

SERVE_SCRIPT = r'''param(
  [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$portalDir = Join-Path $root "artifacts\phase114_replay_evidence_export_review_portal_stub_research_only"
$portalFile = Join-Path $portalDir "phase114_replay_evidence_export_review_portal_stub.html"

if (-not (Test-Path $portalFile)) {
  Write-Host "Portal artifact not found. Run Phase 114 or Phase 117 first." -ForegroundColor Red
  exit 1
}

Write-Host ""
Write-Host "QRDS Review Portal Research-Only"
Write-Host "Operational: BLOCKED_RESEARCH_ONLY"
Write-Host "Edge: False"
Write-Host "Decision layer allowed: False"
Write-Host "trading_signal_generated: False"
Write-Host "allocation_generated: False"
Write-Host "safe_apply_allowed: False"
Write-Host "canonical_data_writes: 0"
Write-Host ""
Write-Host "Serving:"
Write-Host "  http://localhost:$Port/phase114_replay_evidence_export_review_portal_stub.html"
Write-Host ""
Write-Host "Press CTRL+C to stop."
Write-Host ""

Set-Location $portalDir
python -m http.server $Port
'''

def build_serve_script(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()
    index = build_asset_index(root)

    script_path = root / SERVE_SCRIPT_PATH
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(SERVE_SCRIPT, encoding="utf-8")

    portal_html = root / "artifacts" / "phase114_replay_evidence_export_review_portal_stub_research_only" / "phase114_replay_evidence_export_review_portal_stub.html"

    serve_pass = (
        index["asset_index_pass"] is True
        and script_path.exists()
        and portal_html.exists()
        and index["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "serve_script_name": "serve_review_portal_research_only",
        "serve_script_path": SERVE_SCRIPT_PATH,
        "default_port": 8765,
        "portal_url": "http://localhost:8765/phase114_replay_evidence_export_review_portal_stub.html",
        "source_asset_index_gate": index["gate"],
        "source_asset_index_pass": index["asset_index_pass"],
        "serve_script_pass": serve_pass,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase118(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase118_local_review_serve_script_research_only"
    out.mkdir(parents=True, exist_ok=True)

    serve = build_serve_script()
    (out / "phase118_local_review_serve_script.json").write_text(
        json.dumps(serve, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": serve["serve_script_pass"], "serve": serve, **LOCKS}

def main() -> int:
    result = build_phase118()
    serve = result["serve"]

    print(result["gate"])
    print("Serve script pass:", serve["serve_script_pass"])
    print("Serve script path:", serve["serve_script_path"])
    print("Portal URL:", serve["portal_url"])
    print("Approval effect:", serve["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if serve["serve_script_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
