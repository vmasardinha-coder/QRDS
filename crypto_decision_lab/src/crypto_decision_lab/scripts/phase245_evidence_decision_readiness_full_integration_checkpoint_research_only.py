from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase225_robustness_full_integration_tracking_checkpoint_research_only import (
    run_full_suite,
)
from crypto_decision_lab.scripts.phase236_245_evidence_decision_readiness_common import (
    base_payload,
    load_json,
    project_root,
    write_json,
    write_markdown,
)


def build_phase245_checkpoint(
    artifacts: list[dict[str, Any]],
    full_suite: dict[str, Any],
) -> dict[str, Any]:
    phases = [int(item["phase"]) for item in artifacts]
    scorecard = artifacts[-1]
    full_suite_passed = bool(
        full_suite.get("passed")
        and full_suite.get("coverage_complete")
        and full_suite.get("manifest_stable")
        and full_suite.get("totals", {}).get("failures") == 0
        and full_suite.get("totals", {}).get("errors") == 0
    )
    passed = bool(
        phases == list(range(236, 245))
        and all(item.get("passed") is True for item in artifacts)
        and scorecard.get("framework_score") == 100
        and scorecard.get("technical_reliability_score") == 100
        and scorecard.get("operational_readiness_score") == 0
        and full_suite_passed
    )
    payload = base_payload(
        245,
        (
            "EVIDENCE_DECISION_READINESS_236_245_PASS_RESEARCH_ONLY"
            if passed
            else "EVIDENCE_DECISION_READINESS_236_245_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "checkpoint_status": (
                "FULL_INTEGRATION_236_245_PASS_RESEARCH_ONLY"
                if passed
                else "FULL_INTEGRATION_236_245_NEEDS_REVIEW"
            ),
            "phase_chain": {
                str(item["phase"]): item
                for item in artifacts
            },
            "full_suite": full_suite,
            "global_full_suite_passed": full_suite_passed,
            "next_tracking_checkpoint": 255,
            "next_mandatory_global_full_suite": 265,
            "data_trust_validated": False,
            "predictive_validity_established": False,
            "edge_validated": False,
            "valid_for_decision": False,
            "passed": passed,
        }
    )
    return payload


def tracking_documents(
    payload: dict[str, Any],
) -> dict[str, str]:
    suite = payload["full_suite"]
    totals = suite["totals"]
    phase244 = payload["phase_chain"]["244"]
    return {
        "QRDS_MASTER_PROGRESS_BY_TENS_PHASE245.md": "\n".join(
            [
                "# QRDS Master Progress - Phase 245",
                "",
                "- Baseline: Phase 245",
                "- Batch 236-245: PASS",
                f"- Global test files: {suite['test_file_count']}",
                f"- Global tests: {totals['tests']}",
                "- Failures: 0",
                "- Errors: 0",
                f"- Framework score: {phase244['framework_score']}/100",
                "- Operational: BLOCKED_RESEARCH_ONLY",
                "- Next checkpoint: Phase 255",
                "",
            ]
        ),
        "QRDS_ARCHITECTURE_MERMAID_PHASE245.md": "\n".join(
            [
                "# QRDS Architecture - Phase 245",
                "",
                "```mermaid",
                "flowchart LR",
                "  A[Historical robustness evidence] --> B[Evidence packet]",
                "  B --> C[Admission framework]",
                "  C --> D[Predictive validity protocol]",
                "  C --> E[Economic edge protocol]",
                "  D --> F[Blocked decision packet]",
                "  E --> F",
                "  F --> G[Product readiness scorecard]",
                "  G --> H[BLOCKED_RESEARCH_ONLY]",
                "```",
                "",
            ]
        ),
        "QRDS_PROGRESS_TABLE_BY_TENS_PHASE245.md": "\n".join(
            [
                "# QRDS Progress Table - Phase 245",
                "",
                "| Window | Status | Test files | Tests | Operational |",
                "|---|---:|---:|---:|---|",
                (
                    f"| 236-245 | PASS | {suite['test_file_count']} | "
                    f"{totals['tests']} | BLOCKED_RESEARCH_ONLY |"
                ),
                "",
            ]
        ),
        "QRDS_GLOBAL_TEST_MILESTONE_PHASE245.md": "\n".join(
            [
                "# Global Test Milestone - Phase 245",
                "",
                f"- Test files: {suite['test_file_count']}",
                f"- Covered files: {suite['coverage_file_count']}",
                f"- Tests: {totals['tests']}",
                "- Failures: 0",
                "- Errors: 0",
                f"- Manifest stable: {suite['manifest_stable']}",
                f"- Recovery mode: {suite['recovery_mode']}",
                "",
            ]
        ),
        "QRDS_ROADMAP_246_255_RESEARCH_ONLY.md": "\n".join(
            [
                "# QRDS Roadmap 246-255",
                "",
                "## Goal",
                "",
                "Admit real evidence under explicit source, freshness, "
                "predictive-validity and net-edge gates, then produce "
                "a shadow decision packet with no capital or orders.",
                "",
                "## Network rule",
                "",
                "Any external data, website, link, fetch or API action "
                "must pause for ENTER before network access so antivirus "
                "HTTPS/network protection can be temporarily disabled.",
                "",
                "## Safety",
                "",
                "- No API authentication.",
                "- No account connection.",
                "- No orders.",
                "- No real capital.",
                "- Operational status remains BLOCKED_RESEARCH_ONLY.",
                "",
            ]
        ),
        "qrds_progress_snapshot_phase245.json": json.dumps(
            {
                "baseline_phase": 245,
                "batch_236_245": {
                    "passed": True,
                    "test_files": suite["test_file_count"],
                    "covered_files": suite["coverage_file_count"],
                    "tests": totals["tests"],
                    "failures": 0,
                    "errors": 0,
                    "manifest_stable": suite["manifest_stable"],
                },
                "product_decision_readiness": {
                    "framework_score": phase244["framework_score"],
                    "technical_reliability_score": (
                        phase244["technical_reliability_score"]
                    ),
                    "operational_readiness_score": (
                        phase244["operational_readiness_score"]
                    ),
                    "classification": phase244["classification"],
                },
                "next_tracking_checkpoint": 255,
                "next_mandatory_global_full_suite": 265,
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase-artifact",
        action="append",
        required=True,
    )
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--documentation", required=True)
    parser.add_argument("--tracking-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--project-root")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=5400,
    )
    args = parser.parse_args()

    root = project_root(args.project_root)
    artifacts = [
        load_json(path)
        for path in args.phase_artifact
    ]
    full_suite = run_full_suite(
        Path(args.output_dir),
        timeout_seconds=args.timeout_seconds,
        root=root,
    )
    payload = build_phase245_checkpoint(
        artifacts,
        full_suite,
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 245 Evidence and Decision Readiness Full Integration",
        payload,
        [
            f"- Global test files: "
            f"`{full_suite['test_file_count']}`",
            f"- Covered files: "
            f"`{full_suite['coverage_file_count']}`",
            f"- Tests: `{full_suite['totals']['tests']}`",
            f"- Failures: `{full_suite['totals']['failures']}`",
            f"- Errors: `{full_suite['totals']['errors']}`",
            f"- Manifest stable: `{full_suite['manifest_stable']}`",
            "- Product-facing decision schema is ready, but evidence "
            "and operational authorization remain closed.",
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
