from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase141_replay_validity_requirement_registry_research_only import (
    build_replay_validity_requirement_registry,
)

READY_GATE = "PHASE142_BACKTEST_WINDOW_INTEGRITY_CHECK_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def sample_backtest_window(now: datetime | None = None) -> dict[str, str]:
    base = now or datetime.now(timezone.utc)
    train_start = base - timedelta(days=120)
    train_end = base - timedelta(days=31)
    test_start = base - timedelta(days=30)
    test_end = base - timedelta(days=1)
    return {
        "train_start_utc": train_start.isoformat(),
        "train_end_utc": train_end.isoformat(),
        "test_start_utc": test_start.isoformat(),
        "test_end_utc": test_end.isoformat(),
    }

def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def evaluate_backtest_window(window: dict[str, str]) -> dict[str, Any]:
    train_start = _parse(window["train_start_utc"])
    train_end = _parse(window["train_end_utc"])
    test_start = _parse(window["test_start_utc"])
    test_end = _parse(window["test_end_utc"])

    chronological_order = train_start < train_end < test_start < test_end
    train_test_boundary_declared = all(
        key in window for key in ["train_start_utc", "train_end_utc", "test_start_utc", "test_end_utc"]
    )
    no_overlap = train_end < test_start
    train_duration_seconds = int((train_end - train_start).total_seconds())
    test_duration_seconds = int((test_end - test_start).total_seconds())

    return {
        "chronological_order": chronological_order,
        "train_test_boundary_declared": train_test_boundary_declared,
        "no_train_test_overlap": no_overlap,
        "train_duration_seconds": train_duration_seconds,
        "test_duration_seconds": test_duration_seconds,
        "positive_train_duration": train_duration_seconds > 0,
        "positive_test_duration": test_duration_seconds > 0,
        "window_integrity_pass": (
            chronological_order
            and train_test_boundary_declared
            and no_overlap
            and train_duration_seconds > 0
            and test_duration_seconds > 0
        ),
        "valid_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_backtest_window_integrity_check(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_replay_validity_requirement_registry(project_root)
    window = sample_backtest_window()
    evaluation = evaluate_backtest_window(window)

    check_pass = (
        registry["registry_pass"] is True
        and evaluation["window_integrity_pass"] is True
        and evaluation["valid_for_decision"] is False
        and evaluation["operational_effect"] == "NONE_RESEARCH_ONLY"
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "check_name": "backtest_window_integrity_check_research_only",
        "source_registry_gate": registry["gate"],
        "source_registry_pass": registry["registry_pass"],
        "window": window,
        "evaluation": evaluation,
        "check_pass": check_pass,
        "replay_validity_status": "BACKTEST_WINDOW_INTEGRITY_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase142(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase142_backtest_window_integrity_check_research_only"
    out.mkdir(parents=True, exist_ok=True)

    check = build_backtest_window_integrity_check()
    (out / "phase142_backtest_window_integrity_check.json").write_text(
        json.dumps(check, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": check["check_pass"], "check": check, **LOCKS}

def main() -> int:
    result = build_phase142()
    check = result["check"]
    evaluation = check["evaluation"]

    print(result["gate"])
    print("Window integrity pass:", check["check_pass"])
    print("Chronological order:", evaluation["chronological_order"])
    print("No train/test overlap:", evaluation["no_train_test_overlap"])
    print("Valid for decision:", evaluation["valid_for_decision"])
    print("Replay validity status:", check["replay_validity_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge validated: False")
    print("Edge operationally validated: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if check["check_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
