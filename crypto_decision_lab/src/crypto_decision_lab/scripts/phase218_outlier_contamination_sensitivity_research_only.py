from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase216_225_robustness_common import (
    ROOT,
    locks_copy,
    mean,
    median,
    median_absolute_deviation,
    phase_status,
    read_json,
    read_jsonl,
    research_caps,
    row_return_series,
    winsorize,
    write_json,
    write_markdown,
)


def contamination_sensitivity(returns: list[float]) -> dict[str, Any]:
    baseline = list(returns)
    contaminated = list(returns)
    injected_indexes = list(range(10, len(contaminated), max(len(contaminated) // 8, 1)))[:8]
    for offset, index in enumerate(injected_indexes):
        contaminated[index] = 0.35 if offset % 2 == 0 else -0.35

    center = median(contaminated)
    mad = median_absolute_deviation(contaminated)
    scale = max(1.4826 * mad, 1e-12)
    detected_indexes = [
        index
        for index, value in enumerate(contaminated)
        if abs(value - center) / scale > 8.0
    ]

    baseline_robust = mean(abs(value) for value in winsorize(baseline))
    contaminated_robust = mean(abs(value) for value in winsorize(contaminated))
    drift = (
        abs(contaminated_robust - baseline_robust) / max(abs(baseline_robust), 1e-12)
    )
    detected_injected = sorted(set(detected_indexes) & set(injected_indexes))
    recall = len(detected_injected) / len(injected_indexes) if injected_indexes else 1.0

    return {
        "return_count": len(returns),
        "injected_contamination_count": len(injected_indexes),
        "detected_outlier_count": len(detected_indexes),
        "detected_injected_count": len(detected_injected),
        "detector_recall": recall,
        "baseline_winsorized_mean_absolute_return": baseline_robust,
        "contaminated_winsorized_mean_absolute_return": contaminated_robust,
        "robust_metric_relative_drift": drift,
        "detector_threshold_mad_units": 8.0,
    }


def build_phase218(
    phase217_artifact: Path,
    dataset_path: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phase217 = read_json(phase217_artifact)
    rows = read_jsonl(dataset_path)
    returns = row_return_series(rows)
    sensitivity = contamination_sensitivity(returns)
    passed = bool(
        phase217["multi_source_agreement_diagnostic_passed"]
        and sensitivity["return_count"] >= 100
        and sensitivity["detector_recall"] >= 0.875
        and sensitivity["robust_metric_relative_drift"] <= 0.25
    )

    payload = {
        "phase": 218,
        "status": phase_status(
            passed,
            "OUTLIER_CONTAMINATION_SENSITIVITY_PASS_RESEARCH_ONLY",
        ),
        "contamination_sensitivity_passed": passed,
        "sensitivity": sensitivity,
        "caps": research_caps(),
        "interpretation": (
            "Injected contamination is used only to test detector and robust "
            "metric behavior. It does not validate live data or predictive edge."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)
    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 218 - Outlier and Contamination Sensitivity",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Injected:** `{sensitivity['injected_contamination_count']}`",
                f"**Detector recall:** `{sensitivity['detector_recall']:.6f}`",
                f"**Robust metric drift:** `{sensitivity['robust_metric_relative_drift']:.6f}`",
                "",
                "This is deterministic sensitivity analysis, not a market "
                "quality approval or operational filter.",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase217-artifact", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()
    payload = build_phase218(
        args.phase217_artifact,
        args.dataset,
        args.artifact,
        args.documentation,
    )
    print("PHASE218:", payload["status"])
    print("Detector recall:", payload["sensitivity"]["detector_recall"])
    return 0 if payload["contamination_sensitivity_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
