#!/usr/bin/env python3
"""Materialize bounded PIT availability authorities for Grammar 007.

No B3 target body is read. No outcomes/economics/features/candidate ranking occur.
The materializer turns an audited official-source registry into a bounded session
calendar and source-availability coverage, failing closed outside proven coverage.
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA = "qrds.factory.grammar_007.availability_authorities.v1"
UA = "QRDS-GATE-BTC-RESEARCH-ONLY/1.0"
TIMEOUT = 30


def head(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"}, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            length = r.headers.get("Content-Length")
            return {
                "url": url,
                "reachable": True,
                "http_status": int(r.status),
                "content_type": r.headers.get("Content-Type"),
                "content_length": int(length) if length and length.isdigit() else None,
                "last_modified": r.headers.get("Last-Modified"),
                "etag": r.headers.get("ETag"),
                "body_read": False,
            }
    except urllib.error.HTTPError as exc:
        return {"url": url, "reachable": False, "http_status": int(exc.code), "error": f"HTTPError:{exc.code}", "body_read": False}
    except Exception as exc:
        return {"url": url, "reachable": False, "http_status": None, "error": f"{type(exc).__name__}:{exc}", "body_read": False}


def months(start: date, end: date) -> list[str]:
    y, m = start.year, start.month
    out: list[str] = []
    while (y, m) <= (end.year, end.month):
        out.append(f"{y:04d}{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def sessions(start: date, end: date, closed: set[date], special: dict[date, str], regular_open: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    d = start
    while d <= end:
        if d.weekday() < 5 and d not in closed:
            out.append({"date": d.isoformat(), "open": special.get(d, regular_open), "weekday": d.strftime("%A")})
        d += timedelta(days=1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    reg = json.loads(args.registry.read_text(encoding="utf-8"))
    start = date.fromisoformat(reg["coverage"]["start"])
    end = date.fromisoformat(reg["coverage"]["end"])
    closed = {date.fromisoformat(x) for x in reg["b3"]["closed_dates"]}
    special = {date.fromisoformat(k): v for k, v in reg["b3"]["special_open"].items()}
    sess = sessions(start, end, closed, special, reg["b3"]["regular_cash_market_open"])

    focus_end = time.fromisoformat(reg["bcb_focus"]["release_window_end"])
    focus_eligible = []
    for s in sess:
        d = date.fromisoformat(s["date"])
        market_open = time.fromisoformat(s["open"])
        if d.weekday() == 0 and focus_end < market_open:
            focus_eligible.append({"publication_date": s["date"], "release_window_end": reg["bcb_focus"]["release_window_end"], "target_session_open": s["open"]})

    non_session_mondays = []
    d = start
    session_dates = {s["date"] for s in sess}
    while d <= end:
        if d.weekday() == 0 and d.isoformat() not in session_dates:
            non_session_mondays.append(d.isoformat())
        d += timedelta(days=1)

    authority_urls = [reg["bcb_focus"]["official_authority_url"], *reg["b3"]["authority_urls"]]
    with ThreadPoolExecutor(max_workers=8) as ex:
        authority_probes = list(ex.map(head, authority_urls))
    authority_reachable = all(x.get("reachable") is True for x in authority_probes)

    target_probe = head(reg["b3"]["target_source_url"])

    ym = months(start, end)
    delivery_urls = [reg["cvm"]["delivery_url_template"].format(yyyymm=x) for x in ym]
    inf_urls = [reg["cvm"]["inf_diario_url_template"].format(yyyymm=x) for x in ym]
    with ThreadPoolExecutor(max_workers=12) as ex:
        delivery_probes = list(ex.map(head, delivery_urls))
        inf_probes = list(ex.map(head, inf_urls))
    cvm_missing_delivery = [x["url"] for x in delivery_probes if not x.get("reachable")]
    cvm_missing_inf = [x["url"] for x in inf_probes if not x.get("reachable")]
    cvm_archive_coverage_pass = not cvm_missing_delivery and not cvm_missing_inf

    bcb_bounded_pit_pass = authority_reachable and bool(focus_eligible)
    b3_bounded_calendar_pass = authority_reachable and target_probe.get("reachable") is True and target_probe.get("body_read") is False
    bounded_pass = bcb_bounded_pit_pass and b3_bounded_calendar_pass and cvm_archive_coverage_pass

    blockers: list[str] = []
    if not authority_reachable:
        blockers.append("OFFICIAL_AUTHORITY_REACHABILITY_GAP")
    if not cvm_archive_coverage_pass:
        blockers.append("CVM_MONTHLY_ARCHIVE_COVERAGE_GAP")
    if not target_probe.get("reachable"):
        blockers.append("B3_COTAHIST_TARGET_AUTHORITY_REACHABILITY_GAP")

    result = {
        "schema": SCHEMA,
        "materialized_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "MATERIALIZE_HISTORICAL_AVAILABILITY_AUTHORITIES_WITHOUT_OUTCOMES",
        "status": "BOUNDED_PIT_AUTHORITIES_MATERIALIZED" if bounded_pass else "BOUNDED_PIT_AUTHORITIES_BLOCKED",
        "coverage": reg["coverage"],
        "official_authority_probes": authority_probes,
        "B3": {
            "bounded_calendar_pass": b3_bounded_calendar_pass,
            "session_count": len(sess),
            "sessions": sess,
            "target_source_probe": target_probe,
            "target_bytes_read": False,
            "target_bytes_parsed": False,
            "target_outcomes_read": False,
            "outside_coverage_rule": "INELIGIBLE_NO_IMPUTATION",
        },
        "BCB": {
            "bounded_pit_admission_pass": bcb_bounded_pit_pass,
            "publication_window": [reg["bcb_focus"]["release_window_start"], reg["bcb_focus"]["release_window_end"]],
            "eligible_monday_publications": focus_eligible,
            "eligible_count": len(focus_eligible),
            "non_session_mondays_ineligible": non_session_mondays,
            "shifted_release_timestamp_inferred": False,
            "outside_or_shifted_rule": "INELIGIBLE_NO_IMPUTATION",
        },
        "CVM": {
            "archive_coverage_pass": cvm_archive_coverage_pass,
            "months_expected": ym,
            "delivery_archives_reachable": sum(1 for x in delivery_probes if x.get("reachable")),
            "inf_diario_archives_reachable": sum(1 for x in inf_probes if x.get("reachable")),
            "missing_delivery_urls": cvm_missing_delivery,
            "missing_inf_diario_urls": cvm_missing_inf,
            "availability_timestamp": reg["cvm"]["availability_timestamp"],
            "version_key": reg["cvm"]["version_key"],
            "missing_rule": "INELIGIBLE_NO_IMPUTATION",
        },
        "blockers": blockers,
        "next_gate": "CAUSAL_FEATURE_MATERIALIZATION_OUTCOME_BLIND" if bounded_pass else "RESOLVE_AUTHORITY_COVERAGE_GAPS",
        "historical_testing_started": False,
        "features_materialized": False,
        "candidate_ranked": False,
        "outcomes_read": False,
        "economics_read": False,
        "scientific_credit": 0,
        "prospective_credit": 0,
        "historical_backfill_credit": 0,
        "safety": reg["safety"],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "sessions": len(sess), "focus_eligible": len(focus_eligible),
                      "cvm_months": len(ym), "authority_reachable": authority_reachable, "outcomes_read": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
