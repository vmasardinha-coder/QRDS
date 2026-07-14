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
    stable_digest,
    write_json,
    write_markdown,
)


def build_phase220(
    phase216_artifact: Path,
    phase217_artifact: Path,
    phase218_artifact: Path,
    phase219_artifact: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phases = [
        read_json(phase216_artifact),
        read_json(phase217_artifact),
        read_json(phase218_artifact),
        read_json(phase219_artifact),
    ]
    checks = {
        "216_provenance": phases[0]["provenance_completeness_passed"],
        "217_agreement_diagnostic": phases[1]["multi_source_agreement_diagnostic_passed"],
        "218_contamination_sensitivity": phases[2]["contamination_sensitivity_passed"],
        "219_boundary_perturbation": phases[3]["window_boundary_perturbation_passed"],
    }
    passed = all(checks.values())
    payload = {
        "phase": 220,
        "status": phase_status(
            passed,
            "ROBUSTNESS_BATCH_CHECKPOINT_PASS_RESEARCH_ONLY",
        ),
        "robustness_checkpoint_passed": passed,
        "checks": checks,
        "phase_chain_digest": stable_digest(
            {
                str(item["phase"]): {
                    "status": item["status"],
                    "locks": item["locks"],
                }
                for item in phases
            }
        ),
        "classification": (
            "ROBUSTNESS_DIAGNOSTICS_READY_RESEARCH_ONLY"
            if passed
            else "INSUFFICIENT_ROBUSTNESS_DIAGNOSTICS"
        ),
        "caps": research_caps(),
        "interpretation": (
            "The first robustness block is mechanically coherent. Independent "
            "source truth, prediction and edge remain outside this checkpoint."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)
    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 220 - Robustness Batch Checkpoint",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Classification:** `{payload['classification']}`",
                f"**Phase-chain digest:** `{payload['phase_chain_digest']}`",
                "",
                "This checkpoint preserves all research-only caps.",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    for phase in range(216, 220):
        parser.add_argument(f"--phase{phase}-artifact", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()
    payload = build_phase220(
        args.phase216_artifact,
        args.phase217_artifact,
        args.phase218_artifact,
        args.phase219_artifact,
        args.artifact,
        args.documentation,
    )
    print("PHASE220:", payload["status"])
    return 0 if payload["robustness_checkpoint_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
