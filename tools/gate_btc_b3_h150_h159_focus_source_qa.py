from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from urllib.parse import quote, urlencode

import requests

BASE = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
START = "2020-01-01"
CUTOFF = "2026-08-10"
INDICATORS = ("Selic", "IPCA", "Câmbio", "PIB Total")
OUT = Path("artifacts/b3_h150_h159_focus_source_qa.json")
PAGE_SIZE = 5000
MAX_PAGES = 100


def request_url(indicator: str, skip: int) -> str:
    params = {
        "$format": "json",
        "$filter": f"Indicador eq '{indicator}' and Data ge '{START}' and Data lt '{CUTOFF}'",
        "$select": "Indicador,Data,DataReferencia,Mediana,DesvioPadrao,Minimo,Maximo,numeroRespondentes,baseCalculo",
        "$orderby": "Data asc,DataReferencia asc,baseCalculo asc",
        "$top": str(PAGE_SIZE),
        "$skip": str(skip),
    }
    return BASE + "?" + urlencode(params, safe="$',", quote_via=quote)


def fetch_indicator(indicator: str) -> tuple[bytes, dict]:
    # BCB/Olinda is strict about OData URL encoding and may return a full page
    # without @odata.nextLink. Use deterministic $skip pagination. The exact
    # frozen historical window is enforced remotely and re-validated locally.
    all_rows: list[dict] = []
    raw_parts: list[bytes] = []
    request_urls: list[str] = []

    for page_no in range(MAX_PAGES):
        skip = page_no * PAGE_SIZE
        url = request_url(indicator, skip)
        r = requests.get(url, timeout=60, headers={"User-Agent": "QRDS-B3-H150-source-qa/1.4"})
        r.raise_for_status()
        raw_parts.append(r.content)
        request_urls.append(url)
        payload = r.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("value"), list):
            raise RuntimeError(f"Unexpected OData payload for {indicator}")
        page = payload["value"]
        all_rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
    else:
        raise RuntimeError(f"pagination exceeded MAX_PAGES={MAX_PAGES}")

    admitted = []
    rejected_outside_window = 0
    for row in all_rows:
        d = str(row.get("Data") or "")[:10]
        if START <= d < CUTOFF:
            admitted.append(row)
        else:
            rejected_outside_window += 1

    if rejected_outside_window:
        raise RuntimeError(f"remote frozen-window filter leaked rows={rejected_outside_window}")

    raw = b"\n--QRDS-PAGE--\n".join(raw_parts)
    return raw, {
        "url": request_urls[0],
        "request_urls": request_urls,
        "source_rows": len(all_rows),
        "rows_rejected_outside_frozen_window": rejected_outside_window,
        "payload": {"value": admitted},
    }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "qrds.b3_h150_h159.focus_source_qa.v1",
        "provider": "Banco Central do Brasil / Dstat",
        "dataset": "Expectativas de Mercado",
        "service": BASE,
        "license": "ODbL (BCB Open Data catalog)",
        "historical_start_inclusive": START,
        "historical_cutoff_exclusive": CUTOFF,
        "remote_date_filter_used": True,
        "local_frozen_window_enforced": True,
        "pagination": "explicit_skip_until_short_page",
        "page_size": PAGE_SIZE,
        "economics_executed": False,
        "h1_economics_read": False,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "indicators": {},
    }
    failures = []
    for indicator in INDICATORS:
        try:
            raw, obj = fetch_indicator(indicator)
            rows = obj["payload"]["value"]
            if not rows:
                raise RuntimeError("zero rows inside frozen historical window")
            schema = sorted({k for row in rows for k in row.keys()})
            required = {"Indicador", "Data", "DataReferencia", "Mediana"}
            if not required.issubset(schema):
                raise RuntimeError(f"missing required fields: {sorted(required - set(schema))}")
            dates = [str(r.get("Data"))[:10] for r in rows if r.get("Data")]
            refs = [str(r.get("DataReferencia")) for r in rows if r.get("DataReferencia") is not None]
            if any(not (START <= d < CUTOFF) for d in dates):
                raise RuntimeError("local frozen-window enforcement failed")
            keys = [(r.get("Indicador"), r.get("Data"), r.get("DataReferencia"), r.get("baseCalculo")) for r in rows]
            dup = sum(v - 1 for v in Counter(keys).values() if v > 1)
            med_missing = sum(r.get("Mediana") is None for r in rows)
            coverage = {
                "replication_2020_22": any("2020-" <= d < "2022-" for d in dates),
                "replication_2022_24": any("2022-" <= d < "2024-" for d in dates),
                "discovery_2024_26": any("2024-" <= d < CUTOFF for d in dates),
            }
            if not all(coverage.values()):
                raise RuntimeError(f"coverage block missing: {coverage}")
            if dup:
                raise RuntimeError(f"duplicate exact source keys={dup}")
            report["indicators"][indicator] = {
                "request_url": obj["url"],
                "request_urls": obj["request_urls"],
                "request_page_count": len(obj["request_urls"]),
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "source_rows": obj["source_rows"],
                "rows_rejected_outside_frozen_window": obj["rows_rejected_outside_frozen_window"],
                "rows": len(rows),
                "schema": schema,
                "first_data_date": min(dates) if dates else None,
                "last_data_date": max(dates) if dates else None,
                "data_reference_examples": sorted(set(refs))[:8],
                "duplicate_exact_keys": dup,
                "median_missing_rows": med_missing,
                "coverage_blocks_present": coverage,
                "observed_fields": ["Mediana", "DesvioPadrao", "Minimo", "Maximo", "numeroRespondentes"],
                "derived_fields": [],
                "causal_admission": "NOT_YET_ADMITTED_PENDING_PUBLICATION_TIME_AND_FIXED_HORIZON_QA",
            }
        except Exception as exc:
            failures.append(f"{indicator}: {exc}")
    report["status"] = "SOURCE_QA_SCHEMA_COVERAGE_PASS_CAUSALITY_PENDING" if not failures else "DATA_GAP_SOURCE_QA"
    report["failures"] = failures
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
