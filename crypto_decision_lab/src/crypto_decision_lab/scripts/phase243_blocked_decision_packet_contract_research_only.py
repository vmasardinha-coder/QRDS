from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase236_245_evidence_decision_readiness_common import (
    add_standard_output_arguments,
    base_payload,
    write_json,
    write_markdown,
)


DECISION_PACKET_FIELDS = [
    "asset",
    "market",
    "observation_time_utc",
    "evidence_fingerprint",
    "data_trust_status",
    "predictive_validity_status",
    "edge_status",
    "uncertainty",
    "action",
    "position_size",
    "entry",
    "exit",
    "stop",
    "reason_codes",
    "operational_status",
]


def build_blocked_decision_packet(
    *,
    asset: str = "UNSPECIFIED",
    market: str = "RESEARCH_ONLY",
) -> dict[str, Any]:
    return {
        "asset": asset,
        "market": market,
        "observation_time_utc": None,
        "evidence_fingerprint": None,
        "data_trust_status": "NOT_VALIDATED",
        "predictive_validity_status": "NOT_ESTABLISHED",
        "edge_status": "NOT_VALIDATED",
        "uncertainty": None,
        "action": "NO_ACTION_RESEARCH_ONLY",
        "position_size": 0,
        "entry": None,
        "exit": None,
        "stop": None,
        "reason_codes": [
            "DATA_TRUST_NOT_VALIDATED",
            "PREDICTIVE_VALIDITY_NOT_ESTABLISHED",
            "EDGE_NOT_VALIDATED",
        ],
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }


def build_blocked_decision_packet_contract(
    root: Path | None = None,
) -> dict[str, Any]:
    _ = root
    packet = build_blocked_decision_packet()
    fields_complete = list(packet) == DECISION_PACKET_FIELDS
    safe_action = packet["action"] == "NO_ACTION_RESEARCH_ONLY"
    no_position = packet["position_size"] == 0
    no_execution_levels = all(
        packet[key] is None
        for key in ("entry", "exit", "stop")
    )
    passed = bool(
        fields_complete
        and safe_action
        and no_position
        and no_execution_levels
    )
    payload = base_payload(
        243,
        (
            "BLOCKED_DECISION_PACKET_CONTRACT_PASS_RESEARCH_ONLY"
            if passed
            else "BLOCKED_DECISION_PACKET_CONTRACT_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "decision_packet_fields": DECISION_PACKET_FIELDS,
            "sample_packet": packet,
            "fields_complete": fields_complete,
            "no_action_enforced": safe_action,
            "zero_position_enforced": no_position,
            "execution_levels_absent": no_execution_levels,
            "passed": passed,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    add_standard_output_arguments(parser)
    args = parser.parse_args()
    payload = build_blocked_decision_packet_contract(
        Path(args.project_root) if args.project_root else None
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 243 Blocked Decision Packet Contract",
        payload,
        [
            f"- Decision packet fields: "
            f"`{len(payload['decision_packet_fields'])}`",
            "- Current action is hard-coded to "
            "`NO_ACTION_RESEARCH_ONLY`.",
            "- Position size is zero and entry/exit/stop are absent.",
            "- This is the product-facing decision schema without "
            "operational authorization.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
