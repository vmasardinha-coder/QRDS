from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from .phase199_205_research_batch_common import LOCKS, sha256_json, utc_now, write_json, write_text


def parse_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def replay_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    state = {"event_count": 0, "numeric_value_sum": 0.0, "last_timestamp": None}
    trace = []
    for sequence, event in enumerate(events):
        timestamp = str(event["timestamp"])
        parse_time(timestamp)
        numeric_values = [
            float(value)
            for key, value in event.items()
            if key not in {"timestamp", "source_id"} and isinstance(value, (int, float)) and not isinstance(value, bool)
        ]
        state["event_count"] += 1
        state["numeric_value_sum"] = round(state["numeric_value_sum"] + sum(numeric_values), 12)
        state["last_timestamp"] = timestamp
        trace.append({
            "sequence": sequence,
            "timestamp": timestamp,
            "source_id": event.get("source_id", "UNKNOWN"),
            "event_hash": sha256_json(event),
            "state_after": dict(state),
            "decision_emitted": False,
            "order_emitted": False,
        })
    return {
        "input_events": events,
        "trace": trace,
        "final_state": state,
        "replay_checksum": sha256_json({"events": events, "trace": trace, "state": state}),
    }


def default_events() -> list[dict[str, Any]]:
    return [
        {"timestamp": "2026-01-01T00:00:00Z", "source_id": "synthetic_a", "value": 100.0, "volume": 10.0},
        {"timestamp": "2026-01-01T00:01:00Z", "source_id": "synthetic_a", "value": 101.0, "volume": 12.0},
        {"timestamp": "2026-01-01T00:02:00Z", "source_id": "synthetic_b", "value": 99.5, "volume": 11.0},
        {"timestamp": "2026-01-01T00:03:00Z", "source_id": "synthetic_b", "value": 100.5, "volume": 9.0},
    ]


def build_phase201(output_dir: Path, documentation_path: Path | None = None) -> dict[str, Any]:
    replay = replay_events(default_events())
    payload = {
        "schema": "qrds.phase201.shadow_replay_harness.v1",
        "phase": 201,
        "phase_status": "PASS_RESEARCH_ONLY",
        "harness_status": "DETERMINISTIC_SHADOW_REPLAY_HARNESS_READY_RESEARCH_ONLY",
        "generated_at": utc_now(),
        **replay,
        "deterministic_contract": {
            "input_order_preserved": True,
            "hidden_sorting_allowed": False,
            "lookahead_allowed": False,
            "external_network_allowed": False,
            "authenticated_connection_allowed": False,
            "decision_emission_allowed": False,
            "order_emission_allowed": False,
            "canonical_write_allowed": False,
        },
        "shadow_replay_harness_ready": True,
        "reproducibility_validated": False,
        "causality_validated": False,
        "valid_for_decision": False,
        "operational_use_allowed": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "next_stage": "PHASE_202_REPLAY_SNAPSHOT_REPRODUCIBILITY_AUDIT_RESEARCH_ONLY",
        "locks": LOCKS,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase201_deterministic_shadow_replay_harness.json", payload)
    if documentation_path:
        write_text(documentation_path, "\n".join([
            "# Phase 201 - Deterministic Shadow Replay Harness",
            "",
            "**Status:** `PASS_RESEARCH_ONLY`",
            "",
            f"- Events replayed: `{payload['final_state']['event_count']}`",
            f"- Replay checksum: `{payload['replay_checksum']}`",
            "- Decisions emitted: `0`",
            "- Orders emitted: `0`",
            "",
            "The harness validates deterministic state evolution only.",
            "",
            "```text",
            "operational_status: BLOCKED_RESEARCH_ONLY",
            "valid_for_decision: False",
            "canonical_data_writes: 0",
            "```",
        ]))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--documentation-path", type=Path, required=True)
    args = parser.parse_args()
    payload = build_phase201(args.output_dir, args.documentation_path)
    print("PHASE201_SHADOW_REPLAY_HARNESS: PASS")
    print("Events:", payload["final_state"]["event_count"])
    print("Checksum:", payload["replay_checksum"])
    print("Decisions emitted: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
