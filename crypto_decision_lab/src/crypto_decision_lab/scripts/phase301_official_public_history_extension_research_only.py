from __future__ import annotations

import argparse
import math
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import (
    OFFICIAL_ENDPOINT_REGISTRY,
    ROOT,
    base_payload,
    deduplicate_by_timestamp,
    floor_closed_hour_ms,
    gap_report,
    http_get_json,
    iso_from_ms,
    sha256_file,
    utc_now_iso,
    write_csv_gz,
    write_json,
    write_text,
)

HOUR_MS = 60 * 60 * 1000
CANDLE_FIELDS = (
    "provider",
    "market_type",
    "symbol",
    "interval",
    "open_time_ms",
    "open_time_utc",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_volume",
    "complete",
)
FUNDING_FIELDS = (
    "provider",
    "market_type",
    "symbol",
    "funding_time_ms",
    "funding_time_utc",
    "funding_rate",
)
OI_FIELDS = (
    "provider",
    "market_type",
    "symbol",
    "timestamp_ms",
    "timestamp_utc",
    "open_interest",
)


def _pause(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def _normalize_candle(
    provider: str,
    market_type: str,
    symbol: str,
    timestamp: Any,
    open_value: Any,
    high_value: Any,
    low_value: Any,
    close_value: Any,
    volume: Any,
    quote_volume: Any,
    complete: Any = True,
) -> dict[str, Any]:
    ts = int(timestamp)
    values = [float(open_value), float(high_value), float(low_value), float(close_value), float(volume)]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Non-finite candle value.")
    if values[0] <= 0 or values[1] <= 0 or values[2] <= 0 or values[3] <= 0:
        raise ValueError("Non-positive candle price.")
    if values[1] < max(values[0], values[3], values[2]):
        raise ValueError("Candle high violates OHLC.")
    if values[2] > min(values[0], values[3], values[1]):
        raise ValueError("Candle low violates OHLC.")
    quote = float(quote_volume) if quote_volume not in (None, "") else values[4] * values[3]
    return {
        "provider": provider,
        "market_type": market_type,
        "symbol": symbol,
        "interval": "1h",
        "open_time_ms": ts,
        "open_time_utc": iso_from_ms(ts),
        "open": values[0],
        "high": values[1],
        "low": values[2],
        "close": values[3],
        "volume": values[4],
        "quote_volume": quote,
        "complete": bool(int(complete)) if isinstance(complete, str) and complete.isdigit() else bool(complete),
    }


def collect_binance_candles(start_ms: int, end_ms: int) -> tuple[list[dict[str, Any]], int]:
    spec = OFFICIAL_ENDPOINT_REGISTRY["binance_candles"]
    cursor = start_ms
    rows: list[dict[str, Any]] = []
    requests = 0
    while cursor <= end_ms:
        payload = http_get_json(
            spec["endpoint"],
            {
                "symbol": "BTCUSDT",
                "interval": "1h",
                "startTime": cursor,
                "endTime": end_ms + HOUR_MS - 1,
                "limit": spec["max_limit"],
            },
        )
        requests += 1
        if not isinstance(payload, list):
            raise TypeError("Binance candle payload is not a list.")
        if not payload:
            break
        page = [
            _normalize_candle(
                "BINANCE",
                "USDS_M_FUTURES",
                "BTCUSDT",
                item[0],
                item[1],
                item[2],
                item[3],
                item[4],
                item[5],
                item[7] if len(item) > 7 else None,
                True,
            )
            for item in payload
        ]
        rows.extend(page)
        newest = max(int(item["open_time_ms"]) for item in page)
        if newest < cursor:
            raise RuntimeError("Binance pagination did not advance.")
        cursor = newest + HOUR_MS
        _pause(0.08)
    return deduplicate_by_timestamp(rows), requests


def collect_okx_candles(start_ms: int, end_ms: int) -> tuple[list[dict[str, Any]], int]:
    spec = OFFICIAL_ENDPOINT_REGISTRY["okx_candles"]
    after = end_ms + HOUR_MS
    rows: list[dict[str, Any]] = []
    requests = 0
    previous_oldest: int | None = None
    while after > start_ms:
        payload = http_get_json(
            spec["endpoint"],
            {
                "instId": "BTC-USDT-SWAP",
                "bar": "1H",
                "after": after,
                "limit": spec["max_limit"],
            },
        )
        requests += 1
        if not isinstance(payload, dict) or str(payload.get("code")) != "0":
            raise RuntimeError(f"OKX candle response rejected: {payload}")
        data = payload.get("data")
        if not isinstance(data, list):
            raise TypeError("OKX candle data is not a list.")
        if not data:
            break
        page = []
        for item in data:
            if len(item) < 6:
                raise ValueError("OKX candle row has insufficient fields.")
            page.append(
                _normalize_candle(
                    "OKX",
                    "SWAP",
                    "BTC-USDT-SWAP",
                    item[0],
                    item[1],
                    item[2],
                    item[3],
                    item[4],
                    item[5],
                    item[7] if len(item) > 7 else None,
                    item[8] if len(item) > 8 else True,
                )
            )
        rows.extend(page)
        oldest = min(int(item["open_time_ms"]) for item in page)
        if previous_oldest is not None and oldest >= previous_oldest:
            raise RuntimeError("OKX pagination did not move backward.")
        previous_oldest = oldest
        after = oldest
        if oldest <= start_ms:
            break
        _pause(0.22)
    result = [
        row
        for row in deduplicate_by_timestamp(rows)
        if start_ms <= int(row["open_time_ms"]) <= end_ms
    ]
    return result, requests


def collect_bybit_candles(start_ms: int, end_ms: int) -> tuple[list[dict[str, Any]], int]:
    spec = OFFICIAL_ENDPOINT_REGISTRY["bybit_candles"]
    cursor_end = end_ms + HOUR_MS - 1
    rows: list[dict[str, Any]] = []
    requests = 0
    previous_oldest: int | None = None
    while cursor_end >= start_ms:
        payload = http_get_json(
            spec["endpoint"],
            {
                "category": "linear",
                "symbol": "BTCUSDT",
                "interval": "60",
                "start": start_ms,
                "end": cursor_end,
                "limit": spec["max_limit"],
            },
        )
        requests += 1
        if not isinstance(payload, dict) or int(payload.get("retCode", -1)) != 0:
            raise RuntimeError(f"Bybit candle response rejected: {payload}")
        data = payload.get("result", {}).get("list")
        if not isinstance(data, list):
            raise TypeError("Bybit candle data is not a list.")
        if not data:
            break
        page = [
            _normalize_candle(
                "BYBIT",
                "LINEAR_PERPETUAL",
                "BTCUSDT",
                item[0],
                item[1],
                item[2],
                item[3],
                item[4],
                item[5],
                item[6] if len(item) > 6 else None,
                True,
            )
            for item in data
        ]
        rows.extend(page)
        oldest = min(int(item["open_time_ms"]) for item in page)
        if previous_oldest is not None and oldest >= previous_oldest:
            raise RuntimeError("Bybit candle pagination did not move backward.")
        previous_oldest = oldest
        if oldest <= start_ms:
            break
        cursor_end = oldest - 1
        _pause(0.08)
    result = [
        row
        for row in deduplicate_by_timestamp(rows)
        if start_ms <= int(row["open_time_ms"]) <= end_ms
    ]
    return result, requests


def _coinbase_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def collect_coinbase_candles(start_ms: int, end_ms: int) -> tuple[list[dict[str, Any]], int]:
    spec = OFFICIAL_ENDPOINT_REGISTRY["coinbase_candles"]
    chunk_hours = 250
    cursor = start_ms
    rows: list[dict[str, Any]] = []
    requests = 0
    while cursor <= end_ms:
        chunk_end = min(end_ms + HOUR_MS, cursor + chunk_hours * HOUR_MS)
        payload = http_get_json(
            spec["endpoint"],
            {
                "granularity": 3600,
                "start": _coinbase_iso(cursor),
                "end": _coinbase_iso(chunk_end),
            },
            user_agent="QRDS-GATE-BTC-Research-Only/301",
        )
        requests += 1
        if not isinstance(payload, list):
            raise TypeError(f"Coinbase candle payload is not a list: {payload}")
        for item in payload:
            if len(item) < 6:
                raise ValueError("Coinbase candle row has insufficient fields.")
            timestamp_ms = int(item[0]) * 1000
            rows.append(
                _normalize_candle(
                    "COINBASE",
                    "SPOT",
                    "BTC-USD",
                    timestamp_ms,
                    item[3],
                    item[2],
                    item[1],
                    item[4],
                    item[5],
                    float(item[5]) * float(item[4]),
                    True,
                )
            )
        cursor = chunk_end
        _pause(0.12)
    result = [
        row
        for row in deduplicate_by_timestamp(rows)
        if start_ms <= int(row["open_time_ms"]) <= end_ms
    ]
    return result, requests


def collect_binance_funding(start_ms: int, end_ms: int) -> tuple[list[dict[str, Any]], int]:
    spec = OFFICIAL_ENDPOINT_REGISTRY["binance_funding"]
    cursor = start_ms
    rows: list[dict[str, Any]] = []
    requests = 0
    while cursor <= end_ms:
        payload = http_get_json(
            spec["endpoint"],
            {
                "symbol": "BTCUSDT",
                "startTime": cursor,
                "endTime": end_ms,
                "limit": spec["max_limit"],
            },
        )
        requests += 1
        if not isinstance(payload, list):
            raise TypeError("Binance funding payload is not a list.")
        if not payload:
            break
        for item in payload:
            timestamp = int(item["fundingTime"])
            rows.append(
                {
                    "provider": "BINANCE",
                    "market_type": "USDS_M_FUTURES",
                    "symbol": "BTCUSDT",
                    "funding_time_ms": timestamp,
                    "funding_time_utc": iso_from_ms(timestamp),
                    "funding_rate": float(item["fundingRate"]),
                }
            )
        newest = max(int(item["fundingTime"]) for item in payload)
        if newest < cursor:
            raise RuntimeError("Binance funding pagination did not advance.")
        cursor = newest + 1
        _pause(0.08)
    indexed = {int(row["funding_time_ms"]): row for row in rows}
    return [indexed[key] for key in sorted(indexed)], requests


def collect_bybit_funding(start_ms: int, end_ms: int) -> tuple[list[dict[str, Any]], int]:
    spec = OFFICIAL_ENDPOINT_REGISTRY["bybit_funding"]
    cursor_end = end_ms
    rows: list[dict[str, Any]] = []
    requests = 0
    previous_oldest: int | None = None
    while cursor_end >= start_ms:
        payload = http_get_json(
            spec["endpoint"],
            {
                "category": "linear",
                "symbol": "BTCUSDT",
                "endTime": cursor_end,
                "limit": spec["max_limit"],
            },
        )
        requests += 1
        if not isinstance(payload, dict) or int(payload.get("retCode", -1)) != 0:
            raise RuntimeError(f"Bybit funding response rejected: {payload}")
        data = payload.get("result", {}).get("list")
        if not isinstance(data, list):
            raise TypeError("Bybit funding data is not a list.")
        if not data:
            break
        timestamps: list[int] = []
        for item in data:
            timestamp = int(item["fundingRateTimestamp"])
            timestamps.append(timestamp)
            if timestamp >= start_ms:
                rows.append(
                    {
                        "provider": "BYBIT",
                        "market_type": "LINEAR_PERPETUAL",
                        "symbol": "BTCUSDT",
                        "funding_time_ms": timestamp,
                        "funding_time_utc": iso_from_ms(timestamp),
                        "funding_rate": float(item["fundingRate"]),
                    }
                )
        oldest = min(timestamps)
        if previous_oldest is not None and oldest >= previous_oldest:
            raise RuntimeError("Bybit funding pagination did not move backward.")
        previous_oldest = oldest
        if oldest <= start_ms:
            break
        cursor_end = oldest - 1
        _pause(0.08)
    indexed = {int(row["funding_time_ms"]): row for row in rows}
    return [indexed[key] for key in sorted(indexed)], requests


def collect_bybit_open_interest(start_ms: int, end_ms: int) -> tuple[list[dict[str, Any]], int]:
    spec = OFFICIAL_ENDPOINT_REGISTRY["bybit_open_interest"]
    cursor_end = end_ms
    rows: list[dict[str, Any]] = []
    requests = 0
    previous_oldest: int | None = None
    while cursor_end >= start_ms:
        payload = http_get_json(
            spec["endpoint"],
            {
                "category": "linear",
                "symbol": "BTCUSDT",
                "intervalTime": "1h",
                "startTime": start_ms,
                "endTime": cursor_end,
                "limit": spec["max_limit"],
            },
        )
        requests += 1
        if not isinstance(payload, dict) or int(payload.get("retCode", -1)) != 0:
            raise RuntimeError(f"Bybit open-interest response rejected: {payload}")
        data = payload.get("result", {}).get("list")
        if not isinstance(data, list):
            raise TypeError("Bybit open-interest data is not a list.")
        if not data:
            break
        timestamps: list[int] = []
        for item in data:
            timestamp = int(item["timestamp"])
            timestamps.append(timestamp)
            if timestamp >= start_ms:
                rows.append(
                    {
                        "provider": "BYBIT",
                        "market_type": "LINEAR_PERPETUAL",
                        "symbol": "BTCUSDT",
                        "timestamp_ms": timestamp,
                        "timestamp_utc": iso_from_ms(timestamp),
                        "open_interest": float(item["openInterest"]),
                    }
                )
        oldest = min(timestamps)
        if previous_oldest is not None and oldest >= previous_oldest:
            raise RuntimeError("Bybit open-interest pagination did not move backward.")
        previous_oldest = oldest
        if oldest <= start_ms:
            break
        cursor_end = oldest - 1
        _pause(0.08)
    indexed = {int(row["timestamp_ms"]): row for row in rows}
    return [indexed[key] for key in sorted(indexed)], requests


def _write_dataset(
    output_dir: Path,
    name: str,
    rows: list[dict[str, Any]],
    fieldnames: tuple[str, ...],
    timestamp_key: str,
    interval_ms: int | None,
) -> dict[str, Any]:
    path = output_dir / f"{name}.csv.gz"
    write_csv_gz(path, rows, fieldnames)
    timestamps = [int(row[timestamp_key]) for row in rows]
    quality = gap_report(timestamps, interval_ms) if interval_ms else {
        "rows": len(rows),
        "duplicate_count": len(timestamps) - len(set(timestamps)),
    }
    return {
        "name": name,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(path),
        "rows": len(rows),
        "start_ms": min(timestamps) if timestamps else None,
        "end_ms": max(timestamps) if timestamps else None,
        "start_utc": iso_from_ms(min(timestamps)) if timestamps else None,
        "end_utc": iso_from_ms(max(timestamps)) if timestamps else None,
        "quality": quality,
    }


def build_fixture(output_dir: Path, hours: int = 1200) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    start_ms = 1_700_000_000_000 // HOUR_MS * HOUR_MS
    candles: list[dict[str, Any]] = []
    price = 35000.0
    for index in range(hours):
        drift = 0.00012 + 0.0015 * math.sin(index / 37.0)
        close = price * (1.0 + drift)
        high = max(price, close) * 1.002
        low = min(price, close) * 0.998
        candles.append(
            _normalize_candle(
                "BINANCE",
                "USDS_M_FUTURES",
                "BTCUSDT",
                start_ms + index * HOUR_MS,
                price,
                high,
                low,
                close,
                1000 + index % 50,
                (1000 + index % 50) * close,
                True,
            )
        )
        price = close
    funding = [
        {
            "provider": "BINANCE",
            "market_type": "USDS_M_FUTURES",
            "symbol": "BTCUSDT",
            "funding_time_ms": start_ms + index * 8 * HOUR_MS,
            "funding_time_utc": iso_from_ms(start_ms + index * 8 * HOUR_MS),
            "funding_rate": 0.0001 * math.sin(index / 5.0),
        }
        for index in range(max(1, hours // 8))
    ]
    oi = [
        {
            "provider": "BYBIT",
            "market_type": "LINEAR_PERPETUAL",
            "symbol": "BTCUSDT",
            "timestamp_ms": start_ms + index * HOUR_MS,
            "timestamp_utc": iso_from_ms(start_ms + index * HOUR_MS),
            "open_interest": 1_000_000 + index * 100,
        }
        for index in range(hours)
    ]
    datasets = {
        "binance_candles": _write_dataset(
            output_dir, "binance_candles", candles, CANDLE_FIELDS, "open_time_ms", HOUR_MS
        ),
        "binance_funding": _write_dataset(
            output_dir, "binance_funding", funding, FUNDING_FIELDS, "funding_time_ms", None
        ),
        "bybit_open_interest": _write_dataset(
            output_dir, "bybit_open_interest", oi, OI_FIELDS, "timestamp_ms", HOUR_MS
        ),
    }
    payload = base_payload(301, "FIXTURE_READY_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE301_OFFICIAL_PUBLIC_HISTORY_EXTENSION_READY_RESEARCH_ONLY",
            "collection_mode": "SYNTHETIC_TEST_FIXTURE",
            "network_calls_executed": False,
            "official_endpoint_registry": OFFICIAL_ENDPOINT_REGISTRY,
            "official_docs_verified_on": "2026-07-15",
            "official_docs_verification_method": "OFFICIAL_PRIMARY_DOCUMENTATION_REVIEW_PLUS_RUNTIME_PUBLIC_REQUEST",
            "requested": {
                "lookback_days": hours / 24,
                "derivatives_lookback_days": hours / 24,
            },
            "datasets": datasets,
            "successful_candle_providers": ["BINANCE"],
            "provider_errors": {},
            "max_candle_rows": hours,
            "minimum_two_candle_sources": False,
            "substantially_longer_than_phase300_720h": hours > 720,
            "forward_evidence_credit": 0,
            "historical_backfill_to_forward_clock": False,
            "complete": True,
        }
    )
    payload["artifact_fingerprint"] = ""
    payload["artifact_fingerprint"] = __import__(
        "crypto_decision_lab.scripts.phase301_305_evidence_v2_common",
        fromlist=["fingerprint"],
    ).fingerprint({key: value for key, value in payload.items() if key != "artifact_fingerprint"})
    return payload


def collect(
    output_dir: Path,
    *,
    lookback_days: int = 1095,
    derivatives_lookback_days: int = 365,
    now_ms: int | None = None,
) -> dict[str, Any]:
    if lookback_days < 90:
        raise ValueError("lookback_days must be at least 90.")
    if derivatives_lookback_days < 30:
        raise ValueError("derivatives_lookback_days must be at least 30.")
    output_dir.mkdir(parents=True, exist_ok=True)
    end_ms = floor_closed_hour_ms(now_ms)
    start_ms = end_ms - (lookback_days * 24 - 1) * HOUR_MS
    derivative_start_ms = end_ms - (derivatives_lookback_days * 24 - 1) * HOUR_MS

    candle_collectors: dict[str, Callable[[int, int], tuple[list[dict[str, Any]], int]]] = {
        "binance_candles": collect_binance_candles,
        "okx_candles": collect_okx_candles,
        "bybit_candles": collect_bybit_candles,
        "coinbase_candles": collect_coinbase_candles,
    }
    derivative_collectors: dict[
        str, tuple[Callable[[int, int], tuple[list[dict[str, Any]], int]], tuple[str, ...], str, int | None]
    ] = {
        "binance_funding": (collect_binance_funding, FUNDING_FIELDS, "funding_time_ms", None),
        "bybit_funding": (collect_bybit_funding, FUNDING_FIELDS, "funding_time_ms", None),
        "bybit_open_interest": (collect_bybit_open_interest, OI_FIELDS, "timestamp_ms", HOUR_MS),
    }

    datasets: dict[str, Any] = {}
    provider_errors: dict[str, str] = {}
    request_counts: dict[str, int] = {}
    successful_candle_providers: list[str] = []

    for name, collector in candle_collectors.items():
        try:
            rows, count = collector(start_ms, end_ms)
            request_counts[name] = count
            if len(rows) < 720:
                raise RuntimeError(f"Only {len(rows)} hourly rows were returned.")
            datasets[name] = _write_dataset(
                output_dir, name, rows, CANDLE_FIELDS, "open_time_ms", HOUR_MS
            )
            successful_candle_providers.append(str(rows[0]["provider"]))
        except Exception as exc:
            provider_errors[name] = f"{type(exc).__name__}: {exc}"

    for name, (collector, fields, timestamp_key, interval_ms) in derivative_collectors.items():
        try:
            rows, count = collector(derivative_start_ms, end_ms)
            request_counts[name] = count
            if not rows:
                raise RuntimeError("No rows returned.")
            datasets[name] = _write_dataset(
                output_dir, name, rows, fields, timestamp_key, interval_ms
            )
        except Exception as exc:
            provider_errors[name] = f"{type(exc).__name__}: {exc}"

    max_candle_rows = max(
        (item["rows"] for key, item in datasets.items() if key.endswith("_candles")),
        default=0,
    )
    enough_sources = len(set(successful_candle_providers)) >= 2
    complete = enough_sources and max_candle_rows > 720

    payload = base_payload(
        301,
        "PUBLIC_HISTORY_EXTENSION_COMPLETE_RESEARCH_ONLY"
        if complete
        else "PUBLIC_HISTORY_EXTENSION_INCOMPLETE_RESEARCH_ONLY",
    )
    payload.update(
        {
            "gate": "PHASE301_OFFICIAL_PUBLIC_HISTORY_EXTENSION_READY_RESEARCH_ONLY",
            "collection_mode": "PUBLIC_HTTP_NO_AUTH",
            "network_calls_executed": True,
            "collected_at_utc": utc_now_iso(),
            "official_endpoint_registry": OFFICIAL_ENDPOINT_REGISTRY,
            "official_docs_verified_on": "2026-07-15",
            "official_docs_verification_method": "OFFICIAL_PRIMARY_DOCUMENTATION_REVIEW_PLUS_RUNTIME_PUBLIC_REQUEST",
            "requested": {
                "lookback_days": lookback_days,
                "derivatives_lookback_days": derivatives_lookback_days,
                "start_ms": start_ms,
                "start_utc": iso_from_ms(start_ms),
                "end_ms": end_ms,
                "end_utc": iso_from_ms(end_ms),
            },
            "datasets": datasets,
            "request_counts": request_counts,
            "successful_candle_providers": sorted(set(successful_candle_providers)),
            "provider_errors": provider_errors,
            "max_candle_rows": max_candle_rows,
            "substantially_longer_than_phase300_720h": max_candle_rows > 720,
            "minimum_two_candle_sources": enough_sources,
            "forward_evidence_credit": 0,
            "historical_backfill_to_forward_clock": False,
            "strategy_approved": False,
            "complete": complete,
        }
    )
    common = __import__(
        "crypto_decision_lab.scripts.phase301_305_evidence_v2_common",
        fromlist=["fingerprint"],
    )
    payload["artifact_fingerprint"] = common.fingerprint(payload)
    write_json(output_dir / "phase301_official_public_history_extension.json", payload)
    write_text(
        ROOT / "docs/reports/evidence_v2/phase301_official_public_history_extension_summary.md",
        f"""# Phase 301 — Official Public History Extension

Gate: `{payload["gate"]}`

- Mode: `{payload["collection_mode"]}`
- Complete: `{payload["complete"]}`
- Successful candle providers: `{", ".join(payload["successful_candle_providers"]) or "NONE"}`
- Maximum hourly rows: `{payload["max_candle_rows"]}`
- Longer than the prior 720-hour sample: `{payload["substantially_longer_than_phase300_720h"]}`
- Provider errors: `{len(payload["provider_errors"])}`
- Forward evidence credit: `0`
- Historical backfill into forward clock: `False`
- Operational: `BLOCKED_RESEARCH_ONLY`
- Action: `NO_ACTION_RESEARCH_ONLY`

This phase verifies public, no-auth endpoint contracts at runtime and stores
research artifacts only. It does not approve a strategy and cannot count past
data as future evidence.
""",
    )
    if not complete:
        raise RuntimeError(
            "Phase 301 did not obtain at least two candle providers with a sample longer than 720 hours. "
            f"Provider errors: {provider_errors}"
        )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts/phase301_official_public_history_extension_research_only",
    )
    parser.add_argument("--lookback-days", type=int, default=1095)
    parser.add_argument("--derivatives-lookback-days", type=int, default=365)
    parser.add_argument("--fixture", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.fixture:
        payload = build_fixture(args.output_dir)
        write_json(args.output_dir / "phase301_official_public_history_extension.json", payload)
    else:
        payload = collect(
            args.output_dir,
            lookback_days=args.lookback_days,
            derivatives_lookback_days=args.derivatives_lookback_days,
        )
    print(payload["gate"])
    print("Status:", payload["status"])
    print("Complete:", payload["complete"])
    print("Historical backfill to forward clock:", payload["historical_backfill_to_forward_clock"])
    print("Forward evidence credit:", payload["forward_evidence_credit"])
    print("Operational:", payload["locks"]["operational_status"])
    print("Action:", payload["locks"]["action_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
