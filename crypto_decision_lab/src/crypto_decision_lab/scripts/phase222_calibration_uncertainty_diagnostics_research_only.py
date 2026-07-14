from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    group_by_symbol,
    mean,
    population_std,
    relative_change,
)
from crypto_decision_lab.scripts.phase216_225_robustness_common import (
    ROOT,
    locks_copy,
    phase_status,
    read_json,
    read_jsonl,
    research_caps,
    write_json,
    write_markdown,
)


def uncertainty_diagnostics(
    rows: list[dict[str, Any]],
    windows: list[dict[str, Any]],
    z_value: float = 1.2815515655446004,
) -> dict[str, Any]:
    grouped = group_by_symbol(rows)
    covered: list[float] = []
    widths: list[float] = []
    standardized_errors: list[float] = []

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
        sigma = max(population_std(train_returns), 1e-8)

        for index in range(test_start, test_end):
            previous = float(symbol_rows[index - 1]["close"])
            previous_previous = float(symbol_rows[index - 2]["close"])
            actual = float(symbol_rows[index]["close"])
            lag_return = relative_change(previous_previous, previous)
            predicted = previous * (1.0 + lag_return)
            half_width = abs(previous) * z_value * sigma
            lower = predicted - half_width
            upper = predicted + half_width
            covered.append(1.0 if lower <= actual <= upper else 0.0)
            widths.append((upper - lower) / max(abs(actual), 1e-12))
            standardized_errors.append(
                abs(actual - predicted) / max(half_width, 1e-12)
            )

    empirical_coverage = mean(covered)
    nominal_coverage = 0.80
    calibration_gap = abs(empirical_coverage - nominal_coverage)
    return {
        "nominal_coverage": nominal_coverage,
        "empirical_coverage": empirical_coverage,
        "absolute_calibration_gap": calibration_gap,
        "mean_normalized_interval_width": mean(widths),
        "mean_standardized_absolute_error": mean(standardized_errors),
        "observation_count": len(covered),
        "finite": all(
            math.isfinite(value)
            for value in (
                empirical_coverage,
                calibration_gap,
                mean(widths),
                mean(standardized_errors),
            )
        ),
    }


def build_phase222(
    phase207_artifact: Path,
    phase221_artifact: Path,
    dataset_path: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phase207 = read_json(phase207_artifact)
    phase221 = read_json(phase221_artifact)
    rows = read_jsonl(dataset_path)
    diagnostic = uncertainty_diagnostics(rows, phase207["windows"])
    passed = bool(
        phase221["benchmark_comparison_passed"]
        and diagnostic["observation_count"] > 0
        and diagnostic["finite"]
        and 0.0 <= diagnostic["empirical_coverage"] <= 1.0
    )

    payload = {
        "phase": 222,
        "status": phase_status(
            passed,
            "CALIBRATION_UNCERTAINTY_DIAGNOSTICS_READY_RESEARCH_ONLY",
        ),
        "calibration_diagnostic_passed": passed,
        "diagnostic": diagnostic,
        "calibration_validated": False,
        "caps": research_caps(),
        "interpretation": (
            "Coverage and interval width are descriptive diagnostics for a "
            "mechanical baseline. Computing them does not establish calibrated "
            "probabilities, predictive validity or decision readiness."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)
    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 222 - Calibration and Uncertainty Diagnostics",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Nominal coverage:** `{diagnostic['nominal_coverage']:.4f}`",
                f"**Empirical coverage:** `{diagnostic['empirical_coverage']:.4f}`",
                f"**Calibration gap:** `{diagnostic['absolute_calibration_gap']:.4f}`",
                "",
                "Calibration remains explicitly unvalidated.",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase207-artifact", type=Path, required=True)
    parser.add_argument("--phase221-artifact", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()
    payload = build_phase222(
        args.phase207_artifact,
        args.phase221_artifact,
        args.dataset,
        args.artifact,
        args.documentation,
    )
    print("PHASE222:", payload["status"])
    print("Empirical coverage:", payload["diagnostic"]["empirical_coverage"])
    print("Calibration validated: False")
    return 0 if payload["calibration_diagnostic_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
