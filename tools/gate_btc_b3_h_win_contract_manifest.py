#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = "America/Sao_Paulo"
H1_CUTOFF = date(2026, 8, 10)
ALLOWED_START = date(2024, 1, 2)
BDI_PARALLEL_START = date(2025, 12, 15)
LEGACY_PAGE_DEACTIVATED = date(2026, 3, 31)
MONTH_CODES = {2: "G", 4: "J", 6: "M", 8: "Q", 10: "V", 12: "Z"}
LEGACY_SOURCE = "https://arquivos.b3.com.br/rapinegocios/tickercsv/{date}"
BDI_ROOT = "https://arquivos.b3.com.br/bdi/"


@dataclass(frozen=True)
class WinContract:
    symbol: str
    expiry_nominal: date


def closest_wednesday_to_15(year: int, month: int) -> date:
    candidates = []
    for d in range(8, 23):
        x = date(year, month, d)
        if x.weekday() == 2:
            candidates.append(x)
    return min(candidates, key=lambda x: (abs(x.day - 15), x.day))


def next_even_month(year: int, month: int) -> tuple[int, int]:
    for m in (2, 4, 6, 8, 10, 12):
        if month <= m:
            return year, m
    return year + 1, 2


def win_front(session: date) -> WinContract:
    y, m = next_even_month(session.year, session.month)
    expiry = closest_wednesday_to_15(y, m)
    if session > expiry:
        idx = (2, 4, 6, 8, 10, 12).index(m)
        if idx == 5:
            y, m = y + 1, 2
        else:
            m = (2, 4, 6, 8, 10, 12)[idx + 1]
        expiry = closest_wednesday_to_15(y, m)
    return WinContract(symbol=f"WIN{MONTH_CODES[m]}{str(y)[-2:]}", expiry_nominal=expiry)


def source_binding(session: date) -> dict:
    """Describe only causal source policy; never pretend an unverified endpoint is usable."""
    if session < BDI_PARALLEL_START:
        return {
            "source_family": "B3_LEGACY_TRADE_BY_TRADE_ARCHIVE",
            "candidate_url": LEGACY_SOURCE.format(date=session.isoformat()),
            "binding_status": "REQUIRES_STAGE0_AVAILABILITY_AND_SCHEMA_PROOF",
        }
    if session <= LEGACY_PAGE_DEACTIVATED:
        return {
            "source_family": "B3_TRANSITION_LEGACY_OR_BDI",
            "candidate_url": None,
            "binding_status": "REQUIRES_STAGE0_EXACT_SOURCE_RESOLUTION",
        }
    return {
        "source_family": "B3_BDI_TRADE_BY_TRADE",
        "candidate_url": None,
        "bdi_root": BDI_ROOT,
        "binding_status": "REQUIRES_STAGE0_EXACT_DOWNLOAD_ENDPOINT_AND_SCHEMA_PROOF",
    }


def iter_weekdays(start: date, end_exclusive: date):
    d = start
    while d < end_exclusive:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def build_manifest(start: date = ALLOWED_START, end_exclusive: date = H1_CUTOFF) -> dict:
    if start < ALLOWED_START or end_exclusive > H1_CUTOFF or start >= end_exclusive:
        raise ValueError("MANIFEST_RANGE_OUTSIDE_PRE_H1_WINDOW")
    rows = []
    for d in iter_weekdays(start, end_exclusive):
        c = win_front(d)
        rows.append({
            "date": d.isoformat(),
            "WIN": c.symbol,
            "nominal_expiry": c.expiry_nominal.isoformat(),
            **source_binding(d),
            "status": "PRE_H1_ALLOWED_SOURCE_CANDIDATE_NOT_YET_ADMITTED",
        })
    return {
        "schema": "gate_btc.b3.h_nextgen.win_manifest.v2",
        "generated_at": datetime.now(ZoneInfo(TZ)).isoformat(),
        "research_only": True,
        "orders": 0,
        "real_capital": 0,
        "h1_economics_read": False,
        "h1_cutoff_exclusive": H1_CUTOFF.isoformat(),
        "allowed_start": ALLOWED_START.isoformat(),
        "instrument": "WIN",
        "front_policy": "calendar-causal: current even-month contract through nominal expiry; next even-month contract from following session",
        "holiday_policy": "source availability fail-closed; any expiration holiday exception requires explicit reviewed override before use",
        "source_transition": {
            "bdi_parallel_start": BDI_PARALLEL_START.isoformat(),
            "legacy_page_deactivated": LEGACY_PAGE_DEACTIVATED.isoformat(),
            "rule": "do not treat the legacy rapinegocios route as authoritative after B3 migration; exact BDI/archive binding must be proven in Stage 0",
        },
        "stage0_required_before_economics": True,
        "sessions": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=ALLOWED_START.isoformat())
    ap.add_argument("--end-exclusive", default=H1_CUTOFF.isoformat())
    ap.add_argument("--out", default="artifacts/b3_h_nextgen/WIN_PRE_H1_MANIFEST.json")
    a = ap.parse_args()
    obj = build_manifest(date.fromisoformat(a.start), date.fromisoformat(a.end_exclusive))
    p = Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "sessions": len(obj["sessions"]), "out": str(p), "h1_economics_read": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
