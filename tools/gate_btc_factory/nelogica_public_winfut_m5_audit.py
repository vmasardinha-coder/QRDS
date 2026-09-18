#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

URL = "https://raw.githubusercontent.com/ancompstuff/SwingAnalyzer/b7b786fb06ebf6d0d59f3572ade061d17a0086c9/data/WINFUT_F_0_5min.csv"
OUT = Path("artifacts/factory_512_nelogica_public")
START = "2025-01-01"
DISC_END = "2025-12-31"
REPL_START = "2026-01-01"
END = "2026-08-09"
MIN_TOTAL = 322
MIN_PART = 161
WIN_RE = re.compile(r"^WIN[FGHJKMNQUVXZ]\d{2}$", re.I)


def dump(name: str, obj) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def parse_dt(date_value: str, time_value: str) -> datetime:
    raw = f"{date_value.strip()} {time_value.strip()}"
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    raise ValueError(raw)


def find_col(fieldnames, candidates):
    norm = {str(x).strip().lower(): x for x in fieldnames}
    for c in candidates:
        if c in norm:
            return norm[c]
    return None


def main() -> int:
    with urllib.request.urlopen(URL, timeout=60) as r:
        raw = r.read()
    sha = hashlib.sha256(raw).hexdigest()
    text = raw.decode("cp1252")
    sample = text[:65536]
    dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    fields = reader.fieldnames or []
    date_col = find_col(fields, ["data", "date"])
    time_col = find_col(fields, ["hora", "time"])
    if not date_col or not time_col:
        raise RuntimeError(f"DATE_TIME_COLUMNS_NOT_FOUND:{fields}")

    rows = []
    symbol_like = defaultdict(set)
    unique_samples = defaultdict(set)
    parse_errors = []
    for idx, row in enumerate(reader, start=2):
        try:
            dt = parse_dt(row.get(date_col, ""), row.get(time_col, ""))
        except Exception:
            parse_errors.append({"line": idx, "date": row.get(date_col), "time": row.get(time_col)})
            continue
        rows.append((dt, row))
        for k, v in row.items():
            s = str(v or "").strip()
            if len(unique_samples[k]) < 20 and s:
                unique_samples[k].add(s)
            if WIN_RE.fullmatch(s):
                symbol_like[k].add(s.upper())

    rows.sort(key=lambda x: x[0])
    by_day = defaultdict(list)
    for dt, row in rows:
        d = dt.date().isoformat()
        if START <= d <= END:
            by_day[d].append(dt)

    day_qa = []
    for day in sorted(by_day):
        ts = sorted(by_day[day])
        duplicate = len(set(ts)) != len(ts)
        gaps = [int((b-a).total_seconds()) for a, b in zip(ts, ts[1:])]
        exact_300 = bool(ts) and all(g == 300 for g in gaps)
        valid = len(ts) >= 40 and not duplicate and exact_300
        day_qa.append({
            "session": day,
            "bar_count": len(ts),
            "duplicate": duplicate,
            "exact_300s_spacing": exact_300,
            "min_gap_seconds": min(gaps) if gaps else None,
            "max_gap_seconds": max(gaps) if gaps else None,
            "structurally_valid": valid,
            "first_time": ts[0].time().isoformat() if ts else None,
            "last_time": ts[-1].time().isoformat() if ts else None,
        })

    valid_days = [x["session"] for x in day_qa if x["structurally_valid"]]
    counts = {
        "total": len(valid_days),
        "discovery": sum(START <= d <= DISC_END for d in valid_days),
        "replication": sum(REPL_START <= d <= END for d in valid_days),
    }
    capacity = counts["total"] >= MIN_TOTAL and counts["discovery"] >= MIN_PART and counts["replication"] >= MIN_PART

    all_dates = [dt for dt, _ in rows]
    date_counts = Counter(dt.date().isoformat()[:4] for dt in all_dates)
    result = {
        "schema": "qrds.factory.invalidated_512.nelogica_public_winfut_m5_audit.v1",
        "evaluation_namespace": "RQ_STRICT_FORWARD_UNSEEN_2025_2026_V2",
        "source_url": URL,
        "source_git_blob_sha": "298038ec5961f2c6793c4be18f771a26b7d39378",
        "source_git_commit": "b7b786fb06ebf6d0d59f3572ade061d17a0086c9",
        "raw_byte_count": len(raw),
        "raw_sha256": sha,
        "encoding": "cp1252",
        "delimiter": dialect.delimiter,
        "columns": fields,
        "row_count_parsed": len(rows),
        "parse_error_count": len(parse_errors),
        "first_timestamp": all_dates[0].isoformat() if all_dates else None,
        "last_timestamp": all_dates[-1].isoformat() if all_dates else None,
        "rows_by_year": dict(sorted(date_counts.items())),
        "window": {"start": START, "discovery_end": DISC_END, "replication_start": REPL_START, "end": END},
        "window_session_count_observed": len(day_qa),
        "structurally_valid_session_counts": counts,
        "capacity_only_pass": capacity,
        "minimum_required": {"total": MIN_TOTAL, "discovery": MIN_PART, "replication": MIN_PART},
        "symbol_identity_columns": {k: sorted(v) for k, v in symbol_like.items()},
        "column_value_samples": {k: sorted(v) for k, v in unique_samples.items()},
        "scientific_admission_pass": False,
        "scientific_admission_blockers": [
            "CONTINUOUS_SYMBOL_WINFUT_F_0_NOT_EXACT_DELIVERY_CONTRACT_IDENTITY",
            "ROLL_CHRONOLOGY_NOT_PROVEN_FROM_FILE_OR_REPOSITORY",
            "PUBLICATION_SEMANTICS_NOT_PROVEN",
            "REVISION_SEMANTICS_NOT_PROVEN",
            "POINT_IN_TIME_VALIDITY_NOT_PROVEN"
        ],
        "credit": {"scientific_family_credit": 0, "prospective_credit": 0, "historical_backfill_credit": 0},
        "safety": {"RESEARCH_ONLY": True, "SHADOW_ONLY": True, "NOT_APPROVED": True, "ENGINE_FEED": False, "ORDERS": 0, "REAL_CAPITAL": 0, "NO_BACKFILL": True, "NO_RETUNE": True, "FAIL_CLOSED": True, "H1_ECONOMICS_READ": False},
    }
    dump("RESULT.json", result)
    dump("SESSION_QA.json", {"sessions": day_qa})
    dump("PARSE_ERRORS.json", parse_errors)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
