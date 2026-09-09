#!/usr/bin/env python3
"""Add operational status and a complete runtime-ledger inventory to reporting.

Reporting only: no methodology, portfolio, scientific gate, order or capital mutation.
The dynamic inventory is observability-only and never changes delivery health by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else None


def iso(value):
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def freshness(obj, reference, date_key="data_as_of"):
    if obj is None:
        return "MISSING"
    observed = iso(obj.get(date_key))
    if observed is None:
        return "UNKNOWN_DATE"
    if reference is None:
        return "DATE_PRESENT_NO_REFERENCE"
    return "FRESH" if observed >= reference else "STALE"


def latest_weekday(reference):
    """Conservative B3 calendar proxy: weekends only; holidays can false-red, never false-green."""
    if reference is None:
        return None
    expected = reference
    while expected.weekday() >= 5:
        expected -= timedelta(days=1)
    return expected


def b3_freshness(obj, reference):
    if obj is None:
        return "MISSING"
    observed = iso(obj.get("latest_valid_date"))
    if observed is None:
        return "UNKNOWN_DATE"
    expected = latest_weekday(reference)
    if expected is None:
        return "DATE_PRESENT_NO_REFERENCE"
    return "FRESH" if observed >= expected else "STALE"


def safe(name, obj):
    if obj is None:
        return
    for key, expected in {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
    }.items():
        if key in obj and obj[key] != expected:
            raise SystemExit(f"unsafe {name}: {key}={obj[key]!r}")
    if obj.get("engine_feed") is True or obj.get("promotion_allowed") is True:
        raise SystemExit(f"unsafe {name}: operational boundary violated")


def collection_health_hint(name, obj):
    if obj is None:
        return None
    status = str(obj.get("status", "")).upper()
    last_run = str(obj.get("last_run_state", "")).upper()
    signal_producer = str(obj.get("signal_producer", "")).upper()
    if (
        status.startswith(("FAIL", "ERROR", "OPEN_DIAGNOSTIC"))
        or "FAILED" in last_run
        or last_run.startswith("ERROR")
    ):
        return "RED_FAILED_DELIVERY"
    if status.startswith("BLOCKED") or signal_producer.startswith("BLOCKED"):
        return "AMBER_BLOCKED_DEPENDENCY"
    return None


def source_meta(path: Path, obj):
    result = {"exists": path.is_file(), "path": str(path)}
    if path.is_file():
        result["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    if obj and obj.get("schema"):
        result["schema"] = obj["schema"]
    return result


def component_with_hint(component, hint):
    if hint:
        component["collection_health_hint"] = hint
    return component


INVENTORY_FIELDS = (
    "data_as_of",
    "latest_valid_date",
    "latest_snapshot_id",
    "latest_snapshot_date",
    "latest_source_data_as_of",
    "valid_snapshot_count",
    "snapshot_count",
    "observed_snapshots",
    "observed_days",
    "canonical_cycle_count",
    "economics_locked",
    "promotion_allowed",
    "engine_feed",
    "orders_generated",
    "real_capital_used",
)


def _normalize_source(value):
    text = str(value or "").replace("\\", "/")
    if text.startswith("runtime/"):
        text = text[len("runtime/"):]
    return text


def discover_ledger_inventory(runtime_root: Path, current: dict) -> None:
    """Inventory every ledger STATUS without assigning generic scientific freshness/health."""
    ledgers_root = runtime_root / "ledgers"
    inventory = {}
    if ledgers_root.is_dir():
        for status_path in sorted(ledgers_root.glob("*/STATUS.json"), key=lambda p: p.parent.name):
            ledger_id = status_path.parent.name
            obj = load(status_path)
            if obj is None:
                continue
            safe(f"ledger_inventory:{ledger_id}", obj)
            rel = status_path.relative_to(runtime_root).as_posix()
            record = {
                "ledger_id": ledger_id,
                "status": obj.get("status", "UNKNOWN"),
                "schema": obj.get("schema"),
                "source": rel,
                "sha256": hashlib.sha256(status_path.read_bytes()).hexdigest(),
                "inventory_only": True,
                "health_authority": False,
            }
            for key in INVENTORY_FIELDS:
                if key in obj:
                    record[key] = obj[key]
            inventory[ledger_id] = record

    represented_sources = {
        _normalize_source(component.get("source"))
        for component in current.get("components", {}).values()
        if isinstance(component, dict) and component.get("source")
    }
    represented = sorted(
        ledger_id
        for ledger_id, record in inventory.items()
        if _normalize_source(record["source"]) in represented_sources
    )
    unrepresented = sorted(set(inventory) - set(represented))
    current["ledger_inventory"] = inventory
    current["inventory_summary"] = {
        "ledger_count": len(inventory),
        "ledger_ids": sorted(inventory),
        "component_count": len(current.get("components", {})),
        "represented_ledger_ids": represented,
        "unrepresented_ledger_ids": unrepresented,
        "inventory_only": True,
        "does_not_change_delivery_health": True,
    }


def enrich(runtime_root: Path, current: dict) -> dict:
    reference = iso(current.get("reference_data_date"))
    b3p = runtime_root / "ledgers/b3_h1/STATUS.json"
    v16p = runtime_root / "ledgers/v16b/STATUS.json"
    momp = runtime_root / "ledgers/momentum_m1_m2/STATUS.json"
    b3 = load(b3p)
    v16 = load(v16p)
    mom = load(momp)
    safe("b3_h1", b3)
    safe("v16b", v16)
    safe("momentum_m1_m2", mom)

    expected_b3_session = latest_weekday(reference)
    current.setdefault("components", {})["b3_h1"] = component_with_hint({
        "status": (b3 or {}).get("status", "MISSING"),
        "freshness": b3_freshness(b3, reference),
        "latest_valid_date": (b3 or {}).get("latest_valid_date"),
        "expected_session_weekday_proxy": expected_b3_session.isoformat() if expected_b3_session else None,
        "valid_observation_count": (b3 or {}).get("valid_observation_count"),
        "economics_locked": (b3 or {}).get("economics_locked"),
        "backfill_automatically_created": (b3 or {}).get("backfill_automatically_created"),
        "source": "ledgers/b3_h1/STATUS.json",
    }, collection_health_hint("b3_h1", b3))
    current["components"]["v16b"] = component_with_hint({
        "status": (v16 or {}).get("status", "MISSING"),
        "freshness": freshness(v16, reference),
        "canonical_cycle_count": (v16 or {}).get("canonical_cycle_count"),
        "v16b_preflight": (v16 or {}).get("v16b_preflight"),
        "v16b_rehearsal": (v16 or {}).get("v16b_rehearsal"),
        "signal_producer": (v16 or {}).get("signal_producer"),
        "signal_seal": (v16 or {}).get("signal_seal"),
        "entry_seal": (v16 or {}).get("entry_seal"),
        "next_canonical_event": (v16 or {}).get("next_canonical_event"),
        "source": "ledgers/v16b/STATUS.json",
    }, collection_health_hint("v16b", v16))
    current["components"]["momentum_m1_m2"] = component_with_hint({
        "status": (mom or {}).get("status", "MISSING"),
        "freshness": freshness(mom, reference),
        "observed_snapshots": (mom or {}).get("observed_snapshots"),
        "last_run_state": (mom or {}).get("last_run_state"),
        "methodology_failure": (mom or {}).get("methodology_failure"),
        "m1_summary": (mom or {}).get("m1_summary"),
        "m2_summary": (mom or {}).get("m2_summary"),
        "source": "ledgers/momentum_m1_m2/STATUS.json",
    }, collection_health_hint("momentum_m1_m2", mom))

    warnings = current.setdefault("warnings", {})
    stale = list(warnings.get("stale_components", []))
    missing = list(warnings.get("missing_or_undated_components", []))
    failed = list(warnings.get("failed_delivery_components", []))
    blocked = list(warnings.get("blocked_dependency_components", []))
    for name in ("b3_h1", "v16b", "momentum_m1_m2"):
        component = current["components"][name]
        observed_freshness = component["freshness"]
        hint = component.get("collection_health_hint", "")
        if str(observed_freshness).startswith("STALE") and name not in stale:
            stale.append(name)
        if observed_freshness in {"MISSING", "UNKNOWN_DATE", "INVALID_FUTURE_DATE"} and name not in missing:
            missing.append(name)
        if str(hint).startswith("RED") and name not in failed:
            failed.append(name)
        if str(hint).startswith("AMBER") and name not in blocked:
            blocked.append(name)
    warnings["stale_components"] = stale
    warnings["missing_or_undated_components"] = missing
    warnings["failed_delivery_components"] = failed
    warnings["blocked_dependency_components"] = blocked
    current["delivery_complete"] = not stale and not missing and not failed and not blocked
    current["status"] = "PASS" if current["delivery_complete"] else "BLOCKED_INCOMPLETE_DELIVERY"
    sources = current.setdefault("sources", {})
    sources["b3_h1"] = source_meta(b3p, b3)
    sources["v16b"] = source_meta(v16p, v16)
    sources["momentum_m1_m2"] = source_meta(momp, mom)

    # Inventory is intentionally calculated after authoritative components so the
    # summary can expose which runtime ledgers are absent from executive health.
    discover_ledger_inventory(runtime_root, current)
    return current


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    state = load(args.state)
    if not state:
        raise SystemExit("base reporting state missing")
    state = enrich(args.runtime_root, state)
    args.state.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": state["status"],
        "b3_h1": state["components"]["b3_h1"],
        "v16b": state["components"]["v16b"],
        "momentum_m1_m2": state["components"]["momentum_m1_m2"],
        "inventory_summary": state["inventory_summary"],
        "orders_generated": 0,
        "real_capital_used": 0,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
