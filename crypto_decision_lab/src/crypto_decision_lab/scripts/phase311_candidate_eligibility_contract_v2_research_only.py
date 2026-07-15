from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase306_315_stability_common import (
    ROOT,
    base_payload,
    fingerprint,
    gate_record,
    read_json,
    validate_phase,
    write_json,
    write_phase_summary,
)


def build(
    phase304_path: Path,
    phase306_path: Path,
    phase307_path: Path,
    phase308_path: Path,
    phase309_path: Path,
    phase310_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    phase304 = read_json(phase304_path)
    phase306 = read_json(phase306_path)
    phase307 = read_json(phase307_path)
    phase308 = read_json(phase308_path)
    phase309 = read_json(phase309_path)
    phase310 = read_json(phase310_path)
    for number, payload in (
        (304, phase304),
        (306, phase306),
        (307, phase307),
        (308, phase308),
        (309, phase309),
        (310, phase310),
    ):
        validate_phase(payload, number)

    gates = [
        gate_record(
            "G01_PHASE304_ROBUSTNESS",
            "Nested walk-forward robustness passed",
            bool(phase304.get("robustness_pass")),
            phase304.get("robustness_pass"),
            "PHASE304_ROBUSTNESS_FAILED",
        ),
        gate_record(
            "G02_SELECTION_STABLE",
            "Phase 304 selection stable",
            bool(phase304.get("selection_stable")),
            phase304.get("modal_selection_share"),
            "SELECTION_NOT_STABLE",
        ),
        gate_record(
            "G03_MULTIPLE_TESTING",
            "Modal hypothesis survives mandatory multiple-testing penalty",
            bool(phase304.get("modal_survives_multiple_testing")),
            phase304.get("multiple_testing", {}).get("rejected_ids", []),
            "MODAL_DID_NOT_SURVIVE_MULTIPLE_TESTING",
        ),
        gate_record(
            "G04_TEMPORAL_STABILITY",
            "Temporal selection audit passed",
            bool(phase306.get("temporal_stability_pass")),
            phase306.get("failure_reasons", []),
            "TEMPORAL_STABILITY_FAILED",
        ),
        gate_record(
            "G05_REGIME_CONCENTRATION",
            "Regime concentration audit passed",
            bool(phase307.get("regime_concentration_pass")),
            phase307.get("failure_reasons", []),
            "REGIME_CONCENTRATION_FAILED",
        ),
        gate_record(
            "G06_HYPOTHESIS_DEPENDENCE",
            "Hypothesis dependence audit passed",
            bool(phase308.get("dependency_pass")),
            phase308.get("failure_reasons", []),
            "HYPOTHESIS_DEPENDENCE_FAILED",
        ),
        gate_record(
            "G07_EXTREME_COST_LIQUIDITY",
            "Extreme cost and liquidity audit passed",
            bool(phase309.get("extreme_cost_liquidity_pass")),
            phase309.get("failure_reasons", []),
            "EXTREME_COST_LIQUIDITY_FAILED",
        ),
        gate_record(
            "G08_TIMESTAMP_SENSITIVITY",
            "Timestamp sensitivity audit passed",
            bool(phase310.get("timestamp_sensitivity_pass")),
            phase310.get("failure_reasons", []),
            "TIMESTAMP_SENSITIVITY_FAILED",
        ),
        gate_record(
            "G09_MINIMUM_OUTER_TRADES",
            "At least 50 external modeled trades",
            int(phase304.get("outer_metrics_10bps", {}).get("trade_count", 0)) >= 50,
            phase304.get("outer_metrics_10bps", {}).get("trade_count", 0),
            "INSUFFICIENT_EXTERNAL_TRADES",
        ),
    ]
    failed = [gate for gate in gates if not gate["passed"]]
    candidate_eligible = not failed
    modal_id = str(phase304.get("modal_hypothesis_id"))

    payload = base_payload(311, "CANDIDATE_ELIGIBILITY_CONTRACT_V2_EVALUATED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE311_CANDIDATE_ELIGIBILITY_CONTRACT_V2_READY_RESEARCH_ONLY",
            "candidate_hypothesis_id": modal_id,
            "eligibility_gate_count": len(gates),
            "passed_gate_count": len(gates) - len(failed),
            "failed_gate_count": len(failed),
            "gates": gates,
            "candidate_eligible": candidate_eligible,
            "failed_gate_ids": [gate["gate_id"] for gate in failed],
            "failed_gate_codes": [gate["failure_code"] for gate in failed],
            "gate_waivers_allowed": False,
            "automatic_freeze_allowed": False,
            "freeze_created": False,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
            "forward_shadow_started": False,
            "paper_trading_started": False,
            "conclusion": (
                "ELIGIBLE_FOR_MANUAL_FREEZE_REVIEW_RESEARCH_ONLY"
                if candidate_eligible
                else "NOT_ELIGIBLE_NO_FREEZE_RESEARCH_ONLY"
            ),
        }
    )
    payload["eligibility_contract_fingerprint"] = fingerprint(
        {
            "candidate_hypothesis_id": modal_id,
            "gates": gates,
            "gate_waivers_allowed": False,
            "automatic_freeze_allowed": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase311_candidate_eligibility_contract_v2.json", payload)
    write_phase_summary(
        ROOT / "docs/reports/stability_v2/phase311_candidate_eligibility_contract_v2_summary.md",
        title="Phase 311 — Candidate Eligibility Contract v2",
        gate=payload["gate"],
        bullets=[
            f"Candidate hypothesis: `{modal_id}`",
            f"Eligibility gates: `{len(gates)}`",
            f"Passed gates: `{payload['passed_gate_count']}`",
            f"Failed gates: `{payload['failed_gate_count']}`",
            f"Candidate eligible: `{candidate_eligible}`",
            "Gate waivers allowed: `False`",
            "Automatic freeze allowed: `False`",
            "Freeze created: `False`",
            "Strategy approved: `False`",
            f"Conclusion: `{payload['conclusion']}`",
        ],
    )
    return payload


def parse_args() -> argparse.Namespace:
    artifacts = ROOT / "artifacts"
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase304-artifact", type=Path, default=artifacts / "phase304_nested_walk_forward_v2_research_only/phase304_nested_walk_forward_v2.json")
    parser.add_argument("--phase306-artifact", type=Path, default=artifacts / "phase306_temporal_selection_stability_audit_research_only/phase306_temporal_selection_stability_audit.json")
    parser.add_argument("--phase307-artifact", type=Path, default=artifacts / "phase307_regime_concentration_audit_research_only/phase307_regime_concentration_audit.json")
    parser.add_argument("--phase308-artifact", type=Path, default=artifacts / "phase308_hypothesis_dependence_audit_research_only/phase308_hypothesis_dependence_audit.json")
    parser.add_argument("--phase309-artifact", type=Path, default=artifacts / "phase309_extreme_cost_liquidity_audit_research_only/phase309_extreme_cost_liquidity_audit.json")
    parser.add_argument("--phase310-artifact", type=Path, default=artifacts / "phase310_timestamp_sensitivity_audit_research_only/phase310_timestamp_sensitivity_audit.json")
    parser.add_argument("--output-dir", type=Path, default=artifacts / "phase311_candidate_eligibility_contract_v2_research_only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build(
        args.phase304_artifact,
        args.phase306_artifact,
        args.phase307_artifact,
        args.phase308_artifact,
        args.phase309_artifact,
        args.phase310_artifact,
        args.output_dir,
    )
    print(payload["gate"])
    print("Candidate:", payload["candidate_hypothesis_id"])
    print("Passed gates:", payload["passed_gate_count"])
    print("Failed gates:", payload["failed_gate_count"])
    print("Candidate eligible:", payload["candidate_eligible"])
    print("Freeze created:", payload["freeze_created"])
    print("Strategy approved:", payload["strategy_approved"])
    print("Operational:", payload["locks"]["operational_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
