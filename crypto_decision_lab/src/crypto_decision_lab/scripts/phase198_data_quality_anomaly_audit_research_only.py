from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "artifacts/phase196_data_source_registry_lineage_contract_research_only/phase196_data_source_registry_lineage_contract.json"
TEMPORAL = ROOT / "artifacts/phase197_timestamp_timezone_freshness_policy_research_only/phase197_timestamp_timezone_freshness_policy.json"

LOCKS = {
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "promotion_allowed": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "safe_apply_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "orders_generated": False,
    "real_orders_generated": False,
    "real_capital_used": False,
    "authenticated_connection_used": False,
    "canonical_data_writes": 0,
}

SUPPORTED = {".csv", ".tsv", ".json", ".jsonl", ".ndjson"}
OHLC = {
    "open": {"open", "o", "open_price"},
    "high": {"high", "h", "high_price"},
    "low": {"low", "l", "low_price"},
    "close": {"close", "c", "close_price"},
}
VOLUME = {"volume", "vol", "base_volume", "quote_volume", "turnover"}
SYMBOL = {"symbol", "ticker", "instrument", "market", "pair", "asset"}


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected object: {path}")
    return value


def source_path(raw: str) -> Path:
    path = Path(raw)
    return (path if path.is_absolute() else ROOT / path).resolve()


def norm(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"", "na", "n/a", "nan", "none", "null"}
    if isinstance(value, float):
        return math.isnan(value)
    return False


def number(value: Any) -> float | None:
    if missing(value) or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def field(names: list[str], aliases: set[str]) -> str | None:
    return next((name for name in names if norm(name) in aliases), None)


def read_text(path: Path) -> str:
    raw = path.read_bytes()[: 4 * 1024 * 1024]
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def records(path: Path) -> tuple[list[dict[str, Any]], list[str], str]:
    text = read_text(path)
    if not text.strip():
        return [], [], "EMPTY"

    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        try:
            delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
        except csv.Error:
            pass
        reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
        rows = [dict(row) for _, row in zip(range(10000), reader)]
        return rows, list(reader.fieldnames or []), "PARSED"

    if suffix in {".jsonl", ".ndjson"}:
        rows: list[dict[str, Any]] = []
        for line in text.splitlines():
            if len(rows) >= 10000:
                break
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    elif suffix == ".json":
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return [], [], "JSON_DECODE_ERROR"
        if isinstance(value, list):
            rows = [item for item in value[:10000] if isinstance(item, dict)]
        elif isinstance(value, dict):
            lists = [item for item in value.values() if isinstance(item, list)]
            rows = [item for item in (lists[0][:10000] if lists else [value]) if isinstance(item, dict)]
        else:
            rows = []
    else:
        return [], [], "UNSUPPORTED"

    names = sorted({str(key) for row in rows for key in row})
    return rows, names, "PARSED"


def timestamp(value: Any) -> datetime | None:
    if missing(value) or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = None
    if numeric is not None and math.isfinite(numeric):
        absolute = abs(numeric)
        divisor = 1 if absolute < 1e11 else 1e3 if absolute < 1e14 else 1e6 if absolute < 1e17 else 1e9
        if absolute < 1e8 or absolute >= 1e20:
            return None
        try:
            return datetime.fromtimestamp(numeric / divisor, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def gaps(rows: list[dict[str, Any]], timestamp_field: str | None) -> dict[str, Any]:
    if not timestamp_field:
        return {"evaluated": False, "median_interval_seconds": None, "large_gap_count": 0, "irregular_interval_count": 0}
    values = [timestamp(row.get(timestamp_field)) for row in rows]
    values = [item for item in values if item is not None]
    intervals = [(b - a).total_seconds() for a, b in zip(values, values[1:]) if b > a]
    if not intervals:
        return {"evaluated": True, "median_interval_seconds": None, "large_gap_count": 0, "irregular_interval_count": 0}
    ordered = sorted(intervals)
    lower_half_size = max(1, (len(ordered) + 1) // 2)
    baseline_interval = statistics.median(
        ordered[:lower_half_size]
    )
    tolerance = max(1.0, baseline_interval * 0.10)

    return {
        "evaluated": True,
        "median_interval_seconds": statistics.median(intervals),
        "baseline_interval_seconds": baseline_interval,
        "large_gap_count": sum(
            value > baseline_interval * 3
            for value in intervals
        ),
        "irregular_interval_count": sum(
            abs(value - baseline_interval) > tolerance
            for value in intervals
        ),
    }


def analyze(source: dict[str, Any], temporal: dict[str, Any] | None) -> dict[str, Any]:
    raw = str(source["relative_or_absolute_path"])
    path = source_path(raw)
    result = {
        "source_id": source["source_id"],
        "path": raw,
        "inspection_status": "NOT_INSPECTED",
        "row_count": 0,
        "duplicate_record_count": 0,
        "missing_value_count": 0,
        "rows_with_missing_values": 0,
        "ohlc_invariant_violation_count": 0,
        "negative_price_count": 0,
        "negative_volume_count": 0,
        "missing_symbol_count": 0,
        "gap_analysis": {"evaluated": False, "median_interval_seconds": None, "large_gap_count": 0, "irregular_interval_count": 0},
        "temporal_findings": {},
        "anomaly_flags": [],
    }

    if not path.is_file():
        result["inspection_status"] = "SOURCE_MISSING"
        result["anomaly_flags"] = ["SOURCE_MISSING"]
        return result
    if path.suffix.lower() not in SUPPORTED:
        result["inspection_status"] = "UNSUPPORTED_FORMAT"
        return result

    rows, names, status = records(path)
    result["inspection_status"] = status
    if status == "EMPTY":
        result["anomaly_flags"] = ["EMPTY_SOURCE"]
        return result
    if status != "PARSED":
        result["anomaly_flags"] = [status]
        return result

    result["row_count"] = len(rows)
    hashes = [
        hashlib.sha256(json.dumps(row, sort_keys=True, default=str, ensure_ascii=True).encode("utf-8")).hexdigest()
        for row in rows
    ]
    result["duplicate_record_count"] = len(hashes) - len(set(hashes))

    for row in rows:
        count = sum(missing(value) for value in row.values())
        result["missing_value_count"] += count
        result["rows_with_missing_values"] += int(count > 0)

    ohlc_fields = {role: field(names, aliases) for role, aliases in OHLC.items()}
    if all(ohlc_fields.values()):
        for row in rows:
            values = {role: number(row.get(name)) for role, name in ohlc_fields.items()}
            if any(item is None for item in values.values()):
                continue
            o, h, l, c = values["open"], values["high"], values["low"], values["close"]
            if min(o, h, l, c) < 0:
                result["negative_price_count"] += 1
            if h < max(o, l, c) or l > min(o, h, c):
                result["ohlc_invariant_violation_count"] += 1

    volume_field = field(names, VOLUME)
    if volume_field:
        result["negative_volume_count"] = sum(
            (value := number(row.get(volume_field))) is not None and value < 0
            for row in rows
        )

    symbol_field = field(names, SYMBOL)
    if symbol_field:
        result["missing_symbol_count"] = sum(missing(row.get(symbol_field)) for row in rows)

    timestamp_field = temporal.get("timestamp_field") if temporal else None
    result["gap_analysis"] = gaps(rows, timestamp_field)
    if temporal:
        result["temporal_findings"] = {
            "invalid_timestamp_count": temporal.get("invalid_timestamp_count", 0),
            "non_monotonic_timestamp_count": temporal.get("non_monotonic_timestamp_count", 0),
            "duplicate_adjacent_timestamp_count": temporal.get("duplicate_adjacent_timestamp_count", 0),
            "timezone_status": temporal.get("timezone_status", "NOT_EVALUATED"),
        }

    checks = {
        "DUPLICATE_RECORDS_PRESENT": result["duplicate_record_count"],
        "MISSING_VALUES_PRESENT": result["missing_value_count"],
        "OHLC_INVARIANT_VIOLATIONS_PRESENT": result["ohlc_invariant_violation_count"],
        "NEGATIVE_PRICES_PRESENT": result["negative_price_count"],
        "NEGATIVE_VOLUME_PRESENT": result["negative_volume_count"],
        "MISSING_SYMBOLS_PRESENT": result["missing_symbol_count"],
        "LARGE_TIME_GAPS_PRESENT": result["gap_analysis"]["large_gap_count"],
        "IRREGULAR_INTERVALS_PRESENT": result["gap_analysis"]["irregular_interval_count"],
        "INVALID_TIMESTAMPS_PRESENT": result["temporal_findings"].get("invalid_timestamp_count", 0),
        "NON_MONOTONIC_TIME_ORDER_PRESENT": result["temporal_findings"].get("non_monotonic_timestamp_count", 0),
        "DUPLICATE_TIMESTAMPS_PRESENT": result["temporal_findings"].get("duplicate_adjacent_timestamp_count", 0),
    }
    result["anomaly_flags"] = sorted(name for name, count in checks.items() if count > 0)
    return result


def render(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    rows = [
        "| `{}` | `{}` | {} | {} | {} | {} | {} | {} | `{}` |".format(
            item["source_id"],
            item["inspection_status"],
            item["row_count"],
            item["duplicate_record_count"],
            item["missing_value_count"],
            item["ohlc_invariant_violation_count"],
            item["gap_analysis"]["large_gap_count"],
            len(item["anomaly_flags"]),
            item["path"],
        )
        for item in payload["source_audits"][:100]
    ] or ["| _none_ | _none_ | 0 | 0 | 0 | 0 | 0 | 0 | _none_ |"]

    return "\n".join([
        "# Phase 198 - Data Quality Anomaly Audit",
        "",
        "**Status:** `PASS_RESEARCH_ONLY`",
        "",
        "## Summary",
        "",
        f"- Registered sources: `{summary['registered_source_count']}`",
        f"- Inspected sources: `{summary['inspected_source_count']}`",
        f"- Flagged sources: `{summary['flagged_source_count']}`",
        f"- Duplicate records: `{summary['duplicate_record_count']}`",
        f"- Missing values: `{summary['missing_value_count']}`",
        f"- OHLC invariant violations: `{summary['ohlc_invariant_violation_count']}`",
        f"- Negative volume rows: `{summary['negative_volume_count']}`",
        f"- Missing symbols: `{summary['missing_symbol_count']}`",
        f"- Large time gaps: `{summary['large_gap_count']}`",
        "",
        "## Source audit",
        "",
        "| Source | Inspection | Rows | Duplicates | Missing | OHLC | Gaps | Flags | Path |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
        *rows,
        "",
        "Findings are descriptive. Zero detected anomalies does not establish data trust.",
        "",
        "```text",
        "operational_status: BLOCKED_RESEARCH_ONLY",
        "anomaly_audit_ready: True",
        "anomaly_free_validated: False",
        "data_trust_validated: False",
        "decision_layer_allowed: False",
        "canonical_data_writes: 0",
        "```",
        "",
        "Next: `PHASE_199_SOURCE_RECONCILIATION_PROVENANCE_SCORE_RESEARCH_ONLY`",
        "",
    ])


def build_phase198(
    registry_path: Path,
    temporal_path: Path,
    output_dir: Path,
    documentation_path: Path | None = None,
) -> dict[str, Any]:
    registry = load_json(registry_path)
    temporal = load_json(temporal_path)
    if registry.get("phase") != 196 or registry.get("registry_ready") is not True:
        raise ValueError("Invalid Phase 196 registry.")
    if temporal.get("phase") != 197 or temporal.get("temporal_policy_ready") is not True:
        raise ValueError("Invalid Phase 197 temporal audit.")

    temporal_by_source = {item["source_id"]: item for item in temporal.get("source_audits", [])}
    audits = [analyze(source, temporal_by_source.get(source["source_id"])) for source in registry.get("sources", [])]

    summary = {
        "registered_source_count": len(audits),
        "inspected_source_count": sum(item["inspection_status"] == "PARSED" for item in audits),
        "flagged_source_count": sum(bool(item["anomaly_flags"]) for item in audits),
        "missing_source_count": sum(item["inspection_status"] == "SOURCE_MISSING" for item in audits),
        "empty_source_count": sum(item["inspection_status"] == "EMPTY" for item in audits),
        "duplicate_record_count": sum(item["duplicate_record_count"] for item in audits),
        "missing_value_count": sum(item["missing_value_count"] for item in audits),
        "ohlc_invariant_violation_count": sum(item["ohlc_invariant_violation_count"] for item in audits),
        "negative_price_count": sum(item["negative_price_count"] for item in audits),
        "negative_volume_count": sum(item["negative_volume_count"] for item in audits),
        "missing_symbol_count": sum(item["missing_symbol_count"] for item in audits),
        "large_gap_count": sum(item["gap_analysis"]["large_gap_count"] for item in audits),
        "irregular_interval_count": sum(item["gap_analysis"]["irregular_interval_count"] for item in audits),
    }

    payload = {
        "schema": "qrds.phase198.data_quality_anomaly_audit.v1",
        "phase": 198,
        "phase_status": "PASS_RESEARCH_ONLY",
        "audit_status": "DATA_ANOMALY_AUDIT_READY_RESEARCH_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registry_phase": 196,
        "temporal_policy_phase": 197,
        "source_audits": audits,
        "summary": summary,
        "audit_contract": {
            "mutate_sources_allowed": False,
            "repair_sources_allowed": False,
            "duplicate_detection_enabled": True,
            "missing_value_detection_enabled": True,
            "ohlc_invariant_detection_enabled": True,
            "negative_volume_detection_enabled": True,
            "missing_symbol_detection_enabled": True,
            "large_gap_detection_enabled": True,
            "findings_are_descriptive_only": True,
        },
        "anomaly_audit_ready": True,
        "anomaly_free_validated": False,
        "data_trust_validated": False,
        "sources_reconciled": False,
        "valid_for_decision": False,
        "operational_use_allowed": False,
        "production_trading_ready": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "next_stage": "PHASE_199_SOURCE_RECONCILIATION_PROVENANCE_SCORE_RESEARCH_ONLY",
        "locks": LOCKS,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "phase198_data_quality_anomaly_audit.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    if documentation_path:
        documentation_path.parent.mkdir(parents=True, exist_ok=True)
        documentation_path.write_text(render(payload), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-path", type=Path, default=REGISTRY)
    parser.add_argument("--temporal-audit-path", type=Path, default=TEMPORAL)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--documentation-path", type=Path, required=True)
    args = parser.parse_args()

    payload = build_phase198(
        args.registry_path,
        args.temporal_audit_path,
        args.output_dir,
        args.documentation_path,
    )
    summary = payload["summary"]
    print("PHASE198_DATA_QUALITY_ANOMALY_AUDIT: PASS")
    print("Registered sources:", summary["registered_source_count"])
    print("Inspected sources:", summary["inspected_source_count"])
    print("Flagged sources:", summary["flagged_source_count"])
    print("Duplicate records:", summary["duplicate_record_count"])
    print("Missing values:", summary["missing_value_count"])
    print("OHLC violations:", summary["ohlc_invariant_violation_count"])
    print("Large gaps:", summary["large_gap_count"])
    print("Operational:", payload["locks"]["operational_status"])
    print("Data trust validated:", payload["data_trust_validated"])
    print("Canonical data writes:", payload["locks"]["canonical_data_writes"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
