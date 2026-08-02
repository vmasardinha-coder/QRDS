#!/usr/bin/env python3
"""Fail-closed comparison of two V2A packages produced from frozen inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

DETERMINISTIC_MEMBERS = (
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
            archive.read(_single_member(archive, "outputs/v2a_run_manifest.json")).decode("utf-8-sig")
        )
        input_manifest = json.loads(
            archive.read(_single_member(archive, "outputs/v2a_input_manifest.json")).decode("utf-8-sig")
        )
        member_hashes = {}
        missing = []
        for suffix in DETERMINISTIC_MEMBERS:
            matches = [name for name in archive.namelist() if name.endswith(suffix)]
            if len(matches) != 1:
                missing.append({"suffix": suffix, "count": len(matches)})
            else:
                member_hashes[suffix] = _sha256_bytes(archive.read(matches[0]))
    if run_manifest.get("technical_status") != "PASS":
        raise ValueError(f"package technical_status={run_manifest.get('technical_status')!r}")
    if run_manifest.get("operational_status") != "NOT_APPROVED":
        raise ValueError("package operational status is not NOT_APPROVED")
    if run_manifest.get("real_orders", 0) != 0 or run_manifest.get("capital_used", 0) != 0:
        raise ValueError("package violates zero-order / zero-capital safety lock")
    return {
        "package": str(package),
        "package_sha256": _sha256_path(package),
        "run_manifest": run_manifest,
        "input_manifest": input_manifest,
        "member_hashes": member_hashes,
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

    ref_input = reference["input_manifest"].get("input_snapshot_id")
    replay_input = replay["input_manifest"].get("input_snapshot_id")
    matched_input = bool(ref_input and ref_input == replay_input)
    if not matched_input:
        errors.append({"input_snapshot_mismatch": {"reference": ref_input, "replay": replay_input}})

    mismatched_members = {
        name: {
            "reference": reference["member_hashes"].get(name),
            "replay": replay["member_hashes"].get(name),
        }
        for name in DETERMINISTIC_MEMBERS
        if reference["member_hashes"].get(name) != replay["member_hashes"].get(name)
    }
    if mismatched_members:
        errors.append({"deterministic_member_mismatches": mismatched_members})

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

    status = "PASS" if not errors else "ERROR"
    return {
        "schema": "qos-v2a-frozen-input-parity-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "equivalence_claim": status == "PASS",
        "scope": "V2A_DETERMINISTIC_REPLAY_ON_IDENTICAL_INPUT_BYTES",
        "matched_input_snapshot": matched_input,
        "matched_data_as_of": same_close,
        "deterministic_members_checked": len(DETERMINISTIC_MEMBERS),
        "deterministic_members_matched": len(DETERMINISTIC_MEMBERS) - len(mismatched_members),
        "reference": {
            "package_sha256": reference["package_sha256"],
            "mode": reference["run_manifest"].get("mode"),
            "data_as_of": reference["run_manifest"].get("data_as_of"),
            "input_snapshot_id": ref_input,
        },
        "replay": {
            "package_sha256": replay["package_sha256"],
            "mode": replay["run_manifest"].get("mode"),
            "data_as_of": replay["run_manifest"].get("data_as_of"),
            "input_snapshot_id": replay_input,
        },
        "mismatched_members": mismatched_members,
        "errors": errors,
        "safety": {
            "research_only": True,
            "orders_generated": 0,
            "real_capital_used": 0,
            "operational_status": "NOT_APPROVED",
        },
        "limitation": (
            "This proves deterministic V2A replay for identical bytes; "
            "local-versus-remote parity still requires the local runner to consume this same frozen package."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference_package", type=Path)
    parser.add_argument("replay_package", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = args.output_dir / f"V2A_FROZEN_INPUT_PARITY_{stamp}.json"
    txt_path = args.output_dir / f"V2A_FROZEN_INPUT_PARITY_{stamp}.txt"
    try:
        result = compare(args.reference_package, args.replay_package)
    except Exception as exc:
        result = {
            "schema": "qos-v2a-frozen-input-parity-v1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "ERROR",
            "equivalence_claim": False,
            "errors": [f"{type(exc).__name__}: {exc}"],
            "safety": {"research_only": True, "orders_generated": 0, "real_capital_used": 0},
        }
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    error_lines = [json.dumps(item, ensure_ascii=False) for item in result.get("errors", [])] or ["NONE"]
    lines = [
        "GATE BTC — V2A FROZEN INPUT PARITY",
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
        *error_lines,
        "",
        f"LIMITATION={result.get('limitation', 'UNAVAILABLE')}",
    ]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
