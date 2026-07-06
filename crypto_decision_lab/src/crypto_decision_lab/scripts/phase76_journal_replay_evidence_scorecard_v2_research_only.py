from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase72_journal_replay_dry_run_engine_research_only import (
    SAMPLE_REPLAY_ENTRIES,
    replay_batch_dry_run,
)
from crypto_decision_lab.scripts.phase73_journal_replay_aggregate_metrics_research_only import (
    aggregate_replay_metrics,
)
from crypto_decision_lab.scripts.phase74_journal_replay_distribution_diagnostics_research_only import (
    replay_distribution_diagnostics,
)
from crypto_decision_lab.scripts.phase75_journal_replay_quality_flags_research_only import (
    compute_quality_flags,
)

READY_GATE = "PHASE76_JOURNAL_REPLAY_EVIDENCE_SCORECARD_V2_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_evidence_scorecard(
    replay: dict[str, Any],
    metrics: dict[str, Any],
    diagnostics: dict[str, Any],
    quality: dict[str, Any],
) -> dict[str, Any]:
    high = int(quality.get("high_flag_count", 0))
    medium = int(quality.get("medium_flag_count", 0))
    active_n = int(metrics.get("active_paper_observation_count", 0))
    invalid_n = int(metrics.get("invalid_row_count", 0))

    blockers: list[str] = []
    if active_n < 30:
        blockers.append("active_sample_below_minimum_research_threshold")
    if invalid_n > 0:
        blockers.append("invalid_replay_rows_present")
    if high > 0:
        blockers.append("high_quality_flags_present")
    if medium > 0:
        blockers.append("medium_quality_flags_present")
    blockers.append("descriptive_replay_is_not_edge_validation")

    evidence_status = (
        "INSUFFICIENT_EVIDENCE_RESEARCH_ONLY"
        if blockers
        else "DESCRIPTIVE_EVIDENCE_READY_FOR_HUMAN_REVIEW_RESEARCH_ONLY"
    )

    return {
        "scorecard_descriptive_only": True,
        "evidence_status": evidence_status,
        "blockers_to_edge": blockers,
        "row_count": replay.get("row_count", 0),
        "valid_row_count": replay.get("valid_row_count", 0),
        "invalid_row_count": invalid_n,
        "active_paper_observation_count": active_n,
        "total_paper_pnl": metrics.get("total_paper_pnl", 0.0),
        "avg_paper_return_pct": metrics.get("avg_paper_return_pct", 0.0),
        "win_rate_descriptive_only": metrics.get("win_rate_descriptive_only", 0.0),
        "drawdown_like_paper_pnl_sequence": diagnostics.get("drawdown_like_paper_pnl_sequence", 0.0),
        "outlier_count": diagnostics.get("outlier_count", 0),
        "quality_status": quality.get("quality_status"),
        "quality_flag_count": quality.get("flag_count", 0),
        "high_quality_flag_count": high,
        "medium_quality_flag_count": medium,
        "info_quality_flag_count": quality.get("info_flag_count", 0),
        "by_asset": metrics.get("by_asset", []),
        "quality_flags": quality.get("flags", []),
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

def build_scorecard_from_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    replay = replay_batch_dry_run(entries)
    metrics = aggregate_replay_metrics(replay)
    diagnostics = replay_distribution_diagnostics(replay)
    quality = compute_quality_flags(metrics, diagnostics)
    return build_evidence_scorecard(replay, metrics, diagnostics, quality)

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase76(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase76_journal_replay_evidence_scorecard_v2_research_only"
    out.mkdir(parents=True, exist_ok=True)

    scorecard = build_scorecard_from_entries(SAMPLE_REPLAY_ENTRIES)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_evidence_scorecard": scorecard,
        **LOCKS,
    }

    (out / "phase76_journal_replay_evidence_scorecard_v2.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase76_sample_evidence_scorecard_only.json").write_text(
        json.dumps(scorecard, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    blocker_rows = "".join(f"<li>{b}</li>" for b in scorecard["blockers_to_edge"])
    asset_rows = "".join(
        "<tr>"
        f"<td>{row['asset']}</td>"
        f"<td>{row['row_count']}</td>"
        f"<td>{row['active_paper_observation_count']}</td>"
        f"<td>{row['total_paper_pnl']}</td>"
        f"<td>{row['avg_paper_return_pct']}</td>"
        "</tr>"
        for row in scorecard["by_asset"]
    )

    html = f"""
<html>
<body>
<h1>QRDS Phase 76 • Journal Replay Evidence Scorecard V2</h1>
<p>{READY_GATE}</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>Shadow decision allowed: False</p>
<p>Decision layer allowed: False</p>
<p>Promotion allowed: False</p>
<p>safe_apply_allowed: False</p>
<p>canonical_data_writes: 0</p>
<p>scorecard_descriptive_only: True</p>
<h2>Evidence Status</h2>
<p>{scorecard["evidence_status"]}</p>
<h2>Blockers to Edge</h2>
<ul>{blocker_rows}</ul>
<h2>Metrics</h2>
<p>active_paper_observation_count: {scorecard["active_paper_observation_count"]}</p>
<p>total_paper_pnl: {scorecard["total_paper_pnl"]}</p>
<p>avg_paper_return_pct: {scorecard["avg_paper_return_pct"]}</p>
<p>win_rate_descriptive_only: {scorecard["win_rate_descriptive_only"]}</p>
<p>quality_status: {scorecard["quality_status"]}</p>
<table border="1">
<tr><th>Asset</th><th>Rows</th><th>Active</th><th>Total PnL</th><th>Avg Return %</th></tr>
{asset_rows}
</table>
</body>
</html>
"""
    (out / "index.html").write_text(html, encoding="utf-8")

    project_out = project / "docs" / "reports" / "journal_replay"
    project_out.mkdir(parents=True, exist_ok=True)
    (project_out / "phase76_journal_replay_evidence_scorecard_v2.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (project_out / "phase76_journal_replay_evidence_scorecard_v2.html").write_text(
        html,
        encoding="utf-8",
    )

    return result

def main() -> int:
    result = build_phase76()
    print("QRDS Phase 76 • Journal Replay Evidence Scorecard V2 Research-Only")
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
