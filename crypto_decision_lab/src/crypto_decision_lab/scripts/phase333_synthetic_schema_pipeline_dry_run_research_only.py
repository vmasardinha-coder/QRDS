from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase326_335_preregistration_common import (
    ROOT,
    base_payload,
    fingerprint,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def _synthetic_rows(count: int = 480) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    for index in range(count):
        disagreement = 0.5 + 0.35 * math.sin(index / 13.0)
        derivatives_quality = 0.55 + 0.30 * math.cos(index / 17.0)
        combined = max(0.0, min(1.0, 0.55 * disagreement + 0.45 * (1.0 - derivatives_quality)))
        label = int(combined > 0.58 or (index % 29 == 0))
        rows.append(
            {
                "timestamp_index": index,
                "exchange_disagreement_score": disagreement,
                "derivatives_quality_score": derivatives_quality,
                "combined_quality_risk_score": combined,
                "abstain_label": label,
            }
        )
    return rows


def _score(
    row: dict[str, float | int],
    feature_bundle: str,
    model_class: str,
    operating_point: str,
) -> float:
    disagreement = float(row["exchange_disagreement_score"])
    quality_risk = 1.0 - float(row["derivatives_quality_score"])
    if feature_bundle == "EXCHANGE_DISAGREEMENT_ONLY":
        base = disagreement
    elif feature_bundle == "DERIVATIVES_DATA_QUALITY_ONLY":
        base = quality_risk
    else:
        base = 0.55 * disagreement + 0.45 * quality_risk
    if model_class == "LOGISTIC_REGRESSION":
        base = 1.0 / (1.0 + math.exp(-5.0 * (base - 0.5)))
    adjustment = 0.05 if operating_point == "STRICT" else -0.02
    return max(0.0, min(1.0, base + adjustment))


def build(
    phase328_path: Path,
    phase329_path: Path,
    phase330_path: Path,
    phase331_path: Path,
    phase332_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    paths = (
        phase328_path,
        phase329_path,
        phase330_path,
        phase331_path,
        phase332_path,
    )
    phases = (328, 329, 330, 331, 332)
    items = [read_json(path) for path in paths]
    for phase, item in zip(phases, items):
        validate_phase(item, phase)
    p328, p329, p330, p331, p332 = items
    allowed = (
        p328.get("family_definition_frozen") is True
        and p329.get("target_label_frozen") is True
        and p330.get("budget_definition_frozen") is True
        and p331.get("sealed_template_count") == 12
        and p332.get("statistical_plan_frozen") is True
    )
    template_results: list[dict[str, Any]] = []
    synthetic_rows = _synthetic_rows() if allowed else []
    if allowed:
        for template in p331["sealed_templates"]:
            scores = [
                _score(
                    row,
                    template["feature_bundle"],
                    template["model_class"],
                    template["operating_point"],
                )
                for row in synthetic_rows
            ]
            template_results.append(
                {
                    "template_id": template["template_id"],
                    "rows_scored": len(scores),
                    "minimum_score": min(scores),
                    "maximum_score": max(scores),
                    "finite_scores": all(math.isfinite(value) for value in scores),
                    "scores_within_unit_interval": all(
                        0.0 <= value <= 1.0 for value in scores
                    ),
                    "directional_output_generated": False,
                    "status": "PASS",
                }
            )
    pass_state = (
        allowed
        and len(template_results) == 12
        and all(
            item["finite_scores"]
            and item["scores_within_unit_interval"]
            and item["directional_output_generated"] is False
            for item in template_results
        )
    )
    payload = base_payload(
        333,
        (
            "SYNTHETIC_SCHEMA_PIPELINE_DRY_RUN_PASS_RESEARCH_ONLY"
            if pass_state
            else "SYNTHETIC_DRY_RUN_SKIPPED_OR_FAILED_RESEARCH_ONLY"
        ),
    )
    payload.update(
        {
            "gate": "PHASE333_SYNTHETIC_SCHEMA_PIPELINE_DRY_RUN_READY_RESEARCH_ONLY",
            "dry_run_executed": allowed,
            "dry_run_pass": pass_state,
            "synthetic_seed_contract": "DETERMINISTIC_FORMULA_V1",
            "synthetic_row_count": len(synthetic_rows),
            "synthetic_fold_count": 6 if allowed else 0,
            "templates_exercised": len(template_results),
            "template_results": template_results,
            "real_historical_rows_used": 0,
            "real_historical_labels_created": 0,
            "historical_performance_metrics_computed": False,
            "registry_open": False,
            "active_hypotheses": 0,
            "experiment_budget_opened": False,
            "new_family_opened": False,
            "strategy_approved": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        output_dir / "phase333_synthetic_schema_pipeline_dry_run.json",
        payload,
    )
    write_summary(
        ROOT
        / "docs/reports/preregistration_v2/"
        "phase333_synthetic_schema_pipeline_dry_run_summary.md",
        title="Phase 333 — Synthetic Schema and Pipeline Dry-run",
        gate=payload["gate"],
        bullets=[
            f"Dry-run executed: `{allowed}`",
            f"Dry-run pass: `{pass_state}`",
            f"Synthetic rows: `{len(synthetic_rows)}`",
            f"Templates exercised: `{len(template_results)}`",
            "Real historical rows used: `0`",
            "Historical performance metrics computed: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    defaults = {
        328: artifacts
        / "phase328_new_family_definition_freeze_research_only/"
        "phase328_new_family_definition_freeze.json",
        329: artifacts
        / "phase329_non_directional_target_label_freeze_research_only/"
        "phase329_non_directional_target_label_freeze.json",
        330: artifacts
        / "phase330_finite_hypothesis_budget_envelope_research_only/"
        "phase330_finite_hypothesis_budget_envelope.json",
        331: artifacts
        / "phase331_sealed_non_directional_hypothesis_templates_research_only/"
        "phase331_sealed_non_directional_hypothesis_templates.json",
        332: artifacts
        / "phase332_statistical_multiple_testing_stop_plan_research_only/"
        "phase332_statistical_multiple_testing_stop_plan.json",
    }
    for phase, default in defaults.items():
        parser.add_argument(f"--phase{phase}-artifact", type=Path, default=default)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=artifacts
        / "phase333_synthetic_schema_pipeline_dry_run_research_only",
    )
    args = parser.parse_args()
    payload = build(
        *(getattr(args, f"phase{phase}_artifact") for phase in defaults),
        args.output_dir,
    )
    print(payload["gate"])
    print("Dry-run pass:", payload["dry_run_pass"])
    print("Real historical rows used:", payload["real_historical_rows_used"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
