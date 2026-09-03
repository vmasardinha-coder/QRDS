#!/usr/bin/env python3
"""Physical capture + fail-closed structural QA for official B3 COTAHIST annual objects.

DATA only. No family/economics/prospective credit.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
import urllib.request
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.ZIP"
SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "NO_RETUNE": True,
    "NO_BACKFILL": True,
    "NO_COUNTER_RESET": True,
    "FAIL_CLOSED": True,
}

def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def fetch(url: str, attempts: int = 3) -> bytes:
    err = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "QRDS-research-source-audit/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
                if r.status != 200 or not data:
                    raise RuntimeError(f"HTTP {r.status}, bytes={len(data)}")
                return data
        except Exception as e:
            err = e
            if i + 1 < attempts:
                time.sleep(2 ** i)
    raise RuntimeError(f"official source fetch failed: {url}: {err}")

def parse_date(raw: bytes) -> date:
    return datetime.strptime(raw.decode("ascii"), "%Y%m%d").date()

def weekday_gap_count(ds: set[date]) -> int:
    if not ds:
        return 0
    cur, end = min(ds), max(ds)
    n = 0
    while cur <= end:
        if cur.weekday() < 5 and cur not in ds:
            n += 1
        cur += timedelta(days=1)
    return n

def field(line: bytes, a: int, b: int, enc: str = "ascii") -> str:
    return line[a:b].decode(enc, errors="replace").strip()

def inspect_payload(payload: bytes) -> dict:
    lines = payload.splitlines()
    invalid_len = 0
    invalid_quote = 0
    quote_count = 0
    dates: set[date] = set()
    keys: set[tuple[str, ...]] = set()
    duplicate_keys = 0
    symbol_isins: dict[str, set[str]] = defaultdict(set)
    record_types: dict[str, int] = defaultdict(int)

    for line in lines:
        if len(line) != 245:
            invalid_len += 1
            continue
        rt = field(line, 0, 2)
        record_types[rt] += 1
        if rt != "01":
            continue
        try:
            d = parse_date(line[2:10])
            bdi = field(line, 10, 12)
            symbol = field(line, 12, 24, "latin1")
            market = field(line, 24, 27)
            company = field(line, 27, 39, "latin1")
            spec = field(line, 39, 49, "latin1")
            term = field(line, 49, 52)
            currency = field(line, 52, 56)
            option_index = field(line, 201, 202)
            expiry = field(line, 202, 210)
            quotation_factor = field(line, 210, 217)
            isin = field(line, 230, 242)
            distribution = field(line, 242, 245)
            if not symbol or not market or not bdi:
                raise ValueError("empty identity")
        except Exception:
            invalid_quote += 1
            continue
        quote_count += 1
        dates.add(d)
        key = (
            d.isoformat(), bdi, symbol, market, company, spec, term, currency,
            option_index, expiry, quotation_factor, isin, distribution,
        )
        if key in keys:
            duplicate_keys += 1
        else:
            keys.add(key)
        if isin:
            symbol_isins[symbol].add(isin)

    multi_isin_symbols = {s: sorted(v) for s, v in symbol_isins.items() if len(v) > 1}
    return {
        "payload_line_count": len(lines),
        "record_types": dict(sorted(record_types.items())),
        "daily_quote_record_count": quote_count,
        "date_min": min(dates).isoformat() if dates else None,
        "date_max": max(dates).isoformat() if dates else None,
        "duplicate_full_identity_count": duplicate_keys,
        "invalid_record_length_count": invalid_len,
        "invalid_daily_quote_count": invalid_quote,
        "weekday_gap_count_in_observed_range_including_market_holidays": weekday_gap_count(dates),
        "symbol_count": len(symbol_isins),
        "symbols_with_multiple_isins_count": len(multi_isin_symbols),
        "symbols_with_multiple_isins_sample": dict(list(sorted(multi_isin_symbols.items()))[:25]),
    }

def capture_year(year: int, out: Path) -> dict:
    url = URL.format(year=year)
    raw = fetch(url)
    raw_path = out / f"COTAHIST_A{year}.ZIP"
    raw_path.write_bytes(raw)
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as e:
        raise RuntimeError(f"{year}: official object is not a valid ZIP") from e
    members = [n for n in z.namelist() if not n.endswith("/")]
    if len(members) != 1:
        raise RuntimeError(f"{year}: expected exactly one payload member, got {members}")
    member = members[0]
    payload = z.read(member)
    qa = inspect_payload(payload)
    if qa["daily_quote_record_count"] <= 0:
        raise RuntimeError(f"{year}: no daily quote records")
    if qa["duplicate_full_identity_count"] != 0:
        raise RuntimeError(f"{year}: duplicate full identity records={qa['duplicate_full_identity_count']}")
    if qa["invalid_record_length_count"] != 0 or qa["invalid_daily_quote_count"] != 0:
        raise RuntimeError(f"{year}: invalid records: {qa}")
    return {
        "year": year,
        "source_url": url,
        "raw_object": raw_path.name,
        "raw_zip_bytes": len(raw),
        "raw_zip_sha256": sha256(raw),
        "payload_member_name": member,
        "payload_bytes": len(payload),
        "payload_sha256": sha256(payload),
        **qa,
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2020-2026")
    ap.add_argument("--out", default="artifacts/gate_btc/factory/cotahist_capture")
    args = ap.parse_args()
    a, b = (int(x) for x in args.years.split("-", 1))
    if a > b:
        raise SystemExit("invalid year range")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    captures = [capture_year(y, out) for y in range(a, b + 1)]
    manifest = {
        "schema": "qrds.factory.b3_cotahist_physical_capture.v1",
        "stage": "DATA_PHYSICAL_CAPTURE_QA",
        "frontier": "B3_BLUECHIPS_UNIVARIATE",
        "provider": "B3 S.A. - Brasil, Bolsa, Balcao",
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "year_range": [a, b],
        "objects": captures,
        "status": "PASS_PHYSICAL_CAPTURE_QA",
        "economics_read_allowed": False,
        "family_creation_allowed": False,
        "scientific_credit": 0,
        "prospective_credit": 0,
        **SAFETY,
        "next_action": "FREEZE_CAPTURE_MANIFEST_THEN_PREREGISTER_MATERIALLY_DISTINCT_FAMILIES_WITHOUT_READING_ECONOMICS",
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "years": [a, b], "objects": len(captures), **SAFETY}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
