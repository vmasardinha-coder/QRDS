from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase216_225_robustness_common import (
    ROOT,
    locks_copy,
    phase_status,
    read_json,
    research_caps,
    write_json,
    write_markdown,
)


def build_phase224(
    phase_artifacts: list[Path],
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phases = {
        str(phase): read_json(path)
        for phase, path in zip(range(216, 224), phase_artifacts)
    }
    checks = {
        "216_provenance": phases["216"]["provenance_completeness_passed"],
        "217_agreement_diagnostic": phases["217"][
            "multi_source_agreement_diagnostic_passed"
        ],
        "218_contamination": phases["218"]["contamination_sensitivity_passed"],
        "219_boundaries": phases["219"]["window_boundary_perturbation_passed"],
        "220_checkpoint": phases["220"]["robustness_checkpoint_passed"],
        "221_benchmarks": phases["221"]["benchmark_comparison_passed"],
        "222_uncertainty": phases["222"]["calibration_diagnostic_passed"],
        "223_costs": phases["223"]["cost_slippage_sensitivity_passed"],
    }
    weights = {
        "216_provenance": 13,
        "217_agreement_diagnostic": 12,
        "218_contamination": 13,
        "219_boundaries": 12,
        "220_checkpoint": 12,
        "221_benchmarks": 13,
        "222_uncertainty": 12,
        "223_costs": 13,
    }
    score = sum(weights[name] for name, passed in checks.items() if passed)
    ready = all(checks.values()) and score == 100

    payload = {
        "phase": 224,
        "status": phase_status(
            ready,
            "ROBUSTNESS_EVIDENCE_SCORECARD_V2_READY_RESEARCH_ONLY",
        ),
        "robustness_scorecard_passed": ready,
        "score": score,
        "maximum_score": 100,
        "components": {
            name: {
                "passed": checks[name],
                "weight": weights[name],
                "awarded": weights[name] if checks[name] else 0,
            }
            for name in checks
        },
        "classification": (
            "ROBUSTNESS_EVIDENCE_COMPLETE_NO_TRUST_OR_EDGE"
            if ready
            else "INSUFFICIENT_ROBUSTNESS_EVIDENCE"
        ),
        "caps": research_caps(),
        "interpretation": (
            "The score rates robustness-control completeness. It is capped "
            "below independent data trust, calibration validation, predictive "
            "validity, edge and decision permission."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)
    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 224 - Robustness Evidence Scorecard v2",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Score:** `{score}/100`",
                f"**Classification:** `{payload['classification']}`",
                "",
                "A complete control score is not data trust, predictive "
                "validity, financial edge or production readiness.",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    for phase in range(216, 224):
        parser.add_argument(f"--phase{phase}-artifact", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()
    phase_artifacts = [
        getattr(args, f"phase{phase}_artifact")
        for phase in range(216, 224)
    ]
    payload = build_phase224(
        phase_artifacts,
        args.artifact,
        args.documentation,
    )
    print("PHASE224:", payload["status"])
    print("Score:", payload["score"])
    print("Classification:", payload["classification"])
    return 0 if payload["robustness_scorecard_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
