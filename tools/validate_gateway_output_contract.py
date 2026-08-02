#!/usr/bin/env python3
"""Fail-closed structural and safety validator for Gateway v0.10 outputs."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def validate(output_dir: Path, contract_path: Path) -> list[str]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for name, required in contract["required_files"].items():
        path = output_dir / name
        if not path.is_file():
            errors.append(f"missing:{name}")
            continue
        if path.suffix == ".json":
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"invalid_json:{name}:{exc}")
                continue
            missing = [key for key in required if key not in payload]
        else:
            try:
                with path.open(encoding="utf-8-sig", newline="") as handle:
                    fieldnames = csv.DictReader(handle).fieldnames or []
                    missing = [key for key in required if key not in fieldnames]
            except OSError as exc:
                errors.append(f"invalid_csv:{name}:{exc}")
                continue
        if missing:
            errors.append(f"missing_fields:{name}:{','.join(missing)}")

    manifest_path = output_dir / "v2a1_run_manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            safety = contract["safety_invariants"]
            for key in ("mode", "operational_status", "evidence_status"):
                if manifest.get(key) != safety[key]:
                    errors.append(f"safety_mismatch:{key}:{manifest.get(key)!r}")
            if manifest.get("version") != contract["gateway_version"]:
                errors.append(f"version_mismatch:{manifest.get('version')!r}")
        except (OSError, json.JSONDecodeError):
            pass
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--contract", type=Path, default=Path("migration/gateway/gateway_output_contract_v010.json"))
    args = parser.parse_args()
    errors = validate(args.output_dir, args.contract)
    result = {"status": "PASS" if not errors else "ERROR", "research_only": True, "errors": errors}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
