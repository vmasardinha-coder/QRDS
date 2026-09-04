#!/usr/bin/env python3
"""Physically qualify the preregistered BCAP RedStone public oracle route.

Qualification only. Scientific/source failure is preserved as a result and does not
cause methodology relaxation, source substitution, backfill, D0 or credit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API = "https://api.redstone.finance/prices/"
SYMBOL = "BCAP"
PROVIDER = "redstone"
START = datetime(2026, 8, 1, tzinfo=timezone.utc)
END_EXCLUSIVE = datetime(2026, 9, 3, tzinfo=timezone.utc)
EXPECTED_DAYS = 33
ZKSYNC_CONTRACT = "0x57fd71a86522dc06d6255537521886057c1772a3"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fetch() -> tuple[bytes, str]:
    params = {
        "symbol": SYMBOL,
        "provider": PROVIDER,
        "fromTimestamp": int(START.timestamp() * 1000),
        "toTimestamp": int((END_EXCLUSIVE.timestamp() * 1000) - 1),
        "limit": 10000,
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "QRDS-GATE-BTC-2-research-only/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read(), url


def _timestamp_ms(row: dict[str, Any]) -> int | None:
    for key in ("timestamp", "sourceTimestamp", "providerTimestamp"):
        value = row.get(key)
        if value is None:
            continue
        try:
            n = int(value)
            if n < 10_000_000_000:
                n *= 1000
            return n
        except (TypeError, ValueError):
            pass
    return None


def qualify(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "RAW.json"
    status = "FAIL_CLOSED_NO_PHYSICAL_OBSERVATIONS"
    qa_pass = False
    blockers: list[str] = []
    rows: list[dict[str, Any]] = []
    request_url: str | None = None
    raw = b""
    http_error: str | None = None

    try:
        raw, request_url = _fetch()
        raw_path.write_bytes(raw)
        payload = json.loads(raw.decode("utf-8"))
        if isinstance(payload, list):
            rows = [r for r in payload if isinstance(r, dict)]
        elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
            rows = [r for r in payload["data"] if isinstance(r, dict)]
        else:
            blockers.append("UNEXPECTED_RESPONSE_SCHEMA")
    except Exception as exc:  # network/API failure is evidence, not CI failure
        http_error = f"{type(exc).__name__}: {exc}"
        blockers.append("PUBLIC_API_REQUEST_FAILED")

    physical: list[tuple[int, float]] = []
    symbols = set()
    for row in rows:
        if row.get("symbol") is not None:
            symbols.add(str(row.get("symbol")))
        ts = _timestamp_ms(row)
        value = row.get("value")
        try:
            price = float(value)
        except (TypeError, ValueError):
            continue
        if ts is None or price <= 0:
            continue
        if int(START.timestamp() * 1000) <= ts < int(END_EXCLUSIVE.timestamp() * 1000):
            physical.append((ts, price))

    if rows and symbols and SYMBOL not in symbols:
        blockers.append("EXACT_SYMBOL_IDENTITY_NOT_PROVEN")

    by_day: dict[str, int] = defaultdict(int)
    for ts, _ in physical:
        day = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date().isoformat()
        by_day[day] += 1

    expected = {
        datetime.fromtimestamp(START.timestamp() + i * 86400, tz=timezone.utc).date().isoformat()
        for i in range(EXPECTED_DAYS)
    }
    observed = set(by_day)
    missing = sorted(expected - observed)
    if not physical:
        blockers.append("NO_POSITIVE_TIMESTAMPED_BCAP_OBSERVATIONS_IN_FROZEN_WINDOW")
    if missing:
        blockers.append("INCOMPLETE_DAILY_BUCKET_COVERAGE")
    if physical and not missing and (not symbols or SYMBOL in symbols):
        qa_pass = True
        status = "PASS_QUALIFIED_PHYSICAL_SOURCE_CANDIDATE"
    elif http_error:
        status = "FAIL_CLOSED_PUBLIC_API_UNAVAILABLE_OR_UNSUPPORTED"

    result = {
        "schema_version": "GATE_BTC_2_V2A_BCAP_REDSTONE_QUALIFICATION_V1",
        "symbol": SYMBOL,
        "coin_id": "blockchain-capital",
        "provider": "REDSTONE_PUBLIC_ORACLE",
        "provider_symbol": SYMBOL,
        "network": "zksync",
        "token_contract": ZKSYNC_CONTRACT,
        "request_url": request_url,
        "raw_sha256": _sha(raw) if raw else None,
        "response_rows": len(rows),
        "physical_rows_in_frozen_window": len(physical),
        "observed_daily_buckets": len(observed),
        "expected_daily_buckets": EXPECTED_DAYS,
        "missing_daily_buckets": missing,
        "symbols_returned": sorted(symbols),
        "qa_pass": qa_pass,
        "status": status,
        "blockers": list(dict.fromkeys(blockers)),
        "http_error": http_error,
        "qualification_only": True,
        "source_admitted": False,
        "historical_credit": 0,
        "scientific_credit": False,
        "prospective_credit": False,
        "d0_credit": 0,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill": True,
        "no_counter_reset": True,
        "no_silent_source_substitution": True,
        "fail_closed": True,
    }
    (output_dir / "SUMMARY.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    qualify(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
