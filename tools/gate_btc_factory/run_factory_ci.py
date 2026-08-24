#!/usr/bin/env python3
"""CI wrapper for the QRDS factory shadow runner.

Runs only against repository files, writes only a temporary factory-owned status file,
adds explicit source freshness metadata, and never mutates active QRDS paths.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import run_factory

FACTORY_DIR = Path(__file__).resolve().parent
REPO_ROOT = FACTORY_DIR.parents[1]
OUTPUT = FACTORY_DIR / "FACTORY_STATUS_RUNTIME.json"
FRESH_MINUTES = 180


def parse_utc(value: str) -> datetime:
    if not value:
        raise SystemExit("FAIL missing source generated_at_utc")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SystemExit(f"FAIL invalid source generated_at_utc: {value}") from exc
    if parsed.tzinfo is None:
        raise SystemExit("FAIL source generated_at_utc must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def main() -> int:
    master = run_factory.load_json(FACTORY_DIR / "MASTER_STATE.json")
    schema = run_factory.load_json(FACTORY_DIR / "FACTORY_REPORT_SCHEMA.v1.json")
    source_rel = master.get("source_status")
    if source_rel != "tools/gate_btc_research_factory_status.json":
        raise SystemExit("FAIL unexpected source_status binding")
    source_path = REPO_ROOT / source_rel
    source = run_factory.load_json(source_path)
    report = run_factory.build_report(source, master, source_path)
    run_factory.validate_report(report, schema)

    now = datetime.now(timezone.utc)
    source_time = parse_utc(source.get("generated_at_utc"))
    age_minutes = max(0.0, (now - source_time).total_seconds() / 60.0)
    freshness = "FRESH" if age_minutes <= FRESH_MINUTES else "STALE_READ_ONLY"
    report["source_freshness"] = {
        "status": freshness,
        "age_minutes": round(age_minutes, 2),
        "freshness_limit_minutes": FRESH_MINUTES,
        "policy": "STALE_SOURCE_MAY_BE_REPORTED_BUT_MUST_NOT_DRIVE_PROMOTION_OR_ACTIVE_MUTATION",
    }
    report["parity_readiness"]["source_freshness"] = freshness
    if freshness != "FRESH":
        report["blockers"] = list(report.get("blockers", [])) + [
            "Factory source status is stale; output is read-only informational and cannot support transition/promotion."
        ]

    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("PASS QRDS factory CI shadow cycle", json.dumps({
        "freshness": freshness,
        "age_minutes": round(age_minutes, 2),
        "queue_counts": report["queue_counts"],
        "output": str(OUTPUT.relative_to(REPO_ROOT)),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
