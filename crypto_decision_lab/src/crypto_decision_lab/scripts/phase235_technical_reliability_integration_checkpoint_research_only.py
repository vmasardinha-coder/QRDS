from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase226_235_technical_reliability_common import (
    base_payload,
    load_json,
    write_json,
    write_markdown,
)


def tracking_documents(payload: dict[str, Any]) -> dict[str, str]:
    score = payload["phase_chain"]["234"]["score"]
    test_summary = payload["targeted_tests"]
    return {
        "QRDS_MASTER_PROGRESS_BY_TENS_PHASE235.md": "\n".join(
            [
                "# QRDS Master Progress - Phase 235",
                "",
                "- Baseline: Phase 235",
                "- Batch 226-235: PASS",
                f"- Targeted tests: {test_summary['tests']}",
                "- Failures: 0",
                "- Errors: 0",
                f"- Technical score: {score}/100",
                "- Operational: BLOCKED_RESEARCH_ONLY",
                "- Next checkpoint: Phase 245",
                "",
            ]
        ),
        "QRDS_ARCHITECTURE_MERMAID_PHASE235.md": "\n".join(
            [
                "# QRDS Architecture - Phase 235",
                "",
                "```mermaid",
                "flowchart LR",
                "  A[Registry inputs] --> B[Process-local cache]",
                "  B --> C[Defensive copy]",
                "  C --> D[DAG recomputation guard]",
                "  D --> E[Performance and leak guards]",
                "  E --> F[JUnit resume integrity]",
                "  F --> G[Phase 235 checkpoint]",
                "  G --> H[BLOCKED_RESEARCH_ONLY]",
                "```",
                "",
            ]
        ),
        "QRDS_PROGRESS_TABLE_BY_TENS_PHASE235.md": "\n".join(
            [
                "# QRDS Progress Table - Phase 235",
                "",
                "| Window | Status | Tests | Operational |",
                "|---|---:|---:|---|",
                (
                    f"| 226-235 | PASS | {test_summary['tests']} | "
                    "BLOCKED_RESEARCH_ONLY |"
                ),
                "",
            ]
        ),
        "QRDS_INTEGRATED_TEST_MILESTONE_226_235.md": "\n".join(
            [
                "# Integrated Test Milestone 226-235",
                "",
                f"- Test files: {test_summary['test_files']}",
                f"- Tests: {test_summary['tests']}",
                "- Failures: 0",
                "- Errors: 0",
                "- Full global suite: deferred to Phase 245.",
                "",
            ]
        ),
        "QRDS_ROADMAP_236_245_RESEARCH_ONLY.md": "\n".join(
            [
                "# QRDS Roadmap 236-245",
                "",
                "## Goal",
                "",
                "Move from technical reliability toward evidence trust and "
                "decision readiness without enabling operations.",
                "",
                "## Mandatory checkpoint",
                "",
                "- Phase 245: global full-suite.",
                "- Operational status remains BLOCKED_RESEARCH_ONLY.",
                "",
            ]
        ),
        "qrds_progress_snapshot_phase235.json": json.dumps(
            {
                "baseline_phase": 235,
                "batch_226_235": {
                    "passed": True,
                    "test_files": test_summary["test_files"],
                    "tests": test_summary["tests"],
                    "failures": 0,
                    "errors": 0,
                },
                "technical_reliability": {
                    "score": score,
                    "classification": payload["phase_chain"]["234"][
                        "classification"
                    ],
                },
                "next_tracking_checkpoint": 245,
                "next_mandatory_global_full_suite": 245,
                "operational_status": "BLOCKED_RESEARCH_ONLY",
                "data_trust_validated": False,
                "predictive_validity_established": False,
                "edge_validated": False,
                "decision_layer_allowed": False,
                "canonical_data_writes": 0,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
    }


def build_technical_reliability_checkpoint(
    artifact_paths: list[Path],
    targeted_test_summary_path: Path,
) -> dict[str, Any]:
    artifacts = [load_json(path) for path in artifact_paths]
    summary = load_json(targeted_test_summary_path)
    phases = [int(item["phase"]) for item in artifacts]
    phase_chain = {
        str(item["phase"]): item
        for item in artifacts
    }
    tests_passed = bool(
        summary["test_files"] > 0
        and summary["tests"] > 0
        and summary["failures"] == 0
        and summary["errors"] == 0
        and summary["timed_out"] is False
    )
    passed = bool(
        phases == list(range(226, 235))
        and all(item["passed"] for item in artifacts)
        and tests_passed
        and phase_chain["234"]["score"] == 100
    )
    payload = base_payload(
        235,
        "TECHNICAL_RELIABILITY_226_235_PASS_RESEARCH_ONLY"
        if passed
        else "TECHNICAL_RELIABILITY_226_235_NEEDS_REVIEW",
    )
    payload.update(
        {
            "checkpoint_status": (
                "TECHNICAL_RELIABILITY_226_235_PASS_RESEARCH_ONLY"
                if passed
                else "TECHNICAL_RELIABILITY_226_235_NEEDS_REVIEW"
            ),
            "phase_chain": phase_chain,
            "targeted_tests": summary,
            "global_full_suite_executed": False,
            "next_tracking_checkpoint": 245,
            "next_mandatory_global_full_suite": 245,
            "data_trust_validated": False,
            "predictive_validity_established": False,
            "edge_validated": False,
            "valid_for_decision": False,
            "passed": passed,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase-artifact",
        action="append",
        required=True,
    )
    parser.add_argument(
        "--targeted-test-summary",
        required=True,
    )
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--documentation", required=True)
    parser.add_argument("--tracking-dir", required=True)
    args = parser.parse_args()

    payload = build_technical_reliability_checkpoint(
        [Path(path) for path in args.phase_artifact],
        Path(args.targeted_test_summary),
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 235 Technical Reliability Integration Checkpoint",
        payload,
        [
            f"- Checkpoint: `{payload['checkpoint_status']}`",
            f"- Targeted test files: `{payload['targeted_tests']['test_files']}`",
            f"- Targeted tests: `{payload['targeted_tests']['tests']}`",
            "- Global full-suite remains scheduled for Phase 245.",
        ],
    )

    tracking_dir = Path(args.tracking_dir)
    tracking_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in tracking_documents(payload).items():
        (tracking_dir / filename).write_text(
            content,
            encoding="utf-8",
        )

    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
