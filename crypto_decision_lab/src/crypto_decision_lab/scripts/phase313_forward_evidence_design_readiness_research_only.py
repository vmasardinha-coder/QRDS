from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase306_315_stability_common import (
    ROOT,
    base_payload,
    fingerprint,
    read_json,
    validate_phase,
    write_json,
    write_phase_summary,
)


FORWARD_CONTRACT = {
    "clock_starts_only_after_immutable_freeze": True,
    "explicit_manual_scientific_review_required": True,
    "historical_backfill_allowed": False,
    "minimum_calendar_days": 90,
    "minimum_independent_events": 50,
    "minimum_provider_health_percent": 99.0,
    "model_mutation_after_clock_start_allowed": False,
    "cost_model_mutation_after_clock_start_allowed": False,
    "timestamp_policy_mutation_after_clock_start_allowed": False,
    "private_api_required": False,
    "account_connection_required": False,
    "orders_allowed": False,
    "capital_allowed": False,
}


def build(phase311_path: Path, phase312_path: Path, output_dir: Path) -> dict[str, Any]:
    phase311 = read_json(phase311_path)
    phase312 = read_json(phase312_path)
    validate_phase(phase311, 311)
    validate_phase(phase312, 312)

    contract_complete = all(value is not None for value in FORWARD_CONTRACT.values())
    activation_ready = (
        bool(phase311.get("candidate_eligible"))
        and bool(phase312.get("freeze_readiness"))
        and bool(phase312.get("freeze_created"))
        and contract_complete
    )
    payload = base_payload(313, "FORWARD_EVIDENCE_DESIGN_READINESS_EVALUATED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE313_FORWARD_EVIDENCE_DESIGN_READINESS_READY_RESEARCH_ONLY",
            "phase311_artifact": phase311_path.relative_to(ROOT).as_posix(),
            "phase311_fingerprint": phase311.get("artifact_fingerprint"),
            "phase312_artifact": phase312_path.relative_to(ROOT).as_posix(),
            "phase312_fingerprint": phase312.get("artifact_fingerprint"),
            "forward_evidence_contract": FORWARD_CONTRACT,
            "contract_complete": contract_complete,
            "candidate_eligible": phase311.get("candidate_eligible"),
            "freeze_created": phase312.get("freeze_created"),
            "activation_ready": activation_ready,
            "evidence_clock_status": "INACTIVE_NO_IMMUTABLE_FREEZE",
            "evidence_clock_started": False,
            "forward_evidence_credit": 0,
            "historical_backfill_to_forward_clock": False,
            "forward_shadow_eligible": False,
            "forward_shadow_started": False,
            "paper_trading_started": False,
            "strategy_approved": False,
        }
    )
    payload["forward_contract_fingerprint"] = fingerprint(FORWARD_CONTRACT)
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase313_forward_evidence_design_readiness.json", payload)
    write_phase_summary(
        ROOT / "docs/reports/stability_v2/phase313_forward_evidence_design_readiness_summary.md",
        title="Phase 313 — Forward Evidence Design Readiness",
        gate=payload["gate"],
        bullets=[
            f"Forward contract complete: `{contract_complete}`",
            f"Candidate eligible: `{payload['candidate_eligible']}`",
            f"Immutable freeze created: `{payload['freeze_created']}`",
            f"Activation ready: `{activation_ready}`",
            "Minimum calendar duration after freeze: `90 days`",
            "Minimum independent events after freeze: `50`",
            "Historical backfill allowed: `False`",
            "Forward evidence credit: `0`",
            "Evidence clock started: `False`",
            "Forward shadow started: `False`",
        ],
    )
    return payload


def parse_args() -> argparse.Namespace:
    artifacts = ROOT / "artifacts"
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase311-artifact", type=Path, default=artifacts / "phase311_candidate_eligibility_contract_v2_research_only/phase311_candidate_eligibility_contract_v2.json")
    parser.add_argument("--phase312-artifact", type=Path, default=artifacts / "phase312_candidate_lineage_freeze_readiness_research_only/phase312_candidate_lineage_freeze_readiness.json")
    parser.add_argument("--output-dir", type=Path, default=artifacts / "phase313_forward_evidence_design_readiness_research_only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build(args.phase311_artifact, args.phase312_artifact, args.output_dir)
    print(payload["gate"])
    print("Contract complete:", payload["contract_complete"])
    print("Activation ready:", payload["activation_ready"])
    print("Evidence clock status:", payload["evidence_clock_status"])
    print("Forward evidence credit:", payload["forward_evidence_credit"])
    print("Forward shadow started:", payload["forward_shadow_started"])
    print("Operational:", payload["locks"]["operational_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
