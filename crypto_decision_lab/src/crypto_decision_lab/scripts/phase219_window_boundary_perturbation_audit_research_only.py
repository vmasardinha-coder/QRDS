from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    group_by_symbol,
)
from crypto_decision_lab.scripts.phase209_historical_replay_runner_research_only import (
    evaluate_window,
)
from crypto_decision_lab.scripts.phase216_225_robustness_common import (
    ROOT,
    locks_copy,
    mean,
    phase_status,
    read_json,
    read_jsonl,
    research_caps,
    stable_digest,
    write_json,
    write_markdown,
)


def perturb_window(window: dict[str, Any], shift: int, row_count: int) -> dict[str, Any] | None:
    train_start = int(window["train_start_index"]) + shift
    train_end = int(window["train_end_index_exclusive"]) + shift
    test_start = int(window["test_start_index"]) + shift
    test_end = int(window["test_end_index_exclusive"]) + shift
    if train_start < 0 or test_end > row_count:
        return None
    if not (train_start < train_end == test_start < test_end):
        return None
    result = dict(window)
    result.update(
        {
            "train_start_index": train_start,
            "train_end_index_exclusive": train_end,
            "test_start_index": test_start,
            "test_end_index_exclusive": test_end,
            "boundary_shift": shift,
        }
    )
    return result


def boundary_sensitivity(
    rows: list[dict[str, Any]],
    windows: list[dict[str, Any]],
    shifts: tuple[int, ...] = (-2, -1, 1, 2),
) -> dict[str, Any]:
    grouped = group_by_symbol(rows)
    cases: list[dict[str, Any]] = []
    for shift in shifts:
        perturbed: list[dict[str, Any]] = []
        for window in windows:
            candidate = perturb_window(
                window,
                shift,
                len(grouped[window["symbol"]]),
            )
            if candidate is not None:
                perturbed.append(candidate)
        results = [evaluate_window(rows, window) for window in perturbed]
        cases.append(
            {
                "shift": shift,
                "valid_window_count": len(perturbed),
                "mean_normalized_mae": mean(
                    item["normalized_mae"] for item in results
                ),
                "mean_directional_agreement": mean(
                    item["directional_agreement"] for item in results
                ),
                "result_digest": stable_digest(results),
            }
        )
    mae_values = [case["mean_normalized_mae"] for case in cases]
    baseline_center = mean(mae_values)
    max_relative_deviation = max(
        (
            abs(value - baseline_center) / max(abs(baseline_center), 1e-12)
            for value in mae_values
        ),
        default=0.0,
    )
    return {
        "shifts": list(shifts),
        "cases": cases,
        "all_cases_nonempty": all(case["valid_window_count"] > 0 for case in cases),
        "maximum_relative_mae_deviation": max_relative_deviation,
    }


def build_phase219(
    phase207_artifact: Path,
    phase209_artifact: Path,
    phase218_artifact: Path,
    dataset_path: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phase207 = read_json(phase207_artifact)
    phase209 = read_json(phase209_artifact)
    phase218 = read_json(phase218_artifact)
    rows = read_jsonl(dataset_path)
    diagnostic = boundary_sensitivity(rows, phase207["windows"])
    passed = bool(
        phase209["historical_replay_passed"]
        and phase218["contamination_sensitivity_passed"]
        and diagnostic["all_cases_nonempty"]
        and diagnostic["maximum_relative_mae_deviation"] <= 0.35
    )

    payload = {
        "phase": 219,
        "status": phase_status(
            passed,
            "WINDOW_BOUNDARY_PERTURBATION_AUDIT_PASS_RESEARCH_ONLY",
        ),
        "window_boundary_perturbation_passed": passed,
        "diagnostic": diagnostic,
        "caps": research_caps(),
        "interpretation": (
            "Small deterministic boundary shifts test mechanical robustness. "
            "Stability under these shifts does not prove out-of-sample edge."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)
    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 219 - Window-Boundary Perturbation Audit",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Perturbations:** `{len(diagnostic['cases'])}`",
                f"**Maximum MAE deviation:** `{diagnostic['maximum_relative_mae_deviation']:.6f}`",
                "",
                "Boundary stability is a research robustness check only.",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase207-artifact", type=Path, required=True)
    parser.add_argument("--phase209-artifact", type=Path, required=True)
    parser.add_argument("--phase218-artifact", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()
    payload = build_phase219(
        args.phase207_artifact,
        args.phase209_artifact,
        args.phase218_artifact,
        args.dataset,
        args.artifact,
        args.documentation,
    )
    print("PHASE219:", payload["status"])
    print(
        "Maximum relative MAE deviation:",
        payload["diagnostic"]["maximum_relative_mae_deviation"],
    )
    return 0 if payload["window_boundary_perturbation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
