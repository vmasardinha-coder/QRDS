from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase326_335_preregistration_common import (
    PROPOSED_NEW_FAMILY_ID,
    PROPOSED_QUESTION_ID,
    QUESTION,
    ROOT,
    all_pass,
    base_payload,
    fingerprint,
    read_json,
    review_record,
    validate_phase,
    write_json,
    write_summary,
)


def build(paths: dict[int, Path], output_dir: Path) -> dict[str, Any]:
    items = {phase: read_json(path) for phase, path in paths.items()}
    for phase, item in items.items():
        validate_phase(item, phase)

    gates = [
        review_record(
            "R01",
            "The previous directional family is formally closed",
            items[316].get("negative_result_registered") is True,
            items[316].get("current_family_decision"),
            "NEGATIVE_RESULT_NOT_REGISTERED",
        ),
        review_record(
            "R02",
            "All 24 prior hypotheses are protected from silent retest",
            items[317].get("registry_closed") is True
            and items[317].get("prohibited_signature_count") == 24,
            items[317].get("prohibited_signature_count"),
            "ANTI_RETEST_REGISTRY_INCOMPLETE",
        ),
        review_record(
            "R03",
            "Failure causes are documented rather than hidden",
            items[318].get("failure_category_count", 0) >= 5,
            items[318].get("failure_category_counts"),
            "FAILURE_ATLAS_INCOMPLETE",
        ),
        review_record(
            "R04",
            "Public candle coverage is adequate for future research",
            items[319].get("coverage_audit_pass") is True,
            items[319].get("candle_datasets_meeting_threshold"),
            "CANDLE_COVERAGE_INADEQUATE",
        ),
        review_record(
            "R05",
            "Cross-exchange disagreement is measurable",
            items[320].get("disagreement_context_available") is True,
            {
                "common_hours": items[320].get("common_hour_count"),
                "spread_bps_p95": items[320].get("spread_bps_p95"),
            },
            "EXCHANGE_DISAGREEMENT_UNAVAILABLE",
        ),
        review_record(
            "R06",
            "Derivatives-data quality is measurable",
            items[321].get("derivatives_context_usable") is True,
            items[321].get("dataset_audits"),
            "DERIVATIVES_QUALITY_UNUSABLE",
        ),
        review_record(
            "R07",
            "The proposed question passed every novelty gate",
            items[322].get("genuinely_different_question_justified") is True
            and items[322].get("passed_novelty_gate_count")
            == items[322].get("novelty_gate_count"),
            {
                "passed": items[322].get("passed_novelty_gate_count"),
                "total": items[322].get("novelty_gate_count"),
            },
            "NOVELTY_GATES_NOT_COMPLETE",
        ),
        review_record(
            "R08",
            "The draft exists while family and budget remain closed",
            items[323].get("preregistration_draft_created") is True
            and items[323].get("new_family_opened") is False
            and items[323].get("experiment_budget_opened") is False,
            items[323].get("preregistration_contract"),
            "DRAFT_OR_CLOSURE_CONTRACT_INVALID",
        ),
        review_record(
            "R09",
            "The output is abstain/evaluate only, never buy or sell",
            items[322].get("question_output") == "RESEARCH_ABSTAIN_OR_EVALUATE_ONLY"
            and items[322].get("target_type")
            == "ABSTENTION_RELIABILITY_NOT_DIRECTIONAL_RETURN",
            {
                "output": items[322].get("question_output"),
                "target_type": items[322].get("target_type"),
            },
            "QUESTION_IS_DIRECTIONAL",
        ),
        review_record(
            "R10",
            "Phase 325 kept every execution lock closed",
            items[325].get("strategy_approved") is False
            and items[325].get("new_family_opened") is False
            and items[325].get("experiment_budget_opened") is False
            and items[325].get("locks", {}).get("capital_used") == 0,
            {
                "strategy_approved": items[325].get("strategy_approved"),
                "new_family_opened": items[325].get("new_family_opened"),
                "capital_used": items[325].get("locks", {}).get("capital_used"),
            },
            "PHASE325_LOCKS_INVALID",
        ),
    ]
    passed = sum(bool(item["passed"]) for item in gates)
    recommendation = (
        "ACCEPT_QUESTION_FOR_PREREGISTRATION_REVIEW_ONLY"
        if all_pass(gates)
        else "REJECT_OR_REMEDIATE_QUESTION_RESEARCH_ONLY"
    )
    payload = base_payload(
        326,
        "HUMAN_READABLE_NOVELTY_NON_OVERLAP_REVIEW_READY_RESEARCH_ONLY",
    )
    payload.update(
        {
            "gate": "PHASE326_HUMAN_READABLE_NOVELTY_NON_OVERLAP_REVIEW_READY_RESEARCH_ONLY",
            "question_id": PROPOSED_QUESTION_ID,
            "family_id": PROPOSED_NEW_FAMILY_ID,
            "scientific_question": QUESTION,
            "review_gate_count": len(gates),
            "passed_review_gate_count": passed,
            "failed_review_gate_count": len(gates) - passed,
            "failed_review_gate_ids": [
                item["gate_id"] for item in gates if not item["passed"]
            ],
            "review_gates": gates,
            "review_recommendation": recommendation,
            "manual_decision_recorded": False,
            "new_family_opened": False,
            "hypotheses_registered": 0,
            "experiment_budget_opened": False,
            "historical_evaluation_started": False,
            "strategy_approved": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        output_dir / "phase326_human_readable_novelty_non_overlap_review.json",
        payload,
    )
    write_summary(
        ROOT
        / "docs/reports/preregistration_v2/"
        "phase326_human_readable_novelty_non_overlap_review_summary.md",
        title="Phase 326 — Human-readable Novelty and Non-overlap Review",
        gate=payload["gate"],
        bullets=[
            f"Question: `{PROPOSED_QUESTION_ID}`",
            f"Passed review gates: `{passed}/{len(gates)}`",
            f"Recommendation: `{recommendation}`",
            "Manual decision recorded: `False`",
            "New family opened: `False`",
            "Experiment budget opened: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    defaults = {
        316: artifacts
        / "phase316_negative_evidence_registry_research_only/"
        "phase316_negative_evidence_registry.json",
        317: artifacts
        / "phase317_prohibited_retest_signature_registry_research_only/"
        "phase317_prohibited_retest_signature_registry.json",
        318: artifacts
        / "phase318_failure_atlas_research_only/phase318_failure_atlas.json",
        319: artifacts
        / "phase319_data_coverage_audit_v2_research_only/"
        "phase319_data_coverage_audit_v2.json",
        320: artifacts
        / "phase320_exchange_disagreement_audit_research_only/"
        "phase320_exchange_disagreement_audit.json",
        321: artifacts
        / "phase321_derivatives_missingness_audit_research_only/"
        "phase321_derivatives_missingness_audit.json",
        322: artifacts
        / "phase322_new_scientific_question_novelty_audit_research_only/"
        "phase322_new_scientific_question_novelty_audit.json",
        323: artifacts
        / "phase323_new_family_preregistration_contract_research_only/"
        "phase323_new_family_preregistration_contract.json",
        325: artifacts
        / "phase325_negative_evidence_new_question_full_integration_checkpoint_research_only/"
        "phase325_negative_evidence_new_question_full_integration_checkpoint.json",
    }
    for phase, default in defaults.items():
        parser.add_argument(f"--phase{phase}-artifact", type=Path, default=default)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=artifacts
        / "phase326_human_readable_novelty_non_overlap_review_research_only",
    )
    args = parser.parse_args()
    paths = {
        phase: getattr(args, f"phase{phase}_artifact") for phase in defaults
    }
    payload = build(paths, args.output_dir)
    print(payload["gate"])
    print("Review recommendation:", payload["review_recommendation"])
    print(
        "Passed review gates:",
        f"{payload['passed_review_gate_count']}/{payload['review_gate_count']}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
