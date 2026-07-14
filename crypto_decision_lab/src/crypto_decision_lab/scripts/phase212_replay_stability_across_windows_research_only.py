from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    ROOT,
    locks_copy,
    mean,
    population_std,
    read_json,
    write_json,
    write_markdown,
)


def build_phase212(
    phase209_artifact: Path,
    phase211_artifact: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phase209 = read_json(phase209_artifact)
    phase211 = read_json(phase211_artifact)
    values = [
        float(item["normalized_mae"])
        for item in phase209["results"]
    ]
    avg = mean(values)
    std = population_std(values)
    coefficient_of_variation = std / avg if avg > 0 else 0.0

    if coefficient_of_variation <= 0.25:
        variation_band = "LOW_VARIATION"
    elif coefficient_of_variation <= 0.75:
        variation_band = "MODERATE_VARIATION"
    else:
        variation_band = "HIGH_VARIATION"

    coverage_passed = bool(
        phase209["historical_replay_passed"]
        and phase211["counterfactual_audit_passed"]
        and len(values) >= 2
    )

    payload = {
        "phase": 212,
        "status": (
            "REPLAY_STABILITY_ACROSS_WINDOWS_READY_RESEARCH_ONLY"
            if coverage_passed
            else "NEEDS_REVIEW"
        ),
        "stability_audit_passed": coverage_passed,
        "window_count": len(values),
        "mean_normalized_mae": round(avg, 12),
        "std_normalized_mae": round(std, 12),
        "coefficient_of_variation": round(
            coefficient_of_variation,
            12,
        ),
        "variation_band": variation_band,
        "interpretation": (
            "Variation describes replay behavior across windows. "
            "Even low variation does not establish predictive validity, "
            "financial edge or decision readiness."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)

    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 212 - Replay Stability Across Windows",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Windows:** `{payload['window_count']}`",
                f"**Variation band:** `{payload['variation_band']}`",
                f"**Coefficient of variation:** `{payload['coefficient_of_variation']}`",
                "",
                "The variation band is descriptive and cannot authorize "
                "a decision layer.",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase209-artifact", type=Path, required=True)
    parser.add_argument("--phase211-artifact", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()

    payload = build_phase212(
        args.phase209_artifact,
        args.phase211_artifact,
        args.artifact,
        args.documentation,
    )
    print("PHASE212:", payload["status"])
    print("Variation:", payload["variation_band"])
    return 0 if payload["stability_audit_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
