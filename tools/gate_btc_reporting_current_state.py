#!/usr/bin/env python3
"""Build a reporting-only current-state snapshot from immutable GATE BTC runtime evidence.

This module never changes strategy methodology, orders, positions or economic ledgers.
It exists to prevent stale runtime counters from being silently presented as current.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA = "gate_btc.reporting_current_state.v1"


class ReportingStateError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def iso_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    text = str(value)
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_record(path: Path, data: dict[str, Any] | None) -> dict[str, Any]:
    if data is None:
        return {"exists": False, "path": str(path)}
    return {
        "exists": True,
        "path": str(path),
        "sha256": sha256_bytes(path.read_bytes()),
        "schema": data.get("schema"),
    }


def assert_safe(name: str, data: dict[str, Any] | None) -> None:
    if data is None:
        return
    checks = {
        "research_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    # Older aggregate files may omit not_approved but must still forbid promotion.
    for key, expected in checks.items():
        if key not in data:
            continue
        if data.get(key) != expected:
            raise ReportingStateError(f"unsafe {name}: {key}={data.get(key)!r}")
    if data.get("promotion_allowed") is True:
        raise ReportingStateError(f"unsafe {name}: promotion_allowed=true")
    if data.get("engine_feed") is True:
        raise ReportingStateError(f"unsafe {name}: engine_feed=true")


def fresh_label(component_date: date | None, reference_date: date | None) -> str:
    if component_date is None:
        return "UNKNOWN_DATE"
    if reference_date is None:
        return "DATE_PRESENT_NO_REFERENCE"
    if component_date >= reference_date:
        return "FRESH"
    return "STALE"


def _as_int(value: Any, default: int = -1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def d50_runtime_is_newer(
    remote_ledger: dict[str, Any],
    remote_qualification: dict[str, Any],
    reconciled_ledger: dict[str, Any],
    reconciled_qualification: dict[str, Any],
) -> bool:
    """Use monotonic tips; a qualification pass counter may legitimately reset."""
    if _as_int(remote_ledger.get("current")) > _as_int(reconciled_ledger.get("current")):
        return True
    if str(remote_ledger.get("latest_prospective_date") or "") > str(reconciled_ledger.get("latest_prospective_date") or ""):
        return True
    return _as_int(remote_qualification.get("snapshot_count_total")) > _as_int(
        reconciled_qualification.get("snapshot_count_total")
    )


def calendar_waiting(data: dict[str, Any] | None) -> bool:
    if not data:
        return False
    return str(data.get("status", "")).startswith("WAITING_FIRST_UNTOUCHED_SIGNAL")


def reconcile(runtime_root: Path, now: date | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc).date()
    paths = {
        "pointer": runtime_root / "GATE_BTC_LATEST_ELIGIBLE_RUN.json",
        "measurement": runtime_root / "GATE_BTC_MEASUREMENT_STATUS.json",
        "d50": runtime_root / "ledgers" / "d50" / "STATUS.json",
        "gateway": runtime_root / "ledgers" / "gateway_dynamics" / "STATUS.json",
        "lock25_50": runtime_root / "ledgers" / "lock25_50" / "STATUS.json",
        "prl50": runtime_root / "ledgers" / "prl50_position" / "STATUS.json",
        "alt_trail": runtime_root / "ledgers" / "alt_trail40_10" / "STATUS.json",
        "bull_replay": runtime_root / "ledgers" / "bull_replay_live_shadow" / "STATUS.json",
        "delta_paper_monitor": runtime_root / "ledgers" / "delta_paper_monitor" / "STATUS.json",
    }
    data = {name: load_json(path) for name, path in paths.items()}
    for name, obj in data.items():
        assert_safe(name, obj)

    pointer = data["pointer"] or {}
    measurement = data["measurement"] or {}
    pointer_date = iso_date(pointer.get("data_cutoff"))
    reference_date = pointer_date or iso_date(measurement.get("data_as_of"))
    expected_data_cutoff = now - timedelta(days=1)

    components: dict[str, Any] = {}

    pointer_lag_days = (
        (expected_data_cutoff - pointer_date).days
        if pointer_date is not None and pointer_date < expected_data_cutoff
        else 0
    )
    if pointer_date is None:
        pointer_freshness = "MISSING"
    elif pointer_date < expected_data_cutoff:
        pointer_freshness = "STALE"
    elif pointer_date > expected_data_cutoff:
        pointer_freshness = "INVALID_FUTURE_DATE"
    else:
        pointer_freshness = "FRESH"
    components["daily_delivery_pointer"] = {
        "status": "CURRENT" if pointer_freshness == "FRESH" else "LATE_MISSING_OR_INVALID",
        "freshness": pointer_freshness,
        "data_cutoff": pointer_date.isoformat() if pointer_date else None,
        "expected_data_cutoff": expected_data_cutoff.isoformat(),
        "lag_days": pointer_lag_days if pointer_date is not None else None,
        "source": "runtime/GATE_BTC_LATEST_ELIGIBLE_RUN.json",
    }

    delta = measurement.get("delta_walk_forward") or {}
    components["delta"] = {
        "status": delta.get("status", "MISSING"),
        "freshness": fresh_label(iso_date(measurement.get("data_as_of")), reference_date),
        "observations": delta.get("current"),
        "targets": delta.get("targets"),
        "source": "runtime/GATE_BTC_MEASUREMENT_STATUS.json",
    }

    gateway = data["gateway"]
    components["gateway"] = {
        "status": (gateway or {}).get("status", "MISSING"),
        "freshness": fresh_label(iso_date((gateway or {}).get("latest_source_data_as_of")), reference_date),
        "valid_snapshot_count": (gateway or {}).get("valid_snapshot_count"),
        "target": (gateway or {}).get("required_snapshot_count"),
        "latest_source_data_as_of": (gateway or {}).get("latest_source_data_as_of"),
        "source": "runtime/ledgers/gateway_dynamics/STATUS.json",
    }

    lock = data["lock25_50"]
    lock_status = str((lock or {}).get("status", ""))
    lock_first_close = iso_date((lock or {}).get("first_eligible_close"))
    if (
        lock_status == "READY_WAITING_FIRST_ELIGIBLE_CLOSE"
        and lock_first_close is not None
        and reference_date is not None
        and lock_first_close >= reference_date
        and (lock or {}).get("reanchor_authorized_at_utc")
    ):
        lock_freshness = "CURRENT_AUTHORIZED_REANCHOR_WAITING_UNTOUCHED_CLOSE"
    else:
        lock_freshness = fresh_label(iso_date((lock or {}).get("latest_snapshot_id")), reference_date)
    components["lock25_50"] = {
        "status": (lock or {}).get("status", "MISSING"),
        "freshness": lock_freshness,
        "valid_snapshot_count": (lock or {}).get("valid_snapshot_count"),
        "latest_snapshot_id": (lock or {}).get("latest_snapshot_id"),
        "first_eligible_close": (lock or {}).get("first_eligible_close"),
        "retroactive_fill_prohibited_dates": (lock or {}).get("retroactive_fill_prohibited_dates", []),
        "source": "runtime/ledgers/lock25_50/STATUS.json",
    }

    d50 = data["d50"] or {}
    remote_d50_ledger = d50.get("prospective_immutable_ledger") or {}
    remote_d50_qual = d50.get("data_qualification") or {}
    reconciled_d50_ledger = measurement.get("d50_prospective_immutable_ledger") or {}
    reconciled_d50_qual = measurement.get("d50_data_qualification") or {}
    has_verified_reconciliation = bool(
        measurement.get("reconciliation_note")
        and reconciled_d50_ledger.get("user_action_required") is False
        and reconciled_d50_qual.get("hash_chain_valid") is True
        and not d50_runtime_is_newer(
            remote_d50_ledger,
            remote_d50_qual,
            reconciled_d50_ledger,
            reconciled_d50_qual,
        )
    )
    d50_ledger = reconciled_d50_ledger if has_verified_reconciliation else (remote_d50_ledger or reconciled_d50_ledger)
    d50_qual = reconciled_d50_qual if has_verified_reconciliation else (remote_d50_qual or reconciled_d50_qual)
    d50_remote_blocked = (
        "LOCAL" in str(d50_ledger.get("status", "")).upper()
        or "local" in str(d50_ledger.get("blocker", "")).lower()
        or str(d50_qual.get("source", "")).upper() == "LAST_VALIDATED_PROJECT_STATE"
    )
    if has_verified_reconciliation:
        d50_freshness = fresh_label(
            iso_date(d50_ledger.get("latest_prospective_date"))
            or iso_date(measurement.get("data_as_of")),
            reference_date,
        )
        d50_display_current = d50_ledger.get("current")
        d50_authority = "LOCAL_RECONCILED_MEASUREMENT"
    elif d50_remote_blocked:
        d50_freshness = "STALE_REMOTE_DO_NOT_REPORT_AS_CURRENT"
        d50_display_current = None
        d50_authority = "LOCAL_EXTERNAL_EVIDENCE_REQUIRED"
    else:
        d50_freshness = fresh_label(iso_date(d50.get("data_as_of")), reference_date)
        d50_display_current = d50_ledger.get("current")
        d50_authority = (
            "RUNTIME_NEWER_THAN_RECONCILIATION"
            if measurement.get("reconciliation_note")
            else "RUNTIME"
        )
    components["d50"] = {
        "status": d50_ledger.get("status", "MISSING"),
        "freshness": d50_freshness,
        "display_current": d50_display_current,
        "raw_remote_current_for_audit_only": remote_d50_ledger.get("current"),
        "target": d50_ledger.get("target"),
        "authority": d50_authority,
        "data_qualification_current": d50_qual.get("current"),
        "data_qualification_raw_remote": remote_d50_qual.get("current"),
        "data_qualification_status": d50_qual.get("status"),
        "data_qualification_snapshot_count_total": d50_qual.get("snapshot_count_total"),
        "data_qualification_synchronized_failure": d50_qual.get("synchronized_failure", False),
        "data_qualification_qualified": d50_qual.get("qualified", False),
        "source": "runtime/ledgers/d50/STATUS.json",
    }

    for key, src_name in (("prl50", "prl50"), ("alt_trail", "alt_trail")):
        obj = data[src_name]
        if calendar_waiting(obj):
            freshness = "CURRENT_CALENDAR_GATED"
        elif obj is None:
            freshness = "MISSING"
        else:
            freshness = fresh_label(iso_date(obj.get("latest_snapshot_date")), reference_date)
        components[key] = {
            "status": (obj or {}).get("status", "MISSING"),
            "freshness": freshness,
            "snapshot_count": (obj or {}).get("snapshot_count"),
            "first_eligible_signal_date": (obj or {}).get("first_eligible_signal_date"),
            "first_eligible_execution_date": (obj or {}).get("first_eligible_execution_date"),
            "source": str(paths[src_name].relative_to(runtime_root)),
        }

    bull = data["bull_replay"]
    if bull is None:
        bull_component = {
            "status": "PENDING_INITIALIZATION",
            "freshness": "PENDING_NOT_YET_WRITTEN",
            "observed_days": 0,
            "source": "ledgers/bull_replay_live_shadow/STATUS.json",
        }
    else:
        bull_component = {
            "status": bull.get("status"),
            "freshness": fresh_label(iso_date(bull.get("data_as_of")), reference_date),
            "observed_days": bull.get("observed_days", 0),
            "data_as_of": bull.get("data_as_of"),
            "leaderboard_descriptive_only": bull.get("leaderboard_descriptive_only"),
            "source": "ledgers/bull_replay_live_shadow/STATUS.json",
        }
    components["bull_replay_live_shadow"] = bull_component

    paper = data["delta_paper_monitor"]
    if paper is None:
        paper_component = {
            "status": "PENDING_INITIALIZATION",
            "freshness": "PENDING_NOT_YET_WRITTEN",
            "observed_days": 0,
            "source": "ledgers/delta_paper_monitor/STATUS.json",
        }
    else:
        paper_component = {
            "status": paper.get("status"),
            "freshness": fresh_label(iso_date(paper.get("data_as_of")), reference_date),
            "observed_days": paper.get("observed_days", 0),
            "data_as_of": paper.get("data_as_of"),
            "hypothesis_label": paper.get("hypothesis_label"),
            "official_replica_claim": paper.get("official_replica_claim"),
            "leaderboard_descriptive_only": paper.get("leaderboard_descriptive_only"),
            "source": "ledgers/delta_paper_monitor/STATUS.json",
        }
    components["delta_paper_monitor"] = paper_component

    qos = measurement.get("qos_monthly") or {}
    components["qos_monthly"] = {
        "status": qos.get("status", "MISSING"),
        "freshness": "CURRENT_CALENDAR_GATED" if qos.get("status") == "ACTIVE_CALENDAR_GATED" else "UNKNOWN",
        "current": qos.get("current"),
        "target": qos.get("target"),
        "expected_closes": qos.get("expected_closes"),
        "source": "runtime/GATE_BTC_MEASUREMENT_STATUS.json",
    }

    stale = [name for name, comp in components.items() if str(comp.get("freshness", "")).startswith("STALE")]
    missing = [
        name for name, comp in components.items()
        if comp.get("freshness") in {"MISSING", "UNKNOWN_DATE", "INVALID_FUTURE_DATE"}
    ]

    result = {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reporting_date_utc": now.isoformat(),
        "reference_data_date": reference_date.isoformat() if reference_date else None,
        "expected_data_cutoff": expected_data_cutoff.isoformat(),
        "pointer_lag_days": pointer_lag_days if pointer_date is not None else None,
        # Stale or missing expected evidence is an incomplete delivery, not a
        # green collection with a cosmetic warning. Calendar-gated components
        # are labelled CURRENT_CALENDAR_GATED above and do not trip this gate.
        "status": "BLOCKED_INCOMPLETE_DELIVERY" if stale or missing else "PASS",
        "reporting_only": True,
        "methodology_changes": 0,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "freshness_policy": {
            "rule": "Never silently promote a stale counter to current. Preserve raw stale values only as audit metadata.",
            "daily_pointer_rule": "The latest eligible daily pointer must reach the most recent completed UTC close (reporting date minus one day).",
            "d50_remote_rule": "When runtime says local repair/external local authority is pending, suppress the remote D50 counter from display.",
        },
        "components": components,
        "warnings": {
            "stale_components": stale,
            "missing_or_undated_components": missing,
        },
        "delivery_complete": not stale and not missing,
        "sources": {name: source_record(paths[name], data[name]) for name in paths},
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--today", type=str)
    args = parser.parse_args()
    today = date.fromisoformat(args.today) if args.today else None
    result = reconcile(args.runtime_root, today)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "reference_data_date": result["reference_data_date"],
        "stale_components": result["warnings"]["stale_components"],
        "missing_or_undated_components": result["warnings"]["missing_or_undated_components"],
        "output": str(args.output),
        "research_only": True,
        "orders_generated": 0,
        "real_capital_used": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
