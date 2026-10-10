#!/usr/bin/env python3
"""Read-only cumulative publication inventory; never rewrites PIT STATUS or credit."""
import argparse
import hashlib
import json
from pathlib import Path


def inventory(root: Path) -> dict:
    files = sorted((root / "snapshots").glob("*.json"))
    valid, rejected = [], []
    seen = set()
    for path in files:
        try:
            obj = json.loads(path.read_text())
            identity = obj["snapshot_id"]
            basis = {k: v for k, v in obj.items() if k != "record_sha256"}
            raw = (json.dumps(basis, sort_keys=True, separators=(",", ":")) + "\n").encode()
            if obj.get("record_sha256") != hashlib.sha256(raw).hexdigest():
                raise ValueError("SNAPSHOT_RECORD_HASH_MISMATCH")
            if identity != path.stem or identity in seen:
                raise ValueError("SNAPSHOT_ID_FILENAME_MISMATCH_OR_DUPLICATE")
            required = {"schema": "gate_btc.v2a_point_in_time_data_snapshot.v1",
                        "research_only": True, "shadow_only": True, "not_approved": True,
                        "feeds_frozen_engine": False, "promotion_allowed": False,
                        "orders_generated": 0, "real_capital_used": 0,
                        "backfill_performed": False, "retrospective_reconstruction": False,
                        "attempted_symbols": 137}
            if any(obj.get(k) != v for k, v in required.items()):
                raise ValueError("SNAPSHOT_SCOPE_OR_BOUNDARY_MISMATCH")
            if len(obj.get("selected_sources", {})) != 137:
                raise ValueError("EXACT_SOURCE_IDENTITY_COUNT_MISMATCH")
            seen.add(identity)
            valid.append({"snapshot_id": identity, "source_data_as_of": obj["source_data_as_of"],
                          "record_sha256": obj["record_sha256"],
                          "loaded_symbols": obj.get("loaded_symbols"),
                          "failed_symbols": obj.get("failed_symbols"),
                          "source_coverage_complete": obj.get("loaded_symbols") == 137 and obj.get("failed_symbols") == 0,
                          "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        except (ValueError, KeyError, TypeError) as exc:
            rejected.append({"path": path.name, "reason": str(exc)})
    status_path = root / "STATUS.json"
    status = json.loads(status_path.read_text()) if status_path.is_file() else {}
    return {"schema": "gate_btc.registry_pit_publication_inventory.v1",
            "status": "INVENTORY_INTEGRITY_PASS" if valid and not rejected else "INVENTORY_INTEGRITY_BLOCKED",
            "published_snapshot_file_count": len(files), "integrity_valid_unique_snapshot_count": len(valid),
            "distinct_source_date_count": len({x["source_data_as_of"] for x in valid}),
            "complete_source_snapshot_count": sum(x["source_coverage_complete"] for x in valid),
            "incomplete_source_snapshot_count": sum(not x["source_coverage_complete"] for x in valid),
            "artifact_status_snapshot_count_preserved": status.get("snapshot_count"),
            "artifact_status_scope": "SINGLE_UPSTREAM_COLLECTION_ARTIFACT",
            "snapshot_count_is_scientific_credit": False, "archive_bytes_verified": False,
            "snapshots": valid, "rejected": rejected, "reporting_only": True,
            "scientific_credit": 0, "economic_credit": 0, "engine_feed": False,
            "orders": 0, "real_capital": 0, "source_admission_authority": False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = inventory(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in {"snapshots", "rejected"}}))
    return 0  # Reporting diagnostics must not become a new scientific publication gate.


if __name__ == "__main__":
    raise SystemExit(main())
