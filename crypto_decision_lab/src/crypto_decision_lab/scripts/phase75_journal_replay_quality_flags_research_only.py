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

READY_GATE = "PHASE75_JOURNAL_REPLAY_QUALITY_FLAGS_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def compute_quality_flags(
    metrics: dict[str, Any],
    diagnostics: dict[str, Any],
    min_active_observations: int = 30,
    concentration_threshold: float = 0.60,
) -> dict[str, Any]:
    flags: list[dict[str, Any]] = []

    active_n = int(metrics.get("active_paper_observation_count", 0))
    invalid_n = int(metrics.get("invalid_row_count", 0))
    outlier_n = int(diagnostics.get("outlier_count", 0))
    drawdown_like = float(diagnostics.get("drawdown_like_paper_pnl_sequence", 0.0))

    if active_n < min_active_observations:
        flags.append({
            "flag": "sample_too_small",
            "severity": "HIGH",
            "detail": f"active observations {active_n} below required descriptive threshold {min_active_observations}",
        })

    if invalid_n > 0:
        flags.append({
            "flag": "invalid_rows_present",
            "severity": "HIGH",
            "detail": f"invalid replay rows present: {invalid_n}",
        })

    concentration = diagnostics.get("asset_abs_pnl_concentration", [])
    concentrated_assets = [
        row for row in concentration
        if float(row.get("abs_pnl_share", 0.0)) >= concentration_threshold
    ]
    if concentrated_assets:
        flags.append({
            "flag": "asset_concentration_high",
            "severity": "MEDIUM",
            "detail": "one or more assets dominate absolute paper PnL",
            "assets": concentrated_assets,
        })

    if outlier_n > 0:
        flags.append({
            "flag": "outlier_rows_present",
            "severity": "MEDIUM",
            "detail": f"outlier rows present: {outlier_n}",
        })

    if drawdown_like < 0:
        flags.append({
            "flag": "negative_drawdown_like_sequence",
            "severity": "MEDIUM",
            "detail": f"drawdown-like paper PnL sequence is negative: {drawdown_like}",
        })

    flags.append({
        "flag": "metrics_not_edge_evidence",
        "severity": "INFO",
        "detail": "descriptive replay metrics are not edge validation and cannot unlock decision layers",
    })

    high_count = len([f for f in flags if f["severity"] == "HIGH"])
    medium_count = len([f for f in flags if f["severity"] == "MEDIUM"])
    info_count = len([f for f in flags if f["severity"] == "INFO"])

    return {
        "quality_flags_descriptive_only": True,
        "flag_count": len(flags),
        "high_flag_count": high_count,
        "medium_flag_count": medium_count,
        "info_flag_count": info_count,
        "flags": flags,
        "quality_status": "NEEDS_MORE_EVIDENCE_RESEARCH_ONLY" if high_count or medium_count else "DESCRIPTIVE_OK_RESEARCH_ONLY",
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

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase75(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase75_journal_replay_quality_flags_research_only"
    out.mkdir(parents=True, exist_ok=True)

    replay = replay_batch_dry_run(SAMPLE_REPLAY_ENTRIES)
    metrics = aggregate_replay_metrics(replay)
    diagnostics = replay_distribution_diagnostics(replay)
    quality = compute_quality_flags(metrics, diagnostics)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_quality_flags": quality,
        **LOCKS,
    }

    (out / "phase75_journal_replay_quality_flags.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase75_sample_quality_flags_only.json").write_text(
        json.dumps(quality, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    flag_rows = "".join(
        "<tr>"
        f"<td>{row['flag']}</td>"
        f"<td>{row['severity']}</td>"
        f"<td>{row['detail']}</td>"
        "</tr>"
        for row in quality["flags"]
    )

    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 75 • Journal Replay Quality Flags</h1>
<p>{READY_GATE}</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>Shadow decision allowed: False</p>
<p>Decision layer allowed: False</p>
<p>Promotion allowed: False</p>
<p>safe_apply_allowed: False</p>
<p>canonical_data_writes: 0</p>
<p>quality_flags_descriptive_only: True</p>
<p>quality_status: {quality["quality_status"]}</p>
<p>flag_count: {quality["flag_count"]}</p>
<table border="1">
<tr><th>Flag</th><th>Severity</th><th>Detail</th></tr>
{flag_rows}
</table>
</body>
</html>
""",
        encoding="utf-8",
    )

    project_out = project / "docs" / "reports" / "journal_replay"
    project_out.mkdir(parents=True, exist_ok=True)
    (project_out / "phase75_journal_replay_quality_flags.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (project_out / "phase75_journal_replay_quality_flags.html").write_text(
        (out / "index.html").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    return result

def main() -> int:
    result = build_phase75()
    print("QRDS Phase 75 • Journal Replay Quality Flags Research-Only")
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
