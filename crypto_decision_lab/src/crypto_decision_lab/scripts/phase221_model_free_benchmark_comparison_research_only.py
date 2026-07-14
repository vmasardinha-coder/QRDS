from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    group_by_symbol,
    mean,
    relative_change,
)
from crypto_decision_lab.scripts.phase216_225_robustness_common import (
    ROOT,
    locks_copy,
    phase_status,
    read_json,
    read_jsonl,
    research_caps,
    stable_digest,
    write_json,
    write_markdown,
)


def evaluate_benchmarks(
    rows: list[dict[str, Any]],
    windows: list[dict[str, Any]],
) -> dict[str, Any]:
    grouped = group_by_symbol(rows)
    benchmark_errors: dict[str, list[float]] = {
        "last_close": [],
        "train_mean_return": [],
        "lag_return_persistence": [],
    }

    for window in windows:
        symbol_rows = grouped[window["symbol"]]
        train_start = int(window["train_start_index"])
        train_end = int(window["train_end_index_exclusive"])
        test_start = int(window["test_start_index"])
        test_end = int(window["test_end_index_exclusive"])

        train_returns = [
            relative_change(
                float(symbol_rows[index - 1]["close"]),
                float(symbol_rows[index]["close"]),
            )
            for index in range(max(train_start + 1, 1), train_end)
        ]
        train_mean_return = mean(train_returns)

        for index in range(test_start, test_end):
            previous = float(symbol_rows[index - 1]["close"])
            previous_previous = float(symbol_rows[index - 2]["close"])
            actual = float(symbol_rows[index]["close"])
            lag_return = relative_change(previous_previous, previous)
            predictions = {
                "last_close": previous,
                "train_mean_return": previous * (1.0 + train_mean_return),
                "lag_return_persistence": previous * (1.0 + lag_return),
            }
            for name, prediction in predictions.items():
                benchmark_errors[name].append(
                    abs(prediction - actual) / max(abs(actual), 1e-12)
                )

    summary = {
        name: {
            "observations": len(errors),
            "mean_normalized_mae": mean(errors),
            "finite": all(math.isfinite(value) for value in errors),
        }
        for name, errors in benchmark_errors.items()
    }
    ranked = sorted(
        summary,
        key=lambda name: (summary[name]["mean_normalized_mae"], name),
    )
    return {
        "benchmarks": summary,
        "ranked_by_descriptive_mae": ranked,
        "comparison_digest": stable_digest(summary),
    }


def build_phase221(
    phase207_artifact: Path,
    phase209_artifact: Path,
    phase220_artifact: Path,
    dataset_path: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phase207 = read_json(phase207_artifact)
    phase209 = read_json(phase209_artifact)
    phase220 = read_json(phase220_artifact)
    rows = read_jsonl(dataset_path)
    comparison = evaluate_benchmarks(rows, phase207["windows"])
    passed = bool(
        phase209["historical_replay_passed"]
        and phase220["robustness_checkpoint_passed"]
        and len(comparison["benchmarks"]) == 3
        and all(
            item["observations"] > 0 and item["finite"]
            for item in comparison["benchmarks"].values()
        )
    )

    payload = {
        "phase": 221,
        "status": phase_status(
            passed,
            "MODEL_FREE_BENCHMARK_COMPARISON_READY_RESEARCH_ONLY",
        ),
        "benchmark_comparison_passed": passed,
        "comparison": comparison,
        "winner_claim_allowed": False,
        "caps": research_caps(),
        "interpretation": (
            "The ranking is descriptive and exists to prevent a single "
            "mechanical baseline from being evaluated in isolation. No "
            "benchmark superiority, model selection or edge claim is allowed."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)
    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 221 - Model-Free Benchmark Comparison",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Benchmarks:** `{len(comparison['benchmarks'])}`",
                f"**Comparison digest:** `{comparison['comparison_digest']}`",
                f"**Descriptive order:** `{', '.join(comparison['ranked_by_descriptive_mae'])}`",
                "",
                "The descriptive order is not a winner or edge claim.",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase207-artifact", type=Path, required=True)
    parser.add_argument("--phase209-artifact", type=Path, required=True)
    parser.add_argument("--phase220-artifact", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()
    payload = build_phase221(
        args.phase207_artifact,
        args.phase209_artifact,
        args.phase220_artifact,
        args.dataset,
        args.artifact,
        args.documentation,
    )
    print("PHASE221:", payload["status"])
    print("Benchmarks:", len(payload["comparison"]["benchmarks"]))
    return 0 if payload["benchmark_comparison_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
