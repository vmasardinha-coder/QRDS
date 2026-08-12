#!/usr/bin/env python3
"""Collect verified realized USD-M funding evidence for one sealed V16B entry.

RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED. Public Binance Data Vision only.
Monthly fundingRate archives are verified against adjacent CHECKSUM files and
preserved raw. If the required month archive is not yet published, collection
fails closed/pending; zero funding is never synthesized.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import date, timedelta
from pathlib import Path

import requests

from tools.gate_btc_binance_usdm_funding_audit import BASE, close_ms, months_between, parse_funding_zip

HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _get(session: requests.Session, url: str) -> requests.Response:
    r = session.get(url, timeout=45)
    if r.status_code == 404:
        raise RuntimeError(f"FUNDING_ARCHIVE_PENDING:{url}")
    if r.status_code != 200:
        raise RuntimeError(f"Binance Data Vision HTTP {r.status_code}: {url}")
    return r


def fetch_verified_month(session: requests.Session, symbol: str, ym: str, out_dir: Path) -> tuple[list[tuple[int, float]], dict]:
    url = f"{BASE}/{symbol}/{symbol}-fundingRate-{ym}.zip"
    checksum_response = _get(session, url + ".CHECKSUM")
    token = checksum_response.text.strip().split()[0] if checksum_response.text.strip() else ""
    if not HEX64.fullmatch(token):
        raise RuntimeError(f"invalid Binance funding CHECKSUM: {url}")
    expected = token.lower()
    raw = _get(session, url).content
    actual = sha256_bytes(raw)
    if actual != expected:
        raise RuntimeError(f"funding archive checksum mismatch {symbol} {ym}: {actual} != {expected}")
    events, header = parse_funding_zip(raw)
    rel = Path("raw") / symbol / f"{symbol}-fundingRate-{ym}.zip"
    abs_path = out_dir / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(raw)
    checksum_rel = rel.with_suffix(rel.suffix + ".CHECKSUM")
    (out_dir / checksum_rel).write_text(checksum_response.text, encoding="utf-8")
    return events, {
        "symbol": symbol,
        "month": ym,
        "source_url": url,
        "raw_file": rel.as_posix(),
        "checksum_file": checksum_rel.as_posix(),
        "raw_sha256": actual,
        "expected_checksum_sha256": expected,
        "header": header,
    }


def collect(entry_event: dict, out_dir: Path) -> dict:
    if entry_event.get("event_type") != "V16B_ENTRY_SEAL" or not entry_event.get("seal_sha256"):
        raise ValueError("input must be a sealed V16B_ENTRY_SEAL")
    if entry_event.get("status") != "OK":
        raise ValueError("cannot collect funding for BLOCKED entry")
    shorts = list(entry_event["shorts_10"])
    if len(shorts) != 10 or len(set(shorts)) != 10:
        raise ValueError("entry must contain exactly 10 unique shorts")
    entry_day = entry_event["entry_date_utc"]
    exit_day = (date.fromisoformat(entry_day) + timedelta(days=7)).isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)

    cache: dict[tuple[str, str], list[tuple[int, float]]] = {}
    raw_meta: dict[tuple[str, str], dict] = {}
    with requests.Session() as s:
        s.headers.update({"User-Agent": "GATE-BTC-v16b-prospective-funding/1.0"})
        for asset in shorts:
            symbol = str(entry_event["entry_instruments"][asset])
            for ym in months_between(entry_day, exit_day):
                key = (symbol, ym)
                if key not in cache:
                    events, meta = fetch_verified_month(s, symbol, ym, out_dir)
                    cache[key] = events
                    raw_meta[key] = meta

    lo, hi = close_ms(entry_day), close_ms(exit_day)
    rows = []
    exposure = float(entry_event["exposure"])
    for asset in shorts:
        symbol = str(entry_event["entry_instruments"][asset])
        all_events = []
        evidence = []
        for ym in months_between(entry_day, exit_day):
            all_events.extend(cache[(symbol, ym)])
            evidence.append(raw_meta[(symbol, ym)])
        realized = sorted((t, r) for t, r in all_events if lo < t <= hi)
        if not realized:
            raise RuntimeError(f"ZERO_REALIZED_FUNDING_EVENTS:{asset}:{symbol}")
        rows.append({
            "entry_friday": entry_day,
            "exit_friday": exit_day,
            "asset": asset,
            "futures_symbol": symbol,
            "portfolio_exposure": exposure,
            "funding_events": len(realized),
            "funding_rate_sum": sum(r for _, r in realized),
            "first_event_ms": realized[0][0],
            "last_event_ms": realized[-1][0],
            "raw_evidence_sha256": hashlib.sha256(json.dumps([x["raw_sha256"] for x in evidence], separators=(",", ":")).encode()).hexdigest(),
        })

    csv_path = out_dir / "V16B_FUNDING_AUDIT.csv"
    fields = list(rows[0].keys())
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    raw_archives = [raw_meta[k] for k in sorted(raw_meta)]
    summary = {
        "status": "PASS",
        "candidate_id": entry_event["candidate_id"],
        "signal_date_utc": entry_event["signal_date_utc"],
        "entry_date_utc": entry_day,
        "exit_date_utc": exit_day,
        "entry_seal_sha256": entry_event["seal_sha256"],
        "source": BASE,
        "method": "sum checksum-verified archived funding rates strictly after entry-Friday close through exit-Friday close",
        "portfolio_application": "0.05 * sealed exposure * funding_rate_sum per selected short; positive funding benefits short",
        "positions": 10,
        "symbols": len({entry_event["entry_instruments"][a] for a in shorts}),
        "symbol_months": len(raw_archives),
        "zero_event_positions": 0,
        "missing_month_files": [],
        "raw_archives": raw_archives,
        "RESEARCH_ONLY": True,
        "SHADOW_ONLY": True,
        "NOT_APPROVED": True,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
        "ENGINE_FEED": False,
    }
    summary_path = out_dir / "V16B_FUNDING_AUDIT_SUMMARY.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--entry-event", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    entry_event = json.loads(Path(a.entry_event).read_text(encoding="utf-8"))
    result = collect(entry_event, Path(a.output_dir))
    print(json.dumps({"status": result["status"], "positions": result["positions"], "symbol_months": result["symbol_months"], "ORDERS": 0, "REAL_CAPITAL": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
