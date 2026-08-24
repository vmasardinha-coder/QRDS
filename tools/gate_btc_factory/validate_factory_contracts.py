#!/usr/bin/env python3
"""Fail-closed validator for QRDS factory contracts and shadow runner state."""
from __future__ import annotations

import json
from pathlib import Path

import ledger_guard

ROOT = Path(__file__).resolve().parent
REQUIRED_JSON = [
    "MASTER_STATE.json",
    "QUEUES.json",
    "TRANSITION_CONTRACT.v1.json",
    "READ_ADAPTER_CONTRACT.v1.json",
    "PARITY_DRYRUN_CONTRACT.v1.json",
    "FACTORY_REPORT_SCHEMA.v1.json",
    "FAMILY_FLOW_CONTRACT.v1.json",
    "WORKFLOW_CONTRACT.v1.json",
    "FACTORY_STATUS_LATEST.json",
    "DATA_GAPS_LATEST.json",
    "LEDGER_CONTRACT.v1.json",
]
EXPECTED_SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "ENGINE_FEED": False,
}
FORBIDDEN_TOKENS = {
    "activation_allowed": True,
    "replace_daily_collection": True,
    "redirect_runtime_pointer": True,
    "mutate_existing_sources": True,
    "emit_orders": True,
    "use_real_capital": True,
    "feed_engine": True,
    "active_path_rollout_enabled": True,
    "existing_active_workflows_mutated": True,
    "existing_active_schedules_mutated": True,
    "protected_path_mutation": True,
    "commits_generated_status": True,
    "writes_repository": True,
    "stale_transition_or_promotion_allowed": True,
}


def load(name: str) -> dict:
    path = ROOT / name
    if not path.is_file():
        raise SystemExit(f"FAIL missing required factory file: {name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"FAIL invalid JSON {name}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"FAIL expected JSON object: {name}")
    return value


def walk(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key, value
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def main() -> int:
    docs = {name: load(name) for name in REQUIRED_JSON}
    for runner_name in ("run_factory.py", "run_factory_ci.py"):
        if not (ROOT / runner_name).is_file():
            raise SystemExit(f"FAIL missing shadow runner: {runner_name}")

    safety_seen = False
    for doc in docs.values():
        for key in ("global_mode", "global_safety_required", "global_safety", "safety"):
            block = doc.get(key) if isinstance(doc, dict) else None
            if isinstance(block, dict) and all(block.get(k) == v for k, v in EXPECTED_SAFETY.items()):
                safety_seen = True
    if not safety_seen:
        raise SystemExit("FAIL no exact global safety block found")

    for name, doc in docs.items():
        for key, value in walk(doc):
            if key in FORBIDDEN_TOKENS and value == FORBIDDEN_TOKENS[key]:
                raise SystemExit(f"FAIL unsafe factory setting in {name}: {key}={value}")

    adapter = docs["READ_ADAPTER_CONTRACT.v1.json"]
    mandatory_forbidden = {
        "WRITE_ACTIVE_RUNTIME",
        "WRITE_EXISTING_LEDGER",
        "ALTER_WORKFLOW",
        "ALTER_SCHEDULE",
        "ALTER_COLLECTOR",
        "READ_PARTIAL_BLIND_HOLDOUT_ECONOMICS",
    }
    missing = sorted(mandatory_forbidden - set(adapter.get("forbidden_operations", [])))
    if missing:
        raise SystemExit(f"FAIL adapter contract missing prohibitions: {missing}")

    parity = docs["PARITY_DRYRUN_CONTRACT.v1.json"]
    if parity.get("activation_allowed") is not False:
        raise SystemExit("FAIL parity contract permits active rollout")
    dry = parity.get("dry_run_rules", {})
    if dry.get("mutate_existing_sources") is not False or dry.get("replace_daily_collection") is not False:
        raise SystemExit("FAIL parity dry-run can mutate/replace active sources")

    flow = docs["FAMILY_FLOW_CONTRACT.v1.json"]
    activation = flow.get("activation", {})
    required_true = (
        "shadow_runner_enabled",
        "factory_owned_workflow_enabled",
        "factory_owned_schedule_enabled",
        "push_refresh_enabled",
        "manual_dispatch_enabled",
    )
    if any(activation.get(key) is not True for key in required_true):
        raise SystemExit("FAIL factory shadow activation is incomplete")
    required_false = (
        "existing_active_workflows_mutated",
        "existing_active_schedules_mutated",
        "active_path_rollout_enabled",
        "replace_daily_collection",
        "redirect_runtime_pointer",
        "engine_feed",
    )
    if any(activation.get(key) is not False for key in required_false):
        raise SystemExit("FAIL factory shadow activation crosses protected boundary")
    if activation.get("factory_owned_schedule") != "23 * * * *":
        raise SystemExit("FAIL unexpected factory-owned hourly schedule")
    if activation.get("orders") != 0 or activation.get("real_capital") != 0:
        raise SystemExit("FAIL shadow activation permits orders/capital")

    workflow_policy = flow.get("workflow_write_policy", {})
    if workflow_policy.get("repository_permissions") != "contents:read":
        raise SystemExit("FAIL factory workflow has non-read-only repository permission")
    if workflow_policy.get("commits_generated_status") is not False:
        raise SystemExit("FAIL factory workflow may commit generated status")
    if workflow_policy.get("artifact_only") is not True:
        raise SystemExit("FAIL factory workflow must emit artifact only")
    if workflow_policy.get("protected_path_mutation") is not False:
        raise SystemExit("FAIL factory workflow may mutate protected paths")
    if workflow_policy.get("allowed_checkout_diff") != ["tools/gate_btc_factory/FACTORY_STATUS_RUNTIME.json"]:
        raise SystemExit("FAIL factory workflow checkout diff boundary changed")

    freshness_policy = flow.get("freshness_policy", {})
    if freshness_policy.get("source_limit_minutes") != 180:
        raise SystemExit("FAIL unexpected source freshness limit")
    if freshness_policy.get("stale") != "STALE_READ_ONLY":
        raise SystemExit("FAIL stale source is not read-only")
    if freshness_policy.get("stale_transition_or_promotion_allowed") is not False:
        raise SystemExit("FAIL stale source may drive transition/promotion")

    workflow = docs["WORKFLOW_CONTRACT.v1.json"]
    if workflow.get("workflow_path") != ".github/workflows/gate-btc-factory-shadow.yml":
        raise SystemExit("FAIL workflow contract points to unexpected path")
    if workflow.get("schedule_cron") != "23 * * * *":
        raise SystemExit("FAIL workflow contract is not hourly")
    if workflow.get("permissions") != {"contents": "read"}:
        raise SystemExit("FAIL workflow contract permissions are not read-only")
    if workflow.get("writes_repository") is not False:
        raise SystemExit("FAIL workflow contract permits repository writes")
    if workflow.get("uploads_artifact_only") is not True:
        raise SystemExit("FAIL workflow contract must be artifact-only")
    if workflow.get("runner") != "tools/gate_btc_factory/run_factory_ci.py":
        raise SystemExit("FAIL workflow contract runner mismatch")
    if workflow.get("runtime_output") != "tools/gate_btc_factory/FACTORY_STATUS_RUNTIME.json":
        raise SystemExit("FAIL workflow contract runtime output mismatch")
    if workflow.get("source_freshness_minutes") != 180:
        raise SystemExit("FAIL workflow freshness contract mismatch")
    if workflow.get("safety") != EXPECTED_SAFETY:
        raise SystemExit("FAIL workflow safety block mismatch")

    report_schema = docs["FACTORY_REPORT_SCHEMA.v1.json"]
    status = docs["FACTORY_STATUS_LATEST.json"]
    missing_sections = [k for k in report_schema.get("required_sections", []) if k not in status]
    if missing_sections:
        raise SystemExit(f"FAIL status missing report sections: {missing_sections}")
    if status.get("global_safety") != EXPECTED_SAFETY:
        raise SystemExit("FAIL status safety block mismatch")
    parity_status = status.get("parity_readiness", {})
    if parity_status.get("shadow_runner") != "ACTIVE":
        raise SystemExit("FAIL first factory cycle is not active")
    if parity_status.get("engine_feed") is not False or parity_status.get("orders") != 0:
        raise SystemExit("FAIL status violates shadow-only boundary")
    non_interference = status.get("non_interference_assertion", {})
    status_required_false = [
        "active_workflows_mutated",
        "active_ledgers_mutated",
        "runtime_pointers_mutated",
        "parameters_or_clocks_mutated",
        "backfill_performed",
        "partial_holdout_economics_read",
    ]
    if any(non_interference.get(k) is not False for k in status_required_false):
        raise SystemExit("FAIL non-interference assertion is incomplete or unsafe")
    if non_interference.get("write_prefix") != "tools/gate_btc_factory/":
        raise SystemExit("FAIL write boundary escaped factory namespace")

    track_map = status.get("track_map", {})
    if not track_map:
        raise SystemExit("FAIL factory cycle contains no families/tracks")
    if status.get("queue_counts", {}).get("total_tracks") != len(track_map):
        raise SystemExit("FAIL queue total does not match track map")

    ledger_summary = ledger_guard.validate_ledgers(ROOT)\n    expected_ledgers = {"hypotheses", "rejections", "survivors", "handoffs", "data_gaps", "sources"}\n    if set(ledger_summary) != expected_ledgers:\n        raise SystemExit(f"FAIL living ledger set mismatch: {sorted(ledger_summary)}")\n\n    data_gaps = docs["DATA_GAPS_LATEST.json"]
    if data_gaps.get("schema") != "qrds.factory.data_gaps.v1":
        raise SystemExit("FAIL unexpected data-gap schema")
    if data_gaps.get("append_only_semantics") is not True:
        raise SystemExit("FAIL data-gap queue is not append-only")
    if data_gaps.get("safety") != EXPECTED_SAFETY:
        raise SystemExit("FAIL data-gap queue safety block mismatch")
    if data_gaps.get("synthetic_backfill_forbidden") is not True:
        raise SystemExit("FAIL data-gap queue permits synthetic backfill")
    if data_gaps.get("paid_private_or_licensed_requires_user_decision") is not True:
        raise SystemExit("FAIL data-gap queue can bypass user decision for paid/private/licensed sources")
    if data_gaps.get("source_priority") != ["official_free", "open_source_auditable", "community_auditable"]:
        raise SystemExit("FAIL data-gap source priority changed")

    items = data_gaps.get("items")
    if not isinstance(items, list) or not items:
        raise SystemExit("FAIL data-gap queue has no items")
    ids = [item.get("id") for item in items if isinstance(item, dict)]
    if len(ids) != len(items) or any(not isinstance(value, str) or not value for value in ids):
        raise SystemExit("FAIL data-gap queue contains invalid IDs")
    if len(set(ids)) != len(ids):
        raise SystemExit("FAIL duplicate data-gap IDs")

    gap_tracks = set()
    for item in items:
        track = item.get("track")
        if not isinstance(track, str) or not track:
            raise SystemExit("FAIL data-gap item missing track")
        if track in gap_tracks:
            raise SystemExit(f"FAIL duplicate data-gap track: {track}")
        gap_tracks.add(track)
        if not isinstance(item.get("issue"), int) or item.get("issue") <= 0:
            raise SystemExit(f"FAIL data-gap item has invalid issue: {track}")
        if track not in track_map:
            raise SystemExit(f"FAIL data-gap track missing from factory status: {track}")
        if track_map[track].get("classification") != "DATA_BLOCKED":
            raise SystemExit(f"FAIL data-gap track is not DATA_BLOCKED in factory status: {track}")
        if not item.get("gap_type") or not item.get("status") or not item.get("next_action"):
            raise SystemExit(f"FAIL incomplete data-gap metadata: {track}")
        if not isinstance(item.get("candidate_sources"), list) or not item.get("candidate_sources"):
            raise SystemExit(f"FAIL data-gap item has no candidate sources: {track}")
        if not isinstance(item.get("provenance_requirements"), list) or not item.get("provenance_requirements"):
            raise SystemExit(f"FAIL data-gap item has no provenance requirements: {track}")
        if not isinstance(item.get("qa_requirements"), list) or not item.get("qa_requirements"):
            raise SystemExit(f"FAIL data-gap item has no QA requirements: {track}")

    blocked_tracks = {
        track for track, meta in track_map.items()
        if isinstance(meta, dict) and meta.get("classification") == "DATA_BLOCKED"
    }
    if gap_tracks != blocked_tracks:
        missing_gaps = sorted(blocked_tracks - gap_tracks)
        stale_gaps = sorted(gap_tracks - blocked_tracks)
        raise SystemExit(f"FAIL data-gap/status drift missing={missing_gaps} stale={stale_gaps}")

    print("PASS factory v5 shadow machine is ledger-bound, freshness-guarded, fail-closed, non-invasive and DATA_BLOCKED queue-synchronized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
