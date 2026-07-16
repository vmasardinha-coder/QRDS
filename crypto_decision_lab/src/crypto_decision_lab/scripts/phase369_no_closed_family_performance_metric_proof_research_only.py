from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase366_375_remediation_evaluation_common import (
    FORBIDDEN_CLOSED_FAMILY_METRIC_NAMES,
    QUALITY_METRIC_NAMES,
    ROOT,
    base_payload,
    fingerprint,
    phase_summary,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def build(phase367_path: Path, phase368_path: Path, output_dir: Path) -> dict[str, Any]:
    p367 = read_json(phase367_path)
    p368 = read_json(phase368_path)
    validate_phase(p367, 367)
    validate_phase(p368, 368)

    executed = bool(p367.get("evaluation_executed"))
    declared = [str(value).upper() for value in p367.get("quality_metric_names", [])]
    actual_metric_names = [str(value).upper() for value in dict(p367.get("metrics", {})).keys()]
    allowed = set(QUALITY_METRIC_NAMES)
    inspected_metric_names = sorted(set(declared) | set(actual_metric_names))
    forbidden_hits = sorted(
        metric
        for metric in inspected_metric_names
        if any(token in metric for token in FORBIDDEN_CLOSED_FAMILY_METRIC_NAMES)
    )
    unknown_metric_names = sorted(set(inspected_metric_names) - allowed)
    missing_declared_metric_names = sorted(allowed - set(declared)) if executed else []
    missing_actual_metric_names = sorted(allowed - set(actual_metric_names)) if executed else []
    input_phase_allowlist = [301, 363, 365, 366, 367, 368]

    common_checks = {
        "forbidden_metric_hits_are_empty": not forbidden_hits,
        "unknown_metric_names_are_empty": not unknown_metric_names,
        "closed_family_artifact_read_count_is_zero": int(p367.get("closed_family_artifact_read_count", -1)) == 0,
        "closed_family_performance_metric_read_count_is_zero": int(p367.get("closed_family_performance_metric_read_count", -1)) == 0,
        "strategy_or_return_metric_evaluated_is_false": p367.get("strategy_or_return_metric_evaluated") is False,
        "strategy_performance_compared_is_false": p368.get("strategy_performance_compared") is False,
        "closed_family_result_changed_is_false": p368.get("closed_family_result_changed") is False,
    }
    if executed:
        mode_checks = {
            "declared_quality_metric_names_match_frozen_allowlist": set(declared) == allowed,
            "actual_metric_names_match_frozen_allowlist": set(actual_metric_names) == allowed,
            "declared_and_actual_metric_names_match": set(declared) == set(actual_metric_names),
            "real_historical_rows_used_is_positive": int(p367.get("real_historical_rows_used", 0)) > 0,
            "budget_units_consumed_is_one": int(p367.get("budget_units_consumed", -1)) == 1,
        }
        proof_mode = "EXECUTED_QUALITY_ONLY_EVALUATION"
    else:
        mode_checks = {
            "declared_quality_metric_names_are_empty_when_skipped": declared == [],
            "actual_metric_names_are_empty_when_skipped": actual_metric_names == [],
            "real_historical_rows_used_is_zero_when_skipped": int(p367.get("real_historical_rows_used", -1)) == 0,
            "budget_units_consumed_is_zero_when_skipped": int(p367.get("budget_units_consumed", -1)) == 0,
        }
        proof_mode = "SKIPPED_NO_EVALUATION"

    proof_checks = {**common_checks, **mode_checks}
    failed_checks = sorted(name for name, value in proof_checks.items() if not value)
    passed = not failed_checks

    payload = base_payload(
        369,
        "NO_CLOSED_FAMILY_PERFORMANCE_METRIC_PROOF_PASS_RESEARCH_ONLY"
        if passed
        else "NO_CLOSED_FAMILY_PERFORMANCE_METRIC_PROOF_FAIL_RESEARCH_ONLY",
    )
    payload.update(
        {
            "gate": "PHASE369_NO_CLOSED_FAMILY_PERFORMANCE_METRIC_PROOF_READY_RESEARCH_ONLY",
            "input_phase_allowlist": input_phase_allowlist,
            "evaluation_executed": executed,
            "proof_mode": proof_mode,
            "declared_quality_metric_names": declared,
            "actual_metric_names": actual_metric_names,
            "forbidden_metric_hits": forbidden_hits,
            "unknown_metric_names": unknown_metric_names,
            "missing_declared_metric_names": missing_declared_metric_names,
            "missing_actual_metric_names": missing_actual_metric_names,
            "proof_checks": proof_checks,
            "failed_checks": failed_checks,
            "proof_pass": passed,
            "closed_family_performance_metric_used": False if passed else None,
            "closed_family_retest_performed": False,
            "strategy_signal_generated": False,
            "capital_authorized_brl": 0,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase369_no_closed_family_performance_metric_proof.json", payload)
    write_summary(
        phase_summary(369, "no_closed_family_performance_metric_proof"),
        title="Phase 369 — No Closed-family Performance Metric Proof",
        gate=payload["gate"],
        bullets=[
            f"Proof pass: `{passed}`",
            f"Proof mode: `{proof_mode}`",
            f"Failed checks: `{len(failed_checks)}`",
            f"Forbidden metric hits: `{len(forbidden_hits)}`",
            f"Unknown metric names: `{len(unknown_metric_names)}`",
            "Closed-family retest performed: `False`",
            "Strategy signal generated: `False`",
            "Capital authorized: `R$ 0`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    art = ROOT / "artifacts"
    parser.add_argument(
        "--phase367-artifact",
        type=Path,
        default=art
        / "phase367_one_real_data_remediation_evaluation_research_only"
        / "phase367_one_real_data_remediation_evaluation.json",
    )
    parser.add_argument(
        "--phase368-artifact",
        type=Path,
        default=art
        / "phase368_raw_vs_remediated_data_quality_comparison_research_only"
        / "phase368_raw_vs_remediated_data_quality_comparison.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=art / "phase369_no_closed_family_performance_metric_proof_research_only",
    )
    args = parser.parse_args()
    payload = build(args.phase367_artifact, args.phase368_artifact, args.output_dir)
    print(payload["gate"])
    print("Proof pass:", payload["proof_pass"])
    print("Proof mode:", payload["proof_mode"])
    print("Failed checks:", payload["failed_checks"])
    print("Forbidden metric hits:", len(payload["forbidden_metric_hits"]))
    print("Unknown metric names:", len(payload["unknown_metric_names"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
