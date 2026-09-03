#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

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


def cotahist_index(capture_dir: Path) -> tuple[set[str], dict[str, dict[str, list[dict]]]]:
    sessions: set[str] = set()
    exact: dict[str, dict[str, list[dict]]] = {}
    zips = sorted(capture_dir.glob("COTAHIST_A*.ZIP"))
    if not zips:
        raise RuntimeError(f"no COTAHIST annual objects under {capture_dir}")
    for zp in zips:
        with zipfile.ZipFile(zp) as z:
            members = [n for n in z.namelist() if not n.endswith("/")]
            if len(members) != 1:
                raise RuntimeError(f"{zp.name}: expected one payload member, got {members}")
            with z.open(members[0]) as fh:
                for raw in fh:
                    line = raw.rstrip(b"\r\n")
                    if len(line) != 245 or line[:2] != b"01":
                        continue
                    ds = line[2:10].decode("ascii", errors="strict")
                    datetime.strptime(ds, "%Y%m%d")
                    day = f"{ds[:4]}-{ds[4:6]}-{ds[6:8]}"
                    sessions.add(day)
                    symbol = line[12:24].decode("latin1", errors="replace").strip()
                    prefix = "WIN" if symbol.startswith("WIN") else "WDO" if symbol.startswith("WDO") else None
                    if not prefix:
                        continue
                    def price(a: int, b: int) -> int | None:
                        s = line[a:b].decode("ascii", errors="ignore").strip()
                        return int(s) if s.isdigit() else None
                    rec = {
                        "symbol": symbol,
                        "bdi": line[10:12].decode("ascii", errors="replace").strip(),
                        "market_type": line[24:27].decode("ascii", errors="replace").strip(),
                        "open_raw": price(56, 69),
                        "high_raw": price(69, 82),
                        "low_raw": price(82, 95),
                        "close_raw": price(108, 121),
                    }
                    exact.setdefault(day, {}).setdefault(prefix, []).append(rec)
    return sessions, exact


def load_coverage(coverage_dir: Path) -> list[dict]:
    files = sorted(coverage_dir.glob("20??_Q?.json"))
    if len(files) != 20:
        raise RuntimeError(f"expected 20 quarter coverage files, got {len(files)}")
    rows = []
    for p in files:
        x = json.loads(p.read_text(encoding="utf-8"))
        if x.get("schema") != "qrds.factory.b3_win_wdo_coverage_block.v1":
            raise RuntimeError(f"{p.name}: wrong schema")
        if x.get("block_contract_pass") is not True:
            raise RuntimeError(f"{p.name}: block contract not passed")
        rows.append({"file": p.name, **x})
    return rows


def fetch(url: str, attempts: int = 3) -> bytes:
    err = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "QRDS-research-source-audit/1.0"})
            with urllib.request.urlopen(req, timeout=45) as r:
                body = r.read()
                if r.status != 200:
                    raise RuntimeError(f"HTTP {r.status}")
                return body
        except Exception as e:
            err = e
            if i + 1 < attempts:
                time.sleep(i + 1)
    raise RuntimeError(f"fetch failed {url}: {err}")


def xml_leaf_payloads(blob: bytes) -> list[bytes]:
    out: list[bytes] = []
    def walk(data: bytes) -> None:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for name in z.namelist():
                    if name.endswith("/"):
                        continue
                    child = z.read(name)
                    if child[:4] == b"PK\x03\x04":
                        walk(child)
                    elif child.lstrip().startswith(b"<"):
                        out.append(child)
        except zipfile.BadZipFile:
            return
    walk(blob)
    return out


def probe_sprd(day: str) -> dict:
    ymd = datetime.strptime(day, "%Y-%m-%d").strftime("%y%m%d")
    url = f"https://www.b3.com.br/pesquisapregao/download?filelist=SPRD{ymd}.zip"
    body = fetch(url)
    leafs = xml_leaf_payloads(body)
    text = b"\n".join(leafs)
    tickers = []
    for prefix in (b"WIN", b"WDO"):
        if prefix in text:
            tickers.append(prefix.decode())
    required_price_tags = [b"FrstPric", b"MinPric", b"MaxPric", b"LastPric"]
    return {
        "date": day,
        "url": url,
        "outer_bytes": len(body),
        "xml_leaf_count": len(leafs),
        "win_present": "WIN" in tickers,
        "wdo_present": "WDO" in tickers,
        "trade_date_present": day.encode() in text,
        "full_ohlc_tag_set_present": all(tag in text for tag in required_price_tags),
        "usable_as_exact_ohlc_fallback": bool(leafs) and "WIN" in tickers and "WDO" in tickers and day.encode() in text and all(tag in text for tag in required_price_tags),
    }


def probe_cotahist_ohlc(day: str, exact: dict[str, dict[str, list[dict]]]) -> dict:
    by_prefix = exact.get(day, {})
    def usable(prefix: str) -> list[dict]:
        out = []
        for r in by_prefix.get(prefix, []):
            vals = [r.get("open_raw"), r.get("high_raw"), r.get("low_raw"), r.get("close_raw")]
            if all(isinstance(v, int) and v > 0 for v in vals):
                out.append(r)
        return out
    win = usable("WIN")
    wdo = usable("WDO")
    return {
        "date": day,
        "win_records": win,
        "wdo_records": wdo,
        "win_usable_record_count": len(win),
        "wdo_usable_record_count": len(wdo),
        "usable_as_exact_ohlc_fallback": bool(win and wdo),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage-dir", required=True)
    ap.add_argument("--cotahist-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    coverage = load_coverage(Path(args.coverage_dir))
    sessions, cotahist_exact = cotahist_index(Path(args.cotahist_dir))

    no_object = sorted({d for x in coverage for d in x.get("weekday_no_object_dates", [])})
    raw_inconsistent_gaps = sorted(d for d in no_object if d in sessions)
    corroborated_non_sessions = sorted(d for d in no_object if d not in sessions)

    sprd_probes = [probe_sprd(d) for d in raw_inconsistent_gaps]
    sprd_days = sorted(x["date"] for x in sprd_probes if x["usable_as_exact_ohlc_fallback"])
    after_sprd = sorted(d for d in raw_inconsistent_gaps if d not in sprd_days)

    cotahist_ohlc_probes = [probe_cotahist_ohlc(d, cotahist_exact) for d in after_sprd]
    cotahist_ohlc_days = sorted(x["date"] for x in cotahist_ohlc_probes if x["usable_as_exact_ohlc_fallback"])
    unresolved_inconsistent_gaps = sorted(d for d in after_sprd if d not in cotahist_ohlc_days)

    published_dates = sorted({r["date"] for x in coverage for r in x.get("rows", []) if r.get("http_status") == 200 and r.get("leaf_payloads")})
    published_not_in_cotahist = sorted(d for d in published_dates if d not in sessions)

    quarter_summary = []
    for x in coverage:
        quarter_summary.append({
            "file": x["file"],
            "block": x["block"],
            "weekday_probe_count": x["weekday_probe_count"],
            "published_object_count": x["published_object_count"],
            "qualified_source_day_count": x["qualified_source_day_count"],
            "weekday_no_object_dates": x["weekday_no_object_dates"],
            "published_dates_missing_win_wdo_or_schema": x["published_dates_missing_win_wdo_or_schema"],
            "block_contract_pass": x["block_contract_pass"],
        })

    calendar_crosscheck_pass = not unresolved_inconsistent_gaps and not published_not_in_cotahist
    result = {
        "schema": "qrds.factory.b3_win_wdo_calendar_crosscheck.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "frontier": "WIN_UNIVARIATE_WDO_UNIVARIATE",
        "stage": "DATA_CALENDAR_CROSSCHECK",
        "coverage_horizon": ["2020-01-01", "2024-12-31"],
        "calendar_reference": "OFFICIAL_B3_COTAHIST_DAILY_QUOTE_DATES",
        "primary_surface": "BVBG.086.01_PRICEREPORT",
        "fallback_surface_probe": "BVBG.187.01_SPRD_THEN_OFFICIAL_COTAHIST_EXACT_OHLC_ONLY_FOR_PRIMARY_SESSION_GAPS",
        "quarter_count": len(coverage),
        "cotahist_session_count": len([d for d in sessions if "2020-01-01" <= d <= "2024-12-31"]),
        "weekday_no_object_count": len(no_object),
        "weekday_no_object_dates": no_object,
        "corroborated_non_session_dates": corroborated_non_sessions,
        "raw_primary_price_report_gaps_on_cotahist_sessions": raw_inconsistent_gaps,
        "sprd_fallback_probes": sprd_probes,
        "sprd_exact_ohlc_fallback_dates": sprd_days,
        "cotahist_exact_ohlc_fallback_probes": cotahist_ohlc_probes,
        "cotahist_exact_ohlc_fallback_dates": cotahist_ohlc_days,
        "inconsistent_price_report_gaps_on_cotahist_sessions": unresolved_inconsistent_gaps,
        "published_price_report_dates_not_in_cotahist": published_not_in_cotahist,
        "calendar_crosscheck_pass": calendar_crosscheck_pass,
        "quarter_summary": quarter_summary,
        "source_admission_pass": False,
        "source_admission_blocker": "IDENTITY_DEDUPE_PUBLICATION_TIMING_AND_PIT_QA_NOT_YET_FROZEN" if calendar_crosscheck_pass else "CALENDAR_CROSSCHECK_FAIL_UNRESOLVED_OFFICIAL_SESSION_GAP",
        "economics_read_allowed": False,
        "family_creation_allowed": False,
        "prospective_credit": 0,
        "scientific_credit": 0,
        "safety": SAFETY,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "quarter_count": result["quarter_count"],
        "weekday_no_object_count": result["weekday_no_object_count"],
        "raw_primary_session_gap_count": len(raw_inconsistent_gaps),
        "sprd_exact_ohlc_fallback_count": len(sprd_days),
        "cotahist_exact_ohlc_fallback_count": len(cotahist_ohlc_days),
        "unresolved_session_gap_count": len(unresolved_inconsistent_gaps),
        "calendar_crosscheck_pass": result["calendar_crosscheck_pass"],
        "source_admission_pass": result["source_admission_pass"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
