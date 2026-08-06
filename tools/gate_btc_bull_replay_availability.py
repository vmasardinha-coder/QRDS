#!/usr/bin/env python3
"""Fail-closed Bull Replay data-availability inventory.

This tool does not calculate performance. It only inventories candidate series
and emits immutable metadata needed for a later, separately authorized replay.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROHIBITED_KEYS = {
    "return", "cagr", "sharpe", "sortino", "calmar", "drawdown",
    "ranking", "winner", "allocation_recommendation",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_csv(path: Path) -> dict[str, Any]:
    rows = 0
    first_date = None
    last_date = None
    warnings: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames or []
        date_field = next((f for f in fields if f.lower() in {"date", "timestamp", "datetime"}), None)
        for row in reader:
            rows += 1
            if date_field and row.get(date_field):
                value = row[date_field]
                first_date = first_date or value
                last_date = value
        if not date_field:
            warnings.append("DATE_FIELD_NOT_IDENTIFIED")
    return {
        "format": "csv",
        "row_count": rows,
        "start_date": first_date,
        "end_date": last_date,
        "warnings": warnings,
    }


def inspect_file(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".csv":
        meta = inspect_csv(path)
    else:
        meta = {
            "format": path.suffix.lower().lstrip(".") or "unknown",
            "row_count": None,
            "start_date": None,
            "end_date": None,
            "warnings": ["UNSUPPORTED_FORMAT_METADATA_ONLY"],
        }
    meta["sha256"] = sha256(path)
    return meta


def validate_contract(contract: dict[str, Any]) -> None:
    assert contract["research_only"] is True
    assert contract["operational_status"] == "NOT_APPROVED"
    assert contract["orders_generated"] == 0
    assert contract["real_capital_used"] == 0
    assert contract["holdout_opened"] is False
    assert contract["visible_evaluation_allowed"] is False
    assert PROHIBITED_KEYS.issubset(set(contract["prohibited_outputs"]))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--series-map", required=True, help="JSON object: series name -> local path")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    contract_path = Path(args.contract)
    series_map_path = Path(args.series_map)
    output_path = Path(args.output)

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    validate_contract(contract)
    series_map = json.loads(series_map_path.read_text(encoding="utf-8"))
    if not isinstance(series_map, dict):
        raise ValueError("series-map must be a JSON object")

    required = (
        contract["required_benchmarks"]
        + contract["required_core_candidates"]
        + contract["required_delta_candidates"]
    )
    inventory = []
    for name in required + contract["optional_independent_candidates"]:
        raw = series_map.get(name)
        entry: dict[str, Any] = {
            "series_name": name,
            "source_path": raw,
            "exists": False,
            "format": None,
            "start_date": None,
            "end_date": None,
            "row_count": None,
            "frequency": None,
            "currency_base": None,
            "sha256": None,
            "warnings": [],
        }
        if raw:
            path = Path(raw)
            entry["exists"] = path.is_file()
            if path.is_file():
                entry.update(inspect_file(path))
            else:
                entry["warnings"].append("MISSING_FILE")
        else:
            entry["warnings"].append("UNMAPPED_SERIES")
        inventory.append(entry)

    missing_required = [x["series_name"] for x in inventory if x["series_name"] in required and not x["exists"]]
    manifest = {
        "status": "PASS_AVAILABILITY_ONLY" if not missing_required else "BLOCKED_MISSING_REQUIRED_SERIES",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "operational_status": "NOT_APPROVED",
        "orders_generated": 0,
        "real_capital_used": 0,
        "holdout_opened": False,
        "visible_evaluation_run": False,
        "contract_sha256": sha256(contract_path),
        "series_map_sha256": sha256(series_map_path),
        "missing_required": missing_required,
        "inventory": inventory,
        "next_gate": contract["next_gate"],
    }
    if any(k in manifest for k in PROHIBITED_KEYS):
        raise AssertionError("prohibited evaluation output emitted")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if not missing_required else 2


if __name__ == "__main__":
    raise SystemExit(main())
