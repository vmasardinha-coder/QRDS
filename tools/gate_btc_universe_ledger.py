#!/usr/bin/env python3
"""Immutable point-in-time Gateway universe archive for research evidence only.

This ledger preserves the exact ``scanner_top500_raw.csv`` bytes emitted by an
eligible Gateway public-data run. It is deliberately write-only from the
strategy engine's perspective: nothing here is an input to V2A, Delta, Gateway
selection, or any other frozen methodology.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
from datetime import date
from pathlib import Path
from typing import Any


ALLOWED_SNAPSHOT_STATUS = {
    "SNAPSHOT_USABLE_RESEARCH_ONLY",
    "SNAPSHOT_USABLE_WITH_DATA_WARNINGS",
}
REQUIRED_COLUMNS = {
    "base",
    "cg_rank",
    "cg_name",
    "cg_market_cap",
    "cg_volume",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_sha(payload: dict[str, Any], field: str) -> str:
    clean = dict(payload)
    clean.pop(field, None)
    raw = json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(raw)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_immutable_bytes(path: Path, raw: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        require(path.read_bytes() == raw, f"immutable file differs: {path}")
        return True
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_bytes(raw)
    os.replace(tmp, path)
    return False


def parse_csv(raw: bytes) -> tuple[list[str], int]:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    columns = reader.fieldnames or []
    require(REQUIRED_COLUMNS.issubset(set(columns)), "Gateway universe CSV missing required columns")
    rows = sum(1 for _ in reader)
    require(rows > 0, "Gateway universe CSV is empty")
    return columns, rows


def iso_day(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise RuntimeError(f"invalid {field}: {value}") from exc


def snapshot_records(ledger_dir: Path) -> list[Path]:
    return sorted((ledger_dir / "snapshots").glob("*.json"))


def validate_record(path: Path, record: dict[str, Any], ledger_dir: Path) -> None:
    require(record.get("record_sha256") == canonical_sha(record, "record_sha256"), f"invalid record hash: {path}")
    require(record.get("research_only") is True, f"research_only changed: {path}")
    require(record.get("shadow_only") is True, f"shadow_only changed: {path}")
    require(record.get("not_approved") is True, f"not_approved changed: {path}")
    require(record.get("feeds_frozen_engine") is False, f"universe ledger must not feed frozen engine: {path}")
    require(record.get("retrospective_reconstruction") is False, f"retrospective reconstruction prohibited: {path}")
    archive_rel = record.get("archive_path")
    require(isinstance(archive_rel, str) and archive_rel, f"archive path missing: {path}")
    archive_path = ledger_dir / archive_rel
    require(archive_path.is_file(), f"archive missing: {archive_path}")
    compressed = archive_path.read_bytes()
    require(sha256_bytes(compressed) == record.get("archive_sha256"), f"archive hash mismatch: {archive_path}")
    raw = gzip.decompress(compressed)
    require(sha256_bytes(raw) == record.get("raw_csv_sha256"), f"raw CSV hash mismatch: {archive_path}")
    require(len(raw) == int(record.get("raw_csv_size_bytes", -1)), f"raw CSV size mismatch: {archive_path}")


def append(args: argparse.Namespace) -> int:
    manifest = load_json(args.manifest)
    snapshot_status = load_json(args.snapshot_status)
    raw = args.raw_csv.read_bytes()
    columns, row_count = parse_csv(raw)

    source_day = str(manifest.get("data_as_of", ""))
    iso_day(source_day, "Gateway data_as_of")
    require(manifest.get("technical_status") == "PASS", "Gateway technical status must be PASS")
    require(manifest.get("operational_status") == "NOT_APPROVED", "Gateway operational status changed")
    require(
        manifest.get("retrospective_performance_status") == "PROHIBITED_CURRENT_COMPOSITION",
        "retrospective current-composition performance must remain prohibited",
    )
    require(snapshot_status.get("snapshot_status") in ALLOWED_SNAPSHOT_STATUS, "Gateway snapshot is not research-usable")
    require(snapshot_status.get("operational_status") == "NOT_APPROVED", "snapshot operational status changed")
    require(
        snapshot_status.get("evidence_status") == "SNAPSHOT_ONLY_NO_WALK_FORWARD_BACKTEST",
        "snapshot evidence boundary changed",
    )
    require(int(manifest.get("universe_rows", -1)) == row_count, "Gateway universe row count differs from manifest")
    require(args.source_run_id.isdigit(), "source_run_id must be a GitHub Actions numeric run ID")
    expected_id = f"{source_day}-run-{args.source_run_id}"
    require(args.snapshot_id == expected_id, f"snapshot_id must equal {expected_id}")

    ledger_dir = args.ledger_dir
    record_path = ledger_dir / "snapshots" / f"{args.snapshot_id}.json"
    archive_rel = Path("archives") / f"{args.snapshot_id}.scanner_top500_raw.csv.gz"
    archive_path = ledger_dir / archive_rel

    raw_sha = sha256_bytes(raw)
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    archive_sha = sha256_bytes(compressed)
    manifest_sha = sha256_bytes(args.manifest.read_bytes())
    snapshot_status_sha = sha256_bytes(args.snapshot_status.read_bytes())

    if record_path.exists():
        existing = load_json(record_path)
        validate_record(record_path, existing, ledger_dir)
        require(existing.get("snapshot_id") == args.snapshot_id, "existing universe snapshot ID mismatch")
        require(existing.get("source_run_id") == args.source_run_id, "existing source run ID mismatch")
        require(existing.get("raw_csv_sha256") == raw_sha, "immutable universe snapshot bytes changed")
        require(existing.get("source_manifest_sha256") == manifest_sha, "immutable source manifest changed")
        require(existing.get("source_snapshot_status_sha256") == snapshot_status_sha, "immutable source status changed")
        print(json.dumps({
            "result": "IDENTICAL_ALREADY_RECORDED",
            "snapshot_id": args.snapshot_id,
            "sequence": existing.get("sequence"),
            "raw_csv_sha256": raw_sha,
            "counter_incremented": False,
            "research_only": True,
            "feeds_frozen_engine": False,
        }, indent=2))
        return 0

    records = snapshot_records(ledger_dir)
    previous: dict[str, Any] | None = None
    if records:
        previous = load_json(records[-1])
        validate_record(records[-1], previous, ledger_dir)
        require(
            iso_day(source_day, "Gateway data_as_of") >= iso_day(str(previous.get("source_data_as_of")), "previous universe data_as_of"),
            "Gateway universe source date moved backwards; retrospective backfill is prohibited",
        )
        require(previous.get("source_run_id") != args.source_run_id, "source run ID already recorded under another snapshot")

    sequence = int(previous.get("sequence", 0)) + 1 if previous else 1
    record: dict[str, Any] = {
        "schema": "gate_btc.gateway_point_in_time_universe_snapshot.v1",
        "sequence": sequence,
        "snapshot_id": args.snapshot_id,
        "source_data_as_of": source_day,
        "source_run_id": args.source_run_id,
        "source_run_utc": manifest.get("run_utc"),
        "gateway_version": manifest.get("version"),
        "gateway_data_quality_status": manifest.get("data_quality_status"),
        "gateway_snapshot_status": snapshot_status.get("snapshot_status"),
        "gateway_warning_failed_checks": snapshot_status.get("warning_failed_checks", []),
        "row_count": row_count,
        "columns": columns,
        "raw_csv_size_bytes": len(raw),
        "raw_csv_sha256": raw_sha,
        "archive_path": archive_rel.as_posix(),
        "archive_sha256": archive_sha,
        "archive_format": "gzip_mtime_0_exact_csv_bytes",
        "source_manifest_sha256": manifest_sha,
        "source_snapshot_status_sha256": snapshot_status_sha,
        "purpose": "FUTURE_POINT_IN_TIME_UNIVERSE_EVIDENCE_ONLY",
        "survivorship_bias_use": "FORWARD_OBSERVATION_ONLY_NO_RETROACTIVE_ENGINE_FEED",
        "feeds_frozen_engine": False,
        "retrospective_reconstruction": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }
    record["record_sha256"] = canonical_sha(record, "record_sha256")

    write_immutable_bytes(archive_path, compressed)
    atomic_json(record_path, record)

    status: dict[str, Any] = {
        "schema": "gate_btc.gateway_point_in_time_universe_ledger_status.v1",
        "status": "ACTIVE_RESEARCH_ONLY",
        "snapshot_count": sequence,
        "latest_snapshot_id": args.snapshot_id,
        "latest_source_data_as_of": source_day,
        "latest_source_run_id": args.source_run_id,
        "latest_raw_csv_sha256": raw_sha,
        "future_point_in_time_only": True,
        "retrospective_backfill_allowed": False,
        "feeds_frozen_engine": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }
    status["status_sha256"] = canonical_sha(status, "status_sha256")
    atomic_json(ledger_dir / "STATUS.json", status)

    print(json.dumps({
        "result": "APPENDED_POINT_IN_TIME_UNIVERSE_SNAPSHOT",
        "snapshot_id": args.snapshot_id,
        "sequence": sequence,
        "row_count": row_count,
        "raw_csv_sha256": raw_sha,
        "archive_sha256": archive_sha,
        "research_only": True,
        "feeds_frozen_engine": False,
    }, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("append")
    p.add_argument("--raw-csv", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--snapshot-status", type=Path, required=True)
    p.add_argument("--snapshot-id", required=True)
    p.add_argument("--source-run-id", required=True)
    p.add_argument("--ledger-dir", type=Path, required=True)
    p.set_defaults(func=append)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
