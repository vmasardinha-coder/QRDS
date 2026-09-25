#!/usr/bin/env python3
"""Persist contemporaneous V16B CMC captures into the canonical runtime evidence corpus.

Mechanical provenance plumbing only. This tool does not create SIGNAL/ENTRY/RESULT
seals, prospective credit, training labels, orders, or capital usage. It stores only
Thursday captures that already passed the upstream CMC capture contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _single(root: Path, suffix: str) -> Path:
    found = sorted(root.glob(f"*{suffix}"))
    if len(found) != 1:
        raise ValueError(f"expected exactly one {suffix} file, found {len(found)}")
    return found[0]


def _load_and_validate(capture_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    raw = _single(capture_dir, ".raw.json")
    evidence = _single(capture_dir, ".evidence.json")
    ev = json.loads(evidence.read_text(encoding="utf-8"))
    required = {
        "schema", "snapshot_id", "snapshot_date", "available_at_utc", "source_ref",
        "raw_snapshot_sha256", "rows", "research_only", "shadow_only", "not_approved",
        "engine_feed", "orders", "real_capital",
    }
    missing = required - set(ev)
    if missing:
        raise ValueError(f"evidence missing fields: {sorted(missing)}")
    if ev["schema"] != "gate_btc.v16b.cmc_universe_snapshot_evidence.v1":
        raise ValueError("unexpected CMC evidence schema")
    if sha256_file(raw) != str(ev["raw_snapshot_sha256"]).lower():
        raise ValueError("raw snapshot hash mismatch")
    if int(ev["rows"]) < 100:
        raise ValueError("CMC snapshot has fewer than 100 rows")
    if not str(ev["available_at_utc"]).endswith("Z"):
        raise ValueError("available_at_utc must be UTC Z timestamp")
    if ev["research_only"] is not True or ev["shadow_only"] is not True or ev["not_approved"] is not True:
        raise ValueError("research/shadow safety flags changed")
    if ev["engine_feed"] is not False or int(ev["orders"]) != 0 or int(ev["real_capital"]) != 0:
        raise ValueError("execution safety boundary violated")
    if raw.name != f"{ev['snapshot_id']}.raw.json" or evidence.name != f"{ev['snapshot_id']}.evidence.json":
        raise ValueError("snapshot_id does not match capture filenames")
    return raw, evidence, ev


def persist(capture_dir: Path, runtime_root: Path, run_id: str) -> dict[str, Any]:
    if not str(run_id).isdigit():
        raise ValueError("run_id must be numeric")
    raw, evidence, ev = _load_and_validate(capture_dir)
    snapshot_date = str(ev["snapshot_date"])
    import datetime as dt
    day = dt.date.fromisoformat(snapshot_date)
    if day.weekday() != 3:
        return {
            "status": "NOT_THURSDAY_NO_PERSIST",
            "snapshot_date": snapshot_date,
            "snapshot_id": ev["snapshot_id"],
            "run_id": str(run_id),
            "ORDERS": 0,
            "REAL_CAPITAL": 0,
        }

    base = runtime_root / "runtime" / "evidence" / "v16b" / "cmc_weekly"
    dest = base / snapshot_date / f"run_{run_id}"
    index = base / "INDEX.jsonl"
    record = {
        "schema": "gate_btc.v16b.cmc_weekly_runtime_record.v1",
        "snapshot_date": snapshot_date,
        "snapshot_id": ev["snapshot_id"],
        "available_at_utc": ev["available_at_utc"],
        "source_ref": ev["source_ref"],
        "raw_snapshot_sha256": ev["raw_snapshot_sha256"],
        "evidence_sha256": sha256_file(evidence),
        "rows": int(ev["rows"]),
        "github_run_id": int(run_id),
        "path": str(dest.relative_to(runtime_root)).replace("\\", "/"),
        "prospective_credit": 0,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital": 0,
    }

    existing_records: list[dict[str, Any]] = []
    if index.exists():
        for line in index.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing_records.append(json.loads(line))
    same = [r for r in existing_records if int(r.get("github_run_id", -1)) == int(run_id)]
    if same:
        if len(same) != 1 or same[0] != record:
            raise ValueError("existing run_id record conflicts with current capture")
        if not dest.exists():
            raise ValueError("index contains run_id but evidence directory is missing")
        return {"status": "ALREADY_PERSISTED", **record, "ORDERS": 0, "REAL_CAPITAL": 0}

    if dest.exists():
        raise ValueError("destination exists without matching INDEX record")
    dest.mkdir(parents=True, exist_ok=False)
    shutil.copy2(raw, dest / raw.name)
    shutil.copy2(evidence, dest / evidence.name)
    manifest = dest / "PERSISTENCE.json"
    manifest.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    base.mkdir(parents=True, exist_ok=True)
    with index.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")

    return {"status": "PERSISTED", **record, "ORDERS": 0, "REAL_CAPITAL": 0}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--capture-dir", required=True)
    p.add_argument("--runtime-root", required=True)
    p.add_argument("--run-id", required=True)
    a = p.parse_args()
    result = persist(Path(a.capture_dir), Path(a.runtime_root), a.run_id)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
