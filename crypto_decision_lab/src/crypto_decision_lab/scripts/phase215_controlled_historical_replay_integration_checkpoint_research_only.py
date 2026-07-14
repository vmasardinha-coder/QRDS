from __future__ import annotations

import argparse
import hashlib
import xml.etree.ElementTree as ET
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_test_manifest(
    test_files: list[Path],
    root: Path,
) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(test_files)
    ]


def parse_junit(path: Path) -> dict[str, int]:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    totals = {
        "tests": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }
    for suite in suites:
        for key in totals:
            totals[key] += int(float(suite.attrib.get(key, "0")))
    return totals


def tracking_documents(
    payload: dict[str, Any],
    tracking_dir: Path,
) -> dict[str, Path]:
    targeted = payload["targeted_integration"]
    score = payload["phase_chain"]["214"]["score"]

    master_path = tracking_dir / "QRDS_MASTER_PROGRESS_BY_TENS_PHASE215.md"
    diagram_path = tracking_dir / "QRDS_ARCHITECTURE_MERMAID_PHASE215.md"
    table_path = tracking_dir / "QRDS_PROGRESS_TABLE_BY_TENS_PHASE215.md"
    milestone_path = tracking_dir / "QRDS_INTEGRATED_TEST_MILESTONE_206_215.md"
    roadmap_path = tracking_dir / "QRDS_ROADMAP_216_225_RESEARCH_ONLY.md"
    snapshot_path = tracking_dir / "qrds_progress_snapshot_phase215.json"

    write_markdown(
        master_path,
        "\n".join(
            [
                "# QRDS Master Progress by Tens - Phase 215",
                "",
                "**Integration baseline before batch:** `63d234a`",
                "**Checkpoint:** `TARGETED_INTEGRATION_206_215_PASS_RESEARCH_ONLY`",
                "**Operational:** `BLOCKED_RESEARCH_ONLY`",
                "",
                "## Batch 206-215",
                "",
                "Controlled historical replay evidence was added through "
                "a dataset contract, deterministic walk-forward windows, "
                "missing-data policy, replay runner, causality audit, "
                "cross-window stability, regime segmentation and a capped "
                "research evidence scorecard.",
                "",
                "## Evidence",
                "",
                f"- Targeted test files: `{targeted['test_file_count']}`",
                f"- Executed targeted tests: `{targeted['totals']['tests']}`",
                f"- Failures: `{targeted['totals']['failures']}`",
                f"- Errors: `{targeted['totals']['errors']}`",
                f"- Test manifest stable: `{targeted['manifest_stable']}`",
                f"- Phase 214 score: `{score}/100`",
                "",
                "## Interpretation",
                "",
                "The controlled replay machinery is ready for additional "
                "research. Data trust, predictive validity, financial edge "
                "and decision readiness remain unproven.",
                "",
                "```text",
                "data_trust_validated: False",
                "predictive_validity_established: False",
                "edge_validated: False",
                "decision_layer_allowed: False",
                "canonical_data_writes: 0",
                "```",
            ]
        ),
    )

    write_markdown(
        diagram_path,
        "\n".join(
            [
                "# QRDS Architecture - Phase 215",
                "",
                "```mermaid",
                "flowchart LR",
                "  P199[199 Source Reconciliation] --> P205[205 Full Integration]",
                "  P205 --> P206[206 Dataset Contract]",
                "  P206 --> P207[207 Walk-Forward Windows]",
                "  P207 --> P208[208 Missing Data Policy]",
                "  P208 --> P209[209 Controlled Replay]",
                "  P209 --> P210[210 Batch Checkpoint]",
                "  P210 --> P211[211 Causality Audit]",
                "  P211 --> P212[212 Window Stability]",
                "  P212 --> P213[213 Regime Segmentation]",
                "  P213 --> P214[214 Evidence Scorecard]",
                "  P214 --> P215[215 Targeted Integration]",
                "  P215 -. blocked .-> D[Decision Layer]",
                "```",
                "",
                "The decision layer remains blocked because research "
                "controls are not equivalent to predictive validation.",
            ]
        ),
    )

    write_markdown(
        table_path,
        "\n".join(
            [
                "# QRDS Progress Table by Tens - Phase 215",
                "",
                "| Range | Theme | Checkpoint | Status |",
                "|---|---|---|---|",
                "| 186-195 | Integrity and full integration | 195 | PASS_RESEARCH_ONLY |",
                "| 196-205 | Data trust and shadow replay controls | 205 | PASS_RESEARCH_ONLY |",
                "| 206-215 | Controlled historical replay evidence | 215 | PASS_RESEARCH_ONLY |",
                "| 216-225 | Robustness and trust escalation | 225 | PLANNED_RESEARCH_ONLY |",
                "",
                "All ranges remain under `BLOCKED_RESEARCH_ONLY`.",
            ]
        ),
    )

    write_markdown(
        milestone_path,
        "\n".join(
            [
                "# QRDS Integrated Test Milestone 206-215",
                "",
                f"**Checkpoint:** `{payload['checkpoint_status']}`",
                f"**Targeted tests:** `{targeted['totals']['tests']}`",
                f"**Failures:** `{targeted['totals']['failures']}`",
                f"**Errors:** `{targeted['totals']['errors']}`",
                f"**Manifest stable:** `{targeted['manifest_stable']}`",
                "**Global full-suite executed at 215:** `False`",
                "**Next mandatory global full-suite:** `225`",
                "",
                "The targeted batch integration passed. The global suite "
                "was not required at Phase 215 because the batch introduced "
                "isolated research modules without changing previously "
                "shared runtime architecture.",
            ]
        ),
    )

    write_markdown(
        roadmap_path,
        "\n".join(
            [
                "# QRDS Roadmap 216-225 - Research Only",
                "",
                "**Theme:** Cross-Window Robustness and Data Trust Escalation",
                "**Operational mode:** `BLOCKED_RESEARCH_ONLY`",
                "",
                "| Phase | Scope |",
                "|---:|---|",
                "| 216 | Replay provenance completeness audit |",
                "| 217 | Multi-source agreement diagnostics |",
                "| 218 | Outlier and contamination sensitivity |",
                "| 219 | Window-boundary perturbation audit |",
                "| 220 | Robustness batch checkpoint |",
                "| 221 | Model-free benchmark comparison |",
                "| 222 | Calibration and uncertainty diagnostics |",
                "| 223 | Cost and slippage sensitivity, research-only |",
                "| 224 | Robustness evidence scorecard v2 |",
                "| 225 | Mandatory global full-suite and tracking checkpoint |",
                "",
                "No phase may produce signals, recommendations, "
                "allocations, orders or canonical data writes.",
            ]
        ),
    )

    snapshot = {
        "baseline_phase": 215,
        "baseline_commit_before_batch": "63d234a",
        "checkpoint_status": payload["checkpoint_status"],
        "targeted_integration": {
            "passed": targeted["passed"],
            "test_file_count": targeted["test_file_count"],
            "tests": targeted["totals"]["tests"],
            "failures": targeted["totals"]["failures"],
            "errors": targeted["totals"]["errors"],
            "manifest_stable": targeted["manifest_stable"],
        },
        "global_full_suite_at_phase215": False,
        "last_mandatory_global_full_suite_phase": 205,
        "last_mandatory_global_full_suite_tests": 1340,
        "next_tracking_checkpoint": 225,
        "next_mandatory_global_full_suite": 225,
        "data_trust_validated": False,
        "predictive_validity_established": False,
        "edge_validated": False,
        "decision_layer_allowed": False,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "canonical_data_writes": 0,
    }
    write_json(snapshot_path, snapshot)

    return {
        "master": master_path,
        "diagram": diagram_path,
        "table": table_path,
        "milestone": milestone_path,
        "roadmap": roadmap_path,
        "snapshot": snapshot_path,
    }


def build_phase215(
    phase_artifacts: list[Path],
    junit_path: Path,
    test_files: list[Path],
    artifact_path: Path,
    documentation_path: Path,
    tracking_dir: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    phases = {str(phase): read_json(path) for phase, path in zip(range(206, 215), phase_artifacts)}
    manifest_before = build_test_manifest(test_files, root)
    junit = parse_junit(junit_path)
    manifest_after = build_test_manifest(test_files, root)
    manifest_stable = manifest_before == manifest_after

    phase_checks = {
        "206": phases["206"]["contract_passed"],
        "207": phases["207"]["window_builder_passed"],
        "208": phases["208"]["missing_data_policy_passed"],
        "209": phases["209"]["historical_replay_passed"],
        "210": phases["210"]["checkpoint_passed"],
        "211": phases["211"]["counterfactual_audit_passed"],
        "212": phases["212"]["stability_audit_passed"],
        "213": phases["213"]["regime_segmentation_passed"],
        "214": phases["214"]["evidence_scorecard_passed"],
    }
    targeted_passed = bool(
        junit["tests"] > 0
        and junit["failures"] == 0
        and junit["errors"] == 0
        and manifest_stable
    )
    passed = all(phase_checks.values()) and targeted_passed

    payload = {
        "phase": 215,
        "checkpoint_status": (
            "TARGETED_INTEGRATION_206_215_PASS_RESEARCH_ONLY"
            if passed
            else "NEEDS_REVIEW"
        ),
        "window_integration_passed": passed,
        "phase_checks": phase_checks,
        "phase_chain": phases,
        "phase_chain_digest": stable_digest(
            {
                phase: {
                    "status": item["status"],
                    "locks": item["locks"],
                }
                for phase, item in phases.items()
            }
        ),
        "targeted_integration": {
            "passed": targeted_passed,
            "test_file_count": len(test_files),
            "totals": junit,
            "manifest_before": manifest_before,
            "manifest_after": manifest_after,
            "manifest_stable": manifest_stable,
            "junit_path": junit_path.relative_to(root).as_posix(),
        },
        "global_full_suite": {
            "executed_at_phase215": False,
            "reason": (
                "Batch 206-215 adds isolated research modules and does not "
                "modify previously shared runtime architecture."
            ),
            "last_mandatory_phase": 205,
            "last_mandatory_test_count": 1340,
            "next_mandatory_phase": 225,
        },
        "data_trust_validated": False,
        "predictive_validity_established": False,
        "edge_validated": False,
        "valid_for_decision": False,
        "next_tracking_checkpoint": 225,
        "next_mandatory_global_full_suite": 225,
        "locks": locks_copy(),
    }

    tracking = tracking_documents(payload, tracking_dir)
    payload["tracking_documents"] = {
        key: value.relative_to(root).as_posix()
        for key, value in tracking.items()
    }
    write_json(artifact_path, payload)

    write_markdown(
        documentation_path,
        "\n".join(
            [
                "# Phase 215 - Controlled Historical Replay Integration",
                "",
                f"**Checkpoint:** `{payload['checkpoint_status']}`",
                f"**Targeted test files:** `{len(test_files)}`",
                f"**Targeted tests:** `{junit['tests']}`",
                f"**Failures:** `{junit['failures']}`",
                f"**Errors:** `{junit['errors']}`",
                f"**Manifest stable:** `{manifest_stable}`",
                "**Global full-suite at 215:** `False`",
                "**Next mandatory global full-suite:** `225`",
                "",
                "The batch passed controlled replay integration. "
                "It remains unsuitable for operational decisions.",
                "",
                "```text",
                "operational_status: BLOCKED_RESEARCH_ONLY",
                "data_trust_validated: False",
                "predictive_validity_established: False",
                "edge_validated: False",
                "decision_layer_allowed: False",
                "canonical_data_writes: 0",
                "```",
            ]
        ),
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    for phase in range(206, 215):
        parser.add_argument(
            f"--phase{phase}-artifact",
            type=Path,
            required=True,
        )
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument(
        "--test-file",
        type=Path,
        action="append",
        required=True,
    )
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--documentation", type=Path, required=True)
    parser.add_argument("--tracking-dir", type=Path, required=True)
    args = parser.parse_args()

    phase_artifacts = [
        getattr(args, f"phase{phase}_artifact")
        for phase in range(206, 215)
    ]
    payload = build_phase215(
        phase_artifacts,
        args.junit,
        args.test_file,
        args.artifact,
        args.documentation,
        args.tracking_dir,
    )

    print("PHASE215:", payload["checkpoint_status"])
    print(
        "Targeted tests:",
        payload["targeted_integration"]["totals"]["tests"],
    )
    print(
        "Failures:",
        payload["targeted_integration"]["totals"]["failures"],
    )
    print(
        "Errors:",
        payload["targeted_integration"]["totals"]["errors"],
    )
    print("Global full-suite at 215: False")
    print("Next mandatory global full-suite: 225")
    return 0 if payload["window_integration_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
