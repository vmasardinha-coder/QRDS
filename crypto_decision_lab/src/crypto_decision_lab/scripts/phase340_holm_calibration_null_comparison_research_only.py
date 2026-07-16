from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase336_345_abstention_evaluation_common import (
    ROOT,
    base_payload,
    classification_metrics,
    fingerprint,
    holm_bonferroni,
    one_sided_positive_pvalue,
    read_csv_gz,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def build(phase332_path: Path, phase339_path: Path, output_dir: Path) -> dict[str, Any]:
    phase332 = read_json(phase332_path)
    phase339 = read_json(phase339_path)
    validate_phase(phase332, 332)
    validate_phase(phase339, 339)
    if phase332.get("statistical_plan_frozen") is not True:
        raise RuntimeError("Frozen statistical plan is missing.")
    if phase339.get("outer_holdout_untouched_for_selection") is not True:
        raise RuntimeError("Outer holdout integrity was not preserved.")

    rows = read_csv_gz(ROOT / phase339["predictions_path"])
    by_template: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_template.setdefault(str(row["template_id"]), []).append(row)
    pvalues: dict[str, float] = {}
    aggregate: dict[str, Any] = {}
    for template_id, template_rows in sorted(by_template.items()):
        labels = [int(row["label"]) for row in template_rows]
        probabilities = [float(row["probability"]) for row in template_rows]
        null_probabilities = [float(row["train_prevalence"]) for row in template_rows]
        metrics = classification_metrics(labels, probabilities, null_probabilities)
        fold_improvements = []
        fold_pass_count = 0
        for fold in phase339["fold_results"]:
            fold_metrics = fold["template_metrics"][template_id]
            fold_improvements.append(float(fold_metrics["null_brier"]) - float(fold_metrics["brier"]))
            fold_pass_count += int(bool(fold_metrics["fold_pass"]))
        pvalue = one_sided_positive_pvalue(fold_improvements)
        pvalues[template_id] = pvalue
        aggregate[template_id] = {
            **metrics,
            "fold_pass_count": fold_pass_count,
            "fold_count": len(phase339["fold_results"]),
            "one_sided_brier_improvement_pvalue": pvalue,
            "mean_fold_brier_improvement": sum(fold_improvements) / len(fold_improvements),
        }
    penalty = holm_bonferroni(pvalues)
    survivors: list[str] = []
    for template_id, metrics in aggregate.items():
        metrics["holm_adjusted_pvalue"] = penalty["adjusted_pvalues"].get(template_id, 1.0)
        metrics["holm_rejected_null"] = template_id in penalty["rejected_ids"]
        metrics["calibration_validated"] = metrics["expected_calibration_error"] <= 0.05
        metrics["primary_metric_positive"] = metrics["brier_skill"] > 0
        metrics["secondary_guardrails_pass"] = (
            metrics["pr_auc_improvement"] >= 0.02
            and metrics["expected_calibration_error"] <= 0.05
            and metrics["fold_pass_count"] >= 6
        )
        metrics["survives_phase340"] = (
            metrics["holm_rejected_null"]
            and metrics["primary_metric_positive"]
            and metrics["secondary_guardrails_pass"]
        )
        if metrics["survives_phase340"]:
            survivors.append(template_id)
    ranking = sorted(
        aggregate,
        key=lambda template_id: (
            float(aggregate[template_id]["brier_skill"]),
            float(aggregate[template_id]["pr_auc_improvement"]),
            -float(aggregate[template_id]["expected_calibration_error"]),
            template_id,
        ),
        reverse=True,
    )
    top_id = ranking[0] if ranking else None
    payload = base_payload(340, "HOLM_CALIBRATION_NULL_COMPARISON_COMPLETE_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE340_HOLM_CALIBRATION_NULL_COMPARISON_READY_RESEARCH_ONLY",
            "template_count": len(aggregate),
            "aggregate_metrics": aggregate,
            "holm_bonferroni": penalty,
            "survivor_ids": survivors,
            "survivor_count": len(survivors),
            "top_diagnostic_template_id": top_id,
            "top_diagnostic_metrics": aggregate.get(top_id) if top_id else None,
            "calibration_gate_threshold": 0.05,
            "minimum_outer_fold_passes": 6,
            "null_model": "TRAINING_FOLD_PREVALENCE",
            "outer_data_used_for_model_selection": False,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase340_holm_calibration_null_comparison.json", payload)
    write_summary(
        ROOT / "docs/reports/abstention_v1/phase340_holm_calibration_null_comparison_summary.md",
        title="Phase 340 — Holm, Calibration and Null-model Comparison",
        gate=payload["gate"],
        bullets=[
            f"Templates compared: `{len(aggregate)}`",
            f"Holm survivors: `{len(survivors)}`",
            f"Top diagnostic template: `{top_id or 'NONE'}`",
            "Null model: `TRAINING_FOLD_PREVALENCE`",
            "Outer data used for model selection: `False`",
            "Strategy approved: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    parser.add_argument("--phase332-artifact", type=Path, default=artifacts / "phase332_statistical_multiple_testing_stop_plan_research_only/phase332_statistical_multiple_testing_stop_plan.json")
    parser.add_argument("--phase339-artifact", type=Path, default=artifacts / "phase339_nested_walk_forward_abstention_research_only/phase339_nested_walk_forward_abstention.json")
    parser.add_argument("--output-dir", type=Path, default=artifacts / "phase340_holm_calibration_null_comparison_research_only")
    args = parser.parse_args()
    payload = build(args.phase332_artifact, args.phase339_artifact, args.output_dir)
    print(payload["gate"])
    print("Survivors:", payload["survivor_count"])
    print("Top diagnostic template:", payload["top_diagnostic_template_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
