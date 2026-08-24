#!/usr/bin/env python3
"""Fail-closed validator for QRDS factory contracts and shadow runner state."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED_JSON = [
    "MASTER_STATE.json",
    "QUEUES.json",
    "TRANSITION_CONTRACT.v1.json",
    "READ_ADAPTER_CONTRACT.v1.json",
    "PARITY_DRYRUN_CONTRACT.v1.json",
    "FACTORY_REPORT_SCHEMA.v1.json",
    "FAMILY_FLOW_CONTRACT.v1.json",
    "FACTORY_STATUS_LATEST.json",
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
    "alter_workflow_or_schedule": True,
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
    runner = ROOT / "run_factory.py"
    if not runner.is_file():
        raise SystemExit("FAIL missing shadow runner: run_factory.py")

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
    if activation.get("shadow_runner_enabled") is not True:
        raise SystemExit("FAIL shadow runner is not enabled")
    for key in ("active_path_rollout_enabled", "replace_daily_collection", "redirect_runtime_pointer", "alter_workflow_or_schedule", "engine_feed"):
        if activation.get(key) is not False:
            raise SystemExit(f"FAIL unsafe activation setting: {key}")
    if activation.get("orders") != 0 or activation.get("real_capital") != 0:
        raise SystemExit("FAIL shadow activation permits orders/capital")

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
    required_false = [
        "active_workflows_mutated",
        "active_ledgers_mutated",
        "runtime_pointers_mutated",
        "parameters_or_clocks_mutated",
        "backfill_performed",
        "partial_holdout_economics_read",
    ]
    if any(non_interference.get(k) is not False for k in required_false):
        raise SystemExit("FAIL non-interference assertion is incomplete or unsafe")
    if non_interference.get("write_prefix") != "tools/gate_btc_factory/":
        raise SystemExit("FAIL write boundary escaped factory namespace")

    track_map = status.get("track_map", {})
    if not track_map:
        raise SystemExit("FAIL factory cycle contains no families/tracks")
    if status.get("queue_counts", {}).get("total_tracks") != len(track_map):
        raise SystemExit("FAIL queue total does not match track map")

    print("PASS factory v3 shadow runner is active, fail-closed and non-invasive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
