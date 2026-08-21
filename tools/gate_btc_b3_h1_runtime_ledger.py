#!/usr/bin/env python3
"""Append one qualified B3 H1 structural artifact to a canonical runtime ledger.

Integration only. No economics are evaluated. Missing dates are never synthesized and
failed/pending runs never count. Repeated publication of the same qualified date is
idempotent and conflicting evidence for an existing date fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return obj


def find_status(root: Path) -> Path:
    matches = list(root.rglob("H1_STRUCTURAL_STATUS.json"))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one H1_STRUCTURAL_STATUS.json, found {len(matches)}")
    return matches[0]


def validate_source(s: dict[str, Any]) -> None:
    if s.get("schema") != "gate_btc.b3.h1.cloud_structural.v2":
        raise RuntimeError("unexpected B3 H1 schema")
    if s.get("status") != "STRUCTURAL_PASS" or s.get("qualified") is not True:
        raise RuntimeError("B3 H1 artifact is not a qualified structural pass")
    if int(s.get("h1_increment_candidate", 0)) != 1:
        raise RuntimeError("B3 H1 increment contract did not pass")
    if s.get("research_only") is not True or s.get("shadow_only") is not True or s.get("not_approved") is not True:
        raise RuntimeError("B3 H1 safety flags changed")
    if int(s.get("orders", 0) or 0) != 0 or float(s.get("real_capital", 0) or 0) != 0:
        raise RuntimeError("B3 H1 zero-order/zero-capital lock changed")
    if s.get("economics_locked") is not True or s.get("economic_functions_called") is not False:
        raise RuntimeError("B3 H1 economics lock changed")
    qa = s.get("qa") or {}
    if qa.get("m1_to_m5_exact") is not True or qa.get("tick_grid") != "PASS" or qa.get("ohlc_integrity") != "PASS":
        raise RuntimeError("B3 H1 structural QA did not pass")


def canonical_entry(source: dict[str, Any], status_path: Path, run_id: str) -> dict[str, Any]:
    src = source.get("source") or {}
    return {
        "date": source["date"],
        "qualified": True,
        "WIN": source["front_contracts"]["WIN"],
        "WDO": source["front_contracts"]["WDO"],
        "collector_status": source["status"],
        "collector_schema": source["schema"],
        "source_raw_sha256": src.get("sha256"),
        "status_sha256": sha(status_path),
        "source_run_id": str(run_id),
        "freeze_status": source.get("freeze_status"),
        "upstream_engine_sha256": source.get("upstream_engine_sha256"),
        "full_frozen_schedule_sha256": source.get("full_frozen_schedule_sha256"),
        "h1_schedule_prefix_sha256": source.get("h1_schedule_prefix_sha256"),
        "blind_lock_sha256": source.get("blind_lock_sha256"),
    }


def build(source: dict[str, Any], status_path: Path, existing: dict[str, Any] | None, run_id: str) -> dict[str, Any]:
    validate_source(source)
    entries = list((existing or {}).get("entries", []))
    by_date = {str(x["date"]): x for x in entries}
    entry = canonical_entry(source, status_path, run_id)
    prior = by_date.get(entry["date"])
    if prior is not None:
        comparable = dict(prior)
        comparable.pop("source_run_id", None)
        new = dict(entry)
        new.pop("source_run_id", None)
        if comparable != new:
            raise RuntimeError(f"conflicting B3 H1 evidence for frozen date {entry['date']}")
    else:
        entries.append(entry)
    entries.sort(key=lambda x: x["date"])
    payload = {
        "schema": "gate_btc.b3.h1.runtime_ledger.v1",
        "status": "ACTIVE_STRUCTURAL_COLLECTION",
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "economics_locked": True,
        "backfill_automatically_created": False,
        "valid_observation_count": len(entries),
        "latest_valid_date": entries[-1]["date"] if entries else None,
        "entries": entries,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact-root", type=Path, required=True)
    ap.add_argument("--existing", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()
    status_path = find_status(args.artifact_root)
    source = load(status_path)
    existing = load(args.existing) if args.existing and args.existing.is_file() else None
    payload = build(source, status_path, existing, args.run_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("B3_H1_RUNTIME_LEDGER=PASS")
    print(f"VALID_OBSERVATIONS={payload['valid_observation_count']}")
    print(f"LATEST_VALID_DATE={payload['latest_valid_date']}")
    print("AUTO_BACKFILL=0")
    print("ORDERS=0")
    print("REAL_CAPITAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
