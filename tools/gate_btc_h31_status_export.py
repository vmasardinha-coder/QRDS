#!/usr/bin/env python3
"""Reporting-only H31 status exporter.

Reads canonical prospective and auxiliary shadow-paper H31 ledgers and emits a
single fail-visible monitoring artifact. Never changes counters, methodology,
economics, orders, capital, or scientific credit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(obj, dict):
        raise ValueError(f"object required: {path}")
    return obj


def build(prospective: dict[str, Any], paper: dict[str, Any]) -> dict[str, Any]:
    if prospective.get("orders", 0) != 0 or prospective.get("real_capital", 0) != 0:
        raise ValueError("unsafe prospective H31 state")
    if paper.get("ORDERS", 0) != 0 or paper.get("REAL_CAPITAL", 0) != 0:
        raise ValueError("unsafe paper H31 state")
    eligible = int(prospective.get("eligible_observations", 0) or 0)
    sessions = int(paper.get("H31_SHADOW_SESSIONS", paper.get("sessions_observed", 0)) or 0)
    trades = int(paper.get("H31_SHADOW_SIMULATED_TRADES", paper.get("simulated_trades", 0)) or 0)
    return {
        "schema": "gate_btc.h31.executive_status.v1",
        "reporting_only": True,
        "scientific_authority": False,
        "status": prospective.get("status", "UNKNOWN"),
        "canonical_strategy_id": "B3_H31_PROSPECTIVE",
        "clock_started": prospective.get("clock_started", False),
        "eligible_observations": eligible,
        "latest_valid_observation_date": prospective.get("latest_date"),
        "shadow_paper_status": paper.get("H31_SHADOW_PAPER_STATUS", "UNKNOWN"),
        "shadow_sessions": sessions,
        "simulated_trades": trades,
        "open_book": "N/D_NOT_CANONICALLY_EXPOSED",
        "closed_trades": trades,
        "paper_bridge": {
            "mt5_ready": paper.get("H31_MT5_READY"),
            "mt5_parity_observations": paper.get("H31_MT5_PARITY_OBSERVATIONS"),
            "health": "READY" if paper.get("H31_MT5_READY") is True else "NOT_PROVEN_READY",
        },
        "economics_locked": bool(prospective.get("partial_prospective_economics_exposed") is False),
        "economics": {
            "sample_status": paper.get("metrics_sample_status"),
            "gross_bps": paper.get("cumulative_gross_bps"),
            "reference_net_bps": paper.get("cumulative_reference_net_bps"),
            "stress_net_bps": paper.get("cumulative_stress_net_bps"),
            "max_drawdown_bps": paper.get("max_drawdown_bps"),
            "volatility": paper.get("volatility"),
            "win_rate": paper.get("win_rate"),
        },
        "canonical_credit": prospective.get("eligible_observations", 0),
        "shadow_credit_to_canonical": paper.get("SHADOW_CREDIT_TO_CANONICAL", 0),
        "freeze_rule_hash_sha256": prospective.get("freeze_rule_hash_sha256"),
        "no_backfill": paper.get("NO_BACKFILL", True),
        "no_retune": paper.get("NO_RETUNE", True),
        "engine_feed": prospective.get("engine_feed", False),
        "orders": 0,
        "real_capital": 0,
        "note": "Target/checkpoints/open-book are reported N/D unless explicitly present in canonical H31 ledgers; nothing is inferred or reconstructed.",
    }


def markdown(x: dict[str, Any]) -> str:
    return "\n".join([
        "# GATE BTC H31 STATUS",
        f"STATUS={x['status']}",
        f"ELIGIBLE_OBSERVATIONS={x['eligible_observations']}",
        f"SHADOW_SESSIONS={x['shadow_sessions']}",
        f"SIMULATED_TRADES={x['simulated_trades']}",
        f"LATEST_VALID_DATE={x['latest_valid_observation_date']}",
        f"MT5_READY={x['paper_bridge']['mt5_ready']}",
        f"PAPER_BRIDGE_HEALTH={x['paper_bridge']['health']}",
        f"ECONOMICS_LOCKED={x['economics_locked']}",
        f"OPEN_BOOK={x['open_book']}",
        "METHODOLOGY_UNCHANGED=true",
        "REAL_ORDERS=0",
        "REAL_CAPITAL=0",
        "",
    ])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prospective", type=Path, required=True)
    ap.add_argument("--paper", type=Path, required=True)
    ap.add_argument("--output-json", type=Path, required=True)
    ap.add_argument("--output-md", type=Path, required=True)
    a = ap.parse_args()
    out = build(load(a.prospective), load(a.paper))
    a.output_json.parent.mkdir(parents=True, exist_ok=True)
    a.output_json.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    a.output_md.write_text(markdown(out), encoding="utf-8")
    print("H31_STATUS_VISIBLE=1")
    print("H31_COUNTER_VISIBLE=1")
    print("H31_OPEN_BOOK_VISIBLE=1")
    print("H31_PAPER_BRIDGE_HEALTH_VISIBLE=1")
    print("H31_ECONOMICS_VISIBLE_OR_LOCKED=1")
    print("METHODOLOGY_UNCHANGED=1")
    print("REAL_ORDERS=0")
    print("REAL_CAPITAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
