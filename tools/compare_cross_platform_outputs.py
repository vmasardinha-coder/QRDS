#!/usr/bin/env python3
"""Fail-closed semantic parity comparison across Linux and Windows.

Byte-for-byte comparators remain authoritative for same-platform deterministic
replays. This comparator is narrower: it admits only line-ending differences
and floating-point text deltas at <= 1e-12 while requiring identical schemas,
row order, strings, safety locks, inputs, and close dates.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

RTOL = 1e-12
ATOL = 1e-12

V2A_OUTPUT_MEMBERS = (
    "data/processed/qos_v2a_master_daily.csv",
    "data/processed/qos_v2a_monthly_features.csv",
    "data/processed/qos_v2a_current_features.csv",
    "outputs/data_quality_summary.csv",
    "outputs/download_failures_v2a.csv",
    "outputs/qos_v2a_bear_replay.csv",
    "outputs/qos_v2a_buy_sell_log.csv",
    "outputs/qos_v2a_current_portfolios.csv",
    "outputs/qos_v2a_current_ranking_top50.csv",
    "outputs/qos_v2a_equity_curves.csv",
    "outputs/qos_v2a_monte_carlo_10000_summary.csv",
    "outputs/qos_v2a_monthly_allocations.csv",
    "outputs/qos_v2a_reference_compositions.csv",
    "outputs/qos_v2a_summary.csv",
)
V2A_INPUT_MEMBERS = (
    "data/processed/qos_v2a_master_daily.csv",
    "data/raw/coingecko_current_universe_v04.csv",
    "outputs/download_failures_v2a.csv",
)
DELTA_OUTPUT_MEMBERS = (
    "outputs/btc_bottom_estimates_user_supplied.csv",
    "outputs/btc_regime_daily.csv",
    "outputs/comparison_protocol.json",
    "outputs/data_quality_by_asset.csv",
    "outputs/delta_daily_positions.csv",
    "outputs/delta_daily_returns.csv",
    "outputs/delta_historical_selections.csv",
    "outputs/delta_monte_carlo_10000_summary.csv",
    "outputs/delta_summary.csv",
    "outputs/delta_trade_ledger.csv",
    "outputs/delta_vs_external_benchmark.csv",
    "outputs/download_failures.csv",
    "outputs/external_delta_benchmark_user_supplied.json",
    "outputs/strategy_evidence_gate.csv",
    "outputs/strategy_selection_current.json",
)
DELTA_INPUT_MEMBERS = (
    "inputs/delta_ohlc_daily.csv",
    "inputs/delta_funding_events.csv",
    "inputs/data_quality_by_asset.csv",
    "inputs/download_failures.csv",
)


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _single_member(archive: zipfile.ZipFile, suffix: str) -> str:
    matches = [name for name in archive.namelist() if name.endswith(suffix)]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {suffix}; found {len(matches)}")
    return matches[0]


def _read_member(archive: zipfile.ZipFile, suffix: str) -> bytes:
    return archive.read(_single_member(archive, suffix))


def _open_zip(path: Path) -> zipfile.ZipFile:
    archive = zipfile.ZipFile(path)
    bad = archive.testzip()
    if bad:
        archive.close()
        raise ValueError(f"corrupt ZIP member in {path}: {bad}")
    return archive


def _safe_manifest(manifest: dict[str, Any], label: str) -> None:
    if manifest.get("technical_status") != "PASS":
        raise ValueError(f"{label} technical_status={manifest.get('technical_status')!r}")
    if manifest.get("operational_status") != "NOT_APPROVED":
        raise ValueError(f"{label} operational status is not NOT_APPROVED")
    if manifest.get("real_orders", 0) != 0 or manifest.get("capital_used", 0) != 0:
        raise ValueError(f"{label} violates zero-order / zero-capital lock")


def _normalize_text(value: Any) -> str:
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def _numeric_column(series: pd.Series) -> tuple[bool, np.ndarray]:
    numeric = pd.to_numeric(series, errors="coerce")
    nonnull = series.notna()
    is_numeric = bool(numeric[nonnull].notna().all())
    return is_numeric, numeric.to_numpy(dtype=float)


def _compare_csv(reference: bytes, replay: bytes, *, exact_numeric: bool) -> dict[str, Any]:
    left = pd.read_csv(io.BytesIO(reference), float_precision="round_trip")
    right = pd.read_csv(io.BytesIO(replay), float_precision="round_trip")
    result: dict[str, Any] = {
        "kind": "csv",
        "reference_shape": list(left.shape),
        "replay_shape": list(right.shape),
        "columns_match": list(left.columns) == list(right.columns),
        "matched": True,
        "column_differences": {},
        "max_abs_diff": 0.0,
        "max_rel_diff": 0.0,
    }
    if left.shape != right.shape or list(left.columns) != list(right.columns):
        result["matched"] = False
        return result

    for column in left.columns:
        left_numeric, left_array = _numeric_column(left[column])
        right_numeric, right_array = _numeric_column(right[column])
        if left_numeric != right_numeric:
            result["matched"] = False
            result["column_differences"][column] = {"reason": "numeric_type_mismatch"}
            continue
        if left_numeric:
            if exact_numeric:
                equal = np.equal(left_array, right_array) | (
                    np.isnan(left_array) & np.isnan(right_array)
                )
            else:
                equal = np.isclose(
                    left_array,
                    right_array,
                    rtol=RTOL,
                    atol=ATOL,
                    equal_nan=True,
                )
            differences = np.abs(left_array - right_array)
            both_nan = np.isnan(left_array) & np.isnan(right_array)
            differences[both_nan] = 0.0
            finite = np.isfinite(differences)
            max_abs = float(np.max(differences[finite])) if finite.any() else 0.0
            scale = np.maximum(np.abs(left_array), np.abs(right_array))
            relative = np.divide(
                differences,
                scale,
                out=np.zeros_like(differences),
                where=(scale != 0) & finite,
            )
            max_rel = float(np.max(relative[finite])) if finite.any() else 0.0
            result["max_abs_diff"] = max(result["max_abs_diff"], max_abs)
            result["max_rel_diff"] = max(result["max_rel_diff"], max_rel)
            mismatch_count = int((~equal).sum())
            if mismatch_count:
                result["matched"] = False
                indexes = np.flatnonzero(~equal)[:5].tolist()
                result["column_differences"][column] = {
                    "reason": "numeric_mismatch",
                    "mismatch_count": mismatch_count,
                    "sample_row_indexes": indexes,
                    "max_abs_diff": max_abs,
                    "max_rel_diff": max_rel,
                }
        else:
            left_values = left[column].where(left[column].notna(), "<NA>").map(_normalize_text)
            right_values = right[column].where(right[column].notna(), "<NA>").map(_normalize_text)
            equal = left_values == right_values
            mismatch_count = int((~equal).sum())
            if mismatch_count:
                result["matched"] = False
                indexes = np.flatnonzero((~equal).to_numpy())[:5].tolist()
                result["column_differences"][column] = {
                    "reason": "string_mismatch",
                    "mismatch_count": mismatch_count,
                    "sample_row_indexes": indexes,
                }
    return result


def _compare_json_value(
    left: Any,
    right: Any,
    path: str,
    differences: list[dict[str, Any]],
) -> tuple[float, float]:
    max_abs = 0.0
    max_rel = 0.0
    if isinstance(left, bool) or isinstance(right, bool):
        if left is not right:
            differences.append({
                "path": path,
                "reason": "boolean_mismatch",
                "reference": left,
                "replay": right,
            })
        return max_abs, max_rel
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        left_float = float(left)
        right_float = float(right)
        abs_diff = abs(left_float - right_float)
        scale = max(abs(left_float), abs(right_float))
        rel_diff = abs_diff / scale if scale else 0.0
        if not math.isclose(left_float, right_float, rel_tol=RTOL, abs_tol=ATOL):
            differences.append({
                "path": path,
                "reason": "numeric_mismatch",
                "reference": left,
                "replay": right,
                "abs_diff": abs_diff,
                "rel_diff": rel_diff,
            })
        return abs_diff, rel_diff
    if type(left) is not type(right):
        differences.append({
            "path": path,
            "reason": "type_mismatch",
            "reference_type": type(left).__name__,
            "replay_type": type(right).__name__,
        })
        return max_abs, max_rel
    if isinstance(left, dict):
        if set(left) != set(right):
            differences.append({
                "path": path,
                "reason": "key_mismatch",
                "reference_only": sorted(set(left) - set(right)),
                "replay_only": sorted(set(right) - set(left)),
            })
            return max_abs, max_rel
        for key in sorted(left):
            child_abs, child_rel = _compare_json_value(
                left[key], right[key], f"{path}.{key}" if path else key, differences
            )
            max_abs = max(max_abs, child_abs)
            max_rel = max(max_rel, child_rel)
        return max_abs, max_rel
    if isinstance(left, list):
        if len(left) != len(right):
            differences.append({
                "path": path,
                "reason": "length_mismatch",
                "reference": len(left),
                "replay": len(right),
            })
            return max_abs, max_rel
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            child_abs, child_rel = _compare_json_value(
                left_item, right_item, f"{path}[{index}]", differences
            )
            max_abs = max(max_abs, child_abs)
            max_rel = max(max_rel, child_rel)
        return max_abs, max_rel
    if isinstance(left, str):
        if _normalize_text(left) != _normalize_text(right):
            differences.append({"path": path, "reason": "string_mismatch"})
        return max_abs, max_rel
    if left != right:
        differences.append({
            "path": path,
            "reason": "value_mismatch",
            "reference": left,
            "replay": right,
        })
    return max_abs, max_rel


def _compare_json(reference: bytes, replay: bytes) -> dict[str, Any]:
    left = json.loads(reference.decode("utf-8-sig"))
    right = json.loads(replay.decode("utf-8-sig"))
    differences: list[dict[str, Any]] = []
    max_abs, max_rel = _compare_json_value(left, right, "", differences)
    return {
        "kind": "json",
        "matched": not differences,
        "differences": differences[:50],
        "difference_count": len(differences),
        "max_abs_diff": max_abs,
        "max_rel_diff": max_rel,
    }


def _compare_member(
    reference: bytes,
    replay: bytes,
    suffix: str,
    *,
    exact_numeric: bool,
) -> dict[str, Any]:
    if suffix.endswith(".csv"):
        return _compare_csv(reference, replay, exact_numeric=exact_numeric)
    if suffix.endswith(".json"):
        return _compare_json(reference, replay)
    raise ValueError(f"unsupported semantic member type: {suffix}")


def _compare_member_set(
    reference_archive: zipfile.ZipFile,
    replay_archive: zipfile.ZipFile,
    members: tuple[str, ...],
    *,
    exact_numeric: bool,
) -> dict[str, Any]:
    details: dict[str, Any] = {}
    matched = 0
    byte_identical = 0
    max_abs = 0.0
    max_rel = 0.0
    errors: list[dict[str, Any]] = []
    for suffix in members:
        try:
            reference = _read_member(reference_archive, suffix)
            replay = _read_member(replay_archive, suffix)
            if hashlib.sha256(reference).digest() == hashlib.sha256(replay).digest():
                byte_identical += 1
            comparison = _compare_member(
                reference,
                replay,
                suffix,
                exact_numeric=exact_numeric,
            )
            details[suffix] = comparison
            max_abs = max(max_abs, float(comparison.get("max_abs_diff", 0.0)))
            max_rel = max(max_rel, float(comparison.get("max_rel_diff", 0.0)))
            if comparison["matched"]:
                matched += 1
            else:
                errors.append({"member": suffix, "details": comparison})
        except Exception as exc:
            errors.append({"member": suffix, "error": f"{type(exc).__name__}: {exc}"})
    return {
        "checked": len(members),
        "matched": matched,
        "byte_identical": byte_identical,
        "max_abs_diff": max_abs,
        "max_rel_diff": max_rel,
        "details": details,
        "errors": errors,
    }


def compare(
    engine: str,
    reference_package: Path,
    replay_package: Path,
    reference_input_snapshot: Path | None = None,
    replay_input_snapshot: Path | None = None,
) -> dict[str, Any]:
    engine = engine.lower()
    if engine not in {"v2a", "delta"}:
        raise ValueError(f"unsupported engine: {engine}")

    with _open_zip(reference_package) as reference_archive, _open_zip(replay_package) as replay_archive:
        if engine == "v2a":
            run_suffix = "outputs/v2a_run_manifest.json"
            input_suffix = "outputs/v2a_input_manifest.json"
            output_members = V2A_OUTPUT_MEMBERS
        else:
            run_suffix = "outputs/delta_v11_run_manifest.json"
            input_suffix = "outputs/delta_input_manifest.json"
            output_members = DELTA_OUTPUT_MEMBERS

        reference_run = json.loads(
            _read_member(reference_archive, run_suffix).decode("utf-8-sig")
        )
        replay_run = json.loads(
            _read_member(replay_archive, run_suffix).decode("utf-8-sig")
        )
        reference_input = json.loads(
            _read_member(reference_archive, input_suffix).decode("utf-8-sig")
        )
        replay_input = json.loads(
            _read_member(replay_archive, input_suffix).decode("utf-8-sig")
        )
        _safe_manifest(reference_run, "reference")
        _safe_manifest(replay_run, "replay")

        matched_data_as_of = reference_run.get("data_as_of") == replay_run.get("data_as_of")
        matched_cutoff = reference_run.get("data_cutoff") == replay_run.get("data_cutoff")
        output_result = _compare_member_set(
            reference_archive,
            replay_archive,
            output_members,
            exact_numeric=False,
        )

        if engine == "v2a":
            input_result = _compare_member_set(
                reference_archive,
                replay_archive,
                V2A_INPUT_MEMBERS,
                exact_numeric=True,
            )
            input_manifest_metadata_match = (
                reference_input.get("data_cutoff") == replay_input.get("data_cutoff")
                and reference_input.get("data_as_of") == replay_input.get("data_as_of")
                and reference_input.get("attempted_symbols")
                == replay_input.get("attempted_symbols")
                and reference_input.get("loaded_symbols")
                == replay_input.get("loaded_symbols")
            )
        else:
            if reference_input_snapshot is None or replay_input_snapshot is None:
                raise ValueError(
                    "Delta cross-platform comparison requires both input snapshot ZIPs"
                )
            with _open_zip(reference_input_snapshot) as reference_snapshot, _open_zip(
                replay_input_snapshot
            ) as replay_snapshot:
                reference_snapshot_manifest = json.loads(
                    _read_member(
                        reference_snapshot,
                        "delta_input_snapshot_manifest.json",
                    ).decode("utf-8-sig")
                )
                replay_snapshot_manifest = json.loads(
                    _read_member(
                        replay_snapshot,
                        "delta_input_snapshot_manifest.json",
                    ).decode("utf-8-sig")
                )
                _safe_manifest(reference_snapshot_manifest, "reference input snapshot")
                _safe_manifest(replay_snapshot_manifest, "replay input snapshot")
                input_result = _compare_member_set(
                    reference_snapshot,
                    replay_snapshot,
                    DELTA_INPUT_MEMBERS,
                    exact_numeric=True,
                )
                input_manifest_metadata_match = (
                    reference_snapshot_manifest.get("data_cutoff")
                    == replay_snapshot_manifest.get("data_cutoff")
                    and reference_snapshot_manifest.get("data_as_of")
                    == replay_snapshot_manifest.get("data_as_of")
                    and reference_snapshot_manifest.get("loaded_assets")
                    == replay_snapshot_manifest.get("loaded_assets")
                )

    input_semantic_match = (
        input_result["matched"] == input_result["checked"]
        and input_manifest_metadata_match
    )
    output_semantic_match = output_result["matched"] == output_result["checked"]
    errors: list[Any] = []
    if not matched_data_as_of:
        errors.append({
            "data_as_of_mismatch": {
                "reference": reference_run.get("data_as_of"),
                "replay": replay_run.get("data_as_of"),
            }
        })
    if not matched_cutoff:
        errors.append({
            "data_cutoff_mismatch": {
                "reference": reference_run.get("data_cutoff"),
                "replay": replay_run.get("data_cutoff"),
            }
        })
    if not input_semantic_match:
        errors.append({
            "input_semantic_mismatch": {
                "metadata_match": input_manifest_metadata_match,
                "member_errors": input_result["errors"],
            }
        })
    if not output_semantic_match:
        errors.append({"output_semantic_mismatch": output_result["errors"]})

    status = "PASS" if not errors else "ERROR"
    return {
        "schema": "gate-btc-cross-platform-semantic-parity-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "equivalence_claim": status == "PASS",
        "scope": f"{engine.upper()}_LINUX_WINDOWS_SAME_INPUT_SEMANTIC_PARITY",
        "engine": engine.upper(),
        "comparison_policy": {
            "schemas_columns_row_order_strings": "EXACT",
            "input_numeric_values": "EXACT_AFTER_CSV_PARSE",
            "output_numeric_rtol": RTOL,
            "output_numeric_atol": ATOL,
            "line_endings": "NORMALIZED",
            "path_separators_and_all_other_strings": "EXACT",
            "byte_equality_required": False,
        },
        "matched_data_as_of": matched_data_as_of,
        "matched_data_cutoff": matched_cutoff,
        "input_semantic_match": input_semantic_match,
        "output_semantic_match": output_semantic_match,
        "input_members_checked": input_result["checked"],
        "input_members_matched": input_result["matched"],
        "output_members_checked": output_result["checked"],
        "output_members_matched": output_result["matched"],
        "output_members_byte_identical": output_result["byte_identical"],
        "observed_max_abs_numeric_diff": output_result["max_abs_diff"],
        "observed_max_rel_numeric_diff": output_result["max_rel_diff"],
        "reference": {
            "package_sha256": _sha256_path(reference_package),
            "data_as_of": reference_run.get("data_as_of"),
            "data_cutoff": reference_run.get("data_cutoff"),
            "input_snapshot_id": reference_input.get("input_snapshot_id"),
        },
        "replay": {
            "package_sha256": _sha256_path(replay_package),
            "data_as_of": replay_run.get("data_as_of"),
            "data_cutoff": replay_run.get("data_cutoff"),
            "input_snapshot_id": replay_input.get("input_snapshot_id"),
        },
        "errors": errors,
        "safety": {
            "research_only": True,
            "orders_generated": 0,
            "real_capital_used": 0,
            "operational_status": "NOT_APPROVED",
        },
        "limitation": (
            "This proves same-input semantic parity across Linux and Windows. "
            "It does not authorize operational promotion, merge, or shutdown "
            "of the user's local routine."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("engine", choices=("v2a", "delta"))
    parser.add_argument("reference_package", type=Path)
    parser.add_argument("replay_package", type=Path)
    parser.add_argument("--reference-input-snapshot", type=Path)
    parser.add_argument("--replay-input-snapshot", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = args.output_dir / f"{args.engine.upper()}_CROSS_PLATFORM_PARITY_{stamp}.json"
    txt_path = args.output_dir / f"{args.engine.upper()}_CROSS_PLATFORM_PARITY_{stamp}.txt"
    try:
        result = compare(
            args.engine,
            args.reference_package,
            args.replay_package,
            args.reference_input_snapshot,
            args.replay_input_snapshot,
        )
    except Exception as exc:
        result = {
            "schema": "gate-btc-cross-platform-semantic-parity-v1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "ERROR",
            "equivalence_claim": False,
            "engine": args.engine.upper(),
            "errors": [f"{type(exc).__name__}: {exc}"],
            "safety": {
                "research_only": True,
                "orders_generated": 0,
                "real_capital_used": 0,
                "operational_status": "NOT_APPROVED",
            },
        }
    json_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"GATE BTC — {args.engine.upper()} CROSS-PLATFORM SAME-INPUT PARITY",
        f"STATUS={result.get('status', 'ERROR')}",
        f"EQUIVALENCE_CLAIM={result.get('equivalence_claim', False)}",
        f"MATCHED_DATA_AS_OF={result.get('matched_data_as_of', False)}",
        f"MATCHED_DATA_CUTOFF={result.get('matched_data_cutoff', False)}",
        f"INPUT_SEMANTIC_MATCH={result.get('input_semantic_match', False)}",
        f"OUTPUT_SEMANTIC_MATCH={result.get('output_semantic_match', False)}",
        (
            "OUTPUT_MEMBERS_MATCHED="
            f"{result.get('output_members_matched', 0)}/"
            f"{result.get('output_members_checked', 0)}"
        ),
        (
            "OBSERVED_MAX_ABS_NUMERIC_DIFF="
            f"{result.get('observed_max_abs_numeric_diff', 'UNAVAILABLE')}"
        ),
        (
            "OBSERVED_MAX_REL_NUMERIC_DIFF="
            f"{result.get('observed_max_rel_numeric_diff', 'UNAVAILABLE')}"
        ),
        f"RTOL={RTOL}",
        f"ATOL={ATOL}",
        "RESEARCH_ONLY=True",
        "ORDERS_GENERATED=0",
        "REAL_CAPITAL_USED=0",
        "OPERATIONAL_STATUS=NOT_APPROVED",
        "",
        "ERRORS:",
        *(
            [
                json.dumps(item, ensure_ascii=False, default=str)
                for item in result.get("errors", [])
            ]
            or ["NONE"]
        ),
        "",
        f"LIMITATION={result.get('limitation', 'UNAVAILABLE')}",
    ]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
