"""Walk-forward splitter for QRDS research datasets.

Offline/research-only. No API key, no account, no orders, no real capital.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.safety.gates import build_safe_context

WALK_FORWARD_SPLIT_SCHEMA_VERSION = "qrds.walk_forward_split.v1"
WALK_FORWARD_REPORT_SCHEMA_VERSION = "qrds.walk_forward_report.v1"


class WalkForwardSplitError(ValueError):
    """Raised when walk-forward splits cannot be created safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assert_safe_context() -> dict[str, Any]:
    safe = build_safe_context()
    for flag in (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        if safe.get(flag) is True:
            raise WalkForwardSplitError(f"Unsafe context flag {flag}=True.")
    return safe


def load_research_dataset_jsonl(path: str | Path) -> list[dict[str, Any]]:
    dataset_path = Path(path)
    if not dataset_path.exists() or not dataset_path.is_file():
        raise WalkForwardSplitError(f"Dataset JSONL not found: {dataset_path}")

    rows: list[dict[str, Any]] = []
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise WalkForwardSplitError(f"Invalid JSONL at line {line_number}.") from exc
            if not isinstance(row, dict):
                raise WalkForwardSplitError(f"Dataset row at line {line_number} is not an object.")
            rows.append(row)

    if not rows:
        raise WalkForwardSplitError("Dataset JSONL has no rows.")
    return rows


def assert_research_dataset_rows(rows: list[dict[str, Any]]) -> None:
    if not isinstance(rows, list) or not rows:
        raise WalkForwardSplitError("Research dataset rows must be a non-empty list.")

    prev_ts: Any = None
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise WalkForwardSplitError(f"Dataset row {i} must be a dictionary.")
        if "ts" not in row:
            raise WalkForwardSplitError(f"Dataset row {i} is missing ts.")
        if row.get("operational_decision_allowed") is True:
            raise WalkForwardSplitError(f"Dataset row {i} allows operational decisions.")
        for flag in ("api_key_required", "orders_generated", "real_capital_used"):
            if row.get(flag) is True:
                raise WalkForwardSplitError(f"Dataset row {i} has unsafe flag {flag}=True.")
        ts = row.get("ts")
        if prev_ts is not None and ts <= prev_ts:
            raise WalkForwardSplitError("Dataset timestamps must be strictly increasing.")
        prev_ts = ts


def build_walk_forward_splits(
    rows: list[dict[str, Any]],
    *,
    train_size: int,
    test_size: int,
    step_size: int,
    gap_size: int = 0,
) -> list[dict[str, Any]]:
    _assert_safe_context()
    assert_research_dataset_rows(rows)

    if train_size <= 0:
        raise WalkForwardSplitError("train_size must be positive.")
    if test_size <= 0:
        raise WalkForwardSplitError("test_size must be positive.")
    if step_size <= 0:
        raise WalkForwardSplitError("step_size must be positive.")
    if gap_size < 0:
        raise WalkForwardSplitError("gap_size cannot be negative.")

    n_rows = len(rows)
    if n_rows < train_size + gap_size + test_size:
        raise WalkForwardSplitError("Not enough rows for one walk-forward split.")

    splits: list[dict[str, Any]] = []
    split_index = 0
    train_start = 0

    while True:
        train_end = train_start + train_size
        test_start = train_end + gap_size
        test_end = test_start + test_size
        if test_end > n_rows:
            break

        train_rows = rows[train_start:train_end]
        test_rows = rows[test_start:test_end]

        splits.append({
            "schema": WALK_FORWARD_SPLIT_SCHEMA_VERSION,
            "split_index": split_index,
            "train_start_index": train_start,
            "train_end_index_exclusive": train_end,
            "gap_start_index": train_end,
            "gap_end_index_exclusive": test_start,
            "test_start_index": test_start,
            "test_end_index_exclusive": test_end,
            "train_row_count": len(train_rows),
            "gap_row_count": gap_size,
            "test_row_count": len(test_rows),
            "train_start_ts": train_rows[0]["ts"],
            "train_end_ts": train_rows[-1]["ts"],
            "test_start_ts": test_rows[0]["ts"],
            "test_end_ts": test_rows[-1]["ts"],
            "research_allowed": True,
            "operational_decision_allowed": False,
            "app_mode": "INTERACTIVE_RESEARCH_ONLY",
            "api_key_required": False,
            "api_key_present": False,
            "account_connection_required": False,
            "orders_generated": False,
            "real_capital_used": False,
        })

        split_index += 1
        train_start += step_size

    if not splits:
        raise WalkForwardSplitError("No walk-forward splits were generated.")
    return splits


def materialize_walk_forward_split(
    rows: list[dict[str, Any]],
    split: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    assert_research_dataset_rows(rows)

    if split.get("schema") != WALK_FORWARD_SPLIT_SCHEMA_VERSION:
        raise WalkForwardSplitError("Invalid walk-forward split schema.")
    if split.get("operational_decision_allowed") is True:
        raise WalkForwardSplitError("Walk-forward split allows operational decisions.")

    return {
        "train": rows[int(split["train_start_index"]):int(split["train_end_index_exclusive"])],
        "test": rows[int(split["test_start_index"]):int(split["test_end_index_exclusive"])],
    }


def validate_walk_forward_splits(
    splits: list[dict[str, Any]],
    *,
    dataset_row_count: int,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not splits:
        return [{
            "code": "EMPTY_WALK_FORWARD_SPLITS",
            "severity": "error",
            "index": None,
            "message": "No walk-forward splits were provided.",
        }]

    prev_test_start: int | None = None
    for i, split in enumerate(splits):
        if split.get("schema") != WALK_FORWARD_SPLIT_SCHEMA_VERSION:
            issues.append({
                "code": "INVALID_WALK_FORWARD_SPLIT_SCHEMA",
                "severity": "error",
                "index": i,
                "message": "Invalid walk-forward split schema.",
            })
        if split.get("operational_decision_allowed") is True:
            issues.append({
                "code": "OPERATIONAL_WALK_FORWARD_SPLIT",
                "severity": "error",
                "index": i,
                "message": "Walk-forward split cannot allow operational decisions.",
            })

        train_start = int(split.get("train_start_index", -1))
        train_end = int(split.get("train_end_index_exclusive", -1))
        test_start = int(split.get("test_start_index", -1))
        test_end = int(split.get("test_end_index_exclusive", -1))

        if not (0 <= train_start < train_end <= test_start < test_end <= dataset_row_count):
            issues.append({
                "code": "INVALID_WALK_FORWARD_BOUNDS",
                "severity": "error",
                "index": i,
                "message": "Invalid walk-forward split bounds.",
            })

        if prev_test_start is not None and test_start <= prev_test_start:
            issues.append({
                "code": "NON_MONOTONIC_WALK_FORWARD_TEST_START",
                "severity": "error",
                "index": i,
                "message": "Walk-forward test windows must advance over time.",
            })
        prev_test_start = test_start

    return issues


def build_walk_forward_report(
    rows: list[dict[str, Any]],
    splits: list[dict[str, Any]],
    *,
    split_name: str = "walk-forward",
) -> dict[str, Any]:
    safe = _assert_safe_context()
    assert_research_dataset_rows(rows)

    issues = validate_walk_forward_splits(splits, dataset_row_count=len(rows))
    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")

    report = {
        "schema": WALK_FORWARD_REPORT_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "split_name": split_name,
        "dataset_row_count": len(rows),
        "split_count": len(splits),
        "walk_forward_quality_passed": error_count == 0,
        "issue_summary": {
            "total_issues": len(issues),
            "error_count": error_count,
            "warning_count": warning_count,
        },
        "issues": issues,
        "splits": splits,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
    }

    for flag in (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        assert report[flag] == safe[flag]

    return report
