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


def build_evidence_limitations_registry(
    root: Path | None = None,
) -> dict[str, Any]:
    _ = root
    limitations = [
        {
            "id": "LIVE_SOURCE_IDENTITY_NOT_ADMITTED",
            "blocking": True,
        },
        {
            "id": "OBSERVATION_FRESHNESS_NOT_ADMITTED",
            "blocking": True,
        },
        {
            "id": "INDEPENDENT_SOURCE_REPLICATION_NOT_ADMITTED",
            "blocking": True,
        },
        {
            "id": "OUT_OF_SAMPLE_PREDICTIVE_VALIDITY_NOT_ESTABLISHED",
            "blocking": True,
        },
        {
            "id": "NET_ECONOMIC_EDGE_NOT_ESTABLISHED",
            "blocking": True,
        },
        {
            "id": "REAL_CAPITAL_EXECUTION_NOT_AUTHORIZED",
            "blocking": True,
        },
    ]
    passed = bool(
        len(limitations) == 6
        and all(item["blocking"] is True for item in limitations)
    )
    payload = base_payload(
        239,
        (
            "EVIDENCE_LIMITATIONS_REGISTRY_PASS_RESEARCH_ONLY"
            if passed
            else "EVIDENCE_LIMITATIONS_REGISTRY_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "limitations": limitations,
            "blocking_limitation_count": len(limitations),
            "limitations_explicit": True,
            "evidence_admitted": False,
            "passed": passed,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    add_standard_output_arguments(parser)
    args = parser.parse_args()
    payload = build_evidence_limitations_registry(
        Path(args.project_root) if args.project_root else None
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 239 Evidence Limitations Registry",
        payload,
        [
            f"- Blocking limitations: "
            f"`{payload['blocking_limitation_count']}`",
            "- The system explicitly distinguishes framework completion "
            "from admitted live evidence.",
            "- These limitations keep the decision layer closed.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
