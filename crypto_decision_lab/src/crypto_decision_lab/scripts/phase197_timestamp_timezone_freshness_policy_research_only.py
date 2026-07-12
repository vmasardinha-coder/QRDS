from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = (
    ROOT / "artifacts"
    / "phase196_data_source_registry_lineage_contract_research_only"
    / "phase196_data_source_registry_lineage_contract.json"
)

LOCKS = {
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "promotion_allowed": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "operational_decision_allowed": False,
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

TIME_FIELDS = {
    "timestamp", "time", "datetime", "date", "event_time",
    "event_timestamp", "observation_time", "open_time",
    "close_time", "start_time", "end_time", "created_at",
    "updated_at", "ts",
}
TEMPORAL_HINTS = (
    "price", "ohlc", "candle", "kline", "trade", "tick",
    "history", "historical", "timeseries", "time_series",
    "market_data",
)
MAX_SAMPLE_ROWS = 5000
MAX_TEXT_BYTES = 2 * 1024 * 1024


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def normalize_field(value: str) -> str:
    return re.sub(r"[\s\-]+", "_", value.strip().lower())


def candidate_fields(fields: list[str]) -> list[str]:
    found = []
    for raw in fields:
        normalized = normalize_field(str(raw))
        if (
            normalized in TIME_FIELDS
            or normalized.endswith("_timestamp")
            or normalized.endswith("_datetime")
            or normalized.endswith("_time")
            or normalized.endswith("_date")
        ):
            found.append(str(raw))
    return found


def temporal_filename(path: Path) -> bool:
    stem = path.stem.lower()
    return any(hint in stem for hint in TEMPORAL_HINTS)


def resolve_source_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def infer_epoch_unit(value: float) -> str | None:
    absolute = abs(value)
    if absolute < 1e8:
        return None
    if absolute < 1e11:
        return "seconds"
    if absolute < 1e14:
        return "milliseconds"
    if absolute < 1e17:
        return "microseconds"
    if absolute < 1e20:
        return "nanoseconds"
    return None


def parse_timestamp(value: Any) -> tuple[datetime | None, str]:
    if value is None or isinstance(value, bool):
        return None, "INVALID"

    numeric: float | None = None
    if isinstance(value, (int, float)):
        numeric = float(value)
    else:
        text = str(value).strip()
        if not text:
            return None, "INVALID"
        try:
            numeric = float(text)
        except ValueError:
            numeric = None

    if numeric is not None and math.isfinite(numeric):
        unit = infer_epoch_unit(numeric)
        if unit is not None:
            divisor = {
                "seconds": 1.0,
                "milliseconds": 1_000.0,
                "microseconds": 1_000_000.0,
                "nanoseconds": 1_000_000_000.0,
            }[unit]
            try:
                parsed = datetime.fromtimestamp(
                    numeric / divisor,
                    tz=timezone.utc,
                )
            except (OverflowError, OSError, ValueError):
                return None, "INVALID"
            return parsed, f"EPOCH_{unit.upper()}_UTC"

    text = str(value).strip()
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    parsers = (
        lambda: datetime.fromisoformat(normalized),
        lambda: datetime.strptime(text, "%Y-%m-%d"),
        lambda: datetime.strptime(text, "%Y/%m/%d"),
        lambda: datetime.strptime(text, "%Y-%m-%d %H:%M:%S"),
        lambda: datetime.strptime(text, "%Y/%m/%d %H:%M:%S"),
    )

    parsed = None
    for parser in parsers:
        try:
            parsed = parser()
            break
        except ValueError:
            continue

    if parsed is None:
        return None, "INVALID"

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=timezone.utc), "NAIVE_ASSUMED_UTC"

    offset = parsed.utcoffset()
    parsed = parsed.astimezone(timezone.utc)
    if offset is not None and offset.total_seconds() == 0:
        return parsed, "EXPLICIT_UTC"
    return parsed, "EXPLICIT_OFFSET"


def read_text(path: Path) -> str:
    raw = path.read_bytes()[:MAX_TEXT_BYTES]
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def sample_records(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    suffix = path.suffix.lower()
    text = read_text(path)
    if not text.strip():
        return [], []

    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        try:
            delimiter = csv.Sniffer().sniff(
                text[:4096], delimiters=",;\t|"
            ).delimiter
        except csv.Error:
            pass
        reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
        rows = []
        for index, row in enumerate(reader):
            if index >= MAX_SAMPLE_ROWS:
                break
            rows.append(dict(row))
        return rows, list(reader.fieldnames or [])

    if suffix in {".jsonl", ".ndjson"}:
        rows = []
        for line in text.splitlines():
            if len(rows) >= MAX_SAMPLE_ROWS:
                break
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
        fields = sorted({str(k) for row in rows for k in row})
        return rows, fields

    if suffix == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return [], []
        rows: list[dict[str, Any]] = []
        if isinstance(payload, list):
            rows = [x for x in payload[:MAX_SAMPLE_ROWS] if isinstance(x, dict)]
        elif isinstance(payload, dict):
            lists = [v for v in payload.values() if isinstance(v, list)]
            if lists:
                rows = [x for x in lists[0][:MAX_SAMPLE_ROWS] if isinstance(x, dict)]
            else:
                rows = [payload]
        fields = sorted({str(k) for row in rows for k in row})
        return rows, fields

    return [], []


def analyze_values(
    values: list[Any],
    *,
    audit_time: datetime,
    source_role: str,
) -> dict[str, Any]:
    parsed: list[datetime] = []
    modes: dict[str, int] = {}
    invalid = 0

    for value in values:
        stamp, mode = parse_timestamp(value)
        modes[mode] = modes.get(mode, 0) + 1
        if stamp is None:
            invalid += 1
        else:
            parsed.append(stamp)

    non_monotonic = 0
    duplicate_adjacent = 0
    positive_intervals: list[float] = []
    for previous, current in zip(parsed, parsed[1:]):
        if current < previous:
            non_monotonic += 1
        if current == previous:
            duplicate_adjacent += 1
        delta = (current - previous).total_seconds()
        if delta > 0:
            positive_intervals.append(delta)

    earliest = min(parsed) if parsed else None
    latest = max(parsed) if parsed else None
    age_seconds = (
        max(0.0, (audit_time - latest).total_seconds())
        if latest is not None else None
    )

    if not parsed:
        timezone_status = "NOT_EVALUATED"
    elif modes.get("NAIVE_ASSUMED_UTC", 0) > 0:
        timezone_status = "NEEDS_EXPLICIT_TIMEZONE"
    else:
        timezone_status = "UTC_OR_OFFSET_EXPLICIT"

    if source_role == "TEST_FIXTURE":
        freshness = "FIXTURE_NOT_OPERATIONALLY_ENFORCED"
    elif latest is None:
        freshness = "NOT_EVALUATED"
    elif age_seconds is not None and age_seconds <= 86400:
        freshness = "FRESH_WITHIN_24H"
    elif age_seconds is not None and age_seconds <= 604800:
        freshness = "STALE_OVER_24H"
    else:
        freshness = "STALE_OVER_7D"

    return {
        "sample_value_count": len(values),
        "parsed_timestamp_count": len(parsed),
        "invalid_timestamp_count": invalid,
        "parse_modes": dict(sorted(modes.items())),
        "timezone_status": timezone_status,
        "earliest_timestamp_utc": earliest.isoformat() if earliest else None,
        "latest_timestamp_utc": latest.isoformat() if latest else None,
        "age_seconds_at_audit": age_seconds,
        "median_interval_seconds": (
            statistics.median(positive_intervals)
            if positive_intervals else None
        ),
        "duplicate_adjacent_timestamp_count": duplicate_adjacent,
        "non_monotonic_timestamp_count": non_monotonic,
        "monotonic_non_decreasing": non_monotonic == 0,
        "freshness_status": freshness,
    }


def analyze_source(
    source: dict[str, Any],
    *,
    audit_time: datetime,
) -> dict[str, Any]:
    raw_path = str(source["relative_or_absolute_path"])
    path = resolve_source_path(raw_path)
    role = str(source.get("source_role", "DISCOVERED_FILE"))
    format_class = str(source.get("format_class", "UNKNOWN"))

    result: dict[str, Any] = {
        "source_id": source["source_id"],
        "path": raw_path,
        "source_role": role,
        "format_class": format_class,
        "content_sha256": source["content_sha256"],
        "temporal_candidate": False,
        "inspection_status": "NOT_INSPECTED",
        "timestamp_field": None,
        "candidate_fields": [],
        "sample_record_count": 0,
        "policy_findings": [],
    }

    if not path.is_file():
        result["inspection_status"] = "SOURCE_MISSING"
        result["policy_findings"].append("SOURCE_MISSING_AT_PHASE197")
        return result

    if path.suffix.lower() not in {
        ".csv", ".tsv", ".json", ".jsonl", ".ndjson"
    }:
        result["inspection_status"] = "UNSUPPORTED_FORMAT"
        result["temporal_candidate"] = temporal_filename(path)
        if result["temporal_candidate"]:
            result["policy_findings"].append(
                "TEMPORAL_SOURCE_REQUIRES_READER"
            )
        return result

    rows, fields = sample_records(path)
    candidates = candidate_fields(fields)
    result["candidate_fields"] = candidates
    result["sample_record_count"] = len(rows)
    result["temporal_candidate"] = bool(
        candidates or temporal_filename(path)
    )

    if not result["temporal_candidate"]:
        result["inspection_status"] = "NON_TEMPORAL_NO_HINT"
        return result

    if not candidates:
        result["inspection_status"] = "TEMPORAL_HINT_NO_TIMESTAMP_FIELD"
        result["policy_findings"].append(
            "EXPLICIT_TIMESTAMP_FIELD_REQUIRED"
        )
        return result

    field = candidates[0]
    values = [row.get(field) for row in rows if field in row]
    result.update(
        analyze_values(
            values,
            audit_time=audit_time,
            source_role=role,
        )
    )
    result["timestamp_field"] = field
    result["inspection_status"] = "INSPECTED"

    if result["invalid_timestamp_count"] > 0:
        result["policy_findings"].append(
            "INVALID_TIMESTAMP_VALUES_PRESENT"
        )
    if result["timezone_status"] == "NEEDS_EXPLICIT_TIMEZONE":
        result["policy_findings"].append(
            "NAIVE_TIMESTAMPS_REQUIRE_EXPLICIT_TIMEZONE"
        )
    if result["non_monotonic_timestamp_count"] > 0:
        result["policy_findings"].append(
            "NON_MONOTONIC_TIME_ORDER_PRESENT"
        )
    if result["duplicate_adjacent_timestamp_count"] > 0:
        result["policy_findings"].append(
            "DUPLICATE_ADJACENT_TIMESTAMPS_PRESENT"
        )

    return result


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    rows = []
    for item in payload["source_audits"][:100]:
        rows.append(
            "| `{}` | `{}` | `{}` | `{}` | {} | {} | `{}` |".format(
                item["source_id"],
                item["inspection_status"],
                item.get("timezone_status", "NOT_EVALUATED"),
                item.get("freshness_status", "NOT_EVALUATED"),
                item.get("invalid_timestamp_count", 0),
                item.get("non_monotonic_timestamp_count", 0),
                item["path"],
            )
        )
    if not rows:
        rows.append("| _none_ | _none_ | _none_ | _none_ | 0 | 0 | _none_ |")

    return "\n".join([
        "# Phase 197 - Timestamp, Timezone and Freshness Policy",
        "",
        "**Status:** `PASS_RESEARCH_ONLY`",
        "",
        "## Purpose",
        "",
        "Apply a deterministic temporal policy to the Phase 196 source "
        "registry. The audit records timestamp fields, parsing modes, "
        "timezone evidence, ordering and descriptive freshness.",
        "",
        "This phase does not certify data trust.",
        "",
        "## Summary",
        "",
        f"- Registered sources: `{summary['registered_source_count']}`",
        f"- Temporal candidates: `{summary['temporal_candidate_count']}`",
        f"- Inspected temporal sources: `{summary['inspected_temporal_count']}`",
        f"- Sources requiring timezone review: `{summary['timezone_review_count']}`",
        f"- Sources with invalid timestamps: `{summary['invalid_timestamp_source_count']}`",
        f"- Sources with non-monotonic ordering: `{summary['non_monotonic_source_count']}`",
        f"- Missing sources: `{summary['missing_source_count']}`",
        "",
        "## Policy",
        "",
        "- Temporal data requires an explicit timestamp field.",
        "- UTC or explicit offset is preferred.",
        "- Naive timestamps are not accepted as final trust evidence.",
        "- Epoch timestamps are interpreted as UTC with unit recorded.",
        "- Monotonic ordering and duplicate timestamps must be audited.",
        "- Fixture freshness is not operationally enforced.",
        "- Research-input freshness is descriptive at this stage.",
        "",
        "## Source audit",
        "",
        "| Source | Inspection | Timezone | Freshness | Invalid | Non-monotonic | Path |",
        "|---|---|---|---|---:|---:|---|",
        *rows,
        "",
        "## Safety",
        "",
        "```text",
        "operational_status: BLOCKED_RESEARCH_ONLY",
        "temporal_policy_ready: True",
        "data_trust_validated: False",
        "freshness_validated: False",
        "decision_layer_allowed: False",
        "canonical_data_writes: 0",
        "```",
        "",
        "## Next",
        "",
        "`PHASE_198_DATA_QUALITY_ANOMALY_AUDIT_RESEARCH_ONLY`",
        "",
    ])


def build_phase197(
    *,
    registry_path: Path,
    output_dir: Path,
    documentation_path: Path | None = None,
    audit_time: datetime | None = None,
) -> dict[str, Any]:
    registry = load_json(registry_path)
    if registry.get("phase") != 196:
        raise ValueError("Phase 197 requires Phase 196 registry.")
    if registry.get("registry_ready") is not True:
        raise ValueError("Phase 196 registry is not ready.")
    if registry.get("data_trust_validated") is not False:
        raise ValueError("Phase 196 unexpectedly validates data trust.")

    now = audit_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)

    audits = [
        analyze_source(source, audit_time=now)
        for source in registry.get("sources", [])
    ]
    temporal = [item for item in audits if item["temporal_candidate"]]
    inspected = [
        item for item in temporal
        if item["inspection_status"] == "INSPECTED"
    ]

    summary = {
        "registered_source_count": len(audits),
        "temporal_candidate_count": len(temporal),
        "inspected_temporal_count": len(inspected),
        "timezone_review_count": sum(
            item.get("timezone_status") == "NEEDS_EXPLICIT_TIMEZONE"
            for item in inspected
        ),
        "invalid_timestamp_source_count": sum(
            item.get("invalid_timestamp_count", 0) > 0
            for item in inspected
        ),
        "non_monotonic_source_count": sum(
            item.get("non_monotonic_timestamp_count", 0) > 0
            for item in inspected
        ),
        "duplicate_timestamp_source_count": sum(
            item.get("duplicate_adjacent_timestamp_count", 0) > 0
            for item in inspected
        ),
        "missing_source_count": sum(
            item["inspection_status"] == "SOURCE_MISSING"
            for item in audits
        ),
        "unsupported_temporal_source_count": sum(
            item["temporal_candidate"]
            and item["inspection_status"] in {
                "UNSUPPORTED_FORMAT",
                "TEMPORAL_HINT_NO_TIMESTAMP_FIELD",
            }
            for item in audits
        ),
    }

    payload = {
        "schema": "qrds.phase197.temporal_policy_audit.v1",
        "phase": 197,
        "phase_status": "PASS_RESEARCH_ONLY",
        "policy_status": "TEMPORAL_DATA_POLICY_READY_RESEARCH_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audit_time_utc": now.isoformat(),
        "registry_path": str(registry_path),
        "registry_phase": 196,
        "registry_source_count": registry["summary"]["source_count"],
        "source_audits": audits,
        "summary": summary,
        "temporal_policy": {
            "required_timestamp_field": True,
            "preferred_timezone": "UTC",
            "explicit_offset_accepted": True,
            "naive_timestamp_final_trust_allowed": False,
            "epoch_interpretation": "UTC_WITH_UNIT_RECORDED",
            "monotonic_order_required": True,
            "duplicate_timestamp_audit_required": True,
            "fixture_freshness_operationally_enforced": False,
            "freshness_is_descriptive_only": True,
            "fresh_within_seconds": 86400,
            "severely_stale_over_seconds": 604800,
        },
        "temporal_policy_ready": True,
        "data_trust_validated": False,
        "freshness_validated": False,
        "anomaly_free_validated": False,
        "sources_reconciled": False,
        "valid_for_decision": False,
        "operational_use_allowed": False,
        "production_trading_ready": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "next_stage": "PHASE_198_DATA_QUALITY_ANOMALY_AUDIT_RESEARCH_ONLY",
        "locks": LOCKS,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "phase197_timestamp_timezone_freshness_policy.json"
    artifact.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    if documentation_path is not None:
        documentation_path.parent.mkdir(parents=True, exist_ok=True)
        documentation_path.write_text(
            render_markdown(payload),
            encoding="utf-8",
        )

    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-path", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--documentation-path", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_phase197(
        registry_path=args.registry_path,
        output_dir=args.output_dir,
        documentation_path=args.documentation_path,
    )
    summary = payload["summary"]
    print("PHASE197_TEMPORAL_POLICY: PASS")
    print("Registered sources:", summary["registered_source_count"])
    print("Temporal candidates:", summary["temporal_candidate_count"])
    print("Inspected temporal sources:", summary["inspected_temporal_count"])
    print("Timezone review:", summary["timezone_review_count"])
    print("Invalid timestamp sources:", summary["invalid_timestamp_source_count"])
    print("Non-monotonic sources:", summary["non_monotonic_source_count"])
    print("Operational:", payload["locks"]["operational_status"])
    print("Data trust validated:", payload["data_trust_validated"])
    print("Canonical data writes:", payload["locks"]["canonical_data_writes"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
