from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    ROOT,
    group_by_symbol,
    locks_copy,
    mean,
    population_std,
    read_json,
    read_jsonl,
    relative_change,
    stable_digest,
    write_json,
    write_markdown,
)


def evaluate_window(
    rows: list[dict[str, Any]],
    window: dict[str, Any],
) -> dict[str, Any]:
    symbol_rows = group_by_symbol(rows)[window["symbol"]]
    test_start = int(window["test_start_index"])
    test_end = int(window["test_end_index_exclusive"])

    absolute_errors: list[float] = []
    squared_errors: list[float] = []
    normalized_errors: list[float] = []
    direction_matches: list[float] = []
    actual_returns: list[float] = []
    traces: list[dict[str, Any]] = []

    for index in range(test_start, test_end):
        previous = symbol_rows[index - 1]
        previous_previous = symbol_rows[index - 2]
        current = symbol_rows[index]

        previous_close = float(previous["close"])
        previous_previous_close = float(previous_previous["close"])
        actual_close = float(current["close"])

        lag_return = relative_change(
            previous_previous_close,
            previous_close,
        )
        predicted_close = previous_close * (1.0 + lag_return)
        actual_return = relative_change(previous_close, actual_close)
        predicted_delta = predicted_close - previous_close
        actual_delta = actual_close - previous_close
        error = predicted_close - actual_close

        absolute_errors.append(abs(error))
        squared_errors.append(error * error)
        normalized_errors.append(
            abs(error) / max(abs(actual_close), 1e-12)
        )
        direction_matches.append(
            1.0
            if (
                (predicted_delta > 0 and actual_delta > 0)
                or (predicted_delta < 0 and actual_delta < 0)
                or (predicted_delta == 0 and actual_delta == 0)
            )
            else 0.0
        )
        actual_returns.append(actual_return)

        if len(traces) < 20:
            traces.append(
                {
                    "symbol": window["symbol"],
                    "window_index": window["window_index"],
                    "feature_timestamp": previous["timestamp"],
                    "target_timestamp": current["timestamp"],
                    "predicted_delta": round(predicted_delta, 12),
                    "actual_delta": round(actual_delta, 12),
                    "actual_return": round(actual_return, 12),
                }
            )

    mae = mean(absolute_errors)
    rmse = math.sqrt(mean(squared_errors))
    normalized_mae = mean(normalized_errors)
    directional_agreement = mean(direction_matches)
    realized_volatility = population_std(actual_returns)

    return {
        "symbol": window["symbol"],
        "window_index": window["window_index"],
        "test_rows": len(absolute_errors),
        "mae": round(mae, 12),
        "rmse": round(rmse, 12),
        "normalized_mae": round(normalized_mae, 12),
        "directional_agreement": round(directional_agreement, 12),
        "realized_volatility": round(realized_volatility, 12),
        "trace_digest": stable_digest(traces),
        "traces": traces,
    }


def run_replay(
    rows: list[dict[str, Any]],
    windows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [evaluate_window(rows, window) for window in windows]


def build_phase209(
    phase207_artifact: Path,
    phase208_artifact: Path,
    dataset_path: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phase207 = read_json(phase207_artifact)
    phase208 = read_json(phase208_artifact)
    rows = read_jsonl(dataset_path)
    results = run_replay(rows, phase207["windows"])
    digest_first = stable_digest(results)
    digest_second = stable_digest(
        run_replay(rows, phase207["windows"])
    )
    deterministic = digest_first == digest_second

    payload = {
        "phase": 209,
        "status": (
            "CONTROLLED_HISTORICAL_REPLAY_READY_RESEARCH_ONLY"
            if (
                phase207["window_builder_passed"]
                and phase208["missing_data_policy_passed"]
                and results
                and deterministic
            )
            else "NEEDS_REVIEW"
        ),
        "historical_replay_passed": bool(
            phase207["window_builder_passed"]
            and phase208["missing_data_policy_passed"]
            and results
            and deterministic
        ),
        "baseline": {
            "name": "one_step_lag_return_persistence",
            "purpose": "mechanical_replay_validation_only",
            "is_trading_signal": False,
            "is_recommendation": False,
        },
        "window_count": len(results),
        "aggregate": {
            "mean_normalized_mae": round(
                mean(item["normalized_mae"] for item in results),
                12,
            ),
            "mean_directional_agreement": round(
                mean(item["directional_agreement"] for item in results),
                12,
            ),
            "mean_realized_volatility": round(
                mean(item["realized_volatility"] for item in results),
                12,
            ),
        },
        "results": results,
        "replay_digest": digest_first,
        "deterministic_replay": deterministic,
        "interpretation": (
            "Metrics validate deterministic replay mechanics only. "
            "They do not establish predictive validity, financial edge, "
            "trade direction or production readiness."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)

    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 209 - Controlled Historical Replay Runner",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Windows replayed:** `{payload['window_count']}`",
                f"**Deterministic:** `{payload['deterministic_replay']}`",
                f"**Replay digest:** `{payload['replay_digest']}`",
                f"**Mean normalized MAE:** `{payload['aggregate']['mean_normalized_mae']}`",
                "",
                "The baseline exists only to validate replay mechanics. "
                "Its output is not a trading signal or recommendation.",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase207-artifact", type=Path, required=True)
    parser.add_argument("--phase208-artifact", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()

    payload = build_phase209(
        args.phase207_artifact,
        args.phase208_artifact,
        args.dataset,
        args.artifact,
        args.documentation,
    )
    print("PHASE209:", payload["status"])
    print("Windows:", payload["window_count"])
    print("Deterministic:", payload["deterministic_replay"])
    return 0 if payload["historical_replay_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
