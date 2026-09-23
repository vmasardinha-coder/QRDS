#!/usr/bin/env python3
"""Read-only freshness monitor for prospective research collectors.

This is operational observability only. It does not mutate collection cadence,
scientific criteria, runtime records, economic mappings, or credit.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_MINUTES = {
    "F-XAGENT-DISAGREE": 60,
    "F-XMM-INVENTORY": 240,
    "F-XVOL-SURFACE": 240,
}


def parse_utc(value: str) -> datetime:
    value = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)


def classify(age_minutes: float, expected_minutes: int) -> str:
    # Operational-only tolerance: warn after 1.5x cadence; hard-stale after 2x.
    if age_minutes > expected_minutes * 2:
        return "HARD_STALE"
    if age_minutes > expected_minutes * 1.5:
        return "STALE_WARNING"
    return "FRESH"


def read_observation(path: Path, family_id: str) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("family_id") != family_id:
        raise ValueError(f"family mismatch for {family_id}: {data.get('family_id')!r}")
    if family_id == "F-XAGENT-DISAGREE":
        return data["generated_at_utc"]
    return data["latest_observed_at_utc"]


def evaluate(now: datetime, paths: dict[str, Path]) -> dict:
    rows = []
    hard_stale = False
    for family_id, path in paths.items():
        observed = parse_utc(read_observation(path, family_id))
        age_minutes = max(0.0, (now - observed).total_seconds() / 60.0)
        expected = EXPECTED_MINUTES[family_id]
        status = classify(age_minutes, expected)
        hard_stale = hard_stale or status == "HARD_STALE"
        rows.append(
            {
                "family_id": family_id,
                "observed_at_utc": observed.isoformat().replace("+00:00", "Z"),
                "age_minutes": round(age_minutes, 3),
                "expected_cadence_minutes": expected,
                "status": status,
            }
        )
    return {
        "schema": "gate_btc_2.prospective_collector_freshness.v1",
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "operational_only": True,
        "scientific_criteria_changed": False,
        "collection_cadence_changed": False,
        "runtime_mutation": False,
        "economic_outcomes_read": False,
        "hard_stale": hard_stale,
        "collectors": rows,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--xagent", type=Path, required=True)
    p.add_argument("--xmm", type=Path, required=True)
    p.add_argument("--xvol", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--now-utc", default=None, help="ISO timestamp; tests/repro only")
    args = p.parse_args()

    now = parse_utc(args.now_utc) if args.now_utc else datetime.now(timezone.utc)
    result = evaluate(
        now,
        {
            "F-XAGENT-DISAGREE": args.xagent,
            "F-XMM-INVENTORY": args.xmm,
            "F-XVOL-SURFACE": args.xvol,
        },
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 2 if result["hard_stale"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
