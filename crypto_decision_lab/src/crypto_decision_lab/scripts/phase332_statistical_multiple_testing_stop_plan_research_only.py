from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase326_335_preregistration_common import (
    ROOT,
    base_payload,
    canonical_hash,
    fingerprint,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def build(
    phase329_path: Path,
    phase330_path: Path,
    phase331_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    phase329 = read_json(phase329_path)
    phase330 = read_json(phase330_path)
    phase331 = read_json(phase331_path)
    validate_phase(phase329, 329)
    validate_phase(phase330, 330)
    validate_phase(phase331, 331)
    allowed = (
        phase329.get("target_label_frozen") is True
        and phase330.get("budget_definition_frozen") is True
        and phase331.get("sealed_template_count") == 12
        and phase331.get("registry_open") is False
    )
    plan = {
        "primary_metric": "BRIER_SKILL_VS_PREVALENCE_NULL",
        "secondary_metrics": [
            "PR_AUC_IMPROVEMENT_VS_PREVALENCE",
            "EXPECTED_CALIBRATION_ERROR",
            "ABSTENTION_COVERAGE_RATE",
        ],
        "primary_success_rule": "HOLM_ADJUSTED_P_LT_0_05_AND_POSITIVE_BRIER_SKILL",
        "secondary_guardrails": {
            "minimum_pr_auc_improvement": 0.02,
            "maximum_expected_calibration_error": 0.05,
            "minimum_outer_fold_passes": 6,
            "planned_outer_fold_count": 8,
        },
        "multiple_testing_method": "HOLM_BONFERRONI",
        "nested_walk_forward_required": True,
        "outer_holdout_may_influence_selection": False,
        "thresholds_fit_on_training_fold_only": True,
        "closed_family_retest_allowed": False,
        "budget_expansion_after_results_allowed": False,
        "stop_rule": "CLOSE_FAMILY_IF_NO_TEMPLATE_SURVIVES_ALL_GATES",
        "monetary_interpretation_allowed": False,
        "execution_allowed": False,
    }
    frozen = allowed
    payload = base_payload(
        332,
        (
            "STATISTICAL_MULTIPLE_TESTING_STOP_PLAN_FROZEN_RESEARCH_ONLY"
            if frozen
            else "STATISTICAL_PLAN_NOT_FROZEN_REJECTED_OR_BLOCKED"
        ),
    )
    payload.update(
        {
            "gate": "PHASE332_STATISTICAL_MULTIPLE_TESTING_STOP_PLAN_READY_RESEARCH_ONLY",
            "statistical_plan_frozen": frozen,
            "statistical_plan": plan if frozen else None,
            "statistical_plan_sha256": (
                canonical_hash(plan) if frozen else None
            ),
            "registry_open": False,
            "active_hypotheses": 0,
            "experiment_budget_opened": False,
            "historical_experiments_executed": 0,
            "new_family_opened": False,
            "strategy_approved": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        output_dir / "phase332_statistical_multiple_testing_stop_plan.json",
        payload,
    )
    write_summary(
        ROOT
        / "docs/reports/preregistration_v2/"
        "phase332_statistical_multiple_testing_stop_plan_summary.md",
        title="Phase 332 — Statistical, Multiple-testing and Stop Plan",
        gate=payload["gate"],
        bullets=[
            f"Statistical plan frozen: `{frozen}`",
            "Primary metric: `BRIER_SKILL_VS_PREVALENCE_NULL`",
            "Multiple-testing method: `HOLM_BONFERRONI`",
            "Outer folds planned: `8`",
            "Registry open: `False`",
            "Historical experiments executed: `0`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    parser.add_argument(
        "--phase329-artifact",
        type=Path,
        default=artifacts
        / "phase329_non_directional_target_label_freeze_research_only/"
        "phase329_non_directional_target_label_freeze.json",
    )
    parser.add_argument(
        "--phase330-artifact",
        type=Path,
        default=artifacts
        / "phase330_finite_hypothesis_budget_envelope_research_only/"
        "phase330_finite_hypothesis_budget_envelope.json",
    )
    parser.add_argument(
        "--phase331-artifact",
        type=Path,
        default=artifacts
        / "phase331_sealed_non_directional_hypothesis_templates_research_only/"
        "phase331_sealed_non_directional_hypothesis_templates.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=artifacts
        / "phase332_statistical_multiple_testing_stop_plan_research_only",
    )
    args = parser.parse_args()
    payload = build(
        args.phase329_artifact,
        args.phase330_artifact,
        args.phase331_artifact,
        args.output_dir,
    )
    print(payload["gate"])
    print("Statistical plan frozen:", payload["statistical_plan_frozen"])
    print("Registry open:", payload["registry_open"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
