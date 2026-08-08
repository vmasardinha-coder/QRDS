#!/usr/bin/env python3
"""Read-only probe for Bybit's public Spot trade archives.

The V5 API may be geo-blocked on hosted runners. Bybit also publishes a public
archive at public.bybit.com. This probe only verifies direct archive
availability/integrity. It does not bypass authentication, use a proxy, derive
V2A bars, or alter any frozen source chain.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import gzip
import hashlib
import io
import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

BASE = "https://public.bybit.com/spot"
DEFAULT_PAIRS = ("BTCUSDT", "ETHUSDT", "JASMYUSDT", "NEXOUSDT", "SYRUPUSDT")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def fetch_bytes(url: str, timeout: int = 25) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "GATE-BTC-research-bybit-archive-probe/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if getattr(response, "status", 200) != 200:
            raise urllib.error.HTTPError(url, response.status, "non-200", response.headers, None)
        return response.read()


def validate_gzip_csv(raw: bytes) -> dict:
    decompressed = gzip.decompress(raw)
    text = decompressed.decode("utf-8-sig", errors="strict")
    reader = csv.reader(io.StringIO(text, newline=""))
    rows = []
    for index, row in enumerate(reader):
        if row:
            rows.append(row)
        if index >= 10000:
            break
    if not rows:
        raise ValueError("empty Bybit archive CSV")
    header = rows[0]
    data_rows = rows[1:] if any(not cell.replace(".", "", 1).isdigit() for cell in header) else rows
    if not data_rows:
        raise ValueError("Bybit archive has header but no data rows")
    widths = {len(row) for row in data_rows[:100]}
    if len(widths) != 1 or min(widths) < 3:
        raise ValueError(f"unexpected Bybit CSV row widths: {sorted(widths)}")
    return {
        "compressed_size_bytes": len(raw),
        "compressed_sha256": hashlib.sha256(raw).hexdigest(),
        "decompressed_size_bytes": len(decompressed),
        "decompressed_sha256": hashlib.sha256(decompressed).hexdigest(),
        "header": header if data_rows is not rows else None,
        "sampled_data_rows": len(data_rows),
        "sampled_column_count": len(data_rows[0]),
    }


def probe_pair(pair: str, day: str, fetcher: Callable[[str], bytes] = fetch_bytes) -> dict:
    pair = pair.upper().strip()
    if not re.fullmatch(r"[A-Z0-9]{4,30}", pair):
        raise ValueError(f"invalid pair: {pair}")
    filename = f"{pair}_{day}.csv.gz"
    url = f"{BASE}/{pair}/{filename}"
    result = {"pair": pair, "day": day, "archive_path": f"/spot/{pair}/{filename}", "status": "RUNNING"}
    try:
        raw = fetcher(url)
        result.update({"status": "PASS_ARCHIVE_AVAILABLE", **validate_gzip_csv(raw)})
    except urllib.error.HTTPError as exc:
        result.update({
            "status": "NOT_AVAILABLE" if exc.code == 404 else ("GEO_BLOCKED" if exc.code == 403 else "HTTP_ERROR"),
            "http_status": exc.code,
            "error": str(exc)[:300],
        })
    except (urllib.error.URLError, TimeoutError) as exc:
        result.update({"status": "NETWORK_ERROR", "error": str(exc)[:300]})
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        result.update({"status": "FAIL_INTEGRITY", "error": f"{type(exc).__name__}: {str(exc)[:400]}"})
    return result


def safety_payload() -> dict:
    return {
        "role": "SOURCE_REDUNDANCY_PROBE_ONLY",
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "source_substitution_performed": False,
        "strategy_inputs_changed": False,
        "denominator_changed": False,
        "methodology_changes": 0,
        "proxy_or_geo_bypass_used": False,
        "authentication_used": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }


def run(day: str, pairs: list[str], fetcher: Callable[[str], bytes] = fetch_bytes, max_workers: int = 6) -> dict:
    date.fromisoformat(day)
    normalized = []
    for pair in pairs:
        item = pair.strip().upper()
        if item and item not in normalized:
            normalized.append(item)
    if not normalized:
        raise ValueError("at least one Bybit pair is required")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(max_workers, 8))) as executor:
        results = list(executor.map(lambda pair: probe_pair(pair, day, fetcher), normalized))
    counts: dict[str, int] = {}
    for row in results:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    if counts.get("FAIL_INTEGRITY", 0):
        status = "FAIL_INTEGRITY"
    elif counts.get("PASS_ARCHIVE_AVAILABLE", 0):
        status = "PASS_PUBLIC_ARCHIVE_AVAILABLE"
    elif counts.get("GEO_BLOCKED", 0) == len(results):
        status = "WARN_ARCHIVE_GEO_BLOCKED"
    else:
        status = "WARN_ARCHIVE_UNAVAILABLE"
    return {
        "schema": "gate_btc.bybit_public_spot_archive_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source": "BYBIT_PUBLIC_SPOT_ARCHIVE",
        "day": day,
        "pairs": normalized,
        "status_counts": counts,
        "results": results,
        "interpretation": "Public archive availability is independent redundancy evidence only; no V2A/Gateway source integration is authorized by this probe.",
        **safety_payload(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", required=True)
    parser.add_argument("--pairs", default=",".join(DEFAULT_PAIRS))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    payload = run(args.day, args.pairs.split(","))
    atomic_json(args.output, payload)
    print(json.dumps({
        "status": payload["status"],
        "status_counts": payload["status_counts"],
        "feeds_frozen_engine": False,
        "proxy_or_geo_bypass_used": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
