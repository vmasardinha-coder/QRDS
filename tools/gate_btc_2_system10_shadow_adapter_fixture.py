#!/usr/bin/env python3
"""Deterministic System 10 shadow-adapter fixture.

Exercises the complete read-only transformation path from a verified event envelope
through the Nautilus shadow adapter contract into a parity receipt. No Nautilus
engine is imported or instantiated.
"""
from __future__ import annotations

from typing import Any

from tools.gate_btc_2_system10_adapter_contract import project_adapter_events, verify_adapter_contract
from tools.gate_btc_2_system10_event_envelope import verify_event_envelope
from tools.gate_btc_2_system10_parity_receipt import build_parity_receipt, verify_parity_receipt


def run_shadow_adapter_fixture(envelope: dict[str, Any]) -> dict[str, Any]:
    verify_event_envelope(envelope)
    contract = project_adapter_events(envelope, "NAUTILUS_SHADOW_ADAPTER")
    verify_adapter_contract(contract)
    receipt = build_parity_receipt(envelope, "NAUTILUS_SHADOW_ADAPTER", contract["adapter_events"])
    verify_parity_receipt(receipt)
    return {
        "status": "PASS_READ_ONLY_PARITY_FIXTURE",
        "adapter_name": "NAUTILUS_SHADOW_ADAPTER",
        "source_envelope_sha256": envelope["envelope_sha256"],
        "adapter_contract_sha256": contract["contract_sha256"],
        "parity_receipt_sha256": receipt["receipt_sha256"],
        "event_count": envelope["event_count"],
        "engine_instantiated": False,
        "engine_execution": False,
        "nautilus_execution_enabled": False,
        "stage_9_complete": False,
        "system_10_complete": False,
        "economics_allowed": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
    }
