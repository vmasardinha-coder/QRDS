#!/usr/bin/env python3
"""Append-only hash-linked ledger for admitted Stage 9 forward captures.

The ledger is storage/verification plumbing only. It cannot collect or admit market data.
Every appended admission must already pass the Stage 9 physical reviewer/bridge contract.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from tools.gate_btc_2_prospective_counter_bridge import (
    STAGE9_COLLECTOR_ID,
    build_counter,
    canonical_hash,
    validate_admission,
)

LEDGER_SCHEMA = "gate_btc.2_0.stage9_admission_ledger_record.v1"
GENESIS = "GENESIS"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def record_content_hash(record: dict[str, Any]) -> str:
    payload = dict(record)
    payload.pop("record_sha256", None)
    return canonical_hash(payload)


def make_record(admission: dict[str, Any], sequence: int, previous_record_sha256: str) -> dict[str, Any]:
    validate_admission(admission)
    require(isinstance(sequence, int) and not isinstance(sequence, bool) and sequence >= 1, "ledger sequence invalid")
    if sequence == 1:
        require(previous_record_sha256 == GENESIS, "first ledger record must bind GENESIS")
    else:
        require(isinstance(previous_record_sha256, str) and len(previous_record_sha256) == 64, "previous record hash invalid")
    record = {
        "schema": LEDGER_SCHEMA,
        "collector_id": STAGE9_COLLECTOR_ID,
        "sequence": sequence,
        "previous_record_sha256": previous_record_sha256,
        "run_id": admission["run_id"],
        "capture_id": f"gate2-stage9-run-{admission['run_id']}",
        "captured_at_utc": admission["captured_at_utc"],
        "admission_artifact_sha256": admission["admission_artifact_sha256"],
        "review_sha256": admission["review_sha256"],
        "capture_manifest_sha256": admission["capture_manifest_sha256"],
        "admission": admission,
    }
    record["record_sha256"] = record_content_hash(record)
    return record


def parse_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    require(path.is_file(), "ledger path is not a file")
    records: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        require(raw.strip() != "", f"blank ledger line at {line_number}")
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid ledger JSON at line {line_number}") from exc
        require(isinstance(row, dict), f"ledger line {line_number} must be an object")
        records.append(row)
    return records


def validate_ledger(records: list[dict[str, Any]]) -> None:
    require(isinstance(records, list), "ledger records must be a list")
    previous_hash = GENESIS
    previous_time: str | None = None
    seen_runs: set[int] = set()
    seen_admissions: set[str] = set()
    for idx, record in enumerate(records, 1):
        require(record.get("schema") == LEDGER_SCHEMA, f"ledger schema invalid at sequence {idx}")
        require(record.get("collector_id") == STAGE9_COLLECTOR_ID, f"collector binding mismatch at sequence {idx}")
        require(record.get("sequence") == idx, f"non-contiguous ledger sequence at {idx}")
        require(record.get("previous_record_sha256") == previous_hash, f"ledger chain break at sequence {idx}")
        require(record.get("record_sha256") == record_content_hash(record), f"ledger record hash mismatch at sequence {idx}")
        admission = record.get("admission")
        require(isinstance(admission, dict), f"embedded admission missing at sequence {idx}")
        validate_admission(admission)
        require(record.get("run_id") == admission["run_id"], f"run binding mismatch at sequence {idx}")
        require(record.get("capture_id") == f"gate2-stage9-run-{admission['run_id']}", f"capture binding mismatch at sequence {idx}")
        require(record.get("captured_at_utc") == admission["captured_at_utc"], f"capture time binding mismatch at sequence {idx}")
        require(record.get("admission_artifact_sha256") == admission["admission_artifact_sha256"], f"admission hash binding mismatch at sequence {idx}")
        require(record.get("review_sha256") == admission["review_sha256"], f"review hash binding mismatch at sequence {idx}")
        require(record.get("capture_manifest_sha256") == admission["capture_manifest_sha256"], f"manifest hash binding mismatch at sequence {idx}")
        run_id = admission["run_id"]
        require(run_id not in seen_runs, f"duplicate run_id in ledger: {run_id}")
        seen_runs.add(run_id)
        admission_hash = admission["admission_artifact_sha256"]
        require(admission_hash not in seen_admissions, f"duplicate admission in ledger: {admission_hash}")
        seen_admissions.add(admission_hash)
        captured = admission["captured_at_utc"]
        if previous_time is not None:
            require(captured > previous_time, f"non-monotonic prospective clock at sequence {idx}")
        previous_time = captured
        previous_hash = record["record_sha256"]


def admissions_from_ledger(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validate_ledger(records)
    return [record["admission"] for record in records]


def counter_from_ledger(records: list[dict[str, Any]]) -> dict[str, Any]:
    return build_counter(admissions_from_ledger(records))


def append_admission(path: Path, admission: dict[str, Any]) -> dict[str, Any]:
    """Append one validated admission without rewriting any prior ledger bytes."""
    records = parse_ledger(path)
    validate_ledger(records)
    validate_admission(admission)
    existing_runs = {r["run_id"] for r in records}
    existing_admissions = {r["admission_artifact_sha256"] for r in records}
    require(admission["run_id"] not in existing_runs, f"run_id already present: {admission['run_id']}")
    require(admission["admission_artifact_sha256"] not in existing_admissions, "admission already present")
    if records:
        require(admission["captured_at_utc"] > records[-1]["captured_at_utc"], "new admission must advance prospective clock")
        previous = records[-1]["record_sha256"]
    else:
        previous = GENESIS
    record = make_record(admission, len(records) + 1, previous)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)
    verified = parse_ledger(path)
    validate_ledger(verified)
    require(verified[-1]["record_sha256"] == record["record_sha256"], "append verification mismatch")
    return record


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--append-admission", type=Path)
    p.add_argument("--counter-out", type=Path)
    args = p.parse_args()
    if args.append_admission:
        admission = json.loads(args.append_admission.read_text(encoding="utf-8"))
        appended = append_admission(args.ledger, admission)
        print(f"APPENDED_SEQUENCE={appended['sequence']}")
    records = parse_ledger(args.ledger)
    validate_ledger(records)
    counter = counter_from_ledger(records)
    if args.counter_out:
        args.counter_out.parent.mkdir(parents=True, exist_ok=True)
        args.counter_out.write_text(json.dumps(counter, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"STAGE9_LEDGER_RECORDS={len(records)}")
    print(f"STAGE9_CANONICAL_COUNTER={counter['canonical_counter']}")
    print("PROSPECTIVE_CREDIT_FROM_BACKFILL=0")
    print("STAGE9_COMPLETE=false ENGINE_FEED=false ORDERS=0 REAL_CAPITAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
