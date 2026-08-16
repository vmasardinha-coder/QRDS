#!/usr/bin/env python3
"""Build a causal weekly Binance USD-M perpetual shortability ledger.

RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED.
Public Binance Data Vision archive only. No authentication, no orders, no capital.

Historical evidence rule (conservative): a USD-M perpetual contract is considered
shortable at Friday close only when the Binance Data Vision 1d kline archive has
both the Friday and the following Saturday file. This proves the instrument
traded on Friday and remained listed beyond Friday close. Absence is FAIL_CLOSED.
Current exchangeInfo is never used to backfill historical availability.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import requests

S3_BASES = (
    "https://s3.ap-northeast-1.amazonaws.com/data.binance.vision",
    "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision",
)
SYMBOL_ROOT = "data/futures/um/daily/klines/"
QUOTE_SUFFIXES = ("USDT", "USDC")
MULTIPLIER_PREFIXES = ("1000000", "1000", "1M")
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
DATE_RE = re.compile(r"-(\d{4}-\d{2}-\d{2})\.zip$")


def normalize_asset(symbol: str) -> str:
    s = symbol.upper().strip()
    for q in QUOTE_SUFFIXES:
        if s.endswith(q):
            s = s[: -len(q)]
            break
    for p in MULTIPLIER_PREFIXES:
        if s.startswith(p) and len(s) > len(p):
            s = s[len(p) :]
            break
    aliases = {
        "LUNA2": "LUNA",
        "BEAMX": "BEAM",
        "DODOX": "DODO",
    }
    return aliases.get(s, s)


def fridays(start: date, end: date) -> Iterable[date]:
    d = start
    while d.weekday() != 4:
        d += timedelta(days=1)
    while d <= end:
        yield d
        d += timedelta(days=7)


def _request_xml(session: requests.Session, params: dict, retries: int = 5) -> ET.Element:
    last = None
    for attempt in range(retries):
        for base in S3_BASES:
            try:
                r = session.get(base, params=params, timeout=45)
                if r.status_code == 200:
                    return ET.fromstring(r.content)
                last = RuntimeError(f"S3 HTTP {r.status_code}: {r.url}")
            except Exception as exc:  # fail after bounded retry/fallback
                last = exc
        time.sleep(min(0.5 * (2**attempt), 5.0))
    raise RuntimeError(f"Binance Data Vision S3 listing failed: {last}")


def list_common_prefixes(session: requests.Session, prefix: str) -> list[str]:
    out: list[str] = []
    token = None
    while True:
        params = {"list-type": "2", "prefix": prefix, "delimiter": "/", "max-keys": "1000"}
        if token:
            params["continuation-token"] = token
        root = _request_xml(session, params)
        out.extend(x.text or "" for x in root.findall("s3:CommonPrefixes/s3:Prefix", NS))
        truncated = (root.findtext("s3:IsTruncated", default="false", namespaces=NS).lower() == "true")
        if not truncated:
            break
        token = root.findtext("s3:NextContinuationToken", default="", namespaces=NS)
        if not token:
            raise RuntimeError("S3 listing truncated without continuation token")
    return out


def list_keys(session: requests.Session, prefix: str) -> list[str]:
    out: list[str] = []
    token = None
    while True:
        params = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            params["continuation-token"] = token
        root = _request_xml(session, params)
        out.extend(x.text or "" for x in root.findall("s3:Contents/s3:Key", NS))
        truncated = (root.findtext("s3:IsTruncated", default="false", namespaces=NS).lower() == "true")
        if not truncated:
            break
        token = root.findtext("s3:NextContinuationToken", default="", namespaces=NS)
        if not token:
            raise RuntimeError("S3 key listing truncated without continuation token")
    return out


def discover_futures_symbols(session: requests.Session) -> list[str]:
    prefixes = list_common_prefixes(session, SYMBOL_ROOT)
    syms: list[str] = []
    for p in prefixes:
        if not p.startswith(SYMBOL_ROOT):
            continue
        sym = p[len(SYMBOL_ROOT) :].strip("/").upper()
        # USD-M delivery contracts normally contain an underscore. We want perps.
        if not sym or "_" in sym or not sym.endswith(QUOTE_SUFFIXES):
            continue
        syms.append(sym)
    return sorted(set(syms))


def symbol_daily_dates(symbol: str, start: date, end_plus_one: date) -> tuple[str, set[date], str | None]:
    prefix = f"{SYMBOL_ROOT}{symbol}/1d/"
    try:
        with requests.Session() as session:
            session.headers.update({"User-Agent": "GATE-BTC-research-shortability/2.0"})
            keys = list_keys(session, prefix)
        dates: set[date] = set()
        for key in keys:
            if not key.endswith(".zip") or key.endswith(".zip.CHECKSUM"):
                continue
            m = DATE_RE.search(key)
            if not m:
                continue
            d = date.fromisoformat(m.group(1))
            if start <= d <= end_plus_one:
                dates.add(d)
        return symbol, dates, None
    except Exception as exc:
        return symbol, set(), repr(exc)


def build(start: date, end: date, out_csv: Path, out_summary: Path, workers: int = 16) -> dict:
    # Saturday evidence is required, so the last Friday must have a completed Saturday.
    completed_end = min(end, datetime.now(timezone.utc).date() - timedelta(days=1))
    eligible_fridays = [d for d in fridays(start, completed_end) if d + timedelta(days=1) <= completed_end]
    if not eligible_fridays:
        raise RuntimeError("no Friday has a completed following Saturday in requested interval")

    with requests.Session() as session:
        session.headers.update({"User-Agent": "GATE-BTC-research-shortability/2.0"})
        symbols = discover_futures_symbols(session)
    if not symbols:
        raise RuntimeError("no USD-M perpetual symbol directories discovered from Data Vision")

    by_symbol: dict[str, set[date]] = {}
    errors: dict[str, str] = {}
    end_plus_one = eligible_fridays[-1] + timedelta(days=1)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {ex.submit(symbol_daily_dates, sym, start, end_plus_one): sym for sym in symbols}
        for fut in as_completed(futs):
            sym, dates, err = fut.result()
            if err:
                errors[sym] = err
            else:
                by_symbol[sym] = dates

    # Fail closed on listing errors: do not silently treat a failed symbol request as absent.
    if errors:
        sample = dict(list(sorted(errors.items()))[:10])
        raise RuntimeError(f"symbol archive listing errors={len(errors)} sample={sample}")

    rows: list[dict] = []
    date_summaries: list[dict] = []
    for fri in eligible_fridays:
        sat = fri + timedelta(days=1)
        assets: set[str] = set()
        contracts = 0
        for sym, dates in sorted(by_symbol.items()):
            if fri not in dates or sat not in dates:
                continue
            asset = normalize_asset(sym)
            assets.add(asset)
            contracts += 1
            rows.append(
                {
                    "friday_utc": fri.isoformat(),
                    "futures_symbol": sym,
                    "asset": asset,
                    "friday_archive": True,
                    "saturday_archive": True,
                    "shortable_positive_evidence": True,
                }
            )
        date_summaries.append(
            {
                "friday_utc": fri.isoformat(),
                "futures_contracts": contracts,
                "normalized_assets": len(assets),
            }
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "friday_utc",
            "futures_symbol",
            "asset",
            "friday_archive",
            "saturday_archive",
            "shortable_positive_evidence",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    nonempty_dates = sum(1 for x in date_summaries if x["normalized_assets"] > 0)
    payload = {
        "status": "PASS" if rows and nonempty_dates == len(date_summaries) else "FAIL_INCOMPLETE_HISTORY",
        "RESEARCH_ONLY": True,
        "SHADOW_ONLY": True,
        "NOT_APPROVED": True,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
        "source": "Binance Data Vision public S3 archive: USD-M daily 1d klines",
        "source_root": SYMBOL_ROOT,
        "method": "positive evidence at Friday close = both Friday and following Saturday 1d archive files exist",
        "contract_filter": "USD-M symbol directory; exclude '_' delivery symbols; keep USDT/USDC quotes",
        "absence_policy": "FAIL_CLOSED; current exchangeInfo never backfills historical shortability",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "last_evidence_friday": eligible_fridays[-1].isoformat(),
        "fridays": len(date_summaries),
        "discovered_perpetual_symbols": len(symbols),
        "ledger_rows": len(rows),
        "dates": date_summaries,
    }
    out_summary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2020-07-03")
    p.add_argument("--end", default=None, help="UTC date; default most recent completed UTC day")
    p.add_argument("--workers", type=int, default=16)
    p.add_argument("--output-csv", default="artifacts/binance_shortability/BINANCE_USDM_WEEKLY_SHORTABLE.csv")
    p.add_argument("--output-summary", default="artifacts/binance_shortability/BINANCE_USDM_WEEKLY_SHORTABLE_SUMMARY.json")
    a = p.parse_args()
    start = date.fromisoformat(a.start)
    end = date.fromisoformat(a.end) if a.end else (datetime.now(timezone.utc).date() - timedelta(days=1))
    if end < start:
        raise SystemExit("end before start")
    payload = build(start, end, Path(a.output_csv), Path(a.output_summary), workers=a.workers)
    print(json.dumps({k: payload[k] for k in ["status", "start", "end", "fridays", "ledger_rows", "ORDERS", "REAL_CAPITAL"]}))
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
