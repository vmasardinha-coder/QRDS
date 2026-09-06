#!/usr/bin/env python3
"""Fail-closed qualifier for the preregistered official B3 type=1 DRV source.

The qualifier is evidence-only. It reads the frozen preregistration, probes only the
predeclared dates, records transport provenance and response metadata, and never
admits the source or grants historical/prospective credit. It deliberately does not
infer timezone, publication or revision semantics from prices or family outcomes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import requests

SCHEMA = "qrds.factory.b3_type1_drv_semantic_coverage_qualifier.v1"
PREREG = Path("tools/gate_btc_factory/B3_TYPE1_DRV_SEMANTIC_COVERAGE_PREREG.v1.json")
URL = "https://arquivos.b3.com.br/rapinegocios/tickercsv/{date}?type=1"
ZIP_MAGIC = b"PK\x03\x04"


def probe_date(session: requests.Session, date: str) -> dict[str, Any]:
    url = URL.format(date=date)
    row: dict[str, Any] = {"date": date, "url": url}
    try:
        with session.get(url, stream=True, timeout=90, allow_redirects=True,
                         headers={"User-Agent": "QRDS-B3-source-qualification/1.0"}) as r:
            row["http_status"] = int(r.status_code)
            row["content_disposition"] = r.headers.get("content-disposition")
            row["content_type"] = r.headers.get("content-type")
            raw_len = r.headers.get("content-length")
            try:
                row["content_length_header"] = int(raw_len) if raw_len is not None else None
            except ValueError:
                row["content_length_header"] = None
            first = r.raw.read(4, decode_content=True) if r.status_code == 200 else b""
            row["prefix_hex"] = first.hex()
            row["zip_magic_observed"] = first == ZIP_MAGIC
            disp = str(row.get("content_disposition") or "")
            row["drv_filename_observed"] = "NEGOCIOSAVISTA_DRV" in disp
            row["physical_drv_transport_observed"] = bool(
                r.status_code == 200 and row["zip_magic_observed"] and row["drv_filename_observed"]
            )
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
        row["physical_drv_transport_observed"] = False
    return row


def qualify(session: requests.Session, prereg: dict[str, Any]) -> dict[str, Any]:
    dates = list(prereg["frozen_transport_probe_dates"])
    rows = [probe_date(session, d) for d in dates]
    positive_dates = [r["date"] for r in rows if r.get("physical_drv_transport_observed")]
    negative_dates = [r["date"] for r in rows if not r.get("physical_drv_transport_observed")]
    prior = prereg["prior_physical_evidence"]

    # Strict gate remains closed: this bounded matrix cannot prove 161 full sessions,
    # official timestamp timezone/session semantics, publication/revision semantics,
    # PIT-safe immutable snapshots, or independent unseen evaluation data.
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "provider": "B3",
        "source_role": "OFFICIAL_PRIMARY_CANDIDATE_NOT_ADMITTED",
        "prereg_schema": prereg["schema"],
        "prior_exact_win_identity_observed": bool(prior["exact_win_identity_observed"]),
        "prior_zip_sha256": prior["zip_sha256"],
        "prior_columns": prior["columns"],
        "transport_matrix": rows,
        "positive_transport_dates": positive_dates,
        "negative_transport_dates": negative_dates,
        "positive_transport_count": len(positive_dates),
        "frozen_probe_count": len(dates),
        "oldest_positive_transport_date": min(positive_dates) if positive_dates else None,
        "newest_positive_transport_date": max(positive_dates) if positive_dates else None,
        "schema_identity_observed": bool(prior["exact_win_identity_observed"] and prior["columns"]),
        "timezone_session_semantics_proven": False,
        "publication_semantics_proven": False,
        "revision_semantics_proven": False,
        "point_in_time_valid": False,
        "independent_unseen_evaluation_data": False,
        "full_161_session_coverage_proven": False,
        "strict_source_gate_green": False,
        "source_gate_credit": 0,
        "historical_backfill_credit": 0,
        "prospective_credit": 0,
        "economics_read": False,
        "data_gap_definitive": False,
        "mt5_role": "INDEPENDENT_SECONDARY_SOURCE/CROSS_VALIDATION_ONLY_IF_SEPARATELY_QUALIFIED",
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
    if positive_dates:
        out["status"] = "OFFICIAL_TYPE1_DRV_TRANSPORT_EXTENT_OBSERVED_SEMANTICS_AND_161_COVERAGE_UNPROVEN"
        out["next_requirement"] = "QUALIFY_BDM_HISTORICAL_DOWNLOAD_AND_OFFICIAL_TIMESTAMP_PUBLICATION_REVISION_SEMANTICS_WITHOUT_ECONOMIC_READ"
    else:
        out["status"] = "OFFICIAL_TYPE1_DRV_FROZEN_MATRIX_TRANSPORT_UNAVAILABLE_FAIL_CLOSED"
        out["next_requirement"] = "CONTINUE_DISTINCT_OFFICIAL_BDM_SOURCE_DISCOVERY_BEFORE_DATA_GAP"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    out = qualify(requests.Session(), prereg)
    p = Path(args.output)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": out["status"],
        "positive_transport_count": out["positive_transport_count"],
        "strict_source_gate_green": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
