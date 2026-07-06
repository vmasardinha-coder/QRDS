from __future__ import annotations

import json
import statistics
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

READY_GATE = "PHASE74_JOURNAL_REPLAY_DISTRIBUTION_DIAGNOSTICS_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def _max_drawdown_like(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
    return round(max_dd, 6)

def replay_distribution_diagnostics(replay: dict[str, Any]) -> dict[str, Any]:
    rows = replay.get("rows", [])
    valid_rows = [row for row in rows if row.get("valid_for_replay_dry_run") is True]
    active_rows = [
        row for row in valid_rows
        if row.get("would_have_action") in {"paper_long", "paper_short"}
    ]

    pnls = [float(row.get("paper_pnl", 0.0)) for row in active_rows]
    returns = [float(row.get("paper_return_pct", 0.0)) for row in active_rows]

    by_asset_pnl: dict[str, float] = {}
    total_abs_pnl = sum(abs(v) for v in pnls)
    for row in active_rows:
        asset = str(row.get("asset") or "UNKNOWN")
        by_asset_pnl[asset] = round(by_asset_pnl.get(asset, 0.0) + float(row.get("paper_pnl", 0.0)), 6)

    concentration = []
    for asset, pnl in sorted(by_asset_pnl.items()):
        share = abs(pnl) / total_abs_pnl if total_abs_pnl else 0.0
        concentration.append({"asset": asset, "paper_pnl": round(pnl, 6), "abs_pnl_share": round(share, 6)})

    outliers = []
    if returns:
        mean_ret = statistics.mean(returns)
        stdev_ret = statistics.pstdev(returns)
        for row in active_rows:
            ret = float(row.get("paper_return_pct", 0.0))
            z = 0.0 if stdev_ret == 0 else (ret - mean_ret) / stdev_ret
            if abs(z) >= 2.0:
                outliers.append({
                    "journal_id": row.get("journal_id"),
                    "asset": row.get("asset"),
                    "paper_return_pct": round(ret, 6),
                    "z_score": round(z, 6),
                })

    diagnostics = {
        "distribution_diagnostics_descriptive_only": True,
        "row_count": len(rows),
        "active_paper_observation_count": len(active_rows),
        "mean_paper_return_pct": round(statistics.mean(returns), 6) if returns else 0.0,
        "median_paper_return_pct": round(statistics.median(returns), 6) if returns else 0.0,
        "min_paper_return_pct": round(min(returns), 6) if returns else 0.0,
        "max_paper_return_pct": round(max(returns), 6) if returns else 0.0,
        "mean_paper_pnl": round(statistics.mean(pnls), 6) if pnls else 0.0,
        "median_paper_pnl": round(statistics.median(pnls), 6) if pnls else 0.0,
        "min_paper_pnl": round(min(pnls), 6) if pnls else 0.0,
        "max_paper_pnl": round(max(pnls), 6) if pnls else 0.0,
        "positive_count": len([p for p in pnls if p > 0]),
        "negative_count": len([p for p in pnls if p < 0]),
        "flat_count": len([p for p in pnls if p == 0]),
        "drawdown_like_paper_pnl_sequence": _max_drawdown_like(pnls),
        "asset_abs_pnl_concentration": concentration,
        "outlier_rows_descriptive_only": outliers,
        "outlier_count": len(outliers),
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "trading_signal_generated": False,
        "recommendation_generated": False,
        "allocation_generated": False,
        "safe_apply_allowed": False,
        "promotion_allowed": False,
        "canonical_data_writes": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }
    return diagnostics

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase74(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase74_journal_replay_distribution_diagnostics_research_only"
    out.mkdir(parents=True, exist_ok=True)

    replay = replay_batch_dry_run(SAMPLE_REPLAY_ENTRIES)
    metrics = aggregate_replay_metrics(replay)
    diagnostics = replay_distribution_diagnostics(replay)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_replay_metrics": metrics,
        "sample_distribution_diagnostics": diagnostics,
        **LOCKS,
    }

    (out / "phase74_journal_replay_distribution_diagnostics.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase74_sample_distribution_diagnostics_only.json").write_text(
        json.dumps(diagnostics, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    concentration_rows = "".join(
        "<tr>"
        f"<td>{row['asset']}</td>"
        f"<td>{row['paper_pnl']}</td>"
        f"<td>{row['abs_pnl_share']}</td>"
        "</tr>"
        for row in diagnostics["asset_abs_pnl_concentration"]
    )

    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 74 • Journal Replay Distribution Diagnostics</h1>
<p>{READY_GATE}</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>Shadow decision allowed: False</p>
<p>Decision layer allowed: False</p>
<p>Promotion allowed: False</p>
<p>safe_apply_allowed: False</p>
<p>canonical_data_writes: 0</p>
<p>distribution_diagnostics_descriptive_only: True</p>
<p>mean_paper_return_pct: {diagnostics["mean_paper_return_pct"]}</p>
<p>median_paper_return_pct: {diagnostics["median_paper_return_pct"]}</p>
<p>drawdown_like_paper_pnl_sequence: {diagnostics["drawdown_like_paper_pnl_sequence"]}</p>
<p>outlier_count: {diagnostics["outlier_count"]}</p>
<table border="1">
<tr><th>Asset</th><th>Paper PnL</th><th>Abs PnL Share</th></tr>
{concentration_rows}
</table>
</body>
</html>
""",
        encoding="utf-8",
    )

    project_out = project / "docs" / "reports" / "journal_replay"
    project_out.mkdir(parents=True, exist_ok=True)
    (project_out / "phase74_journal_replay_distribution_diagnostics.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (project_out / "phase74_journal_replay_distribution_diagnostics.html").write_text(
        (out / "index.html").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    return result

def main() -> int:
    result = build_phase74()
    print("QRDS Phase 74 • Journal Replay Distribution Diagnostics Research-Only")
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
