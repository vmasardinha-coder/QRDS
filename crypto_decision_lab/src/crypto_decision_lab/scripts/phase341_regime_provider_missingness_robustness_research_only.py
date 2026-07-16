from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase336_345_abstention_evaluation_common import (
    ROOT,
    base_payload,
    classification_metrics,
    fingerprint,
    read_csv_gz,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def _group_metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    labels = [int(row["label"]) for row in rows]
    probabilities = [float(row["probability"]) for row in rows]
    null_probabilities = [float(row["train_prevalence"]) for row in rows]
    return classification_metrics(labels, probabilities, null_probabilities)


def build(phase339_path: Path, phase340_path: Path, output_dir: Path, *, minimum_stratum_rows: int = 200) -> dict[str, Any]:
    phase339 = read_json(phase339_path)
    phase340 = read_json(phase340_path)
    validate_phase(phase339, 339)
    validate_phase(phase340, 340)
    rows = read_csv_gz(ROOT / phase339["predictions_path"])
    diagnostic_ids = list(phase340.get("survivor_ids", []))
    if not diagnostic_ids and phase340.get("top_diagnostic_template_id"):
        diagnostic_ids = [str(phase340["top_diagnostic_template_id"])]

    audits: dict[str, Any] = {}
    robust_ids: list[str] = []
    for template_id in diagnostic_ids:
        selected = [row for row in rows if row["template_id"] == template_id]
        strata: dict[str, list[dict[str, str]]] = {}
        for row in selected:
            keys = (
                f"REGIME:{row['volatility_regime']}",
                f"PROVIDERS:{row['provider_count']}",
                f"MISSINGNESS:{row['missingness_bucket']}",
            )
            for key in keys:
                strata.setdefault(key, []).append(row)
        stratum_metrics: dict[str, Any] = {}
        eligible_count = 0
        positive_count = 0
        for key, group in sorted(strata.items()):
            metrics = _group_metrics(group)
            eligible = metrics["sample_count"] >= minimum_stratum_rows
            positive = eligible and metrics["brier_skill"] > 0
            metrics["eligible_for_gate"] = eligible
            metrics["positive_brier_skill"] = positive
            stratum_metrics[key] = metrics
            eligible_count += int(eligible)
            positive_count += int(positive)
        phase340_survivor = template_id in phase340.get("survivor_ids", [])
        robustness_pass = phase340_survivor and eligible_count >= 5 and positive_count == eligible_count
        audits[template_id] = {
            "phase340_survivor": phase340_survivor,
            "eligible_stratum_count": eligible_count,
            "positive_stratum_count": positive_count,
            "strata": stratum_metrics,
            "robustness_pass": robustness_pass,
        }
        if robustness_pass:
            robust_ids.append(template_id)

    payload = base_payload(341, "REGIME_PROVIDER_MISSINGNESS_ROBUSTNESS_AUDITED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE341_REGIME_PROVIDER_MISSINGNESS_ROBUSTNESS_READY_RESEARCH_ONLY",
            "diagnostic_template_ids": diagnostic_ids,
            "minimum_stratum_rows": minimum_stratum_rows,
            "template_audits": audits,
            "robust_template_ids": robust_ids,
            "robust_template_count": len(robust_ids),
            "result_used_to_change_templates": False,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase341_regime_provider_missingness_robustness.json", payload)
    write_summary(
        ROOT / "docs/reports/abstention_v1/phase341_regime_provider_missingness_robustness_summary.md",
        title="Phase 341 — Regime, Provider-count and Missingness Robustness",
        gate=payload["gate"],
        bullets=[
            f"Diagnostic templates: `{len(diagnostic_ids)}`",
            f"Robust templates: `{len(robust_ids)}`",
            f"Minimum rows per stratum: `{minimum_stratum_rows}`",
            "Templates changed after results: `False`",
            "Strategy approved: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    parser.add_argument("--phase339-artifact", type=Path, default=artifacts / "phase339_nested_walk_forward_abstention_research_only/phase339_nested_walk_forward_abstention.json")
    parser.add_argument("--phase340-artifact", type=Path, default=artifacts / "phase340_holm_calibration_null_comparison_research_only/phase340_holm_calibration_null_comparison.json")
    parser.add_argument("--output-dir", type=Path, default=artifacts / "phase341_regime_provider_missingness_robustness_research_only")
    args = parser.parse_args()
    payload = build(args.phase339_artifact, args.phase340_artifact, args.output_dir)
    print(payload["gate"])
    print("Robust templates:", payload["robust_template_count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
