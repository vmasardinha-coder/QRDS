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
    sha256_file,
    validate_phase,
    write_json,
    write_summary,
)


def _resolve_recorded_path(root: Path, recorded: str) -> Path | None:
    if not recorded:
        return None
    raw = Path(recorded)
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        normalized = recorded.replace("\\", "/")
        candidates.append(root / Path(normalized))
        candidates.append(root.parent / Path(normalized))
        prefix = "crypto_decision_lab/"
        if normalized.lower().startswith(prefix):
            candidates.append(root / Path(normalized[len(prefix):]))
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_file():
            return resolved
    return candidates[0].resolve() if candidates else None


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
    root = (project_root or ROOT).resolve()

    executed = bool(p367.get("evaluation_executed"))
    manifest: list[dict[str, Any]] = []
    failed_checks: list[str] = []
    contract_expected = p363.get("contract_fingerprint")
    contract_actual = p367.get("contract_fingerprint")
    contract_match = bool(contract_expected) and contract_actual == contract_expected

    if not executed:
        audit_mode = "SKIPPED_NO_EVALUATION"
        skip_checks = {
            "explicit_manual_rejection": p367.get("skip_reason")
            == "MANUAL_EXECUTION_REVIEW_REJECTED",
            "contract_fingerprint_present_and_verified": contract_match,
            "input_lineage_is_explicit_empty_list": p367.get("input_lineage") == [],
            "provider_dataset_count_is_zero": int(p367.get("provider_dataset_count", -1)) == 0,
            "real_historical_rows_used_is_zero": int(p367.get("real_historical_rows_used", -1)) == 0,
            "budget_units_consumed_is_zero": int(p367.get("budget_units_consumed", -1)) == 0,
            "remediated_dataset_path_is_null": p367.get("remediated_dataset_path") is None,
            "remediated_dataset_sha256_is_null": p367.get("remediated_dataset_sha256") is None,
        }
        failed_checks = sorted(name for name, passed in skip_checks.items() if not passed)
        lineage_pass = not failed_checks
        input_count = 0
        all_input_verified: bool | None = None
        output_verified: bool | None = None
        input_audit_applicable = False
        output_audit_applicable = False
    else:
        audit_mode = "EXECUTED_LINEAGE_AND_HASH_AUDIT"
        input_items = list(p367.get("input_lineage", []))
        input_count = len(input_items)
        input_audit_applicable = True
        output_audit_applicable = True

        if input_count == 0:
            failed_checks.append("executed_evaluation_requires_nonempty_input_lineage")

        for item in input_items:
            recorded = str(item.get("path", ""))
            path = _resolve_recorded_path(root, recorded)
            exists = path is not None and path.is_file()
            actual_hash = sha256_file(path) if exists and path is not None else None
            expected_hash = str(item.get("sha256", ""))
            verified = bool(expected_hash) and exists and actual_hash == expected_hash
            if not verified:
                failed_checks.append(f"input_hash_or_path_failed:{item.get('provider')}")
            manifest.append(
                {
                    "role": "PHASE301_CANDLE_INPUT",
                    "provider": item.get("provider"),
                    "recorded_path": recorded,
                    "resolved_path": str(path) if path is not None else None,
                    "expected_sha256": expected_hash or None,
                    "actual_sha256": actual_hash,
                    "verified": verified,
                }
            )

        all_input_verified = bool(manifest) and all(item["verified"] for item in manifest)

        output_recorded = p367.get("remediated_dataset_path")
        output_path = _resolve_recorded_path(root, str(output_recorded or ""))
        output_exists = output_path is not None and output_path.is_file()
        output_actual = sha256_file(output_path) if output_exists and output_path is not None else None
        output_expected = p367.get("remediated_dataset_sha256")
        output_verified = bool(output_expected) and output_exists and output_actual == output_expected
        if not output_verified:
            failed_checks.append("remediated_output_hash_or_path_failed")
        manifest.append(
            {
                "role": "REMEDIATED_DATASET_OUTPUT",
                "recorded_path": output_recorded,
                "resolved_path": str(output_path) if output_path is not None else None,
                "expected_sha256": output_expected,
                "actual_sha256": output_actual,
                "verified": output_verified,
            }
        )
        if not contract_match:
            failed_checks.append("contract_fingerprint_mismatch")
        lineage_pass = not failed_checks

    payload = base_payload(
        371,
        "REMEDIATION_LINEAGE_AND_HASH_AUDIT_PASS_RESEARCH_ONLY"
        if lineage_pass
        else "REMEDIATION_LINEAGE_AND_HASH_AUDIT_FAIL_RESEARCH_ONLY",
    )
    payload.update(
        {
            "gate": "PHASE371_REMEDIATION_LINEAGE_AND_HASH_AUDIT_READY_RESEARCH_ONLY",
            "audit_mode": audit_mode,
            "evaluation_executed": executed,
            "lineage_manifest": manifest,
            "input_dataset_count": input_count,
            "input_hash_audit_applicable": input_audit_applicable,
            "all_input_hashes_verified": all_input_verified,
            "output_hash_audit_applicable": output_audit_applicable,
            "output_hash_verified": output_verified,
            "contract_fingerprint_verified": contract_match,
            "audit_checks": skip_checks if not executed else None,
            "failed_checks": failed_checks,
            "lineage_audit_pass": lineage_pass,
            "canonical_data_writes": 0,
            "closed_families_reopened": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase371_remediation_lineage_and_hash_audit.json", payload)
    write_summary(
        phase_summary(371, "remediation_lineage_and_hash_audit"),
        title="Phase 371 — Remediation Lineage and Hash Audit",
        gate=payload["gate"],
        bullets=[
            f"Audit mode: `{audit_mode}`",
            f"Lineage audit pass: `{lineage_pass}`",
            f"Input datasets: `{input_count}`",
            f"Input hash audit applicable: `{input_audit_applicable}`",
            f"Output hash audit applicable: `{output_audit_applicable}`",
            f"Contract fingerprint verified: `{contract_match}`",
            f"Failed checks: `{failed_checks}`",
            "Canonical data writes: `0`",
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
        default=art / "phase371_remediation_lineage_and_hash_audit_research_only",
    )
    args = parser.parse_args()
    payload = build(args.phase301_artifact, args.phase363_artifact, args.phase367_artifact, args.output_dir)
    print(payload["gate"])
    print("Audit mode:", payload["audit_mode"])
    print("Lineage audit pass:", payload["lineage_audit_pass"])
    print("Failed checks:", payload["failed_checks"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
