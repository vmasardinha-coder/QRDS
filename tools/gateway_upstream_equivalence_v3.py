#!/usr/bin/env python3
"""Gateway upstream equivalence with strict cross-platform numeric tolerance.

Linux capture/replay remains byte-semantic deterministic. Windows consumes the
identical HTTP cassette and is compared against the Linux output with the same
frozen cross-platform policy already used by GATE BTC: identical member sets,
schemas, row order and strings, allowing only numeric differences at
rtol=atol=1e-12. Canonical Gateway source bytes are never changed.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import gateway_upstream_equivalence as base
import gateway_upstream_equivalence_v2 as warning_validator

RTOL = 1e-12
ATOL = 1e-12
base.validate_gateway_output = warning_validator.validate_gateway_output


def normalize_text(value: Any) -> str:
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def numeric_column(series: pd.Series) -> tuple[bool, np.ndarray]:
    numeric = pd.to_numeric(series, errors="coerce")
    nonnull = series.notna()
    return bool(numeric[nonnull].notna().all()), numeric.to_numpy(dtype=float)


def compare_csv(reference: bytes, candidate: bytes) -> dict[str, Any]:
    left = pd.read_csv(io.BytesIO(reference), float_precision="round_trip")
    right = pd.read_csv(io.BytesIO(candidate), float_precision="round_trip")
    result: dict[str, Any] = {
        "kind": "csv",
        "matched": True,
        "reference_shape": list(left.shape),
        "candidate_shape": list(right.shape),
        "columns_match": list(left.columns) == list(right.columns),
        "row_order_policy": "EXACT",
        "string_policy": "EXACT_NORMALIZED_LINE_ENDINGS",
        "numeric_rtol": RTOL,
        "numeric_atol": ATOL,
        "max_abs_diff": 0.0,
        "max_rel_diff": 0.0,
        "column_differences": {},
    }
    if left.shape != right.shape or list(left.columns) != list(right.columns):
        result["matched"] = False
        return result

    for column in left.columns:
        left_numeric, left_values = numeric_column(left[column])
        right_numeric, right_values = numeric_column(right[column])
        if left_numeric != right_numeric:
            result["matched"] = False
            result["column_differences"][column] = {"reason": "numeric_type_mismatch"}
            continue
        if left_numeric:
            equal = np.isclose(left_values, right_values, rtol=RTOL, atol=ATOL, equal_nan=True)
            difference = np.abs(left_values - right_values)
            both_nan = np.isnan(left_values) & np.isnan(right_values)
            difference[both_nan] = 0.0
            finite = np.isfinite(difference)
            max_abs = float(np.max(difference[finite])) if finite.any() else 0.0
            scale = np.maximum(np.abs(left_values), np.abs(right_values))
            relative = np.divide(
                difference,
                scale,
                out=np.zeros_like(difference),
                where=(scale != 0) & finite,
            )
            max_rel = float(np.max(relative[finite])) if finite.any() else 0.0
            result["max_abs_diff"] = max(result["max_abs_diff"], max_abs)
            result["max_rel_diff"] = max(result["max_rel_diff"], max_rel)
            mismatch_count = int((~equal).sum())
            if mismatch_count:
                result["matched"] = False
                result["column_differences"][column] = {
                    "reason": "numeric_mismatch",
                    "mismatch_count": mismatch_count,
                    "sample_row_indexes": np.flatnonzero(~equal)[:10].tolist(),
                    "max_abs_diff": max_abs,
                    "max_rel_diff": max_rel,
                }
        else:
            left_text = left[column].where(left[column].notna(), "<NA>").map(normalize_text)
            right_text = right[column].where(right[column].notna(), "<NA>").map(normalize_text)
            equal = left_text == right_text
            mismatch_count = int((~equal).sum())
            if mismatch_count:
                result["matched"] = False
                result["column_differences"][column] = {
                    "reason": "string_mismatch",
                    "mismatch_count": mismatch_count,
                    "sample_row_indexes": np.flatnonzero((~equal).to_numpy())[:10].tolist(),
                }
    return result


def compare_json_value(left: Any, right: Any, path: str, differences: list[dict[str, Any]]) -> tuple[float, float]:
    max_abs = max_rel = 0.0
    if isinstance(left, bool) or isinstance(right, bool):
        if left is not right:
            differences.append({"path": path, "reason": "boolean_mismatch", "reference": left, "candidate": right})
        return max_abs, max_rel
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        a, b = float(left), float(right)
        abs_diff = abs(a - b)
        scale = max(abs(a), abs(b))
        rel_diff = abs_diff / scale if scale else 0.0
        if not math.isclose(a, b, rel_tol=RTOL, abs_tol=ATOL):
            differences.append({"path": path, "reason": "numeric_mismatch", "reference": left, "candidate": right, "abs_diff": abs_diff, "rel_diff": rel_diff})
        return abs_diff, rel_diff
    if type(left) is not type(right):
        differences.append({"path": path, "reason": "type_mismatch", "reference_type": type(left).__name__, "candidate_type": type(right).__name__})
        return max_abs, max_rel
    if isinstance(left, dict):
        if set(left) != set(right):
            differences.append({"path": path, "reason": "key_mismatch", "reference_only": sorted(set(left) - set(right)), "candidate_only": sorted(set(right) - set(left))})
            return max_abs, max_rel
        for key in sorted(left):
            child_abs, child_rel = compare_json_value(left[key], right[key], f"{path}.{key}" if path else key, differences)
            max_abs, max_rel = max(max_abs, child_abs), max(max_rel, child_rel)
        return max_abs, max_rel
    if isinstance(left, list):
        if len(left) != len(right):
            differences.append({"path": path, "reason": "length_mismatch", "reference": len(left), "candidate": len(right)})
            return max_abs, max_rel
        for index, (a, b) in enumerate(zip(left, right)):
            child_abs, child_rel = compare_json_value(a, b, f"{path}[{index}]", differences)
            max_abs, max_rel = max(max_abs, child_abs), max(max_rel, child_rel)
        return max_abs, max_rel
    if isinstance(left, str):
        if normalize_text(left) != normalize_text(right):
            differences.append({"path": path, "reason": "string_mismatch"})
        return max_abs, max_rel
    if left != right:
        differences.append({"path": path, "reason": "value_mismatch", "reference": left, "candidate": right})
    return max_abs, max_rel


def compare_json(reference: bytes, candidate: bytes) -> dict[str, Any]:
    left = base.clean_json(json.loads(reference.decode("utf-8-sig")))
    right = base.clean_json(json.loads(candidate.decode("utf-8-sig")))
    differences: list[dict[str, Any]] = []
    max_abs, max_rel = compare_json_value(left, right, "", differences)
    return {
        "kind": "json",
        "matched": not differences,
        "difference_count": len(differences),
        "differences": differences[:100],
        "numeric_rtol": RTOL,
        "numeric_atol": ATOL,
        "max_abs_diff": max_abs,
        "max_rel_diff": max_rel,
    }


def semantic_members(path: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"corrupt output ZIP member: {bad}")
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            if name.lower().endswith((".csv", ".json")):
                result[name] = archive.read(info)
    return result


def compare_output_zips(reference_path: Path, candidate_path: Path) -> dict[str, Any]:
    reference = semantic_members(reference_path)
    candidate = semantic_members(candidate_path)
    errors: list[dict[str, Any]] = []
    details: dict[str, Any] = {}
    max_abs = max_rel = 0.0
    if set(reference) != set(candidate):
        errors.append({"reason": "member_set_mismatch", "reference_only": sorted(set(reference) - set(candidate)), "candidate_only": sorted(set(candidate) - set(reference))})
    for name in sorted(set(reference) & set(candidate)):
        comparison = compare_csv(reference[name], candidate[name]) if name.lower().endswith(".csv") else compare_json(reference[name], candidate[name])
        details[name] = comparison
        max_abs = max(max_abs, float(comparison.get("max_abs_diff", 0.0)))
        max_rel = max(max_rel, float(comparison.get("max_rel_diff", 0.0)))
        if not comparison["matched"]:
            errors.append({"member": name, "details": comparison})
    return {
        "status": "PASS" if not errors else "FAIL",
        "checked_members": len(set(reference) & set(candidate)),
        "max_abs_diff": max_abs,
        "max_rel_diff": max_rel,
        "numeric_rtol": RTOL,
        "numeric_atol": ATOL,
        "details": details,
        "errors": errors,
    }


def replay_only(args: argparse.Namespace) -> int:
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema": "gate-btc-gateway-upstream-equivalence-v2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "REPLAY_ONLY_WINDOWS_TOLERANT_NUMERIC",
        "status": "RUNNING",
        "stage_reached": "STARTED",
        "research_only": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "operational_status": "NOT_APPROVED",
        "methodology_changes": 0,
        "errors": [],
    }
    try:
        if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
            raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
        source_zip = out / "canonical_gateway_v010_source.zip"
        payload["source"] = base.decode_source(source_zip)
        cassette = args.cassette.resolve()
        replay_status = out / "gateway_public_http_windows_replay_status.json"
        replay_output = out / "windows_offline_replay_outputs.zip"
        payload["windows_replay"] = base.run_gateway(source_zip, "replay", cassette, replay_status, replay_output, out, args.timeout_seconds)
        payload["cross_platform_parity"] = compare_output_zips(args.reference_output_zip.resolve(), replay_output)
        payload["semantic_parity"] = payload["cross_platform_parity"]
        if payload["cross_platform_parity"]["status"] != "PASS":
            raise RuntimeError(f"Windows cross-platform output mismatch: {payload['cross_platform_parity']['errors'][:5]}")
        payload["public_source_acquisition_equivalence"] = "PASS_FROM_LINUX_CAPTURE_ARTIFACT"
        payload["feature_construction_equivalence"] = "PASS_WINDOWS_OFFLINE_SAME_INPUT_REPLAY_WITH_FROZEN_1E-12_NUMERIC_TOLERANCE"
        payload["stage_reached"] = "WINDOWS_OFFLINE_IDENTICAL_HTTP_REPLAY_PASS"
        payload["status"] = "PASS"
        payload["next_action"] = "COMBINE_WITH_LINUX_CAPTURE_AND_GATEWAY_DOWNSTREAM_EVIDENCE"
    except Exception as exc:
        payload["status"] = "FAIL"
        payload["errors"].append({"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
        payload["next_action"] = "FAIL_CLOSED_REVIEW_EVIDENCE"
    base.save_json(out / "GATE_BTC_GATEWAY_WINDOWS_UPSTREAM_REPLAY.json", payload)
    base.save_text(out / "GATE_BTC_GATEWAY_WINDOWS_UPSTREAM_REPLAY.txt", base.render(payload))
    base.package_directory(out, out / "GATE_BTC_GATEWAY_WINDOWS_UPSTREAM_REPLAY_EVIDENCE.zip")
    print(base.render(payload), end="")
    return 0 if payload["status"] == "PASS" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("capture-replay")
    capture.add_argument("--output-dir", type=Path, required=True)
    capture.add_argument("--timeout-seconds", type=int, default=1800)
    capture.set_defaults(func=base.capture_replay)
    replay = sub.add_parser("replay-only")
    replay.add_argument("--cassette", type=Path, required=True)
    replay.add_argument("--reference-output-zip", type=Path, required=True)
    replay.add_argument("--output-dir", type=Path, required=True)
    replay.add_argument("--timeout-seconds", type=int, default=1800)
    replay.set_defaults(func=replay_only)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
