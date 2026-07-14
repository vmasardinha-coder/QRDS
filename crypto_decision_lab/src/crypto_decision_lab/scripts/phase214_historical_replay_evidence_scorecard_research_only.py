from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    ROOT,
    locks_copy,
    read_json,
    write_json,
    write_markdown,
)


def build_phase214(
    phase206_artifact: Path,
    phase207_artifact: Path,
    phase208_artifact: Path,
    phase209_artifact: Path,
    phase210_artifact: Path,
    phase211_artifact: Path,
    phase212_artifact: Path,
    phase213_artifact: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    p206 = read_json(phase206_artifact)
    p207 = read_json(phase207_artifact)
    p208 = read_json(phase208_artifact)
    p209 = read_json(phase209_artifact)
    p210 = read_json(phase210_artifact)
    p211 = read_json(phase211_artifact)
    p212 = read_json(phase212_artifact)
    p213 = read_json(phase213_artifact)

    components = {
        "dataset_contract": {
            "weight": 15,
            "passed": p206["contract_passed"],
        },
        "window_determinism": {
            "weight": 15,
            "passed": p207["window_builder_passed"],
        },
        "missing_data_policy": {
            "weight": 10,
            "passed": p208["missing_data_policy_passed"],
        },
        "deterministic_replay": {
            "weight": 15,
            "passed": p209["deterministic_replay"],
        },
        "batch_checkpoint": {
            "weight": 10,
            "passed": p210["checkpoint_passed"],
        },
        "causality_detector": {
            "weight": 15,
            "passed": p211["counterfactual_audit_passed"],
        },
        "window_stability_coverage": {
            "weight": 10,
            "passed": p212["stability_audit_passed"],
        },
        "regime_coverage": {
            "weight": 10,
            "passed": p213["regime_segmentation_passed"],
        },
    }
    score = sum(
        item["weight"]
        for item in components.values()
        if item["passed"]
    )
    evidence_ready = score >= 70

    payload = {
        "phase": 214,
        "status": (
            "HISTORICAL_REPLAY_EVIDENCE_SCORECARD_READY_RESEARCH_ONLY"
            if evidence_ready
            else "NEEDS_REVIEW"
        ),
        "evidence_scorecard_passed": evidence_ready,
        "score": score,
        "maximum_score": 100,
        "components": components,
        "classification": (
            "CONTROLLED_HISTORICAL_REPLAY_EVIDENCE_NO_EDGE"
            if evidence_ready
            else "INSUFFICIENT_CONTROLLED_REPLAY_EVIDENCE"
        ),
        "caps": {
            "data_trust_validated": False,
            "predictive_validity_established": False,
            "edge_validated": False,
            "decision_layer_allowed": False,
            "promotion_allowed": False,
        },
        "interpretation": (
            "The scorecard rates control quality for replay research. "
            "It is explicitly capped below data-trust approval, "
            "predictive validity, edge validation and decision readiness."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)

    lines = [
        "# Phase 214 - Historical Replay Evidence Scorecard",
        "",
        f"**Status:** `{payload['status']}`",
        f"**Score:** `{score}/100`",
        f"**Classification:** `{payload['classification']}`",
        "",
        "| Component | Weight | Passed |",
        "|---|---:|---:|",
    ]
    for name, item in components.items():
        lines.append(
            f"| {name} | {item['weight']} | {item['passed']} |"
        )
    lines.extend(
        [
            "",
            "The score is a research-control score only. It does not "
            "measure expected return and cannot authorize trading.",
            "",
            "```text",
            "data_trust_validated: False",
            "predictive_validity_established: False",
            "edge_validated: False",
            "decision_layer_allowed: False",
            "```",
        ]
    )
    write_markdown(documentation_path, "\n".join(lines))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    for phase in range(206, 214):
        parser.add_argument(
            f"--phase{phase}-artifact",
            type=Path,
            required=True,
        )
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()

    payload = build_phase214(
        args.phase206_artifact,
        args.phase207_artifact,
        args.phase208_artifact,
        args.phase209_artifact,
        args.phase210_artifact,
        args.phase211_artifact,
        args.phase212_artifact,
        args.phase213_artifact,
        args.artifact,
        args.documentation,
    )
    print("PHASE214:", payload["status"])
    print("Score:", payload["score"])
    print("Classification:", payload["classification"])
    return 0 if payload["evidence_scorecard_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
