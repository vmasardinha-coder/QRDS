from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase127_data_timestamp_freshness_check_research_only import (
    build_timestamp_freshness_check,
)

READY_GATE = "PHASE128_DATA_GAP_SENTINEL_RESEARCH_ONLY_READY_RESEARCH_ONLY"

LOCKS = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
    "edge_operationally_validated": False,
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

REQUIRED_FIELDS = ["timestamp_utc", "symbol", "price", "volume", "source_id"]

def sample_market_rows(now: datetime | None = None) -> list[dict[str, Any]]:
    base = now or datetime.now(timezone.utc)
    return [
        {
            "timestamp_utc": (base - timedelta(minutes=3)).isoformat(),
            "symbol": "BTCUSDT",
            "price": 100000.0,
            "volume": 10.0,
            "source_id": "public_exchange_market_data",
        },
        {
            "timestamp_utc": (base - timedelta(minutes=2)).isoformat(),
            "symbol": "BTCUSDT",
            "price": 100100.0,
            "volume": 11.0,
            "source_id": "public_exchange_market_data",
        },
        {
            "timestamp_utc": (base - timedelta(minutes=1)).isoformat(),
            "symbol": "BTCUSDT",
            "price": 100200.0,
            "volume": 12.0,
            "source_id": "public_exchange_market_data",
        },
    ]

def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def evaluate_gaps(rows: list[dict[str, Any]], max_gap_seconds: int = 90) -> dict[str, Any]:
    missing_field_rows = []
    invalid_value_rows = []

    for idx, row in enumerate(rows):
        missing = [field for field in REQUIRED_FIELDS if field not in row or row[field] in (None, "")]
        if missing:
            missing_field_rows.append({"row_index": idx, "missing_fields": missing})

        if "price" in row and row.get("price") is not None and float(row["price"]) <= 0:
            invalid_value_rows.append({"row_index": idx, "field": "price", "reason": "non_positive"})
        if "volume" in row and row.get("volume") is not None and float(row["volume"]) < 0:
            invalid_value_rows.append({"row_index": idx, "field": "volume", "reason": "negative"})

    sorted_rows = sorted(
        [row for row in rows if row.get("timestamp_utc")],
        key=lambda item: _parse_timestamp(item["timestamp_utc"]),
    )

    time_gaps = []
    for previous, current in zip(sorted_rows, sorted_rows[1:]):
        previous_ts = _parse_timestamp(previous["timestamp_utc"])
        current_ts = _parse_timestamp(current["timestamp_utc"])
        gap_seconds = int((current_ts - previous_ts).total_seconds())
        if gap_seconds > max_gap_seconds:
            time_gaps.append(
                {
                    "previous_timestamp_utc": previous_ts.isoformat(),
                    "current_timestamp_utc": current_ts.isoformat(),
                    "gap_seconds": gap_seconds,
                    "max_gap_seconds": max_gap_seconds,
                }
            )

    return {
        "row_count": len(rows),
        "required_fields": REQUIRED_FIELDS,
        "missing_field_rows": missing_field_rows,
        "invalid_value_rows": invalid_value_rows,
        "time_gaps": time_gaps,
        "max_gap_seconds": max_gap_seconds,
        "gap_check_pass": (
            len(rows) > 0
            and len(missing_field_rows) == 0
            and len(invalid_value_rows) == 0
            and len(time_gaps) == 0
        ),
        "decision_gap_authority": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_data_gap_sentinel(project_root: str | Path | None = None) -> dict[str, Any]:
    freshness = build_timestamp_freshness_check(project_root)
    rows = sample_market_rows()
    gap_eval = evaluate_gaps(rows)

    sentinel_pass = (
        freshness["freshness_pass"] is True
        and gap_eval["gap_check_pass"] is True
        and gap_eval["decision_gap_authority"] is False
        and gap_eval["operational_effect"] == "NONE_RESEARCH_ONLY"
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sentinel_name": "data_gap_sentinel_research_only",
        "source_freshness_gate": freshness["gate"],
        "source_freshness_pass": freshness["freshness_pass"],
        "gap_evaluation": gap_eval,
        "sentinel_pass": sentinel_pass,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "data_trust_status": "GAP_SENTINEL_CANDIDATE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase128(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase128_data_gap_sentinel_research_only"
    out.mkdir(parents=True, exist_ok=True)

    sentinel = build_data_gap_sentinel()
    (out / "phase128_data_gap_sentinel.json").write_text(
        json.dumps(sentinel, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": sentinel["sentinel_pass"],
        "sentinel": sentinel,
        **LOCKS,
    }

def main() -> int:
    result = build_phase128()
    sentinel = result["sentinel"]
    gap_eval = sentinel["gap_evaluation"]

    print(result["gate"])
    print("Gap sentinel pass:", sentinel["sentinel_pass"])
    print("Row count:", gap_eval["row_count"])
    print("Missing field rows:", gap_eval["missing_field_rows"])
    print("Invalid value rows:", gap_eval["invalid_value_rows"])
    print("Time gaps:", gap_eval["time_gaps"])
    print("Data trust status:", sentinel["data_trust_status"])
    print("Approval effect:", sentinel["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if sentinel["sentinel_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
