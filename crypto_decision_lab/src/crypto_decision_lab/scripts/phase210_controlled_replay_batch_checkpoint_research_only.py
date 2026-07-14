from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    ROOT,
    locks_copy,
    read_json,
    stable_digest,
    write_json,
    write_markdown,
)


def build_phase210(
    phase206_artifact: Path,
    phase207_artifact: Path,
    phase208_artifact: Path,
    phase209_artifact: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phases = [
        read_json(phase206_artifact),
        read_json(phase207_artifact),
        read_json(phase208_artifact),
        read_json(phase209_artifact),
    ]
    checks = {
        "dataset_contract": phases[0]["contract_passed"],
        "window_builder": phases[1]["window_builder_passed"],
        "missing_data_policy": phases[2]["missing_data_policy_passed"],
        "historical_replay": phases[3]["historical_replay_passed"],
        "deterministic_replay": phases[3]["deterministic_replay"],
    }
    passed = all(checks.values())

    payload = {
        "phase": 210,
        "status": (
            "CONTROLLED_REPLAY_BATCH_CHECKPOINT_PASS_RESEARCH_ONLY"
            if passed
            else "NEEDS_REVIEW"
        ),
        "checkpoint_passed": passed,
        "checks": checks,
        "phase_chain_digest": stable_digest(
            {
                "phase206": phases[0]["dataset"]["dataset_digest"],
                "phase207": phases[1]["window_manifest_digest"],
                "phase208": phases[2]["audit"],
                "phase209": phases[3]["replay_digest"],
            }
        ),
        "classification": (
            "CONTROLLED_REPLAY_PIPELINE_READY_RESEARCH_ONLY"
            if passed
            else "INSUFFICIENT_CONTROLLED_REPLAY_EVIDENCE"
        ),
        "interpretation": (
            "The 206-209 pipeline is mechanically coherent. "
            "No data-trust approval, predictive validity or decision "
            "permission is granted."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)

    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 210 - Controlled Replay Batch Checkpoint",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Classification:** `{payload['classification']}`",
                f"**Phase-chain digest:** `{payload['phase_chain_digest']}`",
                "",
                "The checkpoint confirms research pipeline mechanics only.",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase206-artifact", type=Path, required=True)
    parser.add_argument("--phase207-artifact", type=Path, required=True)
    parser.add_argument("--phase208-artifact", type=Path, required=True)
    parser.add_argument("--phase209-artifact", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()

    payload = build_phase210(
        args.phase206_artifact,
        args.phase207_artifact,
        args.phase208_artifact,
        args.phase209_artifact,
        args.artifact,
        args.documentation,
    )
    print("PHASE210:", payload["status"])
    return 0 if payload["checkpoint_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
