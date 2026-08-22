#!/usr/bin/env python3
"""Isolated V16B rehearsal wrapper.

This module reuses the frozen prospective signal/entry builders and dual-rank
validators, but writes only to a rehearsal ledger and stamps every event as
non-canonical. Rehearsal events NEVER advance the prospective clock.

RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED / ORDERS=0 / REAL_CAPITAL=0.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools import gate_btc_v16b_prospective_chain as chain
from tools import gate_btc_v16b_prospective_entry as entry_builder
from tools import gate_btc_v16b_prospective_signal as signal_builder

REHEARSAL_PROTOCOL_VERSION = "V16B_REHEARSAL_1D_V1_20260822"
REHEARSAL_FIELDS = {
    "REHEARSAL": True,
    "PROSPECTIVE_COUNT": 0,
    "CANONICAL_LEDGER": False,
    "REHEARSAL_PROTOCOL_VERSION": REHEARSAL_PROTOCOL_VERSION,
}


def _assert_rehearsal_ledger(path: Path) -> None:
    lowered = str(path).replace("\\", "/").lower()
    if "rehearsal" not in lowered:
        raise ValueError("rehearsal output ledger path must contain 'rehearsal'")
    if "prospective" in lowered and "rehearsal" not in path.name.lower():
        raise ValueError("refusing canonical-looking prospective ledger path")


def _mark(row: dict) -> dict:
    out = dict(row)
    out.update(REHEARSAL_FIELDS)
    out.update(
        RESEARCH_ONLY=True,
        SHADOW_ONLY=True,
        NOT_APPROVED=True,
        ORDERS=0,
        REAL_CAPITAL=0,
        ENGINE_FEED=False,
    )
    return out


def build_and_seal_signal(panel: Path, historical_shortability: Path, signal_date: str,
                          universe_snapshot: Path, universe_snapshot_evidence: Path,
                          code_commit: str, ledger: Path, output: Path) -> dict:
    _assert_rehearsal_ledger(ledger)
    built = signal_builder.build(
        panel, historical_shortability,
        signal_builder.pd.Timestamp(signal_date),
        universe_snapshot, universe_snapshot_evidence,
        code_commit,
    )
    event = chain.validate_signal_row(_mark(built))
    chain.base.append_jsonl(ledger, event)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(event, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return event


def build_and_seal_entry(signal_event_path: Path, usdm_exchange_info: Path,
                         spot_exchange_info: Path, ledger: Path, output: Path) -> dict:
    _assert_rehearsal_ledger(ledger)
    signal_event = json.loads(signal_event_path.read_text(encoding="utf-8"))
    for k, v in REHEARSAL_FIELDS.items():
        if signal_event.get(k) != v:
            raise ValueError(f"signal event missing rehearsal invariant {k}={v!r}")
    built = entry_builder.build(signal_event, usdm_exchange_info, spot_exchange_info)
    event = chain.validate_entry_row(_mark(built), signal_event)
    chain.base.append_jsonl(ledger, event)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(event, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return event


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("signal")
    s.add_argument("--panel", required=True)
    s.add_argument("--historical-shortability", required=True)
    s.add_argument("--signal-date", required=True)
    s.add_argument("--universe-snapshot", required=True)
    s.add_argument("--universe-snapshot-evidence", required=True)
    s.add_argument("--code-commit", required=True)
    s.add_argument("--ledger", required=True)
    s.add_argument("--output", required=True)

    e = sub.add_parser("entry")
    e.add_argument("--signal-event", required=True)
    e.add_argument("--usdm-exchange-info", required=True)
    e.add_argument("--spot-exchange-info", required=True)
    e.add_argument("--ledger", required=True)
    e.add_argument("--output", required=True)

    a = p.parse_args()
    if a.cmd == "signal":
        event = build_and_seal_signal(
            Path(a.panel), Path(a.historical_shortability), a.signal_date,
            Path(a.universe_snapshot), Path(a.universe_snapshot_evidence),
            a.code_commit, Path(a.ledger), Path(a.output),
        )
    else:
        event = build_and_seal_entry(
            Path(a.signal_event), Path(a.usdm_exchange_info), Path(a.spot_exchange_info),
            Path(a.ledger), Path(a.output),
        )
    print(json.dumps({
        "event_type": event["event_type"],
        "status": event["status"],
        "REHEARSAL": event["REHEARSAL"],
        "PROSPECTIVE_COUNT": event["PROSPECTIVE_COUNT"],
        "CANONICAL_LEDGER": event["CANONICAL_LEDGER"],
        "ORDERS": event["ORDERS"],
        "REAL_CAPITAL": event["REAL_CAPITAL"],
    }, sort_keys=True))
    return 0 if event["status"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
