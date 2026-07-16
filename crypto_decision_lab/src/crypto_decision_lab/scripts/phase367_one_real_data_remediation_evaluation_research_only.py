from __future__ import annotations

import argparse
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase366_375_remediation_evaluation_common import (
    QUALITY_METRIC_NAMES,
    ROOT,
    base_payload,
    fingerprint,
    iso_from_ms,
    percentile,
    phase_summary,
    read_csv_gz,
    read_json,
    sha256_file,
    validate_phase,
    write_deterministic_csv_gz,
    write_json,
    write_summary,
)

HOUR_MS = 60 * 60 * 1000
OUTPUT_FIELDS = (
    "open_time_ms",
    "open_time_utc",
    "provider_count",
    "providers",
    "consensus_close",
    "spread_bps",
)


def _load_candle_maps(phase301: dict[str, Any], project_root: Path) -> tuple[dict[str, dict[int, float]], list[dict[str, Any]], int]:
    datasets = phase301.get("datasets", {})
    maps: dict[str, dict[int, float]] = {}
    lineage: list[dict[str, Any]] = []
    total_rows = 0

    for dataset_name, info in sorted(datasets.items()):
        if not str(dataset_name).endswith("_candles"):
            continue
        relative = str(info.get("path", ""))
        path = (project_root / relative).resolve()
        if not path.is_file():
            raise RuntimeError(f"Phase 301 candle dataset is missing: {path}")
        recorded_hash = str(info.get("sha256", ""))
        actual_hash = sha256_file(path)
        if recorded_hash and actual_hash.lower() != recorded_hash.lower():
            raise RuntimeError(f"Phase 301 candle dataset hash mismatch: {dataset_name}")

        rows = read_csv_gz(path)
        provider_map: dict[int, float] = {}
        provider_name: str | None = None
        duplicates = 0
        non_hourly = 0
        for row in rows:
            if str(row.get("complete", "True")).strip().lower() in {"false", "0", "no"}:
                continue
            ts = int(row["open_time_ms"])
            if ts % HOUR_MS != 0:
                non_hourly += 1
                continue
            close = float(row["close"])
            provider = str(row.get("provider") or dataset_name.replace("_candles", "").upper())
            provider_name = provider_name or provider
            if ts in provider_map:
                duplicates += 1
                continue
            provider_map[ts] = close

        if not provider_map:
            continue
        provider_key = provider_name or dataset_name.replace("_candles", "").upper()
        maps[provider_key] = provider_map
        total_rows += len(provider_map)
        lineage.append(
            {
                "dataset_name": dataset_name,
                "provider": provider_key,
                "path": relative,
                "sha256": actual_hash,
                "recorded_rows": int(info.get("rows", len(rows))),
                "usable_exact_hour_rows": len(provider_map),
                "duplicate_timestamp_count": duplicates,
                "non_exact_hour_row_count": non_hourly,
            }
        )

    if len(maps) < 3:
        raise RuntimeError(f"At least three candle providers are required; found {len(maps)}.")
    return maps, lineage, total_rows


def evaluate_existing_data(
    phase301: dict[str, Any],
    contract: dict[str, Any],
    *,
    project_root: Path,
) -> dict[str, Any]:
    provider_maps, lineage, total_input_rows = _load_candle_maps(phase301, project_root)
    providers = sorted(provider_maps)
    required_all = len(providers)
    minimum_provider_count = int(contract.get("success_criteria", {}).get("minimum_provider_count", 3))
    if minimum_provider_count < 3:
        raise RuntimeError("Frozen minimum provider count is below three.")
    if contract.get("success_criteria", {}).get("no_forward_shift") is not True:
        raise RuntimeError("Frozen contract does not prohibit forward shift.")
    if contract.get("success_criteria", {}).get("no_interpolation") is not True:
        raise RuntimeError("Frozen contract does not prohibit interpolation.")

    union_hours = sorted(set().union(*(set(values) for values in provider_maps.values())))
    strict_all_provider_hours = 0
    valid_consensus_hours = 0
    raw_strict_spreads: list[float] = []
    remediated_spreads: list[float] = []
    provider_count_distribution: Counter[int] = Counter()
    output_rows: list[dict[str, Any]] = []

    for timestamp_ms in union_hours:
        values = [(provider, provider_maps[provider][timestamp_ms]) for provider in providers if timestamp_ms in provider_maps[provider]]
        provider_count = len(values)
        provider_count_distribution[provider_count] += 1
        prices = [value for _, value in values]
        median_price = float(statistics.median(prices)) if prices else 0.0
        spread_bps = ((max(prices) - min(prices)) / median_price * 10000.0) if len(prices) >= 2 and median_price else 0.0

        if provider_count == required_all:
            strict_all_provider_hours += 1
            raw_strict_spreads.append(spread_bps)

        if provider_count >= minimum_provider_count:
            valid_consensus_hours += 1
            remediated_spreads.append(spread_bps)
            output_rows.append(
                {
                    "open_time_ms": timestamp_ms,
                    "open_time_utc": iso_from_ms(timestamp_ms),
                    "provider_count": provider_count,
                    "providers": "|".join(provider for provider, _ in values),
                    "consensus_close": f"{median_price:.12f}",
                    "spread_bps": f"{spread_bps:.8f}",
                }
            )

    total_union_hours = len(union_hours)
    raw_ratio = strict_all_provider_hours / total_union_hours if total_union_hours else 0.0
    remediated_ratio = valid_consensus_hours / total_union_hours if total_union_hours else 0.0
    raw_defects = total_union_hours - strict_all_provider_hours
    remediated_defects = total_union_hours - valid_consensus_hours

    metrics = {
        "TOTAL_UNION_HOURS": total_union_hours,
        "STRICT_ALL_PROVIDER_HOURS": strict_all_provider_hours,
        "VALID_CONSENSUS_HOURS": valid_consensus_hours,
        "RAW_VALID_HOUR_RATIO": raw_ratio,
        "REMEDIATED_VALID_HOUR_RATIO": remediated_ratio,
        "RAW_TIMESTAMP_ALIGNMENT_DEFECT_COUNT": raw_defects,
        "REMEDIATED_TIMESTAMP_ALIGNMENT_DEFECT_COUNT": remediated_defects,
        "PROVIDER_COUNT_DISTRIBUTION": {str(key): value for key, value in sorted(provider_count_distribution.items())},
        "RAW_STRICT_SPREAD_P95_BPS": percentile(raw_strict_spreads, 0.95),
        "REMEDIATED_SPREAD_P95_BPS": percentile(remediated_spreads, 0.95),
    }
    rows_fingerprint = fingerprint(output_rows)
    evaluation_id = fingerprint(
        {
            "selected_remediation_id": contract.get("selected_remediation_id"),
            "preregistration_fingerprint": contract.get("preregistration_fingerprint"),
            "contract_success_criteria": contract.get("success_criteria"),
            "input_hashes": [item["sha256"] for item in lineage],
            "implementation_version": "TIMESTAMP_CONSENSUS_ALIGNMENT_V1",
        }
    )
    return {
        "providers": providers,
        "provider_dataset_count": len(providers),
        "input_lineage": lineage,
        "real_historical_rows_used": total_input_rows,
        "quality_metric_names": list(QUALITY_METRIC_NAMES),
        "metrics": metrics,
        "remediated_rows": output_rows,
        "remediated_rows_fingerprint": rows_fingerprint,
        "evaluation_id": evaluation_id,
        "minimum_provider_count": minimum_provider_count,
        "forward_shift_count": 0,
        "interpolation_count": 0,
        "closed_family_artifact_read_count": 0,
        "closed_family_performance_metric_read_count": 0,
    }


def build(
    phase301_path: Path,
    phase363_path: Path,
    phase366_path: Path,
    output_dir: Path,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    p301 = read_json(phase301_path)
    p363 = read_json(phase363_path)
    p366 = read_json(phase366_path)
    validate_phase(p301, 301)
    validate_phase(p363, 363)
    validate_phase(p366, 366)

    approved = bool(p366.get("one_real_data_quality_evaluation_approved"))
    output_dir.mkdir(parents=True, exist_ok=True)
    if not approved:
        contract = dict(p363.get("contract", {}))
        decision_rejected = (
            p366.get("selected_decision") == "REJECT_REAL_DATA_REMEDIATION_EVALUATION"
            and p366.get("one_real_data_quality_evaluation_approved") is False
        )
        if not decision_rejected:
            raise RuntimeError(
                "Phase 367 cannot skip unless Phase 366 explicitly rejected the evaluation."
            )
        payload = base_payload(367, "REAL_DATA_REMEDIATION_EVALUATION_SKIPPED_RESEARCH_ONLY")
        payload.update(
            {
                "gate": "PHASE367_ONE_REAL_DATA_REMEDIATION_EVALUATION_READY_RESEARCH_ONLY",
                "evaluation_mode": "SKIPPED_BY_EXPLICIT_MANUAL_REJECTION",
                "evaluation_executed": False,
                "skip_reason": "MANUAL_EXECUTION_REVIEW_REJECTED",
                "selected_remediation_id": contract.get("selected_remediation_id"),
                "contract_fingerprint": p363.get("contract_fingerprint"),
                "evaluation_id": None,
                "evaluation_reexecution_same_inputs_is_same_budget_unit": True,
                "budget_units_consumed": 0,
                "future_experiment_budget": int(contract.get("future_experiment_budget", 0)),
                "providers": [],
                "provider_dataset_count": 0,
                "input_lineage": [],
                "real_historical_rows_used": 0,
                "quality_metric_names": [],
                "metrics": {},
                "remediated_rows_fingerprint": None,
                "remediated_dataset_path": None,
                "remediated_dataset_sha256": None,
                "minimum_provider_count": int(
                    contract.get("success_criteria", {}).get("minimum_provider_count", 3)
                ),
                "forward_shift_count": 0,
                "interpolation_count": 0,
                "closed_family_artifact_read_count": 0,
                "closed_family_performance_metric_read_count": 0,
                "strategy_or_return_metric_evaluated": False,
                "public_collection_started": False,
                "closed_families_reopened": False,
                "skipped_schema_complete": True,
            }
        )
    else:
        contract = dict(p363.get("contract", {}))
        if p366.get("contract_fingerprint") != p363.get("contract_fingerprint"):
            raise RuntimeError("Phase 366 did not review the exact frozen contract.")
        result = evaluate_existing_data(p301, contract, project_root=(project_root or ROOT).resolve())
        csv_path = output_dir / "phase367_timestamp_consensus_remediated.csv.gz"
        write_deterministic_csv_gz(csv_path, result.pop("remediated_rows"), OUTPUT_FIELDS)
        payload = base_payload(367, "ONE_REAL_DATA_REMEDIATION_EVALUATION_COMPLETE_RESEARCH_ONLY")
        payload.update(
            {
                "gate": "PHASE367_ONE_REAL_DATA_REMEDIATION_EVALUATION_READY_RESEARCH_ONLY",
                "evaluation_executed": True,
                "selected_remediation_id": contract.get("selected_remediation_id"),
                "contract_fingerprint": p363.get("contract_fingerprint"),
                "evaluation_id": result["evaluation_id"],
                "evaluation_reexecution_same_inputs_is_same_budget_unit": True,
                "budget_units_consumed": 1,
                "future_experiment_budget": int(contract.get("future_experiment_budget", 0)),
                **result,
                "remediated_dataset_path": str(csv_path),
                "remediated_dataset_sha256": sha256_file(csv_path),
                "public_collection_started": False,
                "closed_families_reopened": False,
                "strategy_or_return_metric_evaluated": False,
            }
        )

    payload["artifact_fingerprint"] = fingerprint(payload)
    write_json(output_dir / "phase367_one_real_data_remediation_evaluation.json", payload)
    metrics = payload.get("metrics", {})
    write_summary(
        phase_summary(367, "one_real_data_remediation_evaluation"),
        title="Phase 367 — One Real-data Remediation Evaluation",
        gate=payload["gate"],
        bullets=[
            f"Evaluation executed: `{payload['evaluation_executed']}`",
            f"Real historical rows used: `{payload.get('real_historical_rows_used', 0)}`",
            f"Raw valid-hour ratio: `{float(metrics.get('RAW_VALID_HOUR_RATIO', 0.0)):.6f}`",
            f"Remediated valid-hour ratio: `{float(metrics.get('REMEDIATED_VALID_HOUR_RATIO', 0.0)):.6f}`",
            "Strategy or return metric evaluated: `False`",
            "Public collection started: `False`",
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
        "--phase366-artifact",
        type=Path,
        default=art
        / "phase366_manual_frozen_remediation_execution_review_research_only"
        / "phase366_manual_frozen_remediation_execution_review.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=art / "phase367_one_real_data_remediation_evaluation_research_only",
    )
    args = parser.parse_args()
    payload = build(args.phase301_artifact, args.phase363_artifact, args.phase366_artifact, args.output_dir)
    print(payload["gate"])
    print("Evaluation executed:", payload["evaluation_executed"])
    print("Budget units consumed:", payload.get("budget_units_consumed", 0))
    print("Strategy or return metric evaluated:", payload.get("strategy_or_return_metric_evaluated", False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
