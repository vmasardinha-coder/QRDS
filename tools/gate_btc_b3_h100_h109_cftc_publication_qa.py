#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "tools/gate_btc_b3_h100_h109_cftc_publication_contract.json"
OUT = ROOT / "artifacts/b3_h100_h109/B3_H100_H109_CFTC_PUBLICATION_QA.json"

# Revised official CFTC schedule published 2025-12-09. Times are fixed at 15:30 ET per CFTC.
CATCHUP = {
    "2025-09-30": "2025-11-19",
    "2025-10-07": "2025-11-21",
    "2025-10-14": "2025-11-25",
    "2025-10-21": "2025-12-02",
    "2025-10-28": "2025-12-05",
    "2025-11-04": "2025-12-09",
    "2025-11-10": "2025-12-10",
    "2025-11-18": "2025-12-12",
    "2025-11-25": "2025-12-15",
    "2025-12-02": "2025-12-17",
    "2025-12-09": "2025-12-19",
    "2025-12-16": "2025-12-23",
    "2025-12-23": "2025-12-29"
}

NY = ZoneInfo("America/New_York")
SP = ZoneInfo("America/Sao_Paulo")


def normal_available(asof: date) -> datetime:
    # Deliberately conservative: Thursday after Tuesday as-of, at start of B3-local day.
    return datetime.combine(asof + timedelta(days=9), datetime.min.time(), tzinfo=SP)


def catchup_available(asof: date) -> datetime | None:
    published = CATCHUP.get(asof.isoformat())
    if not published:
        return None
    d = date.fromisoformat(published)
    return datetime(d.year, d.month, d.day, 15, 30, tzinfo=NY).astimezone(SP)


def effective_available(asof: date) -> datetime:
    special = catchup_available(asof)
    if special is not None:
        return max(normal_available(asof), special)
    return normal_available(asof)


def main() -> int:
    c = json.loads(CONTRACT.read_text(encoding="utf-8"))
    inv = c["scientific_invariants"]
    assert inv == {
        "historical_cutoff_exclusive": "2026-08-10",
        "h1_economics_read": False,
        "survivor_partial_economics_read": False,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "not_approved": True,
    }
    assert c["normal_rule"]["never_use_same_week"] is True
    assert c["exception_policy"]["unknown_or_ambiguous_exception"] == "DATA_GAP_PUBLICATION_TIMESTAMP"
    assert c["b3_join_rule"]["strict_before_signal"] is True
    assert c["b3_join_rule"]["synthetic_backfill"] is False

    # Sanity examples: normal report is never available before +9d; shutdown reports use later official dates.
    normal_example = date(2026, 8, 18)
    assert effective_available(normal_example) == datetime(2026, 8, 27, 0, 0, tzinfo=SP)
    shutdown_example = date(2025, 9, 30)
    assert effective_available(shutdown_example) == datetime(2025, 11, 19, 15, 30, tzinfo=NY).astimezone(SP)

    rows = []
    for raw, pub in sorted(CATCHUP.items()):
        asof = date.fromisoformat(raw)
        eff = effective_available(asof)
        rows.append({"report_asof": raw, "official_catchup_publish_date": pub, "effective_available_at": eff.isoformat()})
        assert eff >= catchup_available(asof)
        assert eff >= normal_available(asof)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "gate_btc.b3.h100_h109.cftc_publication_qa.v1",
        "status": "PASS_CONSERVATIVE_PUBLICATION_CONTRACT_FROZEN",
        "normal_rule": "+9 calendar days from Tuesday report-as-of, 00:00 America/Sao_Paulo",
        "known_exception_rows": rows,
        "unknown_exception_policy": "DATA_GAP_PUBLICATION_TIMESTAMP",
        "economics_run": False,
        "h1_economics_read": False,
        "survivor_partial_economics_read": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "engine_feed": False,
        "not_approved": True
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(report["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
