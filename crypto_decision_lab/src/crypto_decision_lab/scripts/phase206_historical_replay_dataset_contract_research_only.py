from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    ROOT,
    load_or_create_dataset,
    locks_copy,
    stable_digest,
    write_json,
    write_jsonl,
    write_markdown,
)


def build_phase206(
    artifact_path: Path,
    dataset_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    rows, metadata = load_or_create_dataset(root)
    symbols = metadata["symbols"]

    contract = {
        "required_fields": [
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ],
        "timezone": "UTC",
        "ordering": "symbol_then_timestamp_ascending",
        "duplicate_policy": "last_normalized_record_wins",
        "minimum_rows": 240,
        "minimum_symbols": 1,
        "canonical_data_writes": 0,
    }

    contract_passed = (
        len(rows) >= contract["minimum_rows"]
        and len(symbols) >= contract["minimum_symbols"]
        and metadata["dataset_digest"] == stable_digest(rows)
    )

    write_jsonl(dataset_path, rows)

    payload = {
        "phase": 206,
        "status": (
            "HISTORICAL_REPLAY_DATASET_CONTRACT_READY_RESEARCH_ONLY"
            if contract_passed
            else "NEEDS_REVIEW"
        ),
        "contract_passed": contract_passed,
        "contract": contract,
        "dataset": {
            **metadata,
            "normalized_dataset_path": dataset_path.relative_to(root).as_posix(),
        },
        "interpretation": (
            "The dataset is normalized for controlled historical replay. "
            "This is not a data-trust approval, predictive validation, "
            "trading signal or operational decision."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)

    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 206 - Historical Replay Dataset Contract",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Source mode:** `{metadata['source_mode']}`",
                f"**Rows:** `{metadata['row_count']}`",
                f"**Symbols:** `{len(symbols)}`",
                f"**Dataset digest:** `{metadata['dataset_digest']}`",
                "",
                "The normalized dataset is available only for controlled, "
                "research-only replay. No trust approval or market edge is "
                "implied.",
                "",
                "```text",
                "operational_status: BLOCKED_RESEARCH_ONLY",
                "decision_layer_allowed: False",
                "canonical_data_writes: 0",
                "```",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()

    payload = build_phase206(
        args.artifact,
        args.dataset,
        args.documentation,
    )
    print("PHASE206:", payload["status"])
    print("Rows:", payload["dataset"]["row_count"])
    print("Source mode:", payload["dataset"]["source_mode"])
    return 0 if payload["contract_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
