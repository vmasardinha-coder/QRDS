#!/usr/bin/env python3
"""Gateway upstream equivalence with documented research-only warning states.

This wrapper changes only the validator. The canonical Gateway source and its
methodology remain byte-identical. Public runs may legitimately report partial
source redundancy while remaining technically usable for research.
"""
from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path
from typing import Any

import gateway_upstream_equivalence as base

ALLOWED_DATA_QUALITY = {"PASS", "PASS_PARTIAL_REDUNDANCY_WARNING"}
ALLOWED_SNAPSHOT_STATUS = {
    "SNAPSHOT_USABLE_RESEARCH_ONLY",
    "SNAPSHOT_USABLE_WITH_DATA_WARNINGS",
}


def validate_gateway_output(path: Path) -> dict[str, Any]:
    contract = json.loads(base.CONTRACT.read_text(encoding="utf-8"))
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        for basename, required_fields in contract["required_files"].items():
            matches = [name for name in names if Path(name).name == basename]
            if len(matches) != 1:
                raise RuntimeError(f"contract member {basename} count={len(matches)}")
            data = archive.read(matches[0])
            if basename.endswith(".json"):
                present = json.loads(data.decode("utf-8-sig"))
            else:
                present = next(csv.reader(data.decode("utf-8-sig").splitlines()), [])
            missing = [field for field in required_fields if field not in present]
            if missing:
                raise RuntimeError(f"contract member {basename} missing {missing}")

    _, raw_manifest = base.find_member_by_basename(path, "v2a1_run_manifest.json")
    manifest = json.loads(raw_manifest.decode("utf-8-sig"))
    exact = {
        "version": "QOS_V2A1_GATEWAY_SCANNER_0.10",
        "technical_status": "PASS",
        "evidence_status": "SNAPSHOT_ONLY_NO_WALK_FORWARD_BACKTEST",
        "operational_status": "NOT_APPROVED",
        "retrospective_performance_status": "PROHIBITED_CURRENT_COMPOSITION",
        "errors": [],
        "selected_rows": 118,
        "execution_profile_rows": 8,
        "delta_stop_rule_rows": 80,
    }
    mismatches = {
        key: {"actual": manifest.get(key), "expected": value}
        for key, value in exact.items()
        if manifest.get(key) != value
    }
    if manifest.get("data_quality_status") not in ALLOWED_DATA_QUALITY:
        mismatches["data_quality_status"] = {
            "actual": manifest.get("data_quality_status"),
            "allowed": sorted(ALLOWED_DATA_QUALITY),
        }
    if manifest.get("snapshot_status") not in ALLOWED_SNAPSHOT_STATUS:
        mismatches["snapshot_status"] = {
            "actual": manifest.get("snapshot_status"),
            "allowed": sorted(ALLOWED_SNAPSHOT_STATUS),
        }
    if mismatches:
        raise RuntimeError(f"Gateway public output manifest mismatch: {mismatches}")

    warning_state = (
        manifest.get("data_quality_status") != "PASS"
        or manifest.get("snapshot_status") != "SNAPSHOT_USABLE_RESEARCH_ONLY"
    )
    return {
        "status": "PASS_WITH_DATA_WARNINGS" if warning_state else "PASS",
        "warning_state": warning_state,
        "manifest": manifest,
        "output_zip": {
            "size_bytes": path.stat().st_size,
            "sha256": base.file_sha256(path),
        },
    }


base.validate_gateway_output = validate_gateway_output

if __name__ == "__main__":
    raise SystemExit(base.main())
