#!/usr/bin/env python3
"""Add operational status and a complete runtime-ledger inventory to reporting.

Reporting only: no methodology, portfolio, scientific gate, order or capital mutation.
The dynamic inventory is observability-only and never changes delivery health by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
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
    "physical_snapshot_count",
    "distinct_capture_days",
    "latest_physical_capture_at_utc",
    "scientific_observations_credited",
    "scientific_target",
    "economic_status",
    "scientific_blockers",
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


def enrich(runtime_root: Path, current: dict, as_of_utc=None) -> dict:
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

    # Fresh Momentum signals do not imply fresh or admissible economic marks.
    me_root = runtime_root / "ledgers/momentum_m1_m2_economics"
    active_epoch = load(me_root / "ACTIVE_EPOCH.json")
    legacy_disposition = load(me_root / "INTERRUPTED_EPOCH.json")
    if active_epoch:
        safe("momentum_active_epoch", active_epoch)
        if active_epoch.get("relative_path") != "epochs/hold_20260928":
            raise RuntimeError("UNRECOGNIZED_MOMENTUM_EPOCH_PATH")
        me_root = me_root / active_epoch["relative_path"]
    me = load(me_root / "ECONOMICS_STATUS.json")
    md = load(me_root / "DELIVERY_STATUS.json")
    mp = load(me_root / "PRICE_COVERAGE_STATUS.json")
    if me or md or mp:
        for label, obj in (("momentum_economics", me), ("momentum_delivery", md), ("momentum_prices", mp)):
            safe(label, obj)
        component = current["components"]["momentum_m1_m2"]
        component.update(signal_status=component["status"],
                         economic_status=(md or me or {}).get("status", "MISSING"),
                         last_economic_cutoff=(me or {}).get("data_as_of"),
                         economic_freshness=freshness(me, reference),
                         price_coverage_status=(mp or {}).get("status", "MISSING"),
                         price_coverage_cutoff=(mp or {}).get("cutoff"),
                         economic_gaps=(md or {}).get("gaps", []),
                         weighting_audit=(md or {}).get("weighting_audit"),
                         next_economic_action=(md or {}).get("next_action"),
                         cost_status=(me or {}).get("cost_status"),
                         economics_source=str((me_root / "DELIVERY_STATUS.json").relative_to(runtime_root)))
        if active_epoch:
            latest_completed = (as_of_utc or datetime.now(timezone.utc)).date() - timedelta(days=1)
            component["economic_freshness"] = freshness(me, latest_completed)
            component["freshness"] = freshness(mom, latest_completed)
            component.update(economic_epoch_id=active_epoch["epoch_id"],
                             legacy_economic_status=(legacy_disposition or {}).get("status"),
                             return_observations=(me or {}).get("return_observations", 0),
                             first_eligible_economic_cutoff=(me or {}).get("first_eligible_cutoff"),
                             economic_nav=(me or {}).get("nav"),
                             latest_economics=(me or {}).get("latest_economics"),
                             terminal_observation_target=None)
            if component["economic_status"] == "WAITING_FIRST_POST_APPROVAL_CLOSE" and latest_completed >= iso(me["first_eligible_cutoff"]):
                component["economic_status"] = "FAILED_MISSING_FIRST_ECONOMIC_CLOSE"
                component["next_economic_action"] = "CHECK_AUTOMATIC_COLLECTION_NO_RESET_NO_BACKFILL"
        blocked = str(component["economic_status"]).startswith("BLOCKED")
        failed = str(component["economic_status"]).startswith("FAILED") or str(component["price_coverage_status"]).startswith("FAILED")
        if failed:
            component["collection_health_hint"] = "RED_FAILED_DELIVERY"
        elif component["economic_status"] == "WAITING_FIRST_POST_APPROVAL_CLOSE":
            component["economic_freshness"] = "CURRENT_CALENDAR_GATED"
            component["collection_health_hint"] = "GREEN_ACTIVE" if component["freshness"] == "FRESH" else "AMBER_BLOCKED_DEPENDENCY"
        elif blocked or component["economic_freshness"] != "FRESH":
            component["collection_health_hint"] = "AMBER_BLOCKED_DEPENDENCY"
        if blocked or failed or active_epoch:
            component["status"] = component["economic_status"]
        current.setdefault("sources", {})["momentum_economic_delivery"] = source_meta(me_root / "DELIVERY_STATUS.json", md)

    # D100 v2 distinguishes physical delivery from scientific readiness.
    d100p = runtime_root / "ledgers/d100/STATUS.json"
    d100 = load(d100p)
    d100_active = bool(d100 and d100.get("schema") == "qrds.d100.forward_collection.v2")
    if d100_active:
        safe("d100", d100)
        failed_capture = d100.get("last_error") is not None
        hint = "RED_FAILED_DELIVERY" if failed_capture else "AMBER_BLOCKED_DEPENDENCY"
        current["components"]["d100"] = {
            "status": d100["status"],
            "freshness": freshness(d100, reference, "latest_physical_capture_at_utc"),
            "collection_health_hint": hint,
            "physical_snapshot_count": d100.get("physical_snapshot_count"),
            "distinct_capture_days": d100.get("distinct_capture_days"),
            "latest_physical_capture_at_utc": d100.get("latest_physical_capture_at_utc"),
            "latest_raw_universe_count": d100.get("latest_raw_universe_count"),
            "latest_market_data_observed_count": d100.get("latest_market_data_observed_count"),
            "scientific_observations_credited": d100.get("scientific_observations_credited"),
            "scientific_target": d100.get("scientific_target"),
            "economic_status": d100.get("economic_status"),
            "scientific_blockers": d100.get("scientific_blockers"),
            "next_action": d100.get("next_action"),
            "source": "ledgers/d100/STATUS.json",
        }
        current.setdefault("sources", {})["d100"] = source_meta(d100p, d100)
        ep = runtime_root / "ledgers/d100/economic/STATUS.json"
        economic = load(ep)
        if economic and economic.get("schema") == "qrds.d100.economics.v1":
            safe("d100_economic", economic)
            failed_economic = economic.get("last_error") is not None
            component = current["components"]["d100"]
            component.update({key: economic.get(key) for key in (
                "scientific_observations_credited", "scientific_target",
                "remaining_scientific_observations", "scientific_blockers", "next_action",
                "latest_eligible_asset_count", "first_possible_bar_date", "anchor_bar_date",
                "latest_signal_available_at_utc", "protocol_approved")})
            component["physical_status"] = component["status"]
            component["status"] = economic["status"]
            component["economic_status"] = economic["status"]
            if str(economic["status"]).startswith("CLOSED_"):
                component["freshness"] = "CLOSED_NOT_APPLICABLE"
            else:
                ef = freshness(economic, reference, "latest_signal_available_at_utc")
                component["economic_freshness"] = ef
                if ef != "FRESH":
                    component["freshness"] = ef
            component["collection_health_hint"] = "RED_FAILED_DELIVERY" if failed_capture or failed_economic else "GREEN_ACTIVE"
            component["economic_source"] = "ledgers/d100/economic/STATUS.json"
            current.setdefault("sources", {})["d100_economic"] = source_meta(ep, economic)


    qos = load(runtime_root / "ledgers/qos_three_track/STATUS.json")
    qos_active = bool(qos and qos.get("schema") == "gate_btc.qos_covered_delivery.v1")
    if qos_active:
        safe("qos_three_track", qos)
        completed = (as_of_utc or datetime.now(timezone.utc)).date() - timedelta(days=1)
        waiting = qos.get("status") == "WAITING_NEXT_APPROVED_MONTH_END" and completed < iso(qos.get("next_signal_date"))
        qfresh = "CURRENT_CALENDAR_GATED" if waiting else freshness(qos, completed, "latest_snapshot_date")
        failed_qos = str(qos.get("status", "")).startswith(("FAILED", "BLOCKED"))
        current["components"]["qos_three_track"] = {
            **qos, "freshness": qfresh,
            "collection_health_hint": "RED_FAILED_DELIVERY" if failed_qos else "GREEN_ACTIVE" if waiting or qfresh == "FRESH" else "AMBER_BLOCKED_DEPENDENCY",
            "source": "ledgers/qos_three_track/STATUS.json"}

    m3 = load(runtime_root / "ledgers/momentum_m3_economics/STATUS.json")
    m3_active = bool(m3 and m3.get("schema") == "gate_btc.momentum_m3_economics_status.v1")
    if m3_active:
        safe("momentum_m3_economics", m3)
        completed = (as_of_utc or datetime.now(timezone.utc)).date() - timedelta(days=1)
        waiting = m3.get("status") == "WAITING_FIRST_POST_IMPLEMENTATION_CLOSE" and completed < iso(m3.get("first_eligible_cutoff"))
        mfresh = "CURRENT_CALENDAR_GATED" if waiting else freshness(m3, completed)
        current["components"]["momentum_m3_economics"] = {
            **m3, "freshness": mfresh,
            "collection_health_hint": "RED_FAILED_DELIVERY" if str(m3.get("status", "")).startswith("FAILED") else "GREEN_ACTIVE" if waiting or mfresh == "FRESH" else "AMBER_BLOCKED_DEPENDENCY",
            "source": "ledgers/momentum_m3_economics/STATUS.json"}

    alt = load(runtime_root / "ledgers/alt_trail40_10/DELIVERY_STATUS.json")
    alt_active = bool(alt and alt.get("schema") == "gate_btc.alt_trail40_10.delivery.v1")
    if alt_active:
        safe("alt_trail", alt)
        alt_status = str(alt.get("status", ""))
        completed = (as_of_utc or datetime.now(timezone.utc)).date() - timedelta(days=1)
        waiting = alt_status == "WAITING_APPROVED_MONTH_END_2026_09_30" and completed < iso(alt.get("first_eligible_signal_date"))
        failed_alt = alt_status.startswith("FAILED")
        blocked_alt = alt_status.startswith("BLOCKED")
        alt_fresh = "CURRENT_CALENDAR_GATED" if waiting else "INTERRUPTED_PRESERVED" if blocked_alt else freshness(alt, completed, "last_archived_date")
        current["components"]["alt_trail"] = {
            **alt, "freshness": alt_fresh,
            "collection_health_hint": "RED_FAILED_DELIVERY" if failed_alt else "AMBER_BLOCKED_DEPENDENCY" if blocked_alt or (not waiting and alt_fresh != "FRESH") else "GREEN_ACTIVE",
            "source": "ledgers/alt_trail40_10/DELIVERY_STATUS.json"}

    prl = load(runtime_root / "ledgers/prl50_position/DELIVERY_STATUS.json")
    prl_active = bool(prl and prl.get("schema") == "gate_btc.prl50.delivery.v1")
    if prl_active:
        safe("prl50", prl)
        prl_status = str(prl.get("status", ""))
        completed = (as_of_utc or datetime.now(timezone.utc)).date() - timedelta(days=1)
        waiting = prl_status == "WAITING_APPROVED_MONTH_END_2026_09_30" and completed < iso(prl.get("first_eligible_signal_date"))
        failed_prl = prl_status.startswith("FAILED")
        blocked_prl = prl_status.startswith("BLOCKED")
        prl_fresh = "CURRENT_CALENDAR_GATED" if waiting else "INTERRUPTED_PRESERVED" if blocked_prl else freshness(prl, completed, "last_archived_date")
        current["components"]["prl50"] = {
            **prl, "freshness": prl_fresh,
            "collection_health_hint": "RED_FAILED_DELIVERY" if failed_prl else "AMBER_BLOCKED_DEPENDENCY" if blocked_prl or (not waiting and prl_fresh != "FRESH") else "GREEN_ACTIVE",
            "source": "ledgers/prl50_position/DELIVERY_STATUS.json"}

    system9_path = runtime_root / "system9/STAGE9_EXIT_STATUS.json"
    system9 = load(system9_path)
    system9_active = bool(system9 and system9.get("schema") == "gate_btc.2_0.stage9_exit_gate_status.v1")
    if system9_active:
        effects = system9.get("completion_effect") or {}
        if effects.get("engine_feed") is not False or effects.get("orders") != 0 or effects.get("real_capital") != 0:
            raise SystemExit("unsafe system9 exit boundary")
        gate_pass = system9.get("decision") == "PASS_STAGE9_EXIT_GATE" and system9.get("stage_9_complete") is True
        current["components"]["system9_exit"] = {
            "status": system9.get("decision"),
            "stage_9_complete": system9.get("stage_9_complete"),
            "current_N": (system9.get("exit_segment") or {}).get("current_N"),
            "required_N": (system9.get("exit_segment") or {}).get("required_N"),
            "distinct_utc_hours": len((system9.get("exit_segment") or {}).get("distinct_utc_hours", [])),
            "distinct_utc_weekdays": len((system9.get("exit_segment") or {}).get("distinct_utc_weekdays", [])),
            "checks": (system9.get("exit_segment") or {}).get("checks"),
            "system10_research_dependency_released":
                (system9.get("completion_effect") or {}).get("system_10_dependency_released_for_research_only_engine_parity"),
            "automatic_promotion": False, "economics_allowed": False,
            "engine_feed": False, "orders_generated": 0, "real_capital_used": 0,
            "freshness": "GATE_RESULT_PRESERVED" if gate_pass else "GATE_COLLECTING",
            "collection_health_hint": "GREEN_GATE_PASSED" if gate_pass else "AMBER_BLOCKED_DEPENDENCY",
            "source": "system9/STAGE9_EXIT_STATUS.json",
        }

    v16b1_path = runtime_root / "ledgers/v16b1/STATUS.json"
    v16b1_corpus_path = runtime_root / "evidence/v16b1/prospective_universe/STATUS.json"
    v16b1 = load(v16b1_path)
    v16b1_corpus = load(v16b1_corpus_path)
    v16b1_active = bool(v16b1 and v16b1.get("schema") == "gate_btc.v16b1.status.v1")
    if v16b1_active:
        safe("v16b1", v16b1)
        safe("v16b1_corpus", v16b1_corpus)
        training_ready = (v16b1_corpus or {}).get("training_ready") is True
        first = iso((v16b1_corpus or {}).get("first_eligible_thursday"))
        completed = (as_of_utc or datetime.now(timezone.utc)).date() - timedelta(days=1)
        calendar_wait = first is not None and completed < first
        current["components"]["v16b1"] = {
            "status": v16b1.get("status"),
            "operational_blocker": v16b1.get("operational_blocker"),
            "canonical_cycle_count": v16b1.get("canonical_cycle_count"),
            "prospective_credit": v16b1.get("prospective_credit"),
            "signal_date": v16b1.get("signal_date"),
            "signal_seal": v16b1.get("signal_seal"),
            "entry_seal": v16b1.get("entry_seal"),
            "next_canonical_event": v16b1.get("next_canonical_event"),
            "first_eligible_thursday": (v16b1_corpus or {}).get("first_eligible_thursday"),
            "training_ready": training_ready,
            "observed_week_count": (v16b1_corpus or {}).get("observed_week_count"),
            "frozen_model_min_prior_weeks": (v16b1_corpus or {}).get("frozen_model_min_prior_weeks"),
            "remaining_blocker": (v16b1_corpus or {}).get("remaining_blocker"),
            "freshness": "CURRENT_CALENDAR_GATED" if calendar_wait else freshness(v16b1, completed),
            "collection_health_hint": "AMBER_BLOCKED_DEPENDENCY" if not training_ready or
                                      v16b1.get("operational_blocker") else "GREEN_ACTIVE",
            "source": "ledgers/v16b1/STATUS.json",
            "corpus_source": "evidence/v16b1/prospective_universe/STATUS.json",
            "research_only": True, "shadow_only": True, "not_approved": True,
            "engine_feed": False, "orders_generated": 0, "real_capital_used": 0,
        }

    bull_path = runtime_root / "ledgers/bull_replay_live_shadow/DELIVERY_STATUS.json"
    bull = load(bull_path)
    bull_active = bool(bull and bull.get("schema") == "gate_btc.bull_replay_live_shadow.delivery.v1")
    if bull_active:
        safe("bull_replay_live_shadow", bull)
        bull_blocked = str(bull.get("status", "")).startswith("BLOCKED")
        bull_waiting = str(bull.get("status", "")).startswith("WAITING_")
        bull_freshness = ("INTERRUPTED_PRESERVED" if bull_blocked else
                          "CURRENT_CALENDAR_GATED" if bull_waiting else freshness(bull, reference))
        current["components"]["bull_replay_live_shadow"] = {
            **bull,
            "freshness": bull_freshness,
            "collection_health_hint": "AMBER_BLOCKED_DEPENDENCY" if bull_blocked or
                                      (not bull_waiting and bull_freshness != "FRESH") else "GREEN_ACTIVE",
            "source": "ledgers/bull_replay_live_shadow/DELIVERY_STATUS.json",
        }

    warnings = current.setdefault("warnings", {})
    stale = list(warnings.get("stale_components", []))
    missing = list(warnings.get("missing_or_undated_components", []))
    failed = list(warnings.get("failed_delivery_components", []))
    blocked = list(warnings.get("blocked_dependency_components", []))
    if d100_active:
        # Reconcile prior D100 warnings against the current economic authority.
        # Other fronts retain their existing reconciliation behavior.
        stale = [x for x in stale if x != "d100"]
        missing = [x for x in missing if x != "d100"]
        failed = [x for x in failed if x != "d100"]
        blocked = [x for x in blocked if x != "d100"]
    if qos_active:
        stale = [x for x in stale if x != "qos_three_track"]
        missing = [x for x in missing if x != "qos_three_track"]
        failed = [x for x in failed if x != "qos_three_track"]
        blocked = [x for x in blocked if x != "qos_three_track"]
    if m3_active:
        stale = [x for x in stale if x != "momentum_m3_economics"]
        missing = [x for x in missing if x != "momentum_m3_economics"]
        failed = [x for x in failed if x != "momentum_m3_economics"]
        blocked = [x for x in blocked if x != "momentum_m3_economics"]
    if alt_active:
        stale = [x for x in stale if x != "alt_trail"]
        missing = [x for x in missing if x != "alt_trail"]
        failed = [x for x in failed if x != "alt_trail"]
        blocked = [x for x in blocked if x != "alt_trail"]
    if prl_active:
        stale = [x for x in stale if x != "prl50"]
        missing = [x for x in missing if x != "prl50"]
        failed = [x for x in failed if x != "prl50"]
        blocked = [x for x in blocked if x != "prl50"]
    if system9_active or v16b1_active:
        for names in (stale, missing, failed, blocked):
            names[:] = [x for x in names if x not in {"system9_exit", "v16b1"}]
    if bull_active:
        for names in (stale, missing, failed, blocked):
            names[:] = [x for x in names if x != "bull_replay_live_shadow"]
    for name in ("b3_h1", "v16b", "momentum_m1_m2") + (("d100",) if d100_active else ()) + (("qos_three_track",) if qos_active else ()) + (("momentum_m3_economics",) if m3_active else ()) + (("prl50",) if prl_active else ()) + (("alt_trail",) if alt_active else ()) + (("bull_replay_live_shadow",) if bull_active else ()) + (("v16b1",) if v16b1_active else ()) + (("system9_exit",) if system9_active else ()):
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
    if bull_active:
        sources["bull_replay_live_shadow"] = source_meta(bull_path, bull)
    if v16b1_active:
        sources["v16b1"] = source_meta(v16b1_path, v16b1)
        sources["v16b1_corpus"] = source_meta(v16b1_corpus_path, v16b1_corpus)
    if system9_active:
        sources["system9_exit"] = source_meta(system9_path, system9)

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
