#!/usr/bin/env python3
"""Bounded idempotent entrypoint for QOS three-track prospective collection.

A repeated workflow may legitimately deliver the same already-sealed snapshot date
under a different GitHub source run ID. For an existing date, compare using the
original sealed source_run_id so the canonical sidecar can prove the entire
scientific row is otherwise byte-for-byte identical. Any material change still
fails closed as same-date revision/backfill. Existing evidence is never rewritten.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

import gate_btc_qos_prospective_three_track as core

_ORIGINAL_APPEND_PATH = core.append_path


def append_path_idempotent(state, root, master, day, runid):
    day = pd.Timestamp(day).normalize()
    out = Path(root) / "snapshots" / f"{day.date().isoformat()}.json"
    effective_runid = runid
    if out.exists():
        existing = core.load(out)
        core.req(existing.get("row_sha256") == core.sharow(existing), "existing same-date hash mismatch")
        core.req(str(existing.get("snapshot_date")) == day.date().isoformat(), "existing same-date identity mismatch")
        core.req(str(existing.get("source_run_id", "")).strip(), "existing same-date source_run_id missing")
        effective_runid = existing["source_run_id"]
    return _ORIGINAL_APPEND_PATH(state, root, master, day, effective_runid)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--v2a-zip", required=True)
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--snapshot-date", required=True)
    parser.add_argument("--source-run-id", required=True)
    args = parser.parse_args()

    core.append_path = append_path_idempotent
    result = core.process(
        Path(args.v2a_zip),
        core.contract(Path(args.contract)),
        Path(args.runtime_dir),
        args.snapshot_date,
        args.source_run_id,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
