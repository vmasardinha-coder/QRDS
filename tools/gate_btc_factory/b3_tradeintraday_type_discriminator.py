#!/usr/bin/env python3
"""Evidence-only discriminator for B3 TradeIntraday query variants.

Compares the same session/host with no ``type`` parameter, ``type=1`` and
``type=2``.  This is transport/identity evidence only.  It never admits a
source, reconstructs history, evaluates economics, or grants scientific credit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests

SCHEMA = "qrds.factory.b3_tradeintraday_type_discriminator.v1"
HOSTS = ("drp.b3.com.br", "arquivos.b3.com.br")
VARIANTS = (("none", ""), ("type1", "?type=1"), ("type2", "?type=2"))
MAX_SAMPLE_BYTES = 65536


def _sha(raw: bytes) -> str | None:
    return hashlib.sha256(raw).hexdigest() if raw else None


def _sample(session: requests.Session, host: str, session_date: str, label: str, suffix: str) -> dict[str, Any]:
    url = f"https://{host}/rapinegocios/tickercsv/{session_date}{suffix}"
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    out: dict[str, Any] = {
        "host": host,
        "variant": label,
        "url": url,
        "requested_type": query.get("type", [None])[0],
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
        out.update(error=f"{type(exc).__name__}: {exc}", response_sample_bytes=0, zip_magic=False)
    return out


def probe(session: requests.Session, session_date: str) -> dict[str, Any]:
    rows = [_sample(session, host, session_date, label, suffix) for host in HOSTS for label, suffix in VARIANTS]
    physical = [r for r in rows if r.get("zip_magic") is True and int(r.get("response_sample_bytes") or 0) > 0]

    by_host: dict[str, Any] = {}
    for host in HOSTS:
        host_rows = [r for r in rows if r["host"] == host]
        fingerprints = {
            r["variant"]: {
                "sample_sha256": r.get("response_sample_sha256"),
                "content_disposition": r.get("content_disposition"),
                "sample_bytes": r.get("response_sample_bytes"),
                "http_status": r.get("http_status"),
            }
            for r in host_rows
        }
        nonempty_hashes = [f["sample_sha256"] for f in fingerprints.values() if f["sample_sha256"]]
        by_host[host] = {
            "fingerprints": fingerprints,
            "all_nonempty_variants_byte_identical": len(nonempty_hashes) >= 2 and len(set(nonempty_hashes)) == 1,
            "all_three_variants_physically_observed": sum(bool(f["sample_sha256"]) for f in fingerprints.values()) == 3,
        }

    type2_distinct_from_untyped_proven = any(
        h["fingerprints"]["type2"]["sample_sha256"]
        and h["fingerprints"]["none"]["sample_sha256"]
        and h["fingerprints"]["type2"]["sample_sha256"] != h["fingerprints"]["none"]["sample_sha256"]
        for h in by_host.values()
    )
    type2_distinct_from_type1_proven = any(
        h["fingerprints"]["type2"]["sample_sha256"]
        and h["fingerprints"]["type1"]["sample_sha256"]
        and h["fingerprints"]["type2"]["sample_sha256"] != h["fingerprints"]["type1"]["sample_sha256"]
        for h in by_host.values()
    )

    return {
        "schema": SCHEMA,
        "generated_from_live_network": True,
        "provider": "B3",
        "source_role": "OFFICIAL_PRIMARY_CANDIDATE_NOT_ADMITTED",
        "surface": "rapinegocios/tickercsv query-variant discriminator",
        "session_date": session_date,
        "probes": rows,
        "host_comparison": by_host,
        "physical_observation_count": len(physical),
        "type2_distinct_from_untyped_proven": type2_distinct_from_untyped_proven,
        "type2_distinct_from_type1_proven": type2_distinct_from_type1_proven,
        "exact_derivatives_identity_proven": False,
        "exact_win_identity_proven": False,
        "full_161_session_coverage_proven": False,
        "schema_qa_pass": False,
        "timezone_and_session_semantics_proven": False,
        "publication_semantics_proven": False,
        "revision_semantics_proven": False,
        "point_in_time_valid": False,
        "hash_bound_full_dataset": False,
        "source_gate_credit": 0,
        "historical_backfill_credit": 0,
        "prospective_credit": 0,
        "strict_source_gate_green": False,
        "status": (
            "TYPE2_TRANSPORT_DIFFERENTIATED_NEEDS_IDENTITY_QUALIFICATION"
            if type2_distinct_from_untyped_proven or type2_distinct_from_type1_proven
            else "TYPE2_NOT_DIFFERENTIATED_FAIL_CLOSED"
        ),
        "next_requirement": (
            "QUALIFY_RETURNED_FILE_IDENTITY_AND_SCHEMA_WITHOUT_SOURCE_CREDIT"
            if type2_distinct_from_untyped_proven or type2_distinct_from_type1_proven
            else "CONTINUE_OFFICIAL_SOURCE_DISCOVERY_TYPE_PARAMETER_NOT_PROVEN_TO_SELECT_DERIVATIVES"
        ),
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
    ap.add_argument("--date", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    result = probe(requests.Session(), args.date)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "strict_source_gate_green": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
