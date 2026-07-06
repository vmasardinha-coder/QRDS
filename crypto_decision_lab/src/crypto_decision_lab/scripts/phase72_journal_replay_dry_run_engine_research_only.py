from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE72_JOURNAL_REPLAY_DRY_RUN_ENGINE_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

ALLOWED_PAPER_ACTIONS = {"watch", "paper_long", "paper_short", "paper_no_action"}

SAMPLE_REPLAY_ENTRIES = [
    {
        "journal_id": "dryrun-001",
        "asset": "BTC",
        "would_have_action": "paper_long",
        "paper_size_notional": 1000.0,
        "entry_reference_price": 100000.0,
        "exit_reference_price": 101500.0,
        "fees_slippage_bps": 10.0,
        "research_only_ack": True,
    },
    {
        "journal_id": "dryrun-002",
        "asset": "ETH",
        "would_have_action": "paper_short",
        "paper_size_notional": 1000.0,
        "entry_reference_price": 3000.0,
        "exit_reference_price": 3030.0,
        "fees_slippage_bps": 10.0,
        "research_only_ack": True,
    },
    {
        "journal_id": "dryrun-003",
        "asset": "SOL",
        "would_have_action": "paper_no_action",
        "paper_size_notional": 0.0,
        "entry_reference_price": 150.0,
        "exit_reference_price": 152.0,
        "fees_slippage_bps": 0.0,
        "research_only_ack": True,
    },
]

def validate_replay_entry(entry: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    if entry.get("research_only_ack") is not True:
        errors.append("research_only_ack_must_be_true")

    if entry.get("would_have_action") not in ALLOWED_PAPER_ACTIONS:
        errors.append("action_must_be_paper_only")

    for field in ["entry_reference_price", "exit_reference_price", "paper_size_notional"]:
        value = entry.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{field}_must_be_number")

    if isinstance(entry.get("entry_reference_price"), (int, float)) and entry["entry_reference_price"] <= 0:
        errors.append("entry_reference_price_must_be_positive")

    if isinstance(entry.get("exit_reference_price"), (int, float)) and entry["exit_reference_price"] <= 0:
        errors.append("exit_reference_price_must_be_positive")

    if isinstance(entry.get("paper_size_notional"), (int, float)) and entry["paper_size_notional"] < 0:
        errors.append("paper_size_notional_must_be_non_negative")

    return {
        "valid_for_replay_dry_run": len(errors) == 0,
        "errors": errors,
        "replay_execution_allowed": False,
        "canonical_data_writes": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def replay_entry_dry_run(entry: dict[str, Any]) -> dict[str, Any]:
    validation = validate_replay_entry(entry)
    if not validation["valid_for_replay_dry_run"]:
        return {
            "journal_id": entry.get("journal_id"),
            "valid_for_replay_dry_run": False,
            "errors": validation["errors"],
            "paper_return_pct": 0.0,
            "paper_pnl": 0.0,
            "replay_execution_allowed": False,
            "canonical_data_writes": 0,
        }

    action = entry["would_have_action"]
    entry_px = float(entry["entry_reference_price"])
    exit_px = float(entry["exit_reference_price"])
    notional = float(entry["paper_size_notional"])
    fees_slippage_bps = float(entry.get("fees_slippage_bps", 0.0))

    raw_return = 0.0
    if action == "paper_long":
        raw_return = (exit_px / entry_px) - 1.0
    elif action == "paper_short":
        raw_return = (entry_px / exit_px) - 1.0
    elif action in {"watch", "paper_no_action"}:
        raw_return = 0.0

    cost = fees_slippage_bps / 10000.0
    net_return = raw_return - cost if action in {"paper_long", "paper_short"} else 0.0
    paper_pnl = notional * net_return

    return {
        "journal_id": entry.get("journal_id"),
        "asset": entry.get("asset"),
        "would_have_action": action,
        "valid_for_replay_dry_run": True,
        "paper_return_pct": round(net_return * 100.0, 6),
        "paper_pnl": round(paper_pnl, 6),
        "fees_slippage_bps": fees_slippage_bps,
        "replay_execution_allowed": False,
        "trading_signal_generated": False,
        "recommendation_generated": False,
        "allocation_generated": False,
        "canonical_data_writes": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def replay_batch_dry_run(entries: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [replay_entry_dry_run(entry) for entry in entries]
    valid_rows = [row for row in rows if row["valid_for_replay_dry_run"]]
    invalid_rows = [row for row in rows if not row["valid_for_replay_dry_run"]]
    total_pnl = sum(float(row["paper_pnl"]) for row in valid_rows)
    active_rows = [row for row in valid_rows if row["would_have_action"] in {"paper_long", "paper_short"}]

    return {
        "dry_run_only": True,
        "row_count": len(entries),
        "valid_row_count": len(valid_rows),
        "invalid_row_count": len(invalid_rows),
        "active_paper_observation_count": len(active_rows),
        "total_paper_pnl": round(total_pnl, 6),
        "rows": rows,
        "replay_execution_allowed": False,
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

def build_phase72(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase72_journal_replay_dry_run_engine_research_only"
    out.mkdir(parents=True, exist_ok=True)

    replay = replay_batch_dry_run(SAMPLE_REPLAY_ENTRIES)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_replay": replay,
        **LOCKS,
    }

    (out / "phase72_journal_replay_dry_run_engine.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase72_sample_replay_entries.json").write_text(
        json.dumps(SAMPLE_REPLAY_ENTRIES, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 72 • Journal Replay Dry-Run Engine</h1>
<p>{READY_GATE}</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>Shadow decision allowed: False</p>
<p>Decision layer allowed: False</p>
<p>Promotion allowed: False</p>
<p>safe_apply_allowed: False</p>
<p>canonical_data_writes: 0</p>
<p>dry_run_only: True</p>
</body>
</html>
""",
        encoding="utf-8",
    )

    project_out = project / "docs" / "reports" / "journal_replay"
    project_out.mkdir(parents=True, exist_ok=True)
    (project_out / "phase72_journal_replay_dry_run_engine.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (project_out / "phase72_journal_replay_dry_run_engine.html").write_text(
        (out / "index.html").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    return result

def main() -> int:
    result = build_phase72()
    print("QRDS Phase 72 • Journal Replay Dry-Run Engine Research-Only")
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
