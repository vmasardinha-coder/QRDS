#!/usr/bin/env python3
"""Evidence-only upper-bound audit for V2A coverage recovery.

Consumes the frozen failure diagnostic and independent Binance Spot history-depth
probe. It never changes the V2A source chain, denominator, universe or outputs.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def build(diagnostic: dict, history: dict) -> dict:
    require(diagnostic.get("schema") == "gate_btc.v2a_failure_diagnostic.v1", "unexpected diagnostic schema")
    require(history.get("schema") == "gate_btc.binance_spot_history_depth_probe.v1", "unexpected history schema")
    for payload in (diagnostic, history):
        require(payload.get("feeds_frozen_engine") is False, "engine-feed boundary changed")
        require(payload.get("source_substitution_performed") is False, "source substitution boundary changed")
        require(int(payload.get("methodology_changes", 0)) == 0, "methodology change detected")

    source_candidates = {
        str(row.get("symbol", "")).upper()
        for row in diagnostic.get("rows", [])
        if row.get("action_class") == "SOURCE_RECOVERY_CANDIDATE"
    }
    ge200 = {
        str(row.get("symbol", "")).upper()
        for row in history.get("results", [])
        if row.get("status") == "PASS_HISTORY_DEPTH_GE_200"
    }
    recoverable_leads = sorted(source_candidates & ge200)
    attempted = int(diagnostic["attempted_symbols"])
    loaded = int(diagnostic["loaded_symbols"])
    failed = int(diagnostic["failed_symbols"])
    require(attempted == loaded + failed, "diagnostic counts inconsistent")
    upper_loaded = loaded + len(recoverable_leads)

    return {
        "schema": "gate_btc.v2a_coverage_lift_audit.v1",
        "status": "PASS_AVAILABILITY_UPPER_BOUND_ONLY",
        "data_as_of": diagnostic.get("data_as_of"),
        "attempted_symbols": attempted,
        "canonical_loaded_symbols": loaded,
        "canonical_failed_symbols": failed,
        "canonical_coverage_pct": 100.0 * loaded / attempted if attempted else 0.0,
        "binance_spot_history_ge_200_recovery_leads": recoverable_leads,
        "recovery_lead_count": len(recoverable_leads),
        "availability_only_upper_bound_loaded_symbols": upper_loaded,
        "availability_only_upper_bound_coverage_pct": 100.0 * upper_loaded / attempted if attempted else 0.0,
        "absolute_coverage_lift_pct_points": 100.0 * len(recoverable_leads) / attempted if attempted else 0.0,
        "integration_eligible": False,
        "remaining_gate": "PER-SYMBOL HISTORICAL SEMANTIC EQUIVALENCE + EXPLICIT METHODOLOGY/DATA-BASIS AUTHORIZATION",
        "interpretation": "Upper bound only: >=200 public Spot archive rows show potential recoverability, not permission to insert a new source into V2A.",
        "role": "SOURCE_RECOVERY_AUDIT_ONLY",
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "source_substitution_performed": False,
        "strategy_inputs_changed": False,
        "denominator_changed": False,
        "universe_changed": False,
        "methodology_changes": 0,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--diagnostic", type=Path, required=True)
    p.add_argument("--history-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    require(os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").lower() in {"1", "true", "yes", "on"}, "research-only must remain true")
    diagnostic = json.loads(args.diagnostic.read_text(encoding="utf-8-sig"))
    history = json.loads(args.history_report.read_text(encoding="utf-8-sig"))
    payload = build(diagnostic, history)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "canonical_coverage_pct": payload["canonical_coverage_pct"],
        "recovery_lead_count": payload["recovery_lead_count"],
        "availability_only_upper_bound_coverage_pct": payload["availability_only_upper_bound_coverage_pct"],
        "integration_eligible": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
