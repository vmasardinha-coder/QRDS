from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase72_journal_replay_dry_run_engine_research_only import (
    SAMPLE_REPLAY_ENTRIES,
    replay_batch_dry_run,
)

READY_GATE = "PHASE73_JOURNAL_REPLAY_AGGREGATE_METRICS_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def aggregate_replay_metrics(replay: dict[str, Any]) -> dict[str, Any]:
    rows = replay.get("rows", [])
    valid_rows = [row for row in rows if row.get("valid_for_replay_dry_run") is True]
    invalid_rows = [row for row in rows if row.get("valid_for_replay_dry_run") is not True]
    active_rows = [
        row for row in valid_rows
        if row.get("would_have_action") in {"paper_long", "paper_short"}
    ]

    total_pnl = round(sum(float(row.get("paper_pnl", 0.0)) for row in valid_rows), 6)
    returns = [float(row.get("paper_return_pct", 0.0)) for row in active_rows]
    avg_return = round(sum(returns) / len(returns), 6) if returns else 0.0

    wins = [row for row in active_rows if float(row.get("paper_pnl", 0.0)) > 0]
    losses = [row for row in active_rows if float(row.get("paper_pnl", 0.0)) < 0]
    flats = [row for row in active_rows if float(row.get("paper_pnl", 0.0)) == 0]
    win_rate = round(len(wins) / len(active_rows), 6) if active_rows else 0.0

    by_asset: dict[str, dict[str, Any]] = {}
    for row in valid_rows:
        asset = str(row.get("asset") or "UNKNOWN")
        if asset not in by_asset:
            by_asset[asset] = {
                "asset": asset,
                "row_count": 0,
                "active_paper_observation_count": 0,
                "total_paper_pnl": 0.0,
                "avg_paper_return_pct": 0.0,
                "wins": 0,
                "losses": 0,
                "flats": 0,
            }
        item = by_asset[asset]
        item["row_count"] += 1
        action = row.get("would_have_action")
        pnl = float(row.get("paper_pnl", 0.0))
        ret = float(row.get("paper_return_pct", 0.0))
        if action in {"paper_long", "paper_short"}:
            item["active_paper_observation_count"] += 1
            item["total_paper_pnl"] = round(float(item["total_paper_pnl"]) + pnl, 6)
            if pnl > 0:
                item["wins"] += 1
            elif pnl < 0:
                item["losses"] += 1
            else:
                item["flats"] += 1
            previous_n = item["active_paper_observation_count"] - 1
            item["avg_paper_return_pct"] = round(
                ((float(item["avg_paper_return_pct"]) * previous_n) + ret)
                / item["active_paper_observation_count"],
                6,
            )

    return {
        "metrics_descriptive_only": True,
        "row_count": len(rows),
        "valid_row_count": len(valid_rows),
        "invalid_row_count": len(invalid_rows),
        "active_paper_observation_count": len(active_rows),
        "total_paper_pnl": total_pnl,
        "avg_paper_return_pct": avg_return,
        "wins": len(wins),
        "losses": len(losses),
        "flats": len(flats),
        "win_rate_descriptive_only": win_rate,
        "by_asset": sorted(by_asset.values(), key=lambda x: x["asset"]),
        "invalid_rows": invalid_rows,
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

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase73(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase73_journal_replay_aggregate_metrics_research_only"
    out.mkdir(parents=True, exist_ok=True)

    replay = replay_batch_dry_run(SAMPLE_REPLAY_ENTRIES)
    metrics = aggregate_replay_metrics(replay)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_replay_metrics": metrics,
        **LOCKS,
    }

    (out / "phase73_journal_replay_aggregate_metrics.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase73_sample_replay_metrics_only.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    html_rows = "".join(
        "<tr>"
        f"<td>{row['asset']}</td>"
        f"<td>{row['row_count']}</td>"
        f"<td>{row['active_paper_observation_count']}</td>"
        f"<td>{row['total_paper_pnl']}</td>"
        f"<td>{row['avg_paper_return_pct']}</td>"
        f"<td>{row['wins']}</td>"
        f"<td>{row['losses']}</td>"
        "</tr>"
        for row in metrics["by_asset"]
    )
    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 73 • Journal Replay Aggregate Metrics</h1>
<p>{READY_GATE}</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>Shadow decision allowed: False</p>
<p>Decision layer allowed: False</p>
<p>Promotion allowed: False</p>
<p>safe_apply_allowed: False</p>
<p>canonical_data_writes: 0</p>
<p>metrics_descriptive_only: True</p>
<p>total_paper_pnl: {metrics["total_paper_pnl"]}</p>
<p>win_rate_descriptive_only: {metrics["win_rate_descriptive_only"]}</p>
<table border="1">
<tr><th>Asset</th><th>Rows</th><th>Active</th><th>Total PnL</th><th>Avg Return %</th><th>Wins</th><th>Losses</th></tr>
{html_rows}
</table>
</body>
</html>
""",
        encoding="utf-8",
    )

    project_out = project / "docs" / "reports" / "journal_replay"
    project_out.mkdir(parents=True, exist_ok=True)
    (project_out / "phase73_journal_replay_aggregate_metrics.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (project_out / "phase73_journal_replay_aggregate_metrics.html").write_text(
        (out / "index.html").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    return result

def main() -> int:
    result = build_phase73()
    print("QRDS Phase 73 • Journal Replay Aggregate Metrics Research-Only")
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
