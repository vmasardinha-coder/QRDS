from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    ROOT,
    group_by_symbol,
    locks_copy,
    median_interval_seconds,
    parse_timestamp,
    read_json,
    read_jsonl,
    write_json,
    write_markdown,
)


def audit_missing_data(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    grouped = group_by_symbol(rows)
    duplicate_records = 0
    large_gaps = 0
    expected_intervals: dict[str, float | None] = {}

    for symbol, symbol_rows in grouped.items():
        keys = [(row["symbol"], row["timestamp"]) for row in symbol_rows]
        duplicate_records += len(keys) - len(set(keys))
        expected = median_interval_seconds(symbol_rows)
        expected_intervals[symbol] = expected

        if expected is None:
            continue

        timestamps = [
            parse_timestamp(row["timestamp"])
            for row in symbol_rows
        ]
        valid = [value for value in timestamps if value is not None]
        for previous, current in zip(valid, valid[1:]):
            if (current - previous).total_seconds() > expected * 1.5:
                large_gaps += 1

    return {
        "row_count": len(rows),
        "symbol_count": len(grouped),
        "duplicate_records": duplicate_records,
        "large_gaps": large_gaps,
        "expected_interval_seconds_by_symbol": expected_intervals,
        "policy": {
            "future_fill_allowed": False,
            "backfill_allowed": False,
            "cross_window_fill_allowed": False,
            "invalid_ohlc_action": "drop_before_contract",
            "duplicate_action": "deduplicate_before_contract",
            "gap_action": "retain_and_flag",
        },
    }


def build_phase208(
    phase206_artifact: Path,
    phase207_artifact: Path,
    dataset_path: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phase206 = read_json(phase206_artifact)
    phase207 = read_json(phase207_artifact)
    rows = read_jsonl(dataset_path)
    audit = audit_missing_data(rows)

    policy_passed = bool(
        phase206["contract_passed"]
        and phase207["window_builder_passed"]
        and audit["duplicate_records"] == 0
        and audit["row_count"] >= 240
    )

    payload = {
        "phase": 208,
        "status": (
            "MISSING_DATA_POLICY_APPLIED_RESEARCH_ONLY"
            if policy_passed
            else "NEEDS_REVIEW"
        ),
        "missing_data_policy_passed": policy_passed,
        "audit": audit,
        "usable_row_count": audit["row_count"],
        "interpretation": (
            "Missingness and gaps are handled without future fill, "
            "backfill or cross-window imputation. Gaps remain descriptive "
            "flags and do not create market recommendations."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)

    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 208 - Missing Data Policy",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Rows retained:** `{payload['usable_row_count']}`",
                f"**Duplicate records:** `{audit['duplicate_records']}`",
                f"**Large gaps flagged:** `{audit['large_gaps']}`",
                "",
                "No future fill, backfill or cross-window interpolation is "
                "permitted.",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase206-artifact", type=Path, required=True)
    parser.add_argument("--phase207-artifact", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()

    payload = build_phase208(
        args.phase206_artifact,
        args.phase207_artifact,
        args.dataset,
        args.artifact,
        args.documentation,
    )
    print("PHASE208:", payload["status"])
    print("Large gaps:", payload["audit"]["large_gaps"])
    return 0 if payload["missing_data_policy_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
