#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shadow-dir", default="runtime/ledgers/b3_h31_shadow_paper")
    args = ap.parse_args()
    root = Path(args.shadow_dir)
    events = []
    for p in sorted((root / "intraday_events").glob("*/*.json")):
        row = load(p)
        if row.get("event_type") == "PAPER_CLOSE":
            events.append(row)

    ref = [float(x.get("reference_net_bps", 0.0)) for x in events]
    stress = [float(x.get("stress_net_bps", 0.0)) for x in events]
    gross = [float(x.get("gross_bps", 0.0)) for x in events]
    wins = sum(1 for x in ref if x > 0)
    out = {
        "schema": "gate_btc.b3.h31.economics.v1",
        "status": "ECONOMICS_ACTIVE" if events else "ECONOMICS_READY_WAITING_FIRST_TRADE",
        "paper_trades": len(events),
        "sessions_with_closed_trade": len({x.get("session") for x in events}),
        "last_trade_session": events[-1].get("session") if events else None,
        "gross_bps_sum": sum(gross),
        "reference_net_bps_sum": sum(ref),
        "stress_net_bps_sum": sum(stress),
        "reference_win_rate": (wins / len(ref)) if ref else None,
        "reference_avg_bps_per_trade": (sum(ref) / len(ref)) if ref else None,
        "max_adverse_excursion_bps_worst": min((float(x.get("MAE_bps", 0.0)) for x in events), default=None),
        "max_favorable_excursion_bps_best": max((float(x.get("MFE_bps", 0.0)) for x in events), default=None),
        "economic_interpretation": "SUM_OF_EXISTING_H31_PAPER_CLOSE_EVENTS_ONLY",
        "canonical_scientific_credit": 0,
        "retrospective_backfill": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "ECONOMICS_STATUS.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
