from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase366_375_remediation_evaluation_common import (
    ROOT,
    base_payload,
    fingerprint,
    phase_summary,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def build(phase363_path: Path, phase367_path: Path, output_dir: Path) -> dict[str, Any]:
    p363 = read_json(phase363_path)
    p367 = read_json(phase367_path)
    validate_phase(p363, 363)
    validate_phase(p367, 367)

    executed = bool(p367.get("evaluation_executed"))
    criteria = dict(p363.get("contract", {}).get("success_criteria", {}))
    metrics = dict(p367.get("metrics", {}))

    if executed:
        checks: dict[str, bool | None] = {
            "minimum_provider_count": int(p367.get("minimum_provider_count", 0))
            >= int(criteria.get("minimum_provider_count", 3)),
            "no_forward_shift": int(p367.get("forward_shift_count", -1)) == 0,
            "no_interpolation": int(p367.get("interpolation_count", -1)) == 0,
            "valid_hour_ratio_not_lower_than_baseline": (
                float(metrics.get("REMEDIATED_VALID_HOUR_RATIO", 0.0))
                >= float(metrics.get("RAW_VALID_HOUR_RATIO", 0.0))
            ),
            "timestamp_mismatch_count_must_decrease": (
                int(metrics.get("REMEDIATED_TIMESTAMP_ALIGNMENT_DEFECT_COUNT", 0))
                < int(metrics.get("RAW_TIMESTAMP_ALIGNMENT_DEFECT_COUNT", 0))
            ),
        }
        passed = all(value is True for value in checks.values())
        mode = "EXECUTED_RAW_VS_REMEDIATED_COMPARISON"
        no_go_preserved = False
        raw_metrics = {
            "valid_hour_ratio": metrics.get("RAW_VALID_HOUR_RATIO", 0.0),
            "timestamp_alignment_defect_count": metrics.get(
                "RAW_TIMESTAMP_ALIGNMENT_DEFECT_COUNT", 0
            ),
            "spread_p95_bps": metrics.get("RAW_STRICT_SPREAD_P95_BPS", 0.0),
        }
        remediated_metrics = {
            "valid_hour_ratio": metrics.get("REMEDIATED_VALID_HOUR_RATIO", 0.0),
            "timestamp_alignment_defect_count": metrics.get(
                "REMEDIATED_TIMESTAMP_ALIGNMENT_DEFECT_COUNT", 0
            ),
            "spread_p95_bps": metrics.get("REMEDIATED_SPREAD_P95_BPS", 0.0),
        }
    else:
        skip_consistent = (
            p367.get("skip_reason") == "MANUAL_EXECUTION_REVIEW_REJECTED"
            and int(p367.get("budget_units_consumed", -1)) == 0
            and int(p367.get("real_historical_rows_used", -1)) == 0
            and p367.get("remediated_dataset_path") is None
            and p367.get("remediated_dataset_sha256") is None
        )
        checks = {name: None for name in (
            "minimum_provider_count",
            "no_forward_shift",
            "no_interpolation",
            "valid_hour_ratio_not_lower_than_baseline",
            "timestamp_mismatch_count_must_decrease",
        )}
        passed = False
        mode = "SKIPPED_NO_COMPARISON_BY_MANUAL_REJECTION"
        no_go_preserved = skip_consistent
        raw_metrics = {}
        remediated_metrics = {}

    payload = base_payload(
        368,
        "RAW_VS_REMEDIATED_DATA_QUALITY_COMPARISON_PASS_RESEARCH_ONLY"
        if passed
        else (
            "RAW_VS_REMEDIATED_DATA_QUALITY_COMPARISON_SKIPPED_RESEARCH_ONLY"
            if not executed and no_go_preserved
            else "RAW_VS_REMEDIATED_DATA_QUALITY_COMPARISON_NO_PASS_RESEARCH_ONLY"
        ),
    )
    payload.update(
        {
            "gate": "PHASE368_RAW_VS_REMEDIATED_DATA_QUALITY_COMPARISON_READY_RESEARCH_ONLY",
            "comparison_mode": mode,
            "comparison_applicable": executed,
            "evaluation_executed": executed,
            "frozen_success_criteria": criteria,
            "criteria_checks": checks,
            "criteria_pass_count": sum(value is True for value in checks.values()),
            "criteria_total_count": len(checks),
            "data_quality_contract_pass": passed,
            "manual_rejection_no_go_preserved": no_go_preserved,
            "raw_metrics": raw_metrics,
            "remediated_metrics": remediated_metrics,
            "strategy_performance_compared": False,
            "closed_family_result_changed": False,
            "capital_authorized_brl": 0,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase368_raw_vs_remediated_data_quality_comparison.json", payload)
    write_summary(
        phase_summary(368, "raw_vs_remediated_data_quality_comparison"),
        title="Phase 368 — Raw versus Remediated Data-quality Comparison",
        gate=payload["gate"],
        bullets=[
            f"Comparison mode: `{mode}`",
            f"Contract pass: `{passed}`",
            f"Manual rejection no-go preserved: `{no_go_preserved}`",
            f"Criteria passed: `{payload['criteria_pass_count']}/{payload['criteria_total_count']}`",
            "Strategy performance compared: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    art = ROOT / "artifacts"
    parser.add_argument(
        "--phase363-artifact",
        type=Path,
        default=art
        / "phase363_future_real_data_remediation_contract_freeze_research_only"
        / "phase363_future_real_data_remediation_contract_freeze.json",
    )
    parser.add_argument(
        "--phase367-artifact",
        type=Path,
        default=art
        / "phase367_one_real_data_remediation_evaluation_research_only"
        / "phase367_one_real_data_remediation_evaluation.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=art / "phase368_raw_vs_remediated_data_quality_comparison_research_only",
    )
    args = parser.parse_args()
    payload = build(args.phase363_artifact, args.phase367_artifact, args.output_dir)
    print(payload["gate"])
    print("Comparison mode:", payload["comparison_mode"])
    print("Data-quality contract pass:", payload["data_quality_contract_pass"])
    print("Manual rejection no-go preserved:", payload["manual_rejection_no_go_preserved"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
