from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase216_225_robustness_common import (
    ROOT,
    locks_copy,
    phase_status,
    read_json,
    read_jsonl,
    research_caps,
    stable_digest,
    write_json,
    write_markdown,
)


def build_phase216(
    phase206_artifact: Path,
    phase209_artifact: Path,
    phase215_artifact: Path,
    dataset_path: Path,
    artifact_path: Path,
    documentation_path: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phase206 = read_json(phase206_artifact)
    phase209 = read_json(phase209_artifact)
    phase215 = read_json(phase215_artifact)
    rows = read_jsonl(dataset_path)

    required_checks = {
        "phase206_contract_passed": bool(phase206.get("contract_passed")),
        "phase209_replay_passed": bool(phase209.get("historical_replay_passed")),
        "phase215_integration_passed": bool(phase215.get("window_integration_passed")),
        "dataset_rows_match": len(rows) == int(phase206["dataset"]["row_count"]),
        "dataset_digest_match": stable_digest(rows) == phase206["dataset"]["dataset_digest"],
        "normalized_dataset_path_present": bool(
            phase206["dataset"].get("normalized_dataset_path")
        ),
        "source_mode_present": bool(phase206["dataset"].get("source_mode")),
        "replay_digest_present": bool(phase209.get("replay_digest")),
        "phase_chain_digest_present": bool(phase215.get("phase_chain_digest")),
        "research_locks_present": (
            phase215["locks"]["operational_status"] == "BLOCKED_RESEARCH_ONLY"
            and phase215["locks"]["canonical_data_writes"] == 0
        ),
    }
    complete_count = sum(required_checks.values())
    completeness_ratio = complete_count / len(required_checks)
    passed = completeness_ratio == 1.0

    payload = {
        "phase": 216,
        "status": phase_status(
            passed,
            "REPLAY_PROVENANCE_COMPLETENESS_AUDIT_PASS_RESEARCH_ONLY",
        ),
        "provenance_completeness_passed": passed,
        "checks": required_checks,
        "complete_checks": complete_count,
        "total_checks": len(required_checks),
        "completeness_ratio": completeness_ratio,
        "lineage_digest": stable_digest(
            {
                "dataset_digest": phase206["dataset"]["dataset_digest"],
                "replay_digest": phase209["replay_digest"],
                "phase215_chain": phase215["phase_chain_digest"],
            }
        ),
        "caps": research_caps(),
        "interpretation": (
            "The replay artifacts have complete internal provenance for this "
            "research chain. This does not validate external source truth, "
            "independent data agreement, predictive validity or financial edge."
        ),
        "locks": locks_copy(),
    }
    write_json(artifact_path, payload)
    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 216 - Replay Provenance Completeness Audit",
                "",
                f"**Status:** `{payload['status']}`",
                f"**Completeness:** `{complete_count}/{len(required_checks)}`",
                f"**Lineage digest:** `{payload['lineage_digest']}`",
                "",
                "Internal lineage is complete for the replay chain. External "
                "data truth and decision readiness remain unvalidated.",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase206-artifact", type=Path, required=True)
    parser.add_argument("--phase209-artifact", type=Path, required=True)
    parser.add_argument("--phase215-artifact", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    args = parser.parse_args()
    payload = build_phase216(
        args.phase206_artifact,
        args.phase209_artifact,
        args.phase215_artifact,
        args.dataset,
        args.artifact,
        args.documentation,
    )
    print("PHASE216:", payload["status"])
    print("Completeness:", payload["completeness_ratio"])
    return 0 if payload["provenance_completeness_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
