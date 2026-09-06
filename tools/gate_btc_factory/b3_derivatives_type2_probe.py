#!/usr/bin/env python3
"""Evidence-only probe for the official B3 derivatives intraday trade surface.

This module does not admit a source and never evaluates economics.  It measures
whether the documented derivative-specific ``type=2`` surface returns physical
ZIP bytes on the canonical B3 hosts and on frozen historical probe dates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests

SCHEMA = "qrds.factory.b3_derivatives_type2_probe.v1"
HOST_TEMPLATES = (
    "https://drp.b3.com.br/rapinegocios/tickercsv/{date}?type=2",
    "https://arquivos.b3.com.br/rapinegocios/tickercsv/{date}?type=2",
)
# Deliberately spans old and recent sessions.  Positive reachability is evidence
# only; these dates do not grant backfill or source-gate credit.
HISTORICAL_PROBE_DATES = (
    "2025-01-02",
    "2025-03-03",
    "2025-06-02",
    "2025-09-01",
    "2025-12-12",
)
MAX_SAMPLE_BYTES = 65536


def _sha(raw: bytes) -> str | None:
    return hashlib.sha256(raw).hexdigest() if raw else None


def _sample(session: requests.Session, url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    out: dict[str, Any] = {
        "url": url,
        "host": parsed.netloc,
        "type_parameter": query.get("type", [None])[0],
        "method": "GET",
    }
    try:
        with session.get(url, timeout=60, stream=True, allow_redirects=True) as response:
            raw = b""
            if 200 <= response.status_code < 400:
                for chunk in response.iter_content(chunk_size=16384):
                    if chunk:
                        raw += chunk
                    if len(raw) >= MAX_SAMPLE_BYTES:
                        break
            raw = raw[:MAX_SAMPLE_BYTES]
            out.update(
                http_status=int(response.status_code),
                final_url=str(response.url),
                response_sample_bytes=len(raw),
                response_sample_sha256=_sha(raw),
                zip_magic=raw.startswith(b"PK\x03\x04"),
                content_type=response.headers.get("content-type"),
                content_length=response.headers.get("content-length"),
                content_disposition=response.headers.get("content-disposition"),
                etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified"),
            )
    except Exception as exc:
        out.update(
            error=f"{type(exc).__name__}: {exc}",
            response_sample_bytes=0,
            zip_magic=False,
        )
    return out


def previous_business_day(today: date | None = None) -> str:
    d = today or date.today()
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()


def probe(session: requests.Session, recent_date: str) -> dict[str, Any]:
    dates = list(HISTORICAL_PROBE_DATES)
    if recent_date not in dates:
        dates.append(recent_date)
    rows: list[dict[str, Any]] = []
    for template in HOST_TEMPLATES:
        for probe_date in dates:
            row = _sample(session, template.format(date=probe_date))
            row["probe_date"] = probe_date
            row["official_surface"] = "B3_TRADE_INTRADAY_DERIVATIVES_TYPE_2"
            rows.append(row)

    positives = [
        row for row in rows
        if 200 <= int(row.get("http_status") or 0) < 400
        and int(row.get("response_sample_bytes") or 0) > 0
        and row.get("zip_magic") is True
        and row.get("type_parameter") == "2"
    ]
    historical_positive_dates = sorted({
        str(row["probe_date"]) for row in positives if row["probe_date"] in HISTORICAL_PROBE_DATES
    })
    hosts_with_physical_zip = sorted({str(row["host"]) for row in positives})

    return {
        "schema": SCHEMA,
        "generated_from_live_network": True,
        "provider": "B3",
        "source_role": "OFFICIAL_PRIMARY_CANDIDATE_NOT_ADMITTED",
        "surface": "TradeIntradayFile / derivatives type=2",
        "evidence_basis": {
            "official_glossary_file": "DD-MM-AAAA_NEGOCIOSAVISTA (TradeIntradayFile)",
            "publication_semantics_claim_under_review": "D+1 morning after prior trading session",
            "transport_variant_under_review": "rapinegocios/tickercsv/YYYY-MM-DD?type=2",
            "type_2_interpretation": "DERIVATIVES",
        },
        "probe_dates": dates,
        "probes": rows,
        "physical_zip_observation_count": len(positives),
        "hosts_with_physical_zip": hosts_with_physical_zip,
        "historical_positive_dates": historical_positive_dates,
        "historical_probe_date_count": len(HISTORICAL_PROBE_DATES),
        "historical_physical_coverage_observed": len(historical_positive_dates) > 0,
        "full_161_session_coverage_proven": False,
        "exact_win_identity_proven": False,
        "schema_qa_pass": False,
        "timezone_and_session_semantics_proven": False,
        "publication_semantics_proven": False,
        "revision_semantics_proven": False,
        "point_in_time_valid": False,
        "independent_unseen_evaluation_data": False,
        "hash_bound_full_dataset": False,
        "source_gate_credit": 0,
        "historical_backfill_credit": 0,
        "prospective_credit": 0,
        "strict_source_gate_green": False,
        "status": (
            "PHYSICAL_DERIVATIVES_TYPE2_ZIP_SURFACE_OBSERVED_NEEDS_FULL_QUALIFICATION"
            if positives else
            "DERIVATIVES_TYPE2_SURFACE_NOT_PHYSICALLY_OBSERVED_FAIL_CLOSED"
        ),
        "next_requirement": (
            "MATERIALIZE_FULL_AUTHORIZED_SAMPLE_AND_PROVE_WIN_IDENTITY_SCHEMA_TIMEZONE_COVERAGE_PUBLICATION_REVISION_PIT"
            if positives else
            "CONTINUE_OFFICIAL_FREE_SOURCE_DISCOVERY_WITHOUT_DATA_GAP_DECLARATION"
        ),
        "blocking_requirements_preserved": [
            "EXACT_WIN_SOURCE_IDENTITY",
            "M5_SCHEMA_AND_SESSION_TIMEZONE",
            "MINIMUM_HISTORY_COVERAGE_161_SESSIONS",
            "PUBLICATION_SEMANTICS",
            "REVISION_SEMANTICS",
            "POINT_IN_TIME_VALIDITY",
            "INDEPENDENT_UNSEEN_EVALUATION_WINDOWS",
            "HASH_BOUND_DATASET",
        ],
        "safety": {
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "engine_feed": False,
            "orders": 0,
            "real_capital": 0,
            "no_retune": True,
            "no_backfill": True,
            "no_counter_reset": True,
            "fail_closed": True,
            "h1_economics_read": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recent-date", default=previous_business_day())
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    result = probe(requests.Session(), args.recent_date)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "source_gate_green": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
