from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase116_export_review_runbook_research_only import build_runbook
from crypto_decision_lab.scripts.phase117_review_portal_asset_index_research_only import build_asset_index
from crypto_decision_lab.scripts.phase119_local_review_portal_smoke_test_research_only import build_smoke_test

READY_GATE = "PHASE121_REVIEW_PORTAL_INDEX_PAGE_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

PORTAL_DIR = "artifacts/phase114_replay_evidence_export_review_portal_stub_research_only"
INDEX_FILE = "index.html"
REVIEW_PAGE = "phase114_replay_evidence_export_review_portal_stub.html"

def render_index(runbook: dict[str, Any], asset_index: dict[str, Any], smoke: dict[str, Any]) -> str:
    asset_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(asset['asset_id'])}</td>"
        f"<td>{asset['phase']}</td>"
        f"<td>{html.escape(asset['asset_type'])}</td>"
        f"<td>{html.escape(asset['operational_effect'])}</td>"
        "</tr>"
        for asset in asset_index["assets"]
    )

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>QRDS Review Portal Index</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background:#07111f; color:#e7edf8; padding:32px; }}
    a {{ color:#8ec7ff; }}
    .badge {{ display:inline-block; padding:6px 10px; border:1px solid #28415f; border-radius:999px; margin:4px; }}
    .card {{ border:1px solid #28415f; background:#101f35; padding:18px; margin:18px 0; border-radius:12px; }}
    table {{ border-collapse: collapse; width:100%; background:#101f35; margin-top:16px; }}
    th, td {{ border:1px solid #28415f; padding:10px; text-align:left; }}
    th {{ background:#162944; }}
    .blocked {{ color:#ffb4b4; font-weight:600; }}
  </style>
</head>
<body>
  <h1>QRDS Review Portal Index</h1>
  <p>{READY_GATE}</p>

  <p class="badge">Research-only</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">Edge: False</p>
  <p class="badge">Decision layer allowed: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>

  <div class="card">
    <h2>Open review portal</h2>
    <p><a href="{REVIEW_PAGE}">Open Phase 114 Review Portal Stub</a></p>
    <p>Smoke test pass: {smoke['smoke_test_pass']}</p>
  </div>

  <div class="card">
    <h2>Runbook</h2>
    <p>Runbook pass: {runbook['runbook_pass']}</p>
    <p>Approval effect: {runbook['approval_effect']}</p>
  </div>

  <div class="card">
    <h2>Asset Index</h2>
    <p>Asset index pass: {asset_index['asset_index_pass']}</p>
    <p>Asset count: {asset_index['asset_count']}</p>
    <table>
      <thead><tr><th>Asset</th><th>Phase</th><th>Type</th><th>Operational Effect</th></tr></thead>
      <tbody>{asset_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Boundary</h2>
    <p class="blocked">This index cannot validate edge, generate trading signals, recommendations, allocations, shadow decisions, operational decisions, safe-apply actions, promotions or canonical writes.</p>
  </div>
</body>
</html>
"""

def build_index_page(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()

    runbook = build_runbook(root)
    asset_index = build_asset_index(root)
    smoke = build_smoke_test(root)

    portal_dir = root / PORTAL_DIR
    portal_dir.mkdir(parents=True, exist_ok=True)

    index_path = portal_dir / INDEX_FILE
    review_page_path = portal_dir / REVIEW_PAGE

    index_path.write_text(
        render_index(runbook, asset_index, smoke),
        encoding="utf-8",
    )

    index_pass = (
        runbook["runbook_pass"] is True
        and asset_index["asset_index_pass"] is True
        and smoke["smoke_test_pass"] is True
        and index_path.exists()
        and review_page_path.exists()
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "index_name": "review_portal_index_page_research_only",
        "index_path": str(index_path.relative_to(root)).replace("\\", "/"),
        "review_page_path": str(review_page_path.relative_to(root)).replace("\\", "/"),
        "local_index_url": "http://localhost:8765/index.html",
        "local_review_url": "http://localhost:8765/phase114_replay_evidence_export_review_portal_stub.html",
        "source_runbook_gate": runbook["gate"],
        "source_asset_index_gate": asset_index["gate"],
        "source_smoke_gate": smoke["gate"],
        "index_pass": index_pass,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase121(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase121_review_portal_index_page_research_only"
    out.mkdir(parents=True, exist_ok=True)

    index = build_index_page()
    (out / "phase121_review_portal_index_page.json").write_text(
        json.dumps(index, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": index["index_pass"], "index": index, **LOCKS}

def main() -> int:
    result = build_phase121()
    index = result["index"]

    print(result["gate"])
    print("Index pass:", index["index_pass"])
    print("Index path:", index["index_path"])
    print("Local index URL:", index["local_index_url"])
    print("Local review URL:", index["local_review_url"])
    print("Approval effect:", index["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if index["index_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
