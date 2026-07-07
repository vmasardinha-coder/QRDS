from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE77_JOURNAL_REPLAY_PORTAL_INDEX_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

REPLAY_PAGES = [
    {
        "phase": 72,
        "title": "Journal Replay Dry-Run Engine",
        "file": "phase72_journal_replay_dry_run_engine.html",
        "purpose": "Paper-only dry-run replay calculation; no execution.",
        "gate": "PHASE72_JOURNAL_REPLAY_DRY_RUN_ENGINE_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    },
    {
        "phase": 73,
        "title": "Journal Replay Aggregate Metrics",
        "file": "phase73_journal_replay_aggregate_metrics.html",
        "purpose": "Descriptive aggregate metrics such as paper PnL and win/loss counts.",
        "gate": "PHASE73_JOURNAL_REPLAY_AGGREGATE_METRICS_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    },
    {
        "phase": 74,
        "title": "Journal Replay Distribution Diagnostics",
        "file": "phase74_journal_replay_distribution_diagnostics.html",
        "purpose": "Distribution, concentration, outlier and drawdown-like diagnostics.",
        "gate": "PHASE74_JOURNAL_REPLAY_DISTRIBUTION_DIAGNOSTICS_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    },
    {
        "phase": 75,
        "title": "Journal Replay Quality Flags",
        "file": "phase75_journal_replay_quality_flags.html",
        "purpose": "Quality flags for small sample, invalid rows, concentration and outliers.",
        "gate": "PHASE75_JOURNAL_REPLAY_QUALITY_FLAGS_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    },
    {
        "phase": 76,
        "title": "Journal Replay Evidence Scorecard V2",
        "file": "phase76_journal_replay_evidence_scorecard_v2.html",
        "purpose": "Unified descriptive evidence scorecard and blockers to edge.",
        "gate": "PHASE76_JOURNAL_REPLAY_EVIDENCE_SCORECARD_V2_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    },
]

def validate_replay_portal_index(pages: list[dict[str, Any]], base_dir: str | Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    required_phases = {72, 73, 74, 75, 76}
    found_phases = {int(page.get("phase")) for page in pages if page.get("phase") is not None}

    missing = sorted(required_phases - found_phases)
    if missing:
        errors.append(f"missing_required_phases:{missing}")

    for page in pages:
        if not str(page.get("gate", "")).endswith("_READY_RESEARCH_ONLY"):
            errors.append(f"invalid_gate_phase:{page.get('phase')}")
        if not str(page.get("file", "")).endswith(".html"):
            errors.append(f"invalid_file_phase:{page.get('phase')}")

    if base_dir is not None:
        base = Path(base_dir)
        for page in pages:
            path = base / str(page.get("file"))
            if not path.exists():
                errors.append(f"missing_page_file:{page.get('file')}")

    return {
        "portal_index_valid_for_research_only": len(errors) == 0,
        "errors": errors,
        "page_count": len(pages),
        "required_phase_count": len(required_phases),
        "found_phases": sorted(found_phases),
        "missing_phases": missing,
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

def render_portal_index(pages: list[dict[str, Any]], validation: dict[str, Any]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{page['phase']}</td>"
        f"<td><a href='{page['file']}'>{page['title']}</a></td>"
        f"<td>{page['purpose']}</td>"
        f"<td>{page['gate']}</td>"
        "</tr>"
        for page in pages
    )
    return f"""
<html>
<head>
  <meta charset="utf-8">
  <title>QRDS Journal Replay Portal Index</title>
  <style>
    body{{font-family:system-ui;background:#07111f;color:#e7edf8;padding:32px}}
    a{{color:#8bd3ff}}
    table{{border-collapse:collapse;width:100%;background:#101f35}}
    th,td{{border:1px solid #28415f;padding:10px;text-align:left;vertical-align:top}}
    .badge{{display:inline-block;padding:6px 10px;border:1px solid #28415f;border-radius:999px;margin:4px}}
  </style>
</head>
<body>
  <h1>QRDS Journal Replay Portal Index</h1>
  <p>{READY_GATE}</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">Edge: False</p>
  <p class="badge">Shadow decision allowed: False</p>
  <p class="badge">Decision layer allowed: False</p>
  <p class="badge">Promotion allowed: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>

  <h2>Validation</h2>
  <p>portal_index_valid_for_research_only: {validation["portal_index_valid_for_research_only"]}</p>
  <p>page_count: {validation["page_count"]}</p>
  <p>missing_phases: {validation["missing_phases"]}</p>

  <h2>Replay Pages</h2>
  <table>
    <thead><tr><th>Phase</th><th>Page</th><th>Purpose</th><th>Gate</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>Important Boundary</h2>
  <p>This portal is descriptive research only. It does not validate edge, generate trading signals,
  recommendations, allocations, shadow decisions, operational decisions, safe-apply, promotion or canonical writes.</p>
</body>
</html>
"""

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase77(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase77_journal_replay_portal_index_research_only"
    out.mkdir(parents=True, exist_ok=True)

    validation = validate_replay_portal_index(REPLAY_PAGES)
    html = render_portal_index(REPLAY_PAGES, validation)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "replay_pages": REPLAY_PAGES,
        "portal_validation": validation,
        **LOCKS,
    }

    (out / "phase77_journal_replay_portal_index.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(html, encoding="utf-8")

    project_out = project / "docs" / "reports" / "journal_replay"
    project_out.mkdir(parents=True, exist_ok=True)
    (project_out / "phase77_journal_replay_portal_index.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (project_out / "index.html").write_text(html, encoding="utf-8")

    return result

def main() -> int:
    result = build_phase77()
    print("QRDS Phase 77 • Journal Replay Portal Index Research-Only")
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
