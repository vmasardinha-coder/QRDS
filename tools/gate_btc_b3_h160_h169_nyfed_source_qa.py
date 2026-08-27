#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode

import requests

BASE = "https://markets.newyorkfed.org/api/rates"
START = "2020-01-01"
END = "2026-08-09"
CUTOFF = "2026-08-10"
SERIES = {
    "SOFR": ("secured", "sofr"),
    "BGCR": ("secured", "bgcr"),
    "TGCR": ("secured", "tgcr"),
    "EFFR": ("unsecured", "effr"),
    "OBFR": ("unsecured", "obfr"),
}
REQUIRED = {
    "effectiveDate", "percentRate", "volumeInBillions",
    "percentPercentile1", "percentPercentile25",
    "percentPercentile75", "percentPercentile99",
}
BLOCKS = {
    "replication_2020_22": ("2020-01-01", "2022-12-31"),
    "replication_2022_24": ("2022-01-01", "2024-12-31"),
    "discovery_2024_26": ("2024-01-01", END),
}


def url_for(group: str, slug: str) -> str:
    return f"{BASE}/{group}/{slug}/search.json?" + urlencode({
        "startDate": START,
        "endDate": END,
        "type": "rate",
    })


def fetch_one(name: str, group: str, slug: str) -> tuple[bytes, dict]:
    url = url_for(group, slug)
    r = requests.get(url, headers={"Accept": "application/json", "User-Agent": "QRDS-B3-research/1.0"}, timeout=45)
    r.raise_for_status()
    raw = r.content
    obj = r.json()
    rows = obj.get("refRates")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"{name}: missing/nonempty refRates")
    return raw, {"url": url, "rows": rows}


def iso_date(v: object) -> str:
    s = str(v or "")[:10]
    if len(s) != 10 or s[4] != "-" or s[7] != "-":
        raise RuntimeError(f"bad effectiveDate:{v}")
    return s


def qa_series(name: str, raw: bytes, meta: dict) -> dict:
    rows = meta["rows"]
    keys = set().union(*(set(r) for r in rows if isinstance(r, dict)))
    missing_schema = sorted(REQUIRED - keys)
    dates = [iso_date(r.get("effectiveDate")) for r in rows]
    if any(d >= CUTOFF for d in dates):
        raise RuntimeError(f"{name}: post-cutoff row")
    dupes = len(dates) - len(set(dates))
    numeric_missing = {}
    for fld in sorted(REQUIRED - {"effectiveDate"}):
        numeric_missing[fld] = sum(r.get(fld) in (None, "") for r in rows)
    block_counts = {}
    for b, (lo, hi) in BLOCKS.items():
        block_counts[b] = sum(lo <= d <= hi for d in dates)
    return {
        "series": name,
        "url": meta["url"],
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "raw_bytes": len(raw),
        "rows": len(rows),
        "first_effective_date": min(dates),
        "last_effective_date": max(dates),
        "schema_fields": sorted(keys),
        "missing_required_schema_fields": missing_schema,
        "duplicate_effective_dates": dupes,
        "missing_required_values": numeric_missing,
        "block_counts": block_counts,
        "rate_name_values": sorted({str(r.get("rateName")) for r in rows if r.get("rateName") is not None})[:10],
        "type_values": sorted({str(r.get("type")) for r in rows if r.get("type") is not None})[:10],
        "observed_fields": sorted(REQUIRED),
    }


def main() -> None:
    out = {
        "schema": "qrds.b3_h160_h169.nyfed_source_qa.v1",
        "provider": "Federal Reserve Bank of New York",
        "resource": "Markets Data API administered reference rates",
        "cutoff_exclusive": CUTOFF,
        "causal_rule": "B3 session D may use only NY Fed observation admitted by prior completed B3 session P; no same-session timing dependency",
        "publication_note": "Reference rates are official daily NY Fed publications; adapter deliberately imposes an additional completed-B3-session lag",
        "economics_executed": False,
        "h1_economics_read": False,
        "survivor_partial_economics_read": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "series": {},
    }
    failures = []
    for name, (group, slug) in SERIES.items():
        raw, meta = fetch_one(name, group, slug)
        q = qa_series(name, raw, meta)
        out["series"][name] = q
        if q["missing_required_schema_fields"] or q["duplicate_effective_dates"]:
            failures.append(name + ":schema_or_dupes")
        if any(q["block_counts"][b] < 200 for b in BLOCKS):
            failures.append(name + ":coverage")
        if q["missing_required_values"].get("percentRate", 0) or q["missing_required_values"].get("volumeInBillions", 0):
            failures.append(name + ":rate_or_volume_missing")
    out["failures"] = failures
    out["status"] = "SOURCE_QA_PASS_ECONOMICS_STILL_BLOCKED" if not failures else "SOURCE_QA_FAIL_CLOSED"
    path = Path("artifacts/b3_h160_h169_nyfed_source_qa.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": out["status"], "failures": failures, "artifact": str(path)}))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
