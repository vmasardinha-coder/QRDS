#!/usr/bin/env python3
"""Outcome-blind handoff from Grammar Scout proposals to preregistration queue.

This module does not read economics, allocate H IDs, execute families, or mutate any
existing grammar. It only converts novel SCOUTED_NOT_PREREGISTERED proposals into
append-only preregistration requests for the existing scientific factory/gatekeeper.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "qrds.factory.grammar_scout_handoff.v1"
SAFETY = {
    "research_only": True, "shadow_only": True, "not_approved": True,
    "engine_feed": False, "orders": 0, "real_capital": 0,
    "no_retune": True, "no_backfill": True, "no_counter_reset": True,
    "fail_closed": True, "h1_h31_untouched": True,
}


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _signature(row):
    payload = {
        "channel_id": row.get("channel_id"),
        "mechanism": row.get("mechanism"),
        "required_new_data": row.get("required_new_data", []),
        "official_free_source_candidates": row.get("official_free_source_candidates", []),
    }
    return hashlib.sha256(_canonical(payload).encode()).hexdigest()


def _seen_signatures(ledger_dir: Path | None):
    seen = set()
    if not ledger_dir or not ledger_dir.exists():
        return seen
    for p in sorted(ledger_dir.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for r in d.get("requests", []):
            if r.get("grammar_signature"):
                seen.add(r["grammar_signature"])
    return seen


def build_handoff(scout: dict, ledger_dir: Path | None = None) -> dict:
    if scout.get("mode") != "IDEATION_ONLY_NO_ECONOMICS":
        raise ValueError("fail closed: scout mode is not outcome blind")
    if scout.get("history_used_for_selection") is not False:
        raise ValueError("fail closed: history used for selection")
    seen = _seen_signatures(ledger_dir)
    requests = []
    for row in scout.get("proposals", []):
        if row.get("status") != "SCOUTED_NOT_PREREGISTERED":
            continue
        if row.get("economics_read") is not False:
            raise ValueError("fail closed: proposal read economics")
        if row.get("may_change_existing_grammar") is not False:
            raise ValueError("fail closed: proposal may change existing grammar")
        sig = _signature(row)
        if sig in seen:
            continue
        requests.append({
            "channel_id": row.get("channel_id"),
            "grammar_signature": sig,
            "status": "ELIGIBLE_FOR_SEPARATE_PREREGISTRATION_GATE",
            "mechanism": row.get("mechanism"),
            "required_new_data": row.get("required_new_data", []),
            "official_free_source_candidates": row.get("official_free_source_candidates", []),
            "source_qualification_required": True,
            "cost_applicability_required": True,
            "economics_read": False,
            "may_allocate_existing_h_id": False,
            "may_modify_existing_grammar": False,
            "may_receive_retroactive_credit": False,
            "next_gate": "SEPARATE_PREREGISTRATION_BEFORE_ANY_OUTCOME_READ",
        })
    return {
        "schema": SCHEMA,
        "mode": "OUTCOME_BLIND_HANDOFF_ONLY",
        "requests": requests,
        "request_count": len(requests),
        "safety": SAFETY,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scout", required=True)
    ap.add_argument("--ledger-dir")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    scout = json.loads(Path(a.scout).read_text(encoding="utf-8"))
    out = build_handoff(scout, Path(a.ledger_dir) if a.ledger_dir else None)
    Path(a.output).write_text(json.dumps(out, indent=2, sort_keys=True)+"\n", encoding="utf-8")

if __name__ == "__main__":
    main()
