from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from .phase199_205_research_batch_common import LOCKS, load_json, require_phase, utc_now, write_json, write_text


def parse_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def audit_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    sequence_violations = 0
    time_order_violations = 0
    future_access_violations = 0
    previous_time: datetime | None = None
    for expected_sequence, item in enumerate(trace):
        if item.get("sequence") != expected_sequence:
            sequence_violations += 1
        current_time = parse_time(str(item["timestamp"]))
        if previous_time is not None and current_time < previous_time:
            time_order_violations += 1
        previous_time = current_time
        consumed = item.get("consumed_through_index", expected_sequence)
        lookahead = item.get("lookahead_index", expected_sequence)
        if consumed > expected_sequence or lookahead > expected_sequence:
            future_access_violations += 1
    total = sequence_violations + time_order_violations + future_access_violations
    return {
        "trace_length": len(trace),
        "sequence_violations": sequence_violations,
        "time_order_violations": time_order_violations,
        "future_access_violations": future_access_violations,
        "total_violations": total,
        "causality_passed": total == 0,
    }


def build_phase203(replay_path: Path, reproducibility_path: Path, output_dir: Path, documentation_path: Path | None = None) -> dict[str, Any]:
    replay = load_json(replay_path)
    reproducibility = load_json(reproducibility_path)
    require_phase(replay, 201)
    require_phase(reproducibility, 202)
    audit = audit_trace(replay["trace"])
    payload = {
        "schema": "qrds.phase203.causality_audit.v1",
        "phase": 203,
        "phase_status": "PASS_RESEARCH_ONLY" if audit["causality_passed"] else "NEEDS_REVIEW_RESEARCH_ONLY",
        "audit_status": "LEAKAGE_CAUSALITY_TIME_ORDER_AUDIT_READY_RESEARCH_ONLY",
        "generated_at": utc_now(),
        "trace_audit": audit,
        "reproducibility_dependency_passed": reproducibility.get("reproducible") is True,
        "causality_audit_passed": audit["causality_passed"],
        "lookahead_detected": audit["future_access_violations"] > 0,
        "data_leakage_validated_absent_for_trace": audit["future_access_violations"] == 0,
        "predictive_validity_established": False,
        "data_trust_validated": False,
        "valid_for_decision": False,
        "operational_use_allowed": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "next_stage": "PHASE_204_SHADOW_REPLAY_EVIDENCE_SCORECARD_RESEARCH_ONLY",
        "locks": LOCKS,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase203_leakage_causality_time_order_audit.json", payload)
    if documentation_path:
        write_text(documentation_path, "\n".join([
            "# Phase 203 - Leakage, Causality and Time-Order Audit",
            "",
            f"**Status:** `{payload['phase_status']}`",
            "",
            f"- Trace events: `{audit['trace_length']}`",
            f"- Sequence violations: `{audit['sequence_violations']}`",
            f"- Time-order violations: `{audit['time_order_violations']}`",
            f"- Future-access violations: `{audit['future_access_violations']}`",
            f"- Causality passed: `{audit['causality_passed']}`",
            "",
            "This audit applies only to the deterministic shadow trace.",
            "",
            "```text",
            "predictive_validity_established: False",
            "valid_for_decision: False",
            "operational_status: BLOCKED_RESEARCH_ONLY",
            "```",
        ]))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-path", type=Path, required=True)
    parser.add_argument("--reproducibility-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--documentation-path", type=Path, required=True)
    args = parser.parse_args()
    payload = build_phase203(args.replay_path, args.reproducibility_path, args.output_dir, args.documentation_path)
    print("PHASE203_CAUSALITY_AUDIT: PASS" if payload["causality_audit_passed"] else "PHASE203_CAUSALITY_AUDIT: NEEDS_REVIEW")
    print("Violations:", payload["trace_audit"]["total_violations"])
    return 0 if payload["causality_audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
