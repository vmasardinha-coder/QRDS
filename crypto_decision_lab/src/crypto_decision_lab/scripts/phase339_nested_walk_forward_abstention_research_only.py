from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase336_345_abstention_evaluation_common import (
    FEATURE_BUNDLES,
    PREDICTION_FIELDS,
    ROOT,
    base_payload,
    classification_metrics,
    fingerprint,
    fit_logistic_regression,
    fit_threshold_rule,
    predict_probability,
    quantile,
    read_csv_gz,
    read_json,
    safe_numeric_feature_row,
    sha256_file,
    target_label,
    validate_phase,
    walk_forward_folds,
    write_csv_gz,
    write_json,
    write_summary,
)


def build(
    phase336_path: Path,
    phase337_path: Path,
    phase338_path: Path,
    output_dir: Path,
    *,
    minimum_train_hours: int = 365 * 24,
    outer_hours: int = 90 * 24,
    max_folds: int = 8,
    logistic_iterations: int = 30,
) -> dict[str, Any]:
    phase336 = read_json(phase336_path)
    phase337 = read_json(phase337_path)
    phase338 = read_json(phase338_path)
    for phase, item in ((336, phase336), (337, phase337), (338, phase338)):
        validate_phase(item, phase)
    if phase336.get("registry_open") is not True or phase336.get("active_template_count") != 12:
        raise RuntimeError("Finite registry is not open with 12 templates.")

    feature_rows = {int(row["open_time_ms"]): row for row in read_csv_gz(ROOT / phase337["matrix_path"])}
    target_rows = {int(row["open_time_ms"]): row for row in read_csv_gz(ROOT / phase338["target_components_path"])}
    timestamps = sorted(set(feature_rows) & set(target_rows))
    joined = [
        {
            "timestamp": timestamp,
            "feature": safe_numeric_feature_row(feature_rows[timestamp]),
            "raw_target": {
                "future_sign_disagreement": int(target_rows[timestamp]["future_sign_disagreement"]),
                "future_return_dispersion_bps": float(target_rows[timestamp]["future_return_dispersion_bps"]),
            },
        }
        for timestamp in timestamps
    ]
    folds = walk_forward_folds(
        len(joined),
        minimum_train_hours=minimum_train_hours,
        outer_hours=outer_hours,
        max_folds=max_folds,
    )
    if len(folds) < 3:
        raise RuntimeError(f"Nested walk-forward requires at least 3 folds; found {len(folds)}.")

    templates = list(phase336["active_templates"])
    template_lookup = {str(item["template_id"]): item for item in templates}
    fold_results: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    per_template_folds: dict[str, list[dict[str, Any]]] = defaultdict(list)
    models_fit_count = 0

    for fold_number, fold in enumerate(folds, start=1):
        train_records = joined[fold["train_start"] : fold["train_end"] + 1]
        outer_records = joined[fold["outer_start"] : fold["outer_end"] + 1]
        dispersion_threshold = quantile(
            [float(item["raw_target"]["future_return_dispersion_bps"]) for item in train_records],
            0.95,
        )
        train_labels = [target_label(item["raw_target"], dispersion_threshold) for item in train_records]
        outer_labels = [target_label(item["raw_target"], dispersion_threshold) for item in outer_records]
        train_prevalence = sum(train_labels) / len(train_labels)
        vol_low = quantile([float(item["feature"]["realized_vol_24h"]) for item in train_records], 1 / 3)
        vol_high = quantile([float(item["feature"]["realized_vol_24h"]) for item in train_records], 2 / 3)

        fitted_models: dict[tuple[str, str], dict[str, Any]] = {}
        for feature_bundle, feature_names in FEATURE_BUNDLES.items():
            train_features = [item["feature"] for item in train_records]
            fitted_models[(feature_bundle, "THRESHOLD_RULE")] = fit_threshold_rule(
                train_features, train_labels, feature_names
            )
            fitted_models[(feature_bundle, "LOGISTIC_REGRESSION")] = fit_logistic_regression(
                train_features,
                train_labels,
                feature_names,
                iterations=logistic_iterations,
            )
            models_fit_count += 2

        fold_template_metrics: dict[str, Any] = {}
        for template in templates:
            template_id = str(template["template_id"])
            model = fitted_models[(str(template["feature_bundle"]), str(template["model_class"]))]
            probabilities = [predict_probability(model, item["feature"]) for item in outer_records]
            null_probabilities = [train_prevalence] * len(outer_labels)
            metrics = classification_metrics(outer_labels, probabilities, null_probabilities)
            fold_pass = (
                metrics["brier_skill"] > 0
                and metrics["pr_auc_improvement"] >= 0.02
                and metrics["expected_calibration_error"] <= 0.05
            )
            metrics["fold_pass"] = fold_pass
            metrics["operating_threshold"] = float(template["operating_threshold"])
            fold_template_metrics[template_id] = metrics
            per_template_folds[template_id].append(metrics)

            for item, label, probability in zip(outer_records, outer_labels, probabilities):
                feature = item["feature"]
                volatility = float(feature["realized_vol_24h"])
                regime = "LOW_VOL" if volatility <= vol_low else "HIGH_VOL" if volatility >= vol_high else "MID_VOL"
                missingness = "ZERO_MISSING" if float(feature["data_quality_risk_score"]) <= 0 else "MISSING_OR_STALE"
                prediction_rows.append(
                    {
                        "template_id": template_id,
                        "fold": fold_number,
                        "open_time_ms": item["timestamp"],
                        "label": label,
                        "probability": probability,
                        "train_prevalence": train_prevalence,
                        "operating_threshold": float(template["operating_threshold"]),
                        "provider_count": int(feature["provider_count"]),
                        "missingness_bucket": missingness,
                        "volatility_regime": regime,
                    }
                )

        fold_results.append(
            {
                "fold": fold_number,
                **fold,
                "training_dispersion_p95_bps": dispersion_threshold,
                "train_prevalence": train_prevalence,
                "train_rows": len(train_records),
                "outer_rows": len(outer_records),
                "outer_used_for_model_fit": False,
                "outer_used_for_threshold_selection": False,
                "template_metrics": fold_template_metrics,
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / "phase339_outer_predictions.csv.gz"
    write_csv_gz(predictions_path, prediction_rows, PREDICTION_FIELDS)
    template_summary = {
        template_id: {
            "fold_count": len(metrics),
            "fold_pass_count": sum(bool(item["fold_pass"]) for item in metrics),
            "mean_brier_skill": sum(float(item["brier_skill"]) for item in metrics) / len(metrics),
            "mean_pr_auc_improvement": sum(float(item["pr_auc_improvement"]) for item in metrics) / len(metrics),
            "mean_ece": sum(float(item["expected_calibration_error"]) for item in metrics) / len(metrics),
            "template": template_lookup[template_id],
        }
        for template_id, metrics in sorted(per_template_folds.items())
    }
    payload = base_payload(339, "NESTED_WALK_FORWARD_ABSTENTION_EVALUATED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE339_NESTED_WALK_FORWARD_ABSTENTION_READY_RESEARCH_ONLY",
            "row_count": len(joined),
            "fold_count": len(folds),
            "template_count": len(templates),
            "historical_experiments_executed": len(templates),
            "models_fit_count": models_fit_count,
            "nested_walk_forward": True,
            "outer_holdout_untouched_for_selection": True,
            "thresholds_fit_on_training_fold_only": True,
            "embargo_hours": folds[0]["embargo_hours"],
            "fold_results": fold_results,
            "template_summary": template_summary,
            "predictions_path": predictions_path.relative_to(ROOT).as_posix(),
            "predictions_sha256": sha256_file(predictions_path),
            "registry_budget_expanded_after_results": False,
            "directional_prediction_created": False,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    write_json(output_dir / "phase339_nested_walk_forward_abstention.json", payload)
    write_summary(
        ROOT / "docs/reports/abstention_v1/phase339_nested_walk_forward_abstention_summary.md",
        title="Phase 339 — Nested Walk-forward Abstention Evaluation",
        gate=payload["gate"],
        bullets=[
            f"Rows: `{len(joined)}`",
            f"Outer folds: `{len(folds)}`",
            f"Templates evaluated: `{len(templates)}`",
            "Outer holdout used for selection: `False`",
            "Thresholds fitted on training fold only: `True`",
            "Strategy approved: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    parser.add_argument("--phase336-artifact", type=Path, default=artifacts / "phase336_finite_registry_opening_research_only/phase336_finite_registry_opening.json")
    parser.add_argument("--phase337-artifact", type=Path, default=artifacts / "phase337_asof_quality_feature_matrix_research_only/phase337_asof_quality_feature_matrix.json")
    parser.add_argument("--phase338-artifact", type=Path, default=artifacts / "phase338_frozen_h8_target_builder_research_only/phase338_frozen_h8_target_builder.json")
    parser.add_argument("--output-dir", type=Path, default=artifacts / "phase339_nested_walk_forward_abstention_research_only")
    args = parser.parse_args()
    payload = build(args.phase336_artifact, args.phase337_artifact, args.phase338_artifact, args.output_dir)
    print(payload["gate"])
    print("Rows:", payload["row_count"])
    print("Folds:", payload["fold_count"])
    print("Templates:", payload["template_count"])
    print("Strategy approved:", payload["strategy_approved"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
