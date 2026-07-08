from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase126_data_source_trust_registry_research_only import (
    build_data_source_trust_registry,
)

READY_GATE = "PHASE127_DATA_TIMESTAMP_FRESHNESS_CHECK_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

FRESHNESS_POLICY = {
    "market_data_max_age_minutes_research_only": 60,
    "fixture_data_max_age_days_research_only": 3650,
    "derived_evidence_max_age_days_research_only": 3650,
    "manual_review_max_age_days_research_only": 3650,
    "decision_freshness_authority": False,
}

def sample_records(now: datetime | None = None) -> list[dict[str, Any]]:
    base = now or datetime.now(timezone.utc)
    return [
        {
            "record_id": "public_exchange_market_data_sample",
            "source_id": "public_exchange_market_data",
            "source_type": "market_data",
            "timestamp_utc": (base - timedelta(minutes=5)).isoformat(),
            "max_age_seconds": 60 * 60,
        },
        {
            "record_id": "offline_fixture_data_sample",
            "source_id": "offline_fixture_data",
            "source_type": "fixture",
            "timestamp_utc": (base - timedelta(days=30)).isoformat(),
            "max_age_seconds": 3650 * 24 * 60 * 60,
        },
        {
            "record_id": "derived_replay_evidence_sample",
            "source_id": "derived_replay_evidence",
            "source_type": "derived_evidence",
            "timestamp_utc": (base - timedelta(days=30)).isoformat(),
            "max_age_seconds": 3650 * 24 * 60 * 60,
        },
        {
            "record_id": "manual_review_notes_sample",
            "source_id": "manual_review_notes",
            "source_type": "human_review",
            "timestamp_utc": (base - timedelta(days=30)).isoformat(),
            "max_age_seconds": 3650 * 24 * 60 * 60,
        },
    ]

def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def evaluate_freshness(records: list[dict[str, Any]], now: datetime | None = None) -> list[dict[str, Any]]:
    base = now or datetime.now(timezone.utc)
    results = []

    for record in records:
        timestamp_present = bool(record.get("timestamp_utc"))
        age_seconds = None
        fresh_for_research = False

        if timestamp_present:
            timestamp = _parse_timestamp(record["timestamp_utc"])
            age_seconds = max(0, int((base - timestamp).total_seconds()))
            fresh_for_research = age_seconds <= int(record["max_age_seconds"])

        results.append(
            {
                "record_id": record["record_id"],
                "source_id": record["source_id"],
                "source_type": record["source_type"],
                "timestamp_present": timestamp_present,
                "age_seconds": age_seconds,
                "max_age_seconds": record["max_age_seconds"],
                "fresh_for_research": fresh_for_research,
                "fresh_for_decision": False,
                "operational_effect": "NONE_RESEARCH_ONLY",
            }
        )

    return results

def build_timestamp_freshness_check(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_data_source_trust_registry(project_root)
    now = datetime.now(timezone.utc)
    records = sample_records(now)
    freshness_results = evaluate_freshness(records, now)

    failed = [item for item in freshness_results if item["fresh_for_research"] is not True]
    decision_fresh = [item for item in freshness_results if item["fresh_for_decision"] is True]
    bad_effects = [item for item in freshness_results if item["operational_effect"] != "NONE_RESEARCH_ONLY"]

    freshness_pass = (
        registry["registry_pass"] is True
        and len(freshness_results) == 4
        and len(failed) == 0
        and len(decision_fresh) == 0
        and len(bad_effects) == 0
        and FRESHNESS_POLICY["decision_freshness_authority"] is False
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": now.isoformat(),
        "freshness_check_name": "data_timestamp_freshness_check_research_only",
        "source_registry_gate": registry["gate"],
        "source_registry_pass": registry["registry_pass"],
        "freshness_policy": FRESHNESS_POLICY,
        "freshness_results": freshness_results,
        "record_count": len(freshness_results),
        "failed_records": failed,
        "decision_fresh_record_count": len(decision_fresh),
        "freshness_pass": freshness_pass,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "data_trust_status": "TIMESTAMP_FRESHNESS_CANDIDATE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase127(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase127_data_timestamp_freshness_check_research_only"
    out.mkdir(parents=True, exist_ok=True)

    check = build_timestamp_freshness_check()
    (out / "phase127_data_timestamp_freshness_check.json").write_text(
        json.dumps(check, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": check["freshness_pass"],
        "freshness_check": check,
        **LOCKS,
    }

def main() -> int:
    result = build_phase127()
    check = result["freshness_check"]

    print(result["gate"])
    print("Freshness pass:", check["freshness_pass"])
    print("Record count:", check["record_count"])
    print("Failed records:", check["failed_records"])
    print("Decision fresh record count:", check["decision_fresh_record_count"])
    print("Data trust status:", check["data_trust_status"])
    print("Approval effect:", check["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if check["freshness_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
