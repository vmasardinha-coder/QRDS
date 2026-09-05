#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

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
    "H1_ECONOMICS_READ": False,
}


def fetch(url: str) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 QRDS research-only source QA"})
    backoff = (0, 2, 5)
    for attempt, delay in enumerate(backoff, start=1):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return int(r.status), dict(r.headers.items()), r.read()
        except urllib.error.HTTPError as e:
            if int(e.code) in (403, 429) and attempt < len(backoff):
                time.sleep(5 * attempt)
                continue
            if 500 <= int(e.code) < 600 and attempt < len(backoff):
                continue
            return int(e.code), dict(e.headers.items()), e.read()
        except (TimeoutError, urllib.error.URLError):
            if attempt < len(backoff):
                continue
            return 599, {}, b""
    return 599, {}, b""


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def leaf_xmls(raw: bytes) -> list[tuple[str, bytes]]:
    out: list[tuple[str, bytes]] = []

    def walk(blob: bytes, prefix: str, depth: int) -> None:
        if depth > 3:
            return
        try:
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                for n in z.namelist():
                    if n.endswith("/"):
                        continue
                    b = z.read(n)
                    full = f"{prefix}{n}"
                    try:
                        with zipfile.ZipFile(io.BytesIO(b)):
                            walk(b, full + "::", depth + 1)
                            continue
                    except zipfile.BadZipFile:
                        pass
                    if n.lower().endswith(".xml"):
                        out.append((full, b))
        except zipfile.BadZipFile:
            return

    walk(raw, "", 0)
    return out


def as_float(text: str | None) -> float | None:
    if text is None:
        return None
    try:
        return float(text.strip().replace(",", "."))
    except (ValueError, AttributeError):
        return None


def parse_xml(xml_bytes: bytes, leaf_path: str, leaf_sha256: str) -> tuple[set[str], set[str], bool, list[dict]]:
    root = ET.fromstring(xml_bytes)
    tickers: set[str] = set()
    tags: set[str] = set()
    parent = {c: p for p in root.iter() for c in p}
    ticker_nodes = []
    for e in root.iter():
        name = local(e.tag)
        tags.add(name)
        if name == "TckrSymb" and e.text:
            symbol = e.text.strip()
            tickers.add(symbol)
            if symbol.startswith(("WIN", "WDO")):
                ticker_nodes.append((e, symbol))
    required = {"TckrSymb", "FrstPric", "MinPric", "MaxPric", "LastPric"}
    schema_ok = required.issubset(tags)
    market_rows: list[dict] = []
    seen = set()
    volume_candidates = ("FinInstrmQty", "TradQty", "RglrTxsQty", "Qty", "NtlFinVol")

    # Mechanical performance cache only: preserve the exact nearest-ancestor
    # selection semantics while avoiding repeated full subtree scans for every
    # WIN/WDO ticker node in large PriceReport XML payloads.
    values_cache: dict[ET.Element, dict[str, str]] = {}

    def values_for(element: ET.Element) -> dict[str, str]:
        cached = values_cache.get(element)
        if cached is not None:
            return cached
        values: dict[str, str] = {}
        for d in element.iter():
            n = local(d.tag)
            if n not in values and d.text and d.text.strip():
                values[n] = d.text.strip()
        values_cache[element] = values
        return values

    for node, symbol in ticker_nodes:
        cur = parent.get(node)
        chosen = None
        values = None
        while cur is not None:
            m = values_for(cur)
            if all(k in m for k in required):
                chosen, values = cur, m
                break
            cur = parent.get(cur)
        if chosen is None or values is None:
            continue
        o, h, l, c = (as_float(values.get(k)) for k in ("FrstPric", "MaxPric", "MinPric", "LastPric"))
        if any(v is None for v in (o, h, l, c)) or min(o, h, l, c) <= 0:
            continue
        volume = None
        volume_tag = None
        for tag in volume_candidates:
            v = as_float(values.get(tag))
            if v is not None and v >= 0:
                volume, volume_tag = v, tag
                break
        key = (symbol, o, h, l, c, leaf_sha256)
        if key in seen:
            continue
        seen.add(key)
        market_rows.append({
            "ticker_symbol": symbol,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume_or_traded_quantity": volume,
            "volume_field": volume_tag,
            "report_leaf_path": leaf_path,
            "report_leaf_sha256": leaf_sha256,
        })
    return tickers, tags, schema_ok, market_rows


def daterange(a: date, b: date):
    d = a
    while d <= b:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    rows = []
    for d in daterange(start, end):
        token = d.strftime("%y%m%d")
        url = f"https://www.b3.com.br/pesquisapregao/download?filelist=PR{token}.zip"
        status, headers, raw = fetch(url)
        item = {
            "date": d.isoformat(), "url": url, "http_status": status,
            "content_type": headers.get("Content-Type") or headers.get("content-type"),
            "outer_byte_count": len(raw), "outer_sha256": hashlib.sha256(raw).hexdigest(),
            "leaf_payloads": [], "win_tickers": [], "wdo_tickers": [],
            "pricereport_schema": False, "market_rows": [],
        }
        if status == 200:
            all_tickers: set[str] = set(); schema = False; all_market_rows = []
            for path, xb in leaf_xmls(raw):
                leaf_hash = hashlib.sha256(xb).hexdigest()
                try:
                    tickers, _tags, ok, mrows = parse_xml(xb, path, leaf_hash)
                except ET.ParseError:
                    continue
                schema = schema or ok; all_tickers.update(tickers); all_market_rows.extend(mrows)
                item["leaf_payloads"].append({"path": path, "byte_count": len(xb), "sha256": leaf_hash})
            item["pricereport_schema"] = schema
            item["win_tickers"] = sorted(t for t in all_tickers if t.startswith("WIN"))
            item["wdo_tickers"] = sorted(t for t in all_tickers if t.startswith("WDO"))
            item["market_rows"] = all_market_rows
        rows.append(item)

    published = [r for r in rows if r["http_status"] == 200 and r["leaf_payloads"]]
    source_days = [r for r in published if r["pricereport_schema"] and r["win_tickers"] and r["wdo_tickers"]]
    weekday_no_object = [r["date"] for r in rows if r["http_status"] != 200 or not r["leaf_payloads"]]
    transport_failures = [r["date"] for r in rows if r["http_status"] == 599]
    source_days_missing_line = [r["date"] for r in published if not (r["pricereport_schema"] and r["win_tickers"] and r["wdo_tickers"])]
    parsed_market_row_count = sum(len(r["market_rows"]) for r in rows)
    parsed_win_row_count = sum(sum(x["ticker_symbol"].startswith("WIN") for x in r["market_rows"]) for r in rows)
    parsed_wdo_row_count = sum(sum(x["ticker_symbol"].startswith("WDO") for x in r["market_rows"]) for r in rows)
    block_pass = bool(source_days) and not source_days_missing_line and not transport_failures and parsed_win_row_count > 0 and parsed_wdo_row_count > 0
    result = {
        "schema": "qrds.factory.b3_win_wdo_coverage_block.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "frontier": "WIN_UNIVARIATE_WDO_UNIVARIATE", "stage": "DATA_SOURCE_QUALIFICATION_BLOCK",
        "block": {"start": start.isoformat(), "end": end.isoformat()},
        "official_surface": "B3 Pesquisa por pregao / PriceReport",
        "candidate_contract": "https://www.b3.com.br/pesquisapregao/download?filelist=PR{YYMMDD}.zip",
        "transport_retry_policy": {"attempts": 3, "backoff_seconds": [0, 2, 5], "timeout_seconds": 45, "terminal_transport_status": 599},
        "weekday_probe_count": len(rows), "published_object_count": len(published), "qualified_source_day_count": len(source_days),
        "parsed_market_row_count": parsed_market_row_count, "parsed_win_row_count": parsed_win_row_count, "parsed_wdo_row_count": parsed_wdo_row_count,
        "weekday_no_object_dates": weekday_no_object, "transport_failure_dates": transport_failures,
        "published_dates_missing_win_wdo_or_schema": source_days_missing_line,
        "block_contract_pass": block_pass,
        "calendar_gap_status": "REQUIRES_OFFICIAL_CALENDAR_CROSSCHECK" if weekday_no_object else "NO_WEEKDAY_GAPS",
        "source_admission_pass": False, "economics_read_allowed": False, "family_creation_allowed": False,
        "prospective_credit": 0, "scientific_credit": 0, "rows": rows, "safety": SAFETY,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ["weekday_probe_count", "published_object_count", "qualified_source_day_count", "parsed_market_row_count", "block_contract_pass", "calendar_gap_status", "source_admission_pass"]}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
