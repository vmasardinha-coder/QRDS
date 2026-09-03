#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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


def cotahist_dates(capture_dir: Path) -> set[str]:
    out: set[str] = set()
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
                    out.add(f"{ds[:4]}-{ds[4:6]}-{ds[6:8]}")
    return out


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage-dir", required=True)
    ap.add_argument("--cotahist-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    coverage = load_coverage(Path(args.coverage_dir))
    sessions = cotahist_dates(Path(args.cotahist_dir))

    no_object = sorted({d for x in coverage for d in x.get("weekday_no_object_dates", [])})
    inconsistent_gaps = sorted(d for d in no_object if d in sessions)
    corroborated_non_sessions = sorted(d for d in no_object if d not in sessions)

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

    calendar_crosscheck_pass = not inconsistent_gaps and not published_not_in_cotahist
    result = {
        "schema": "qrds.factory.b3_win_wdo_calendar_crosscheck.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "frontier": "WIN_UNIVARIATE_WDO_UNIVARIATE",
        "stage": "DATA_CALENDAR_CROSSCHECK",
        "coverage_horizon": ["2020-01-01", "2024-12-31"],
        "calendar_reference": "OFFICIAL_B3_COTAHIST_DAILY_QUOTE_DATES",
        "quarter_count": len(coverage),
        "cotahist_session_count": len([d for d in sessions if "2020-01-01" <= d <= "2024-12-31"]),
        "weekday_no_object_count": len(no_object),
        "weekday_no_object_dates": no_object,
        "corroborated_non_session_dates": corroborated_non_sessions,
        "inconsistent_price_report_gaps_on_cotahist_sessions": inconsistent_gaps,
        "published_price_report_dates_not_in_cotahist": published_not_in_cotahist,
        "calendar_crosscheck_pass": calendar_crosscheck_pass,
        "quarter_summary": quarter_summary,
        "source_admission_pass": False,
        "source_admission_blocker": "IDENTITY_DEDUPE_PUBLICATION_TIMING_AND_PIT_QA_NOT_YET_FROZEN" if calendar_crosscheck_pass else "CALENDAR_CROSSCHECK_FAIL",
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
        "calendar_crosscheck_pass": result["calendar_crosscheck_pass"],
        "source_admission_pass": result["source_admission_pass"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
