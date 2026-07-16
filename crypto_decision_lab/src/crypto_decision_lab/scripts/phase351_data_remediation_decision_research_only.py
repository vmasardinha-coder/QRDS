from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase346_355_closure_navigation_common import (
    FAMILY_ID,
    ROOT,
    base_payload,
    fingerprint,
    phase_summary,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def build(phase349_path: Path, phase350_path: Path, output_dir: Path) -> dict[str, Any]:
    p349 = read_json(phase349_path)
    p350 = read_json(phase350_path)
    validate_phase(p349, 349)
    validate_phase(p350, 350)
    if p350.get("closure_sealed") is not True:
        raise RuntimeError("Family closure is not sealed.")

    backlog = [
        {
            "item_id": "FUNDING_OI_COVERAGE_DIAGNOSTIC",
            "allowed": True,
            "reopens_closed_family": False,
            "network_collection_authorized": False,
        },
        {
            "item_id": "PROVIDER_TIMESTAMP_ALIGNMENT_DIAGNOSTIC",
            "allowed": True,
            "reopens_closed_family": False,
            "network_collection_authorized": False,
        },
        {
            "item_id": "PRIVATE_EXECUTION_DATA",
            "allowed": False,
            "reopens_closed_family": False,
            "network_collection_authorized": False,
        },
    ]
    payload = base_payload(351, "DATA_REMEDIATION_DECISION_RECORDED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE351_DATA_REMEDIATION_DECISION_READY_RESEARCH_ONLY",
            "family_id": FAMILY_ID,
            "data_remediation_backlog": backlog,
            "data_remediation_backlog_count": len(backlog),
            "data_remediation_reopens_family": False,
            "data_remediation_authorizes_new_hypotheses": False,
            "public_network_collection_started": False,
            "decision": "DATA_REMEDIATION_DIAGNOSTICS_ALLOWED_WITHOUT_FAMILY_REOPEN_RESEARCH_ONLY",
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase351_data_remediation_decision.json", payload)
    write_summary(
        phase_summary(351, "data_remediation_decision"),
        title="Phase 351 — Data-remediation Decision",
        gate=payload["gate"],
        bullets=[
            f"Backlog items: `{payload['data_remediation_backlog_count']}`",
            "Data remediation reopens family: `False`",
            "Data remediation authorizes new hypotheses: `False`",
            "Public network collection started: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase349-artifact", type=Path, default=ROOT / "artifacts/phase349_abstention_data_limitation_audit_research_only/phase349_abstention_data_limitation_audit.json")
    parser.add_argument("--phase350-artifact", type=Path, default=ROOT / "artifacts/phase350_abstention_closure_integrity_seal_research_only/phase350_abstention_closure_integrity_seal.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/phase351_data_remediation_decision_research_only")
    args = parser.parse_args()
    payload = build(args.phase349_artifact, args.phase350_artifact, args.output_dir)
    print(payload["gate"])
    print("Decision:", payload["decision"])
    print("Family reopened:", payload["data_remediation_reopens_family"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
