from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase236_245_evidence_decision_readiness_common import (
    add_standard_output_arguments,
    base_payload,
    historical_evidence_inventory,
    project_root,
    write_json,
    write_markdown,
)


def build_historical_evidence_packet(
    root: Path | None = None,
    *,
    inventory: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    resolved = project_root(root)
    rows = (
        inventory
        if inventory is not None
        else historical_evidence_inventory(resolved)
    )
    phases = [int(item["phase"]) for item in rows]
    all_exist = all(item.get("exists") is True for item in rows)
    all_passed = all(item.get("passed") is True for item in rows)
    phase_sequence_valid = phases == list(range(216, 226))
    hashes_present = all(
        isinstance(item.get("sha256"), str)
        and len(item["sha256"]) == 64
        for item in rows
    )
    passed = bool(
        len(rows) == 10
        and all_exist
        and all_passed
        and phase_sequence_valid
        and hashes_present
    )

    payload = base_payload(
        237,
        (
            "HISTORICAL_EVIDENCE_PACKET_PASS_RESEARCH_ONLY"
            if passed
            else "HISTORICAL_EVIDENCE_PACKET_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "source_phases": phases,
            "inventory": rows,
            "artifact_count": len(rows),
            "all_artifacts_exist": all_exist,
            "all_artifacts_passed": all_passed,
            "phase_sequence_valid": phase_sequence_valid,
            "hashes_present": hashes_present,
            "historical_packet_complete": passed,
            "data_trust_validated": False,
            "passed": passed,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    add_standard_output_arguments(parser)
    args = parser.parse_args()
    payload = build_historical_evidence_packet(
        Path(args.project_root) if args.project_root else None
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 237 Historical Evidence Packet Builder",
        payload,
        [
            f"- Historical artifacts: `{payload['artifact_count']}`",
            f"- Sequence valid: `{payload['phase_sequence_valid']}`",
            f"- Hashes present: `{payload['hashes_present']}`",
            "- This packet preserves evidence history but does not "
            "upgrade historical robustness into data trust.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
