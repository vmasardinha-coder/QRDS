from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[3]

LOCKS: dict[str, Any] = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}

TIMESTAMP_ALIASES = (
    "timestamp",
    "time",
    "datetime",
    "date",
    "open_time",
    "open_timestamp",
)
SYMBOL_ALIASES = (
    "symbol",
    "ticker",
    "instrument",
    "market",
    "pair",
)
OPEN_ALIASES = ("open", "o")
HIGH_ALIASES = ("high", "h")
LOW_ALIASES = ("low", "l")
CLOSE_ALIASES = ("close", "c", "price")
VOLUME_ALIASES = ("volume", "v", "base_volume")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_json_dumps(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def stable_digest(payload: Any) -> str:
    return sha256_bytes(stable_json_dumps(payload).encode("utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        numeric = float(value)
        if numeric > 10_000_000_000:
            numeric /= 1000.0
        try:
            dt = datetime.fromtimestamp(numeric, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.isdigit():
            return parse_timestamp(int(text))
        normalized = text.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y",
            ):
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            else:
                return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def find_key(record: dict[str, Any], aliases: Iterable[str]) -> str | None:
    lower_map = {str(key).strip().lower(): str(key) for key in record}
    for alias in aliases:
        if alias in lower_map:
            return lower_map[alias]
    return None


def normalize_record(
    record: dict[str, Any],
    default_symbol: str,
) -> dict[str, Any] | None:
    timestamp_key = find_key(record, TIMESTAMP_ALIASES)
    close_key = find_key(record, CLOSE_ALIASES)

    if timestamp_key is None or close_key is None:
        return None

    timestamp = parse_timestamp(record.get(timestamp_key))
    close = finite_float(record.get(close_key))
    if timestamp is None or close is None or close <= 0:
        return None

    open_key = find_key(record, OPEN_ALIASES)
    high_key = find_key(record, HIGH_ALIASES)
    low_key = find_key(record, LOW_ALIASES)
    volume_key = find_key(record, VOLUME_ALIASES)
    symbol_key = find_key(record, SYMBOL_ALIASES)

    open_value = finite_float(record.get(open_key)) if open_key else close
    high_value = finite_float(record.get(high_key)) if high_key else close
    low_value = finite_float(record.get(low_key)) if low_key else close
    volume_value = finite_float(record.get(volume_key)) if volume_key else 0.0

    if open_value is None or high_value is None or low_value is None:
        return None
    if min(open_value, high_value, low_value) <= 0:
        return None
    if high_value < max(open_value, close):
        return None
    if low_value > min(open_value, close):
        return None
    if high_value < low_value:
        return None

    symbol = (
        str(record.get(symbol_key)).strip().upper()
        if symbol_key and record.get(symbol_key) is not None
        else default_symbol
    )
    if not symbol:
        symbol = default_symbol

    return {
        "symbol": symbol,
        "timestamp": iso_utc(timestamp),
        "open": round(open_value, 12),
        "high": round(high_value, 12),
        "low": round(low_value, 12),
        "close": round(close, 12),
        "volume": round(max(volume_value or 0.0, 0.0), 12),
    }


def _read_csv_candidate(path: Path, max_rows: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    default_symbol = path.stem.upper()

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                return []
            for record in reader:
                normalized = normalize_record(record, default_symbol)
                if normalized is not None:
                    rows.append(normalized)
                if len(rows) >= max_rows:
                    break
    except (OSError, UnicodeError, csv.Error):
        return []

    return rows


def _iter_json_records(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return

    if isinstance(payload, dict):
        for key in ("rows", "records", "data", "candles", "klines"):
            value = payload.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        yield item
                return


def _read_json_candidate(path: Path, max_rows: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    default_symbol = path.stem.upper()

    try:
        if path.suffix.lower() == ".jsonl":
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    if not isinstance(item, dict):
                        continue
                    normalized = normalize_record(item, default_symbol)
                    if normalized is not None:
                        rows.append(normalized)
                    if len(rows) >= max_rows:
                        break
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
            for item in _iter_json_records(payload):
                normalized = normalize_record(item, default_symbol)
                if normalized is not None:
                    rows.append(normalized)
                if len(rows) >= max_rows:
                    break
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []

    return rows


def discover_research_rows(
    root: Path,
    max_rows: int = 3000,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    excluded_parts = {
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        "docs",
        "tests",
    }
    suffixes = {".csv", ".json", ".jsonl"}
    candidates: list[Path] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in suffixes:
            continue
        relative = path.relative_to(root)
        lowered_parts = {part.lower() for part in relative.parts}
        if lowered_parts & excluded_parts:
            continue
        if "phase206_215" in path.as_posix().lower():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size <= 0 or size > 100 * 1024 * 1024:
            continue
        candidates.append(path)

    candidates.sort(key=lambda item: item.relative_to(root).as_posix())

    best_rows: list[dict[str, Any]] = []
    best_path: Path | None = None

    for path in candidates[:250]:
        if path.suffix.lower() == ".csv":
            rows = _read_csv_candidate(path, max_rows)
        else:
            rows = _read_json_candidate(path, max_rows)

        if len(rows) > len(best_rows):
            best_rows = rows
            best_path = path

        if len(best_rows) >= max_rows:
            break

    if best_path is None or len(best_rows) < 240:
        return [], {
            "candidate_count": len(candidates),
            "selected_path": None,
            "selected_rows": 0,
        }

    return best_rows, {
        "candidate_count": len(candidates),
        "selected_path": best_path.relative_to(root).as_posix(),
        "selected_rows": len(best_rows),
        "selected_sha256": sha256_file(best_path),
    }


def synthetic_rows(
    symbols: tuple[str, ...] = ("BTC-USDT", "ETH-USDT", "SOL-USDT"),
    rows_per_symbol: int = 480,
) -> list[dict[str, Any]]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    base_prices = {
        "BTC-USDT": 42_000.0,
        "ETH-USDT": 2_300.0,
        "SOL-USDT": 105.0,
    }
    rows: list[dict[str, Any]] = []

    for symbol_index, symbol in enumerate(symbols):
        price = base_prices.get(symbol, 100.0)
        for index in range(rows_per_symbol):
            drift = 0.00018 * math.sin((index + 1) / 17.0 + symbol_index)
            cycle = 0.0018 * math.sin((index + 3) / 11.0)
            shock = 0.0007 * math.cos((index + 5) / 7.0 + symbol_index)
            change = drift + cycle + shock
            open_value = price
            close = max(0.01, open_value * (1.0 + change))
            spread = abs(change) + 0.0015
            high = max(open_value, close) * (1.0 + spread)
            low = min(open_value, close) * (1.0 - spread)
            volume = 1000.0 + 150.0 * math.sin(index / 13.0) + 10.0 * symbol_index

            rows.append(
                {
                    "symbol": symbol,
                    "timestamp": iso_utc(start + timedelta(hours=index)),
                    "open": round(open_value, 12),
                    "high": round(high, 12),
                    "low": round(low, 12),
                    "close": round(close, 12),
                    "volume": round(max(volume, 1.0), 12),
                }
            )
            price = close

    return rows


def canonicalize_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        symbol = str(row["symbol"]).strip().upper()
        timestamp = str(row["timestamp"])
        key = (symbol, timestamp)
        deduplicated[key] = {
            "symbol": symbol,
            "timestamp": timestamp,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row.get("volume", 0.0)),
        }

    return [
        deduplicated[key]
        for key in sorted(deduplicated, key=lambda item: (item[0], item[1]))
    ]


def load_or_create_dataset(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    discovered, discovery = discover_research_rows(root)
    discovered_rows = canonicalize_rows(discovered) if discovered else []
    discovered_groups = group_by_symbol(discovered_rows) if discovered_rows else {}
    has_replayable_symbol = any(
        len(symbol_rows) >= 120
        for symbol_rows in discovered_groups.values()
    )

    if discovered_rows and has_replayable_symbol:
        rows = discovered_rows
        source_mode = "DISCOVERED_RESEARCH_DATA"
    else:
        rows = canonicalize_rows(synthetic_rows())
        source_mode = "DETERMINISTIC_FIXTURE_FALLBACK"

    metadata = {
        "source_mode": source_mode,
        "discovery": discovery,
        "row_count": len(rows),
        "symbols": sorted({row["symbol"] for row in rows}),
        "dataset_digest": stable_digest(rows),
    }
    return rows, metadata


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(stable_json_dumps(row) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def group_by_symbol(
    rows: Iterable[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["symbol"]), []).append(row)
    for symbol in grouped:
        grouped[symbol].sort(key=lambda item: str(item["timestamp"]))
    return grouped


def median_interval_seconds(rows: list[dict[str, Any]]) -> float | None:
    if len(rows) < 2:
        return None
    timestamps = [parse_timestamp(row["timestamp"]) for row in rows]
    valid = [value for value in timestamps if value is not None]
    intervals = [
        (current - previous).total_seconds()
        for previous, current in zip(valid, valid[1:])
        if current > previous
    ]
    if not intervals:
        return None
    return float(statistics.median(intervals))


def relative_change(previous: float, current: float) -> float:
    if previous == 0:
        return 0.0
    return (current - previous) / previous


def mean(values: Iterable[float]) -> float:
    items = list(values)
    return statistics.fmean(items) if items else 0.0


def population_std(values: Iterable[float]) -> float:
    items = list(values)
    return statistics.pstdev(items) if len(items) > 1 else 0.0


def percentile(values: Iterable[float], quantile: float) -> float:
    items = sorted(values)
    if not items:
        return 0.0
    if len(items) == 1:
        return items[0]
    position = (len(items) - 1) * min(max(quantile, 0.0), 1.0)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return items[lower]
    weight = position - lower
    return items[lower] * (1.0 - weight) + items[upper] * weight


def locks_copy() -> dict[str, Any]:
    return dict(LOCKS)
