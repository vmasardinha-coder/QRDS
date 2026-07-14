from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase236_245_evidence_decision_readiness_common import (
    base_payload,
    load_json,
    write_json,
    write_markdown,
)


def build_evidence_admission_checkpoint(
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    phases = [int(item["phase"]) for item in artifacts]
    all_framework_checks_passed = all(
        item.get("passed") is True for item in artifacts
    )
    limitations = artifacts[-1]
    blocking_limitations_present = (
        limitations.get("blocking_limitation_count", 0) > 0
    )
    evidence_admitted = False
    passed = bool(
        phases == [236, 237, 238, 239]
        and all_framework_checks_passed
        and blocking_limitations_present
        and evidence_admitted is False
    )
    classification = (
        "EVIDENCE_ADMISSION_FRAMEWORK_READY_DATA_NOT_ADMITTED"
        if passed
        else "EVIDENCE_ADMISSION_FRAMEWORK_NEEDS_REVIEW"
    )
    payload = base_payload(
        240,
        (
            "EVIDENCE_ADMISSION_CHECKPOINT_PASS_RESEARCH_ONLY"
            if passed
            else "EVIDENCE_ADMISSION_CHECKPOINT_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "source_phases": phases,
            "framework_checks_passed": all_framework_checks_passed,
            "blocking_limitations_present": (
                blocking_limitations_present
            ),
            "evidence_admitted": evidence_admitted,
            "classification": classification,
            "data_trust_validated": False,
            "passed": passed,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase-artifact",
        action="append",
        required=True,
    )
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--documentation", required=True)
    args = parser.parse_args()

    payload = build_evidence_admission_checkpoint(
        [load_json(path) for path in args.phase_artifact]
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 240 Evidence Admission Checkpoint",
        payload,
        [
            f"- Framework checks passed: "
            f"`{payload['framework_checks_passed']}`",
            f"- Evidence admitted: `{payload['evidence_admitted']}`",
            f"- Classification: `{payload['classification']}`",
            "- The admission framework is ready; current historical "
            "evidence is not promoted to trusted live data.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
