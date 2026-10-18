"""Resolve the unchanged UTC-yesterday target; weekends are no-op, never backfilled."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import json


def resolve_target(now):
    if now.tzinfo is None:
        raise ValueError("timezone-aware timestamp required")
    day = now.astimezone(timezone.utc).date() - timedelta(days=1)
    eligible = day.weekday() < 5
    return {"date": day.isoformat(), "eligible": eligible,
            "status": "CHECK_FROZEN_SOURCE_CALENDAR" if eligible else "NOOP_NON_B3_WEEKDAY_TARGET"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args()
    result = resolve_target(datetime.now(timezone.utc))
    with args.github_output.open("a", encoding="utf-8") as handle:
        handle.write("date=" + result["date"] + "\\n")
        handle.write("eligible=" + str(result["eligible"]).lower() + "\\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
