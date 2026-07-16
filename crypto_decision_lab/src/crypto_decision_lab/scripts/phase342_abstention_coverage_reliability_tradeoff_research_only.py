from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase336_345_abstention_evaluation_common import (
    ROOT,
    base_payload,
    fingerprint,
    read_csv_gz,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def build(phase336_path: Path, phase339_path: Path, phase341_path: Path, output_dir: Path) -> dict[str, Any]:
    phase336 = read_json(phase336_path)
    phase339 = read_json(phase339_path)
    phase341 = read_json(phase341_path)
    for phase, item in ((336, phase336), (339, phase339), (341, phase341)):
        validate_phase(item, phase)
    rows = read_csv_gz(ROOT / phase339["predictions_path"])
    template_ids = [str(item["template_id"]) for item in phase336["active_templates"]]
    results: dict[str, Any] = {}
    eligible_ids: list[str] = []
    for template_id in template_ids:
        selected = [row for row in rows if row["template_id"] == template_id]
        if not selected:
            continue
        threshold = float(selected[0]["operating_threshold"])
        labels = [int(row["label"]) for row in selected]
        probabilities = [float(row["probability"]) for row in selected]
        abstain = [probability >= threshold for probability in probabilities]
        coverage = sum(abstain) / len(abstain)
        evaluated_labels = [label for label, flag in zip(labels, abstain) if not flag]
        overall_failure_rate = sum(labels) / len(labels)
        evaluated_failure_rate = sum(evaluated_labels) / len(evaluated_labels) if evaluated_labels else 1.0
        reliability_improvement = overall_failure_rate - evaluated_failure_rate
        coverage_guardrail = 0.05 <= coverage <= 0.60
        improvement_guardrail = reliability_improvement >= 0.03
        retained_guardrail = len(evaluated_labels) >= 500
        robust = template_id in phase341.get("robust_template_ids", [])
        eligible = robust and coverage_guardrail and improvement_guardrail and retained_guardrail
        results[template_id] = {
            "operating_threshold": threshold,
            "sample_count": len(labels),
            "abstention_coverage_rate": coverage,
            "retained_evaluation_rows": len(evaluated_labels),
            "overall_reliability_failure_rate": overall_failure_rate,
            "evaluated_subset_failure_rate": evaluated_failure_rate,
            "reliability_improvement_absolute": reliability_improvement,
            "coverage_guardrail_pass": coverage_guardrail,
            "reliability_improvement_guardrail_pass": improvement_guardrail,
            "retained_sample_guardrail_pass": retained_guardrail,
            "phase341_robust": robust,
            "coverage_reliability_gate_pass": eligible,
        }
        if eligible:
            eligible_ids.append(template_id)
    ranking = sorted(
        results,
        key=lambda template_id: (
            float(results[template_id]["reliability_improvement_absolute"]),
            -abs(float(results[template_id]["abstention_coverage_rate"]) - 0.25),
            template_id,
        ),
        reverse=True,
    )
    payload = base_payload(342, "ABSTENTION_COVERAGE_RELIABILITY_TRADEOFF_EVALUATED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE342_ABSTENTION_COVERAGE_RELIABILITY_TRADEOFF_READY_RESEARCH_ONLY",
            "template_results": results,
            "coverage_reliability_eligible_ids": eligible_ids,
            "coverage_reliability_eligible_count": len(eligible_ids),
            "top_diagnostic_template_id": ranking[0] if ranking else None,
            "minimum_coverage_rate": 0.05,
            "maximum_coverage_rate": 0.60,
            "minimum_reliability_improvement": 0.03,
            "minimum_retained_rows": 500,
            "monetary_metric_computed": False,
            "directional_metric_computed": False,
            "strategy_approved": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase342_abstention_coverage_reliability_tradeoff.json", payload)
    write_summary(
        ROOT / "docs/reports/abstention_v1/phase342_abstention_coverage_reliability_tradeoff_summary.md",
        title="Phase 342 — Abstention Coverage versus Reliability Improvement",
        gate=payload["gate"],
        bullets=[
            f"Templates assessed: `{len(results)}`",
            f"Coverage/reliability eligible: `{len(eligible_ids)}`",
            "Monetary metric computed: `False`",
            "Directional metric computed: `False`",
            "Strategy approved: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    parser.add_argument("--phase336-artifact", type=Path, default=artifacts / "phase336_finite_registry_opening_research_only/phase336_finite_registry_opening.json")
    parser.add_argument("--phase339-artifact", type=Path, default=artifacts / "phase339_nested_walk_forward_abstention_research_only/phase339_nested_walk_forward_abstention.json")
    parser.add_argument("--phase341-artifact", type=Path, default=artifacts / "phase341_regime_provider_missingness_robustness_research_only/phase341_regime_provider_missingness_robustness.json")
    parser.add_argument("--output-dir", type=Path, default=artifacts / "phase342_abstention_coverage_reliability_tradeoff_research_only")
    args = parser.parse_args()
    payload = build(args.phase336_artifact, args.phase339_artifact, args.phase341_artifact, args.output_dir)
    print(payload["gate"])
    print("Eligible templates:", payload["coverage_reliability_eligible_count"])
    print("Monetary metric computed:", payload["monetary_metric_computed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
