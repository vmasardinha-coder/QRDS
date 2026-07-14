from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    ROOT,
    group_by_symbol,
    locks_copy,
    read_json,
    read_jsonl,
    stable_digest,
    write_json,
    write_markdown,
)


def build_windows(
    rows: list[dict[str, Any]],
    train_size: int = 96,
    test_size: int = 24,
    step_size: int = 24,
    max_windows_per_symbol: int = 12,
) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    grouped = group_by_symbol(rows)

    for symbol, symbol_rows in grouped.items():
        local_windows: list[dict[str, Any]] = []
        start = 0
        while start + train_size + test_size <= len(symbol_rows):
            train_start = start
            train_end = start + train_size
            test_start = train_end
            test_end = test_start + test_size
            local_windows.append(
                {
                    "symbol": symbol,
                    "window_index": len(local_windows),
                    "train_start_index": train_start,
                    "train_end_index_exclusive": train_end,
                    "test_start_index": test_start,
                    "test_end_index_exclusive": test_end,
                    "train_start_timestamp": symbol_rows[train_start]["timestamp"],
                    "train_end_timestamp": symbol_rows[train_end - 1]["timestamp"],
                    "test_start_timestamp": symbol_rows[test_start]["timestamp"],
                    "test_end_timestamp": symbol_rows[test_end - 1]["timestamp"],
                    "train_rows": train_size,
                    "test_rows": test_size,
                }
            )
            start += step_size

        if len(local_windows) > max_windows_per_symbol:
            local_windows = local_windows[-max_windows_per_symbol:]

        windows.extend(local_windows)

    return windows


def build_phase207(
    phase206_artifact: Path,
    dataset_path: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phase206 = read_json(phase206_artifact)
    rows = read_jsonl(dataset_path)
    windows = build_windows(rows)

    payload = {
        "phase": 207,
        "status": (
            "REPLAY_WINDOW_BUILDER_READY_RESEARCH_ONLY"
            if phase206["contract_passed"] and windows
            else "NEEDS_REVIEW"
        ),
        "window_builder_passed": bool(
            phase206["contract_passed"] and windows
        ),
        "configuration": {
            "train_size": 96,
            "test_size": 24,
            "step_size": 24,
            "max_windows_per_symbol": 12,
            "walk_forward": True,
            "overlap_policy": "test_windows_may_touch_but_never_use_future_rows",
        },
        "window_count": len(windows),
        "symbols": sorted({window["symbol"] for window in windows}),
        "windows": windows,
        "window_manifest_digest": stable_digest(windows),
        "interpretation": (
            "Windows establish deterministic walk-forward boundaries only. "
            "They do not authorize predictions, signals or decisions."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)

    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 207 - Replay Window Builder",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Windows:** `{payload['window_count']}`",
                f"**Symbols:** `{len(payload['symbols'])}`",
                f"**Manifest digest:** `{payload['window_manifest_digest']}`",
                "",
                "All windows are deterministic and walk-forward ordered. "
                "No future row is included in a training segment.",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase206-artifact", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()

    payload = build_phase207(
        args.phase206_artifact,
        args.dataset,
        args.artifact,
        args.documentation,
    )
    print("PHASE207:", payload["status"])
    print("Windows:", payload["window_count"])
    return 0 if payload["window_builder_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
