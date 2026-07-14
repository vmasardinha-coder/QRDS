from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .phase199_205_research_batch_common import LOCKS, load_json, require_phase, utc_now, write_json, write_text
from .phase201_deterministic_shadow_replay_harness_research_only import replay_events


def build_phase202(replay_path: Path, output_dir: Path, documentation_path: Path | None = None, runs: int = 3) -> dict[str, Any]:
    source = load_json(replay_path)
    require_phase(source, 201)
    events = source["input_events"]
    run_results = [replay_events(events) for _ in range(runs)]
    checksums = [item["replay_checksum"] for item in run_results]
    states = [item["final_state"] for item in run_results]
    traces = [item["trace"] for item in run_results]
    reproducible = len(set(checksums)) == 1 and all(state == states[0] for state in states) and all(trace == traces[0] for trace in traces)

    payload = {
        "schema": "qrds.phase202.replay_reproducibility.v1",
        "phase": 202,
        "phase_status": "PASS_RESEARCH_ONLY" if reproducible else "NEEDS_REVIEW_RESEARCH_ONLY",
        "audit_status": "REPLAY_REPRODUCIBILITY_AUDIT_READY_RESEARCH_ONLY",
        "generated_at": utc_now(),
        "run_count": runs,
        "checksums": checksums,
        "unique_checksum_count": len(set(checksums)),
        "final_states": states,
        "trace_lengths": [len(trace) for trace in traces],
        "reproducible": reproducible,
        "snapshot_stable": reproducible,
        "reproducibility_validated": reproducible,
        "data_trust_validated": False,
        "valid_for_decision": False,
        "operational_use_allowed": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "next_stage": "PHASE_203_LEAKAGE_CAUSALITY_TIME_ORDER_AUDIT_RESEARCH_ONLY",
        "locks": LOCKS,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase202_replay_snapshot_reproducibility_audit.json", payload)
    if documentation_path:
        write_text(documentation_path, "\n".join([
            "# Phase 202 - Replay Snapshot and Reproducibility Audit",
            "",
            f"**Status:** `{payload['phase_status']}`",
            "",
            f"- Runs: `{runs}`",
            f"- Unique checksums: `{payload['unique_checksum_count']}`",
            f"- Reproducible: `{reproducible}`",
            f"- Stable snapshot: `{payload['snapshot_stable']}`",
            "",
            "Reproducibility does not establish predictive validity.",
            "",
            "```text",
            "data_trust_validated: False",
            "valid_for_decision: False",
            "operational_status: BLOCKED_RESEARCH_ONLY",
            "```",
        ]))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--documentation-path", type=Path, required=True)
    args = parser.parse_args()
    payload = build_phase202(args.replay_path, args.output_dir, args.documentation_path)
    print("PHASE202_REPRODUCIBILITY_AUDIT: PASS" if payload["reproducible"] else "PHASE202_REPRODUCIBILITY_AUDIT: NEEDS_REVIEW")
    print("Runs:", payload["run_count"])
    print("Unique checksums:", payload["unique_checksum_count"])
    return 0 if payload["reproducible"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
