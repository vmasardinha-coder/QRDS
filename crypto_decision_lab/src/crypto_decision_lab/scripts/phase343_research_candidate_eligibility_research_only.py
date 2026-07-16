from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase336_345_abstention_evaluation_common import (
    ROOT,
    base_payload,
    fingerprint,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def build(
    phase336_path: Path,
    phase337_path: Path,
    phase338_path: Path,
    phase339_path: Path,
    phase340_path: Path,
    phase341_path: Path,
    phase342_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    paths = {
        336: phase336_path,
        337: phase337_path,
        338: phase338_path,
        339: phase339_path,
        340: phase340_path,
        341: phase341_path,
        342: phase342_path,
    }
    items = {phase: read_json(path) for phase, path in paths.items()}
    for phase, item in items.items():
        validate_phase(item, phase)

    template_ids = [str(item["template_id"]) for item in items[336].get("active_templates", [])]
    gate_records: dict[str, Any] = {}
    eligible_ids: list[str] = []
    for template_id in template_ids:
        metrics340 = items[340].get("aggregate_metrics", {}).get(template_id, {})
        audit341 = items[341].get("template_audits", {}).get(template_id, {})
        metrics342 = items[342].get("template_results", {}).get(template_id, {})
        gates = [
            {
                "gate_id": "REGISTRY_EXACT_12",
                "passed": items[336].get("active_template_count") == 12,
            },
            {
                "gate_id": "ASOF_FEATURES_NO_FUTURE",
                "passed": items[337].get("features_available_at_or_before_decision_time") is True
                and items[337].get("future_feature_use_allowed") is False,
            },
            {
                "gate_id": "TARGET_THRESHOLD_TRAIN_ONLY",
                "passed": items[338].get("training_fold_threshold_required") is True
                and items[338].get("outer_holdout_threshold_selection_allowed") is False,
            },
            {
                "gate_id": "OUTER_HOLDOUT_UNTOUCHED",
                "passed": items[339].get("outer_holdout_untouched_for_selection") is True,
            },
            {
                "gate_id": "HOLM_PRIMARY_SUCCESS",
                "passed": bool(metrics340.get("survives_phase340")),
            },
            {
                "gate_id": "CALIBRATION_VALIDATED",
                "passed": bool(metrics340.get("calibration_validated")),
            },
            {
                "gate_id": "ROBUST_ACROSS_STRATA",
                "passed": bool(audit341.get("robustness_pass")),
            },
            {
                "gate_id": "COVERAGE_RELIABILITY_PASS",
                "passed": bool(metrics342.get("coverage_reliability_gate_pass")),
            },
            {
                "gate_id": "NO_DIRECTIONAL_OR_MONETARY_TARGET",
                "passed": items[342].get("monetary_metric_computed") is False
                and items[342].get("directional_metric_computed") is False,
            },
        ]
        for gate in gates:
            gate["waiver_allowed"] = False
        eligible = all(bool(gate["passed"]) for gate in gates)
        gate_records[template_id] = {
            "gates": gates,
            "passed_gate_count": sum(bool(gate["passed"]) for gate in gates),
            "gate_count": len(gates),
            "historical_research_candidate_eligible": eligible,
        }
        if eligible:
            eligible_ids.append(template_id)

    candidate_id = eligible_ids[0] if len(eligible_ids) == 1 else None
    family_decision = (
        "HISTORICAL_ABSTENTION_RESEARCH_CANDIDATE_ONLY_PENDING_MANUAL_FREEZE_REVIEW"
        if candidate_id
        else "CLOSE_ABSTENTION_FAMILY_NO_SURVIVOR_RESEARCH_ONLY"
    )
    payload = base_payload(343, "RESEARCH_CANDIDATE_ELIGIBILITY_EVALUATED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE343_RESEARCH_CANDIDATE_ELIGIBILITY_READY_RESEARCH_ONLY",
            "template_gate_records": gate_records,
            "eligible_template_ids": eligible_ids,
            "eligible_template_count": len(eligible_ids),
            "historical_research_candidate_id": candidate_id,
            "historical_research_candidate_only": candidate_id is not None,
            "family_decision": family_decision,
            "registry_open": False,
            "experiment_budget_open": False,
            "historical_evaluation_complete": True,
            "candidate_freeze_created": False,
            "forward_evidence_clock_started": False,
            "forward_evidence_credit": 0,
            "forward_shadow_eligible": False,
            "forward_shadow_started": False,
            "paper_trading_started": False,
            "automatic_promotion_allowed": False,
            "strategy_approved": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase343_research_candidate_eligibility.json", payload)
    write_summary(
        ROOT / "docs/reports/abstention_v1/phase343_research_candidate_eligibility_summary.md",
        title="Phase 343 — Historical Research-candidate Eligibility",
        gate=payload["gate"],
        bullets=[
            f"Eligible templates: `{len(eligible_ids)}`",
            f"Historical research candidate: `{candidate_id or 'NONE'}`",
            f"Family decision: `{family_decision}`",
            "Candidate freeze created: `False`",
            "Forward evidence clock started: `False`",
            "Strategy approved: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    defaults = {
        336: artifacts / "phase336_finite_registry_opening_research_only/phase336_finite_registry_opening.json",
        337: artifacts / "phase337_asof_quality_feature_matrix_research_only/phase337_asof_quality_feature_matrix.json",
        338: artifacts / "phase338_frozen_h8_target_builder_research_only/phase338_frozen_h8_target_builder.json",
        339: artifacts / "phase339_nested_walk_forward_abstention_research_only/phase339_nested_walk_forward_abstention.json",
        340: artifacts / "phase340_holm_calibration_null_comparison_research_only/phase340_holm_calibration_null_comparison.json",
        341: artifacts / "phase341_regime_provider_missingness_robustness_research_only/phase341_regime_provider_missingness_robustness.json",
        342: artifacts / "phase342_abstention_coverage_reliability_tradeoff_research_only/phase342_abstention_coverage_reliability_tradeoff.json",
    }
    for phase, default in defaults.items():
        parser.add_argument(f"--phase{phase}-artifact", type=Path, default=default)
    parser.add_argument("--output-dir", type=Path, default=artifacts / "phase343_research_candidate_eligibility_research_only")
    args = parser.parse_args()
    payload = build(
        args.phase336_artifact,
        args.phase337_artifact,
        args.phase338_artifact,
        args.phase339_artifact,
        args.phase340_artifact,
        args.phase341_artifact,
        args.phase342_artifact,
        args.output_dir,
    )
    print(payload["gate"])
    print("Eligible templates:", payload["eligible_template_count"])
    print("Candidate:", payload["historical_research_candidate_id"])
    print("Family decision:", payload["family_decision"])
    print("Strategy approved:", payload["strategy_approved"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
