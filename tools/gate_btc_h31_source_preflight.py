"""Read-only source dependency receipt for the frozen H31 collector."""
from pathlib import Path

def source_preflight(target_date, schedule, ledger_dir):
    required = sorted(d for d in schedule if "2026-08-10" <= d < target_date)[-20:]
    missing = [d for d in required if not (Path(ledger_dir) / "warmup" / (d + ".json")).is_file()]
    bound = target_date in schedule
    return {
        "schema": "qrds.h31.source_dependency_receipt.v1",
        "target_session": target_date,
        "target_session_bound": bound,
        "last_frozen_source_session": max(schedule) if schedule else None,
        "operational_status": "SOURCE_CALENDAR_BOUND_WARMUP_REQUIRES_VALIDATION" if bound else "BLOCKED_TARGET_OUTSIDE_FROZEN_SOURCE_CALENDAR",
        "required_official_warmup_dates": required,
        "warmup_cache_missing_dates": missing,
        "warmup_cache_presence_is_not_qualification": True,
        "required_next_action": "VALIDATE_BOUND_SESSION_AND_WARMUP" if bound else "REQUIRE_EXPLICIT_PROSPECTIVE_SOURCE_CALENDAR_BINDING_AND_WARMUP",
        "another_day_alone_resolves": False,
        "eligible_observation_increment": 0,
        "canonical_counter_mutated": False,
        "economics_read": False,
        "orders": 0,
        "real_capital": 0,
    }
