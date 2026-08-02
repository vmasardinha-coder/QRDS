#!/usr/bin/env python3
"""Fail-closed comparison of Delta outputs replayed from identical frozen inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

DETERMINISTIC_MEMBERS = (
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


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def _load(package: Path) -> dict:
    with zipfile.ZipFile(package) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"corrupt ZIP member: {bad}")
        run_manifest = json.loads(
            archive.read(
                _single_member(archive, "outputs/delta_v11_run_manifest.json")
            ).decode("utf-8-sig")
        )
        input_manifest = json.loads(
            archive.read(
                _single_member(archive, "outputs/delta_input_manifest.json")
            ).decode("utf-8-sig")
        )
        hashes = {}
        missing = []
        for suffix in DETERMINISTIC_MEMBERS:
            matches = [name for name in archive.namelist() if name.endswith(suffix)]
            if len(matches) != 1:
                missing.append({"suffix": suffix, "count": len(matches)})
            else:
                hashes[suffix] = _sha256_bytes(archive.read(matches[0]))
    if run_manifest.get("technical_status") != "PASS":
        raise ValueError(f"package technical_status={run_manifest.get('technical_status')!r}")
    if run_manifest.get("operational_status") != "NOT_APPROVED":
        raise ValueError("package operational status is not NOT_APPROVED")
    if run_manifest.get("real_orders", 0) != 0 or run_manifest.get("capital_used", 0) != 0:
        raise ValueError("package violates zero-order / zero-capital safety lock")
    return {
        "package_sha256": _sha256_path(package),
        "run_manifest": run_manifest,
        "input_manifest": input_manifest,
        "member_hashes": hashes,
        "missing": missing,
    }


def compare(reference_package: Path, replay_package: Path) -> dict:
    reference = _load(reference_package)
    replay = _load(replay_package)
    errors = []
    if reference["missing"]:
        errors.append({"reference_missing_members": reference["missing"]})
    if replay["missing"]:
        errors.append({"replay_missing_members": replay["missing"]})
    ref_snapshot = reference["input_manifest"].get("input_snapshot_id")
    replay_snapshot = replay["input_manifest"].get("input_snapshot_id")
    matched_input = bool(ref_snapshot and ref_snapshot == replay_snapshot)
    if not matched_input:
        errors.append({
            "input_snapshot_mismatch": {
                "reference": ref_snapshot,
                "replay": replay_snapshot,
            }
        })
    same_close = (
        reference["run_manifest"].get("data_as_of")
        == replay["run_manifest"].get("data_as_of")
    )
    if not same_close:
        errors.append({
            "data_as_of_mismatch": {
                "reference": reference["run_manifest"].get("data_as_of"),
                "replay": replay["run_manifest"].get("data_as_of"),
            }
        })
    mismatches = {
        name: {
            "reference": reference["member_hashes"].get(name),
            "replay": replay["member_hashes"].get(name),
        }
        for name in DETERMINISTIC_MEMBERS
        if reference["member_hashes"].get(name) != replay["member_hashes"].get(name)
    }
    if mismatches:
        errors.append({"deterministic_member_mismatches": mismatches})
    status = "PASS" if not errors else "ERROR"
    return {
        "schema": "delta-frozen-input-parity-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "equivalence_claim": status == "PASS",
        "scope": "DELTA_DETERMINISTIC_REPLAY_ON_IDENTICAL_INPUT_BYTES",
        "matched_input_snapshot": matched_input,
        "matched_data_as_of": same_close,
        "deterministic_members_checked": len(DETERMINISTIC_MEMBERS),
        "deterministic_members_matched": len(DETERMINISTIC_MEMBERS) - len(mismatches),
        "reference": {
            "package_sha256": reference["package_sha256"],
            "data_as_of": reference["run_manifest"].get("data_as_of"),
            "input_snapshot_id": ref_snapshot,
        },
        "replay": {
            "package_sha256": replay["package_sha256"],
            "data_as_of": replay["run_manifest"].get("data_as_of"),
            "input_snapshot_id": replay_snapshot,
        },
        "mismatched_members": mismatches,
        "errors": errors,
        "safety": {
            "research_only": True,
            "orders_generated": 0,
            "real_capital_used": 0,
            "operational_status": "NOT_APPROVED",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference_package", type=Path)
    parser.add_argument("replay_package", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = args.output_dir / f"DELTA_FROZEN_INPUT_PARITY_{stamp}.json"
    txt_path = args.output_dir / f"DELTA_FROZEN_INPUT_PARITY_{stamp}.txt"
    try:
        result = compare(args.reference_package, args.replay_package)
    except Exception as exc:
        result = {
            "schema": "delta-frozen-input-parity-v1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "ERROR",
            "equivalence_claim": False,
            "errors": [f"{type(exc).__name__}: {exc}"],
        }
    json_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    errors = [
        json.dumps(item, ensure_ascii=False)
        for item in result.get("errors", [])
    ] or ["NONE"]
    lines = [
        "GATE BTC — DELTA FROZEN INPUT PARITY",
        f"STATUS={result['status']}",
        f"EQUIVALENCE_CLAIM={result.get('equivalence_claim', False)}",
        f"MATCHED_INPUT_SNAPSHOT={result.get('matched_input_snapshot', False)}",
        f"MATCHED_DATA_AS_OF={result.get('matched_data_as_of', False)}",
        (
            "DETERMINISTIC_MEMBERS_MATCHED="
            f"{result.get('deterministic_members_matched', 0)}/"
            f"{result.get('deterministic_members_checked', 0)}"
        ),
        "RESEARCH_ONLY=True",
        "ORDERS_GENERATED=0",
        "REAL_CAPITAL_USED=0",
        "OPERATIONAL_STATUS=NOT_APPROVED",
        "",
        "ERRORS:",
        *errors,
    ]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
