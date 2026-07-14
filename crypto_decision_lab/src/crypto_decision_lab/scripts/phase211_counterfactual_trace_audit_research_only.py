from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    ROOT,
    locks_copy,
    parse_timestamp,
    read_json,
    write_json,
    write_markdown,
)


def count_causality_violations(
    traces: list[dict[str, Any]],
) -> int:
    violations = 0
    for trace in traces:
        feature_time = parse_timestamp(trace["feature_timestamp"])
        target_time = parse_timestamp(trace["target_timestamp"])
        if (
            feature_time is None
            or target_time is None
            or feature_time >= target_time
        ):
            violations += 1
    return violations


def build_phase211(
    phase209_artifact: Path,
    phase210_artifact: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phase209 = read_json(phase209_artifact)
    phase210 = read_json(phase210_artifact)
    traces = [
        trace
        for result in phase209["results"]
        for trace in result["traces"]
    ]
    normal_violations = count_causality_violations(traces)

    injected = []
    for trace in traces[: min(10, len(traces))]:
        counterfactual = dict(trace)
        counterfactual["feature_timestamp"] = trace["target_timestamp"]
        injected.append(counterfactual)

    injected_violations = count_causality_violations(injected)
    detector_passed = bool(
        phase210["checkpoint_passed"]
        and traces
        and normal_violations == 0
        and injected
        and injected_violations == len(injected)
    )

    payload = {
        "phase": 211,
        "status": (
            "COUNTERFACTUAL_CAUSALITY_AUDIT_PASS_RESEARCH_ONLY"
            if detector_passed
            else "NEEDS_REVIEW"
        ),
        "counterfactual_audit_passed": detector_passed,
        "trace_count": len(traces),
        "normal_causality_violations": normal_violations,
        "injected_counterfactual_count": len(injected),
        "injected_violations_detected": injected_violations,
        "detector_recall_on_injected_fixture": (
            injected_violations / len(injected) if injected else 0.0
        ),
        "interpretation": (
            "The audit demonstrates that the replay trace rejects injected "
            "same-time/future leakage. It does not prove model edge."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)

    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 211 - Counterfactual Trace Audit",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Normal violations:** `{normal_violations}`",
                f"**Injected cases:** `{len(injected)}`",
                f"**Injected violations detected:** `{injected_violations}`",
                "",
                "The detector caught the deliberately injected causal "
                "violations. This is a leakage-control result, not evidence "
                "of profitable forecasting.",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase209-artifact", type=Path, required=True)
    parser.add_argument("--phase210-artifact", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()

    payload = build_phase211(
        args.phase209_artifact,
        args.phase210_artifact,
        args.artifact,
        args.documentation,
    )
    print("PHASE211:", payload["status"])
    return 0 if payload["counterfactual_audit_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
