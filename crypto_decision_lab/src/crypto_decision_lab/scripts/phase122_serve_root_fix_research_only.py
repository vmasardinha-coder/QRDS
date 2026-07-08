from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase121_review_portal_index_page_research_only import build_index_page

READY_GATE = "PHASE122_SERVE_ROOT_FIX_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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
$indexFile = Join-Path $portalDir "index.html"
$reviewFile = Join-Path $portalDir "phase114_replay_evidence_export_review_portal_stub.html"

if (-not (Test-Path $indexFile)) {
  Write-Host "Portal index not found. Run Phase 121 first." -ForegroundColor Red
  exit 1
}

if (-not (Test-Path $reviewFile)) {
  Write-Host "Review portal artifact not found. Run Phase 114 first." -ForegroundColor Red
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
Write-Host "Serving index:"
Write-Host "  http://localhost:$Port/index.html"
Write-Host ""
Write-Host "Review page:"
Write-Host "  http://localhost:$Port/phase114_replay_evidence_export_review_portal_stub.html"
Write-Host ""
Write-Host "Press CTRL+C to stop."
Write-Host ""

Set-Location $portalDir
python -m http.server $Port
'''

def build_serve_root_fix(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()
    index = build_index_page(root)

    script_path = root / SERVE_SCRIPT_PATH
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(SERVE_SCRIPT, encoding="utf-8")

    portal_index = root / "artifacts" / "phase114_replay_evidence_export_review_portal_stub_research_only" / "index.html"
    review_page = root / "artifacts" / "phase114_replay_evidence_export_review_portal_stub_research_only" / "phase114_replay_evidence_export_review_portal_stub.html"

    script_text = script_path.read_text(encoding="utf-8")

    root_fix_pass = (
        index["index_pass"] is True
        and script_path.exists()
        and portal_index.exists()
        and review_page.exists()
        and "http://localhost:$Port/index.html" in script_text
        and "python -m http.server" in script_text
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "serve_root_fix_name": "review_portal_serve_root_fix_research_only",
        "serve_script_path": SERVE_SCRIPT_PATH,
        "local_index_url": "http://localhost:8765/index.html",
        "local_review_url": "http://localhost:8765/phase114_replay_evidence_export_review_portal_stub.html",
        "source_index_gate": index["gate"],
        "source_index_pass": index["index_pass"],
        "serve_root_fix_pass": root_fix_pass,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase122(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase122_serve_root_fix_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_serve_root_fix()
    (out / "phase122_serve_root_fix.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["serve_root_fix_pass"], "serve_root_fix": result, **LOCKS}

def main() -> int:
    result = build_phase122()
    fix = result["serve_root_fix"]

    print(result["gate"])
    print("Serve root fix pass:", fix["serve_root_fix_pass"])
    print("Serve script path:", fix["serve_script_path"])
    print("Local index URL:", fix["local_index_url"])
    print("Local review URL:", fix["local_review_url"])
    print("Approval effect:", fix["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if fix["serve_root_fix_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
