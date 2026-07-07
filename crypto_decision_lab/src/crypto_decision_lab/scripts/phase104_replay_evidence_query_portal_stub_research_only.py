from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase101_replay_evidence_query_index_research_only import build_query_index
from crypto_decision_lab.scripts.phase102_replay_evidence_query_manifest_research_only import build_query_manifest
from crypto_decision_lab.scripts.phase103_replay_evidence_query_cli_dry_run_research_only import build_cli_dry_run

READY_GATE = "PHASE104_REPLAY_EVIDENCE_QUERY_PORTAL_STUB_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def render_portal(index: dict[str, Any], manifest: dict[str, Any], dry_run: dict[str, Any]) -> str:
    rows = []
    for entry in index["entries"]:
        tags = ", ".join(entry["tags"])
        files = "<br>".join(html.escape(path) for path in entry["files"][:6])
        rows.append(
            "<tr>"
            f"<td>{entry['phase']}</td>"
            f"<td>{entry['query_status']}</td>"
            f"<td>{html.escape(tags)}</td>"
            f"<td>{files}</td>"
            "</tr>"
        )

    route_rows = []
    for route in manifest["query_routes"]:
        route_rows.append(
            "<tr>"
            f"<td>{html.escape(route['route'])}</td>"
            f"<td>{route['allowed']}</td>"
            f"<td>{html.escape(route['description'])}</td>"
            "</tr>"
        )

    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>QRDS Replay Evidence Query Portal Stub</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background:#07111f; color:#e7edf8; padding:32px; }}
    .badge {{ display:inline-block; padding:6px 10px; border:1px solid #28415f; border-radius:999px; margin:4px; }}
    table {{ border-collapse: collapse; width:100%; background:#101f35; margin-top:16px; }}
    th, td {{ border:1px solid #28415f; padding:10px; text-align:left; vertical-align:top; }}
    th {{ background:#162944; }}
    .blocked {{ color:#ffb4b4; }}
  </style>
</head>
<body>
  <h1>QRDS Replay Evidence Query Portal Stub</h1>
  <p>{READY_GATE}</p>

  <p class="badge">Research-only</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">Edge: False</p>
  <p class="badge">Decision layer allowed: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>

  <h2>Query Routes</h2>
  <table>
    <thead><tr><th>Route</th><th>Allowed</th><th>Description</th></tr></thead>
    <tbody>{''.join(route_rows)}</tbody>
  </table>

  <h2>Evidence Index</h2>
  <table>
    <thead><tr><th>Phase</th><th>Status</th><th>Tags</th><th>Files</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>

  <h2>Blocked Boundary</h2>
  <p class="blocked">This portal stub cannot generate trading signals, recommendations, allocations, shadow decisions, operational decisions, safe-apply actions, promotions or canonical writes.</p>

  <h2>Dry Run Summary</h2>
  <p>Allowed queries: {dry_run['allowed_query_count']} | Blocked queries: {dry_run['blocked_query_count']}</p>
</body>
</html>
"""

def build_portal_stub(project_root: str | Path | None = None) -> dict[str, Any]:
    index = build_query_index(project_root)
    manifest = build_query_manifest(project_root)
    dry_run = build_cli_dry_run(project_root)

    portal_pass = (
        index["query_index_pass"] is True
        and manifest["manifest_pass"] is True
        and dry_run["dry_run_pass"] is True
        and dry_run["blocked_query_count"] == 3
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "portal_name": "replay_evidence_query_portal_stub",
        "source_index_gate": index["gate"],
        "source_manifest_gate": manifest["gate"],
        "source_dry_run_gate": dry_run["gate"],
        "portal_pass": portal_pass,
        "portal_status": "PASS_RESEARCH_ONLY" if portal_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "blocked_query_count": dry_run["blocked_query_count"],
        "allowed_query_count": dry_run["allowed_query_count"],
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase104(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase104_replay_evidence_query_portal_stub_research_only"
    out.mkdir(parents=True, exist_ok=True)

    index = build_query_index()
    manifest = build_query_manifest()
    dry_run = build_cli_dry_run()
    portal = build_portal_stub()

    (out / "phase104_replay_evidence_query_portal_stub.json").write_text(
        json.dumps(portal, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase104_replay_evidence_query_portal_stub.html").write_text(
        render_portal(index, manifest, dry_run),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": portal["portal_pass"],
        "portal": portal,
        **LOCKS,
    }

def main() -> int:
    result = build_phase104()
    portal = result["portal"]

    print(result["gate"])
    print("Portal pass:", portal["portal_pass"])
    print("Portal status:", portal["portal_status"])
    print("Allowed query count:", portal["allowed_query_count"])
    print("Blocked query count:", portal["blocked_query_count"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if portal["portal_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
