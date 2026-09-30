#!/usr/bin/env python3
"""Preserve same-run Delta evidence when the shared Daily handoff is unavailable."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import date
from pathlib import Path

from tools.gate_btc_delta_paper_monitor import MonitorError, h, load


def preserve(contract: Path, source_zip: Path, runtime: Path, run_id: int, expected_close: str) -> dict:
    date.fromisoformat(expected_close)
    source = load(contract, source_zip)
    manifest = source["manifest"]
    if manifest["data_as_of"] != expected_close:
        raise MonitorError("Delta source is not the exact prospective close")
    strategies = set(source["contract"]["strategies"])
    daily = [row for row in source["daily"] if row.get("date", "")[:10] == expected_close]
    if len(daily) != len(strategies) or {row.get("strategy") for row in daily} != strategies:
        raise MonitorError("Delta source lacks the four same-close strategy rows")
    digest = h(source_zip.read_bytes())
    destination = runtime / "snapshots" / f"{expected_close}.zip"
    receipt = runtime / "snapshots" / f"{expected_close}.json"
    evidence = {
        "schema": "gate_btc.delta_independent_source_receipt.v1",
        "date": expected_close,
        "source_run_id": run_id,
        "source_zip_sha256": digest,
        "source_manifest_data_as_of": manifest["data_as_of"],
        "canonical_contract_sha256": h(contract.read_bytes()),
        "strategy_count": len(strategies),
        "source_only": True,
        "v2a_or_coingecko_required": False,
        "paper_nav_appended": False,
        "scientific_credit": 0,
        "backfill_performed": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    if destination.exists() or receipt.exists():
        if not destination.exists() or not receipt.exists():
            raise MonitorError("Delta source archive is incomplete")
        previous = json.loads(receipt.read_text(encoding="utf-8"))
        if h(destination.read_bytes()) != digest or previous != evidence:
            raise MonitorError("immutable Delta close conflicts with existing archive")
        return {"status": "DUPLICATE_IDENTICAL", **evidence}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as out, source_zip.open("rb") as inp:
        shutil.copyfileobj(inp, out)
    if h(destination.read_bytes()) != digest:
        raise MonitorError("Delta source archive integrity verification failed")
    receipt.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "PRESERVED_UNCREDITED_SOURCE", **evidence}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--contract", type=Path, required=True)
    p.add_argument("--source-zip", type=Path, required=True)
    p.add_argument("--runtime-dir", type=Path, required=True)
    p.add_argument("--source-run-id", type=int, required=True)
    p.add_argument("--expected-close", required=True)
    args = p.parse_args()
    result = preserve(args.contract, args.source_zip, args.runtime_dir, args.source_run_id, args.expected_close)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
