from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase236_245_evidence_decision_readiness_common import (
    add_standard_output_arguments,
    base_payload,
    criteria_registry,
    write_json,
    write_markdown,
)


def build_evidence_admission_contract_registry(
    root: Path | None = None,
) -> dict[str, Any]:
    _ = root
    criteria = criteria_registry()
    identifiers = [item["id"] for item in criteria]
    passed = bool(
        len(criteria) == 10
        and len(set(identifiers)) == 10
        and all(item["required"] is True for item in criteria)
    )
    payload = base_payload(
        236,
        (
            "EVIDENCE_ADMISSION_CONTRACT_REGISTRY_PASS_RESEARCH_ONLY"
            if passed
            else "EVIDENCE_ADMISSION_CONTRACT_REGISTRY_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "criteria": criteria,
            "criterion_count": len(criteria),
            "all_criteria_mandatory": True,
            "evidence_admitted": False,
            "passed": passed,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    add_standard_output_arguments(parser)
    args = parser.parse_args()
    payload = build_evidence_admission_contract_registry(
        Path(args.project_root) if args.project_root else None
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 236 Evidence Admission Contract Registry",
        payload,
        [
            f"- Mandatory criteria: `{payload['criterion_count']}`",
            "- This phase defines admission requirements; it does not "
            "claim that current data satisfies them.",
            "- Evidence admitted: `False`.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
