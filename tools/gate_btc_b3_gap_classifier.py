#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

COUNT_RE = re.compile(r"(?:WIN|WDO)_M5_COUNT got=(\d+) expected=(\d+)")
LATTICE_RE = re.compile(r"(?:WIN|WDO)_M5_LATTICE_MISMATCH missing=(\d+) extra=(\d+)")


def classify(text: str) -> tuple[bool, str | None]:
    """Return (ordinary_gap, matched_reason).

    Only an incomplete expected M5 lattice is treated as an operational source gap.
    Extra bars, schema/contract/tick/OHLC mismatches and processing errors remain hard
    failures.  No coverage threshold is invented here and no incomplete observation is
    promoted to scientific eligibility.
    """
    m = COUNT_RE.search(text)
    if m:
        got, expected = map(int, m.groups())
        if 0 <= got < expected:
            return True, m.group(0)
    m = LATTICE_RE.search(text)
    if m:
        missing, extra = map(int, m.groups())
        if missing > 0 and extra == 0:
            return True, m.group(0)
    return False, None


def write_gap(path: Path, *, stream: str, date: str, reason: str, source_status: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "gate_btc.b3.operational_gap.v1",
        "stream": stream,
        "date": date,
        "classification": "ORDINARY_SOURCE_GAP",
        "reason": reason,
        "scientifically_qualified": False,
        "eligible_observation_increment": 0,
        "synthetic_backfill": False,
        "research_only": True,
        "shadow_only": True,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if source_status:
        src = source_status.get("source") or {}
        payload["source"] = {
            "state": src.get("state"),
            "http_status": src.get("http_status"),
            "sha256": src.get("sha256"),
            "bytes": src.get("bytes"),
        }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def h1(args: argparse.Namespace) -> int:
    status_path = Path(args.status)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status.get("status") == "STRUCTURAL_PASS" and status.get("qualified") is True:
        print("B3_GAP_CLASS=QUALIFIED_PASS")
        return 0
    text = str(status.get("error") or "")
    ordinary, reason = classify(text)
    if not ordinary:
        print(f"B3_GAP_CLASS=TRUE_PROCESSING_FAILURE reason={text}")
        return 2
    if args.out:
        write_gap(Path(args.out), stream="H1", date=str(status.get("date")), reason=str(reason), source_status=status)
    print(f"B3_GAP_CLASS=ORDINARY_SOURCE_GAP reason={reason}")
    print("SCIENTIFICALLY_QUALIFIED=0")
    print("H1_INCREMENT=0")
    return 0


def log_mode(args: argparse.Namespace) -> int:
    text = Path(args.log).read_text(encoding="utf-8", errors="replace")
    ordinary, reason = classify(text)
    if not ordinary:
        print("B3_GAP_CLASS=TRUE_PROCESSING_FAILURE")
        return 2
    if args.out:
        write_gap(Path(args.out), stream=args.stream, date=args.date, reason=str(reason))
    print(f"B3_GAP_CLASS=ORDINARY_SOURCE_GAP reason={reason}")
    print("SCIENTIFICALLY_QUALIFIED=0")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)

    p = sub.add_parser("h1")
    p.add_argument("--status", required=True)
    p.add_argument("--out")
    p.set_defaults(fn=h1)

    p = sub.add_parser("log")
    p.add_argument("--log", required=True)
    p.add_argument("--stream", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--out")
    p.set_defaults(fn=log_mode)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
