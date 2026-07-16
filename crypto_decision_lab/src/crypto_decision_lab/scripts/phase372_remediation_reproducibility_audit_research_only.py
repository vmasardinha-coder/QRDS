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
from crypto_decision_lab.scripts.phase367_one_real_data_remediation_evaluation_research_only import (
    evaluate_existing_data,
)


def build(
    phase301_path: Path,
    phase363_path: Path,
    phase367_path: Path,
    output_dir: Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    p301 = read_json(phase301_path)
    p363 = read_json(phase363_path)
    p367 = read_json(phase367_path)
    validate_phase(p301, 301)
    validate_phase(p363, 363)
    validate_phase(p367, 367)

    executed = bool(p367.get("evaluation_executed"))
    failed_checks: list[str] = []

    if not executed:
        audit_mode = "SKIPPED_NO_EVALUATION"
        consistency_checks = {
            "explicit_manual_rejection": p367.get("skip_reason")
            == "MANUAL_EXECUTION_REVIEW_REJECTED",
            "budget_units_consumed_is_zero": int(p367.get("budget_units_consumed", -1)) == 0,
            "real_historical_rows_used_is_zero": int(p367.get("real_historical_rows_used", -1)) == 0,
            "metrics_are_empty": p367.get("metrics") == {},
            "input_lineage_is_empty": p367.get("input_lineage") == [],
            "remediated_dataset_path_is_null": p367.get("remediated_dataset_path") is None,
            "remediated_dataset_sha256_is_null": p367.get("remediated_dataset_sha256") is None,
        }
        failed_checks = sorted(name for name, value in consistency_checks.items() if not value)
        reproducible = not failed_checks
        replay = {
            "evaluation_id": None,
            "remediated_rows_fingerprint": None,
            "metrics": {},
        }
        metrics_match: bool | None = None
        reason = (
            "MANUAL_REJECTION_REPRODUCIBLY_PRESERVED"
            if reproducible
            else "SKIPPED_STATE_INCONSISTENT"
        )
        applicable = False
    else:
        audit_mode = "EXECUTED_SAME_INPUT_REPLAY"
        replay = evaluate_existing_data(
            p301,
            dict(p363.get("contract", {})),
            project_root=(project_root or ROOT).resolve(),
        )
        metrics_match = fingerprint(replay["metrics"]) == fingerprint(p367.get("metrics", {}))
        checks = {
            "evaluation_id_match": replay["evaluation_id"] == p367.get("evaluation_id"),
            "rows_fingerprint_match": replay["remediated_rows_fingerprint"]
            == p367.get("remediated_rows_fingerprint"),
            "metrics_fingerprint_match": metrics_match,
        }
        failed_checks = sorted(name for name, value in checks.items() if not value)
        reproducible = not failed_checks
        reason = "SAME_INPUTS_SAME_RESULT" if reproducible else "REPRODUCIBILITY_MISMATCH"
        consistency_checks = checks
        applicable = True

    payload = base_payload(
        372,
        "REMEDIATION_REPRODUCIBILITY_AUDIT_PASS_RESEARCH_ONLY"
        if reproducible
        else "REMEDIATION_REPRODUCIBILITY_AUDIT_FAIL_RESEARCH_ONLY",
    )
    payload.update(
        {
            "gate": "PHASE372_REMEDIATION_REPRODUCIBILITY_AUDIT_READY_RESEARCH_ONLY",
            "audit_mode": audit_mode,
            "replay_applicable": applicable,
            "evaluation_executed": executed,
            "original_evaluation_id": p367.get("evaluation_id"),
            "replayed_evaluation_id": replay.get("evaluation_id"),
            "original_rows_fingerprint": p367.get("remediated_rows_fingerprint"),
            "replayed_rows_fingerprint": replay.get("remediated_rows_fingerprint"),
            "metrics_fingerprint_match": metrics_match,
            "audit_checks": consistency_checks,
            "failed_checks": failed_checks,
            "reproducibility_pass": reproducible,
            "reason": reason,
            "network_calls": 0,
            "new_experiment_budget_consumed": 0,
            "same_input_replay_counts_as_new_experiment": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase372_remediation_reproducibility_audit.json", payload)
    write_summary(
        phase_summary(372, "remediation_reproducibility_audit"),
        title="Phase 372 — Remediation Reproducibility Audit",
        gate=payload["gate"],
        bullets=[
            f"Audit mode: `{audit_mode}`",
            f"Reproducibility pass: `{reproducible}`",
            f"Reason: `{reason}`",
            f"Failed checks: `{failed_checks}`",
            "Network calls: `0`",
            "New experiment budget consumed: `0`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    art = ROOT / "artifacts"
    parser.add_argument(
        "--phase301-artifact",
        type=Path,
        default=art
        / "phase301_official_public_history_extension_research_only"
        / "phase301_official_public_history_extension.json",
    )
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
        default=art / "phase372_remediation_reproducibility_audit_research_only",
    )
    args = parser.parse_args()
    payload = build(args.phase301_artifact, args.phase363_artifact, args.phase367_artifact, args.output_dir)
    print(payload["gate"])
    print("Audit mode:", payload["audit_mode"])
    print("Reproducibility pass:", payload["reproducibility_pass"])
    print("Failed checks:", payload["failed_checks"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
