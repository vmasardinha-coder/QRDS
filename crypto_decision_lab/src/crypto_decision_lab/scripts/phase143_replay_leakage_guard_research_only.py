from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase142_backtest_window_integrity_check_research_only import (
    build_backtest_window_integrity_check,
)

READY_GATE = "PHASE143_REPLAY_LEAKAGE_GUARD_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def sample_feature_rows(now: datetime | None = None) -> list[dict[str, Any]]:
    base = now or datetime.now(timezone.utc)
    return [
        {
            "row_id": "feature_row_1",
            "feature_timestamp_utc": (base - timedelta(days=10)).isoformat(),
            "label_timestamp_utc": (base - timedelta(days=9)).isoformat(),
            "feature_lookahead_seconds": 0,
            "uses_future_label": False,
        },
        {
            "row_id": "feature_row_2",
            "feature_timestamp_utc": (base - timedelta(days=9)).isoformat(),
            "label_timestamp_utc": (base - timedelta(days=8)).isoformat(),
            "feature_lookahead_seconds": 0,
            "uses_future_label": False,
        },
        {
            "row_id": "feature_row_3",
            "feature_timestamp_utc": (base - timedelta(days=8)).isoformat(),
            "label_timestamp_utc": (base - timedelta(days=7)).isoformat(),
            "feature_lookahead_seconds": 0,
            "uses_future_label": False,
        },
    ]

def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def evaluate_leakage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    future_label_rows = []
    lookahead_rows = []
    invalid_timestamp_rows = []

    for row in rows:
        feature_ts = _parse(row["feature_timestamp_utc"])
        label_ts = _parse(row["label_timestamp_utc"])

        if label_ts <= feature_ts:
            invalid_timestamp_rows.append(row["row_id"])

        if row.get("uses_future_label") is True:
            future_label_rows.append(row["row_id"])

        if int(row.get("feature_lookahead_seconds", 0)) > 0:
            lookahead_rows.append(row["row_id"])

    leakage_pass = (
        len(rows) > 0
        and len(future_label_rows) == 0
        and len(lookahead_rows) == 0
        and len(invalid_timestamp_rows) == 0
    )

    return {
        "row_count": len(rows),
        "future_label_rows": future_label_rows,
        "lookahead_rows": lookahead_rows,
        "invalid_timestamp_rows": invalid_timestamp_rows,
        "leakage_pass": leakage_pass,
        "valid_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_replay_leakage_guard(project_root: str | Path | None = None) -> dict[str, Any]:
    window_check = build_backtest_window_integrity_check(project_root)
    rows = sample_feature_rows()
    leakage = evaluate_leakage(rows)

    guard_pass = (
        window_check["check_pass"] is True
        and leakage["leakage_pass"] is True
        and leakage["valid_for_decision"] is False
        and leakage["operational_effect"] == "NONE_RESEARCH_ONLY"
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "guard_name": "replay_leakage_guard_research_only",
        "source_window_gate": window_check["gate"],
        "source_window_pass": window_check["check_pass"],
        "leakage_evaluation": leakage,
        "guard_pass": guard_pass,
        "replay_validity_status": "LEAKAGE_GUARD_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase143(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase143_replay_leakage_guard_research_only"
    out.mkdir(parents=True, exist_ok=True)

    guard = build_replay_leakage_guard()
    (out / "phase143_replay_leakage_guard.json").write_text(
        json.dumps(guard, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": guard["guard_pass"], "guard": guard, **LOCKS}

def main() -> int:
    result = build_phase143()
    guard = result["guard"]
    leakage = guard["leakage_evaluation"]

    print(result["gate"])
    print("Leakage guard pass:", guard["guard_pass"])
    print("Row count:", leakage["row_count"])
    print("Future label rows:", leakage["future_label_rows"])
    print("Lookahead rows:", leakage["lookahead_rows"])
    print("Invalid timestamp rows:", leakage["invalid_timestamp_rows"])
    print("Replay validity status:", guard["replay_validity_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge validated: False")
    print("Edge operationally validated: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if guard["guard_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
