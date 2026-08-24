#!/usr/bin/env python3
"""Fail-closed validator for QRDS factory contracts.

This script reads only files inside tools/gate_btc_factory. It does not access runtime,
workflows, collectors, ledgers, reports, network resources, secrets, or economics.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = [
    "MASTER_STATE.json",
    "QUEUES.json",
    "TRANSITION_CONTRACT.v1.json",
    "READ_ADAPTER_CONTRACT.v1.json",
    "PARITY_DRYRUN_CONTRACT.v1.json",
    "FACTORY_REPORT_SCHEMA.v1.json",
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
}


def load(name: str):
    path = ROOT / name
    if not path.is_file():
        raise SystemExit(f"FAIL missing required factory file: {name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # fail closed
        raise SystemExit(f"FAIL invalid JSON {name}: {exc}") from exc


def walk(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key, value
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def main() -> int:
    docs = {name: load(name) for name in REQUIRED_FILES}

    safety_seen = False
    for doc in docs.values():
        for key in ("global_mode", "global_safety_required", "safety"):
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
    forbidden = set(adapter.get("forbidden_operations", []))
    mandatory_forbidden = {
        "WRITE_ACTIVE_RUNTIME",
        "WRITE_EXISTING_LEDGER",
        "ALTER_WORKFLOW",
        "ALTER_SCHEDULE",
        "ALTER_COLLECTOR",
        "READ_PARTIAL_BLIND_HOLDOUT_ECONOMICS",
    }
    missing = sorted(mandatory_forbidden - forbidden)
    if missing:
        raise SystemExit(f"FAIL adapter contract missing prohibitions: {missing}")

    parity = docs["PARITY_DRYRUN_CONTRACT.v1.json"]
    if parity.get("activation_allowed") is not False:
        raise SystemExit("FAIL parity contract permits activation")
    dry = parity.get("dry_run_rules", {})
    if dry.get("mutate_existing_sources") is not False or dry.get("replace_daily_collection") is not False:
        raise SystemExit("FAIL parity dry-run can mutate/replace active sources")

    print("PASS factory contracts are internally safe and non-invasive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
