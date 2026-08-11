#!/usr/bin/env python3
"""Fail-closed prospective sealing for GATE BTC V16B.

RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED.
No orders, no capital, no engine feed.

This tool enforces the preregistered V16B prospective boundary:
- no prospective signal before 2026-08-13 UTC;
- no synthetic economics for BLOCKED observations;
- external Delta print cannot be present in the initial self-result seal;
- append-only JSONL ledger with a deterministic SHA-256 seal per row;
- external Delta can only be attached in a second append-only event that
  references an already-sealed V16B observation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

CANDIDATE_ID = "GATE_BTC_V16B_CAUSAL_SHORT_FREEZE_20260811"
FIRST_SIGNAL = date(2026, 8, 13)
FIRST_ENTRY = date(2026, 8, 14)
FIRST_COMPLETE_EXIT = date(2026, 8, 21)

SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "ENGINE_FEED": False,
}

REQUIRED_BASE = {
    "signal_date_utc",
    "entry_date_utc",
    "exit_date_utc",
    "candidate_id",
    "model_hash",
    "code_commit",
    "input_data_hashes",
    "eligible_universe_count",
    "liquidity_qualified_count",
    "shortable_count",
    "longs_10",
    "shorts_10",
    "scores",
    "exposure",
    "trailing_vol",
    "turnover",
    "transaction_cost",
    "short_funding",
    "gross_long_pnl",
    "gross_short_pnl",
    "net_pnl",
    "btc_benchmark_return",
    "source_coverage",
    "status",
    "blocker_reason",
}

ECONOMIC_FIELDS = {
    "exposure",
    "trailing_vol",
    "turnover",
    "transaction_cost",
    "short_funding",
    "gross_long_pnl",
    "gross_short_pnl",
    "net_pnl",
    "btc_benchmark_return",
}


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def parse_date(v: str) -> date:
    return date.fromisoformat(v)


def _require_counts(row: dict[str, Any]) -> None:
    for k in ("eligible_universe_count", "liquidity_qualified_count", "shortable_count"):
        if not isinstance(row[k], int) or row[k] < 0:
            raise ValueError(f"{k} must be a non-negative integer")
    if row["liquidity_qualified_count"] > row["eligible_universe_count"]:
        raise ValueError("liquidity-qualified count exceeds eligible universe")
    if row["shortable_count"] > row["liquidity_qualified_count"]:
        raise ValueError("shortable count exceeds liquidity-qualified count")


def validate_self_row(row: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(REQUIRED_BASE - row.keys())
    if missing:
        raise ValueError(f"missing required fields: {missing}")
    if "external_delta_print" in row or "external_delta" in row:
        raise ValueError("external Delta is forbidden in the initial V16B self-result seal")
    if row["candidate_id"] != CANDIDATE_ID:
        raise ValueError("unexpected candidate_id")

    signal = parse_date(row["signal_date_utc"])
    entry = parse_date(row["entry_date_utc"])
    exit_ = parse_date(row["exit_date_utc"])
    if signal < FIRST_SIGNAL:
        raise ValueError("pre-freeze/backfilled signal cannot count as prospective")
    if entry < FIRST_ENTRY:
        raise ValueError("pre-freeze/backfilled entry cannot count as prospective")
    if exit_ < FIRST_COMPLETE_EXIT:
        raise ValueError("incomplete/pre-freeze weekly return cannot count as prospective")
    if not (signal < entry < exit_):
        raise ValueError("dates must satisfy signal < entry < exit")

    status = row["status"]
    if status not in {"OK", "BLOCKED"}:
        raise ValueError("status must be OK or BLOCKED")
    _require_counts(row)

    if status == "OK":
        if row["blocker_reason"] not in (None, ""):
            raise ValueError("OK row cannot have blocker_reason")
        if not isinstance(row["longs_10"], list) or len(row["longs_10"]) != 10:
            raise ValueError("OK row requires exactly 10 longs")
        if not isinstance(row["shorts_10"], list) or len(row["shorts_10"]) != 10:
            raise ValueError("OK row requires exactly 10 shorts")
        if len(set(row["longs_10"])) != 10 or len(set(row["shorts_10"])) != 10:
            raise ValueError("selected legs must contain unique assets")
        if set(row["longs_10"]) & set(row["shorts_10"]):
            raise ValueError("same asset cannot be both long and short")
        if not isinstance(row["scores"], dict):
            raise ValueError("scores must be a mapping")
        expected = set(row["longs_10"]) | set(row["shorts_10"])
        if set(row["scores"]) != expected:
            raise ValueError("scores must cover exactly the 20 selected assets")
        for k in ECONOMIC_FIELDS:
            if row[k] is None:
                raise ValueError(f"OK row requires economic field {k}")
    else:
        if not row["blocker_reason"]:
            raise ValueError("BLOCKED row requires blocker_reason")
        # A blocked observation remains in the evidence denominator but cannot
        # contain invented portfolio returns or transaction/funding economics.
        for k in ECONOMIC_FIELDS:
            if row[k] is not None:
                raise ValueError(f"BLOCKED row must not contain synthetic economic field {k}")

    sealed = dict(row)
    sealed.update(SAFETY)
    sealed["event_type"] = "V16B_SELF_RESULT_SEAL"
    sealed["seal_sha256"] = sha256_obj({k: sealed[k] for k in sorted(sealed) if k != "seal_sha256"})
    return sealed


def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")


def load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except Exception as e:
                raise ValueError(f"invalid JSONL at line {n}: {e}") from e
    return out


def seal_self(input_path: Path, ledger: Path) -> dict[str, Any]:
    row = json.loads(input_path.read_text(encoding="utf-8"))
    sealed = validate_self_row(row)
    events = load_events(ledger)
    key = sealed["signal_date_utc"]
    if any(e.get("event_type") == "V16B_SELF_RESULT_SEAL" and e.get("signal_date_utc") == key for e in events):
        raise ValueError(f"self-result already sealed for signal {key}; append-only ledger forbids replacement")
    append_jsonl(ledger, sealed)
    return sealed


def attach_delta(signal_date: str, delta_print: float, source_timestamp: str, source_ref: str, ledger: Path) -> dict[str, Any]:
    parse_date(signal_date)
    events = load_events(ledger)
    self_rows = [e for e in events if e.get("event_type") == "V16B_SELF_RESULT_SEAL" and e.get("signal_date_utc") == signal_date]
    if len(self_rows) != 1:
        raise ValueError("external Delta may be attached only after exactly one sealed V16B self-result exists")
    if any(e.get("event_type") == "EXTERNAL_DELTA_ATTACHMENT" and e.get("signal_date_utc") == signal_date for e in events):
        raise ValueError("external Delta already attached for this signal; append-only ledger forbids replacement")
    base = self_rows[0]
    event = {
        "event_type": "EXTERNAL_DELTA_ATTACHMENT",
        "signal_date_utc": signal_date,
        "candidate_id": CANDIDATE_ID,
        "self_seal_sha256": base["seal_sha256"],
        "external_delta_print": float(delta_print),
        "external_source_timestamp": source_timestamp,
        "external_source_ref": source_ref,
        **SAFETY,
    }
    event["seal_sha256"] = sha256_obj({k: event[k] for k in sorted(event) if k != "seal_sha256"})
    append_jsonl(ledger, event)
    return event


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("seal-self")
    a.add_argument("--input", required=True)
    a.add_argument("--ledger", required=True)
    b = sub.add_parser("attach-delta")
    b.add_argument("--signal-date", required=True)
    b.add_argument("--delta-print", required=True, type=float)
    b.add_argument("--source-timestamp", required=True)
    b.add_argument("--source-ref", required=True)
    b.add_argument("--ledger", required=True)
    args = p.parse_args()
    if args.cmd == "seal-self":
        event = seal_self(Path(args.input), Path(args.ledger))
    else:
        event = attach_delta(args.signal_date, args.delta_print, args.source_timestamp, args.source_ref, Path(args.ledger))
    print(json.dumps({
        "status": "PASS",
        "event_type": event["event_type"],
        "seal_sha256": event["seal_sha256"],
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
        "ENGINE_FEED": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
