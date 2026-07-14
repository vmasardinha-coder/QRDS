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


def build_cross_evidence_consistency_gate(
    packet: dict[str, Any],
) -> dict[str, Any]:
    inventory = packet["inventory"]
    phases = [int(item["phase"]) for item in inventory]
    unique_hashes = len(
        {
            item.get("sha256")
            for item in inventory
            if item.get("sha256")
        }
    )
    all_passed = all(item.get("passed") is True for item in inventory)
    no_positive_canonical_writes = all(
        item.get("canonical_data_writes") in (None, 0)
        for item in inventory
    )
    phase224 = next(
        item for item in inventory if int(item["phase"]) == 224
    )
    phase225 = next(
        item for item in inventory if int(item["phase"]) == 225
    )
    robustness_score_valid = phase224.get("score") == 100
    integration_status_present = bool(phase225.get("status"))

    passed = bool(
        phases == list(range(216, 226))
        and unique_hashes == 10
        and all_passed
        and no_positive_canonical_writes
        and robustness_score_valid
        and integration_status_present
    )
    payload = base_payload(
        238,
        (
            "CROSS_EVIDENCE_CONSISTENCY_GATE_PASS_RESEARCH_ONLY"
            if passed
            else "CROSS_EVIDENCE_CONSISTENCY_GATE_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "source_phases": phases,
            "unique_artifact_hashes": unique_hashes,
            "all_historical_checks_passed": all_passed,
            "no_positive_canonical_writes": (
                no_positive_canonical_writes
            ),
            "phase224_score_100": robustness_score_valid,
            "phase225_status_present": integration_status_present,
            "consistency_passed": passed,
            "data_trust_validated": False,
            "passed": passed,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase237-artifact", required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--documentation", required=True)
    args = parser.parse_args()

    payload = build_cross_evidence_consistency_gate(
        load_json(args.phase237_artifact)
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 238 Cross-Evidence Consistency Gate",
        payload,
        [
            f"- Unique artifact hashes: "
            f"`{payload['unique_artifact_hashes']}`",
            f"- Historical checks passed: "
            f"`{payload['all_historical_checks_passed']}`",
            f"- No canonical writes: "
            f"`{payload['no_positive_canonical_writes']}`",
            "- Consistency is necessary but is not equivalent to "
            "predictive or economic validity.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
