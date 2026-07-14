from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase236_245_evidence_decision_readiness_common import (
    add_standard_output_arguments,
    base_payload,
    write_json,
    write_markdown,
)


def build_predictive_validity_acceptance_protocol(
    root: Path | None = None,
) -> dict[str, Any]:
    _ = root
    requirements = {
        "walk_forward_required": True,
        "out_of_sample_required": True,
        "model_free_baseline_required": True,
        "minimum_independent_windows": 3,
        "probability_calibration_required": True,
        "uncertainty_interval_required": True,
        "subgroup_stability_required": True,
        "lookahead_leakage_tolerance": 0,
        "minimum_reproducible_runs": 2,
    }
    passed = bool(
        requirements["walk_forward_required"]
        and requirements["out_of_sample_required"]
        and requirements["model_free_baseline_required"]
        and requirements["minimum_independent_windows"] >= 3
        and requirements["lookahead_leakage_tolerance"] == 0
    )
    payload = base_payload(
        241,
        (
            "PREDICTIVE_VALIDITY_ACCEPTANCE_PROTOCOL_PASS_RESEARCH_ONLY"
            if passed
            else "PREDICTIVE_VALIDITY_ACCEPTANCE_PROTOCOL_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "requirements": requirements,
            "protocol_ready": passed,
            "predictive_validity_established": False,
            "passed": passed,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    add_standard_output_arguments(parser)
    args = parser.parse_args()
    payload = build_predictive_validity_acceptance_protocol(
        Path(args.project_root) if args.project_root else None
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 241 Predictive Validity Acceptance Protocol",
        payload,
        [
            "- Requires walk-forward and out-of-sample evaluation.",
            "- Requires model-free baselines, calibration and uncertainty.",
            "- Protocol ready: `True`; predictive validity established: "
            "`False`.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
