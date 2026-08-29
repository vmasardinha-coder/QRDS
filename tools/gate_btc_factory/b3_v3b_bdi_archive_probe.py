#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools/gate_btc_factory/B3_V3B_BDI_ARCHIVE_PROBE_RUNTIME.json"

SENTINELS = {
    "2020": "2020-01-02",
    "2021": "2021-01-04",
    "2022": "2022-01-03",
    "2023": "2023-01-02",
    "2024": "2024-01-02",
}

BASE = "https://arquivos.b3.com.br/bdi/download/bdi/{date}/BDI_00_{yyyymmdd}.pdf"

SAFETY = {
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
}


def fetch(url: str) -> tuple[bytes, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "QRDS-research-source-qualification/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read(), r.geturl(), str(r.headers.get("Content-Type", ""))


def main() -> int:
    report = {
        "schema": "qrds.b3_autonomous_science.v3b.bdi_archive_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "purpose": "QUALIFY_OFFICIAL_B3_ARCHIVE_RETRIEVAL_CONTRACT_ONLY_NO_ECONOMICS",
        "provider": "B3",
        "candidate_identifier": "B3_BDI_ARCHIVE:BDI_00_YYYYMMDD.pdf",
        "candidate_url_template": BASE,
        "timezone_semantics": "REFERENCE_DATE_IS_B3_MARKET_DATE_AMERICA_SAO_PAULO; PUBLICATION_TIMESTAMP_NOT_YET_QUALIFIED",
        "role": "PRIMARY_OFFICIAL_DAILY_CONSOLIDATED_CANDIDATE_PENDING_FULL_QUALIFICATION",
        "stage_b_authorized": False,
        "economics_authorized": False,
        "family_ids_authorized": False,
        "h2890_plus_authorized": False,
        "mt5_role": "INDEPENDENT_SECONDARY_SOURCE_CROSS_VALIDATION_ONLY",
        "safety": SAFETY,
        "sentinels": {},
        "unresolved_gates": [
            "FULL_2020_2024_BUSINESS_DAY_COVERAGE_NOT_PROVEN",
            "SCHEMA_STABILITY_NOT_MACHINE_QUALIFIED",
            "PUBLICATION_TIMING_NOT_QUALIFIED",
            "REVISION_ERRATA_IMMUTABILITY_NOT_QUALIFIED",
            "CONTRACT_IDENTITY_AND_ROLL_CONTINUITY_NOT_QUALIFIED",
        ],
    }

    retrieved_years = []
    for year, date in SENTINELS.items():
        yyyymmdd = date.replace("-", "")
        url = BASE.format(date=date, yyyymmdd=yyyymmdd)
        row = {"date": date, "url": url}
        try:
            raw, final_url, content_type = fetch(url)
            row.update({
                "fetch_status": "PASS",
                "final_url": final_url,
                "content_type": content_type,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "pdf_signature": raw.startswith(b"%PDF-"),
            })
            if row["pdf_signature"]:
                row["archive_identity_status"] = "SENTINEL_RETRIEVED_OFFICIAL_PDF"
                retrieved_years.append(year)
            else:
                row["archive_identity_status"] = "FAIL_CLOSED_NON_PDF_PAYLOAD"
        except urllib.error.HTTPError as exc:
            row.update({"fetch_status": "HTTP_FAIL", "http_status": exc.code, "archive_identity_status": "UNQUALIFIED"})
        except Exception as exc:
            row.update({"fetch_status": "FETCH_FAIL", "error": f"{type(exc).__name__}: {exc}", "archive_identity_status": "UNQUALIFIED"})
        report["sentinels"][year] = row

    report["retrieved_years"] = retrieved_years
    report["sentinel_2020_2024_status"] = (
        "PASS_SENTINEL_YEARS_ONLY_NOT_FULL_COVERAGE" if len(retrieved_years) == len(SENTINELS)
        else "FAIL_CLOSED_SENTINEL_GAPS"
    )
    report["source_qualified"] = False
    report["scientific_gate"] = "BLOCKED_FAIL_CLOSED"
    report["hard_execution_fail"] = False

    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "sentinel_2020_2024_status": report["sentinel_2020_2024_status"],
        "retrieved_years": retrieved_years,
        "scientific_gate": report["scientific_gate"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
