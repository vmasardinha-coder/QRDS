from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase346_355_closure_navigation_common import (
    BASELINE_PHASE345_HEAD,
    ROOT,
    base_payload,
    fingerprint,
    parse_junit,
    read_json,
    validate_phase,
    write_json,
    write_summary,
    write_text,
)


def _write_tracking(payload: dict[str, Any], tracking_dir: Path) -> None:
    tracking_dir.mkdir(parents=True, exist_ok=True)
    targeted = payload["targeted_tests"]
    baseline = payload["baseline_global_full_suite"]

    master = f"""# QRDS Master Progress by Tens — Phase 355

## Current decision

`{payload['next_window_decision']}`

## Window 346–355

- Abstention negative evidence registered: `{payload['negative_evidence_registered']}`
- Closed templates blocked from exact/semantic retest: `{payload['blocked_template_count']}`
- Closure sealed: `{payload['closure_sealed']}`
- New family opened: `{payload['new_family_opened']}`
- Active hypotheses: `{payload['active_hypotheses']}`
- Unified project launcher ready: `{payload['unified_launcher_ready']}`
- Targeted tests: `{targeted['tests']}`
- Targeted failures: `{targeted['failures']}`
- Targeted errors: `{targeted['errors']}`

## Last mandatory global suite

- Checkpoint: `Phase 345`
- Test files: `{baseline['test_files']}`
- Tests: `{baseline['tests']}`
- Failures: `{baseline['failures']}`
- Errors: `{baseline['errors']}`
- Manifest stable: `{baseline['manifest_stable']}`

Strategy approved: `False`. Capital used: `R$ 0`.
"""
    mermaid = f"""# QRDS Architecture Mermaid — Phase 355

```mermaid
flowchart TD
    A[Directional family closed] --> B[Abstention family closed]
    B --> C[Negative evidence registered]
    C --> D[12 exact and semantic retests blocked]
    D --> E[Failure causes and data limits audited]
    E --> F[Closure integrity sealed]
    F --> G[Data remediation does not reopen family]
    G --> H[New question requires manual governance]
    H --> I[Unified portal and root launcher]
    I --> J[NO_ACTION_RESEARCH_ONLY]
    J --> K[Manual data-remediation or genuinely-new-question review]
```

**VOCE ESTA AQUI:** unified navigation is ready, while science remains blocked with zero active hypotheses and `R$ 0` capital.
"""
    table = f"""# QRDS Progress Table by Tens — Phase 355

| Range | Dominant delivery | State |
|---|---|---|
| 0–335 | Foundation, finite directional search, negative-evidence controls and preregistration | Complete; no approved strategy |
| 336–345 | One-time abstention evaluation and mandatory global suite | Complete; 0 survivors |
| **346–355** | **Negative-evidence closure, retest blocklist, data-limit governance and unified project entry** | **PASS; {payload['next_window_decision']}** |
| 356–365 | Data-remediation feasibility or genuinely-new-question manual review, with mandatory global suite at 365 | Planned, research-only |

Operational: `BLOCKED_RESEARCH_ONLY`. Capital: `R$ 0`.
"""
    milestone = f"""# QRDS Integrated Test Milestone 346–355

- Phases completed: `346–355`
- Targeted tests: `{targeted['tests']}`
- Targeted failures: `{targeted['failures']}`
- Targeted errors: `{targeted['errors']}`
- Last global suite checkpoint: `345`
- Global test files at baseline: `{baseline['test_files']}`
- Global tests at baseline: `{baseline['tests']}`
- Negative evidence registered: `{payload['negative_evidence_registered']}`
- Blocked templates: `{payload['blocked_template_count']}`
- Closure sealed: `{payload['closure_sealed']}`
- Root launcher ready: `{payload['unified_launcher_ready']}`
- Strategy approved: `False`
- Capital used: `R$ 0`
"""
    roadmap = f"""# QRDS Roadmap 356–365 — Research Only

## Entering decision

`{payload['next_window_decision']}`

## Recommended sequence

- **356:** freeze a manual backlog of data-remediation questions; no collection yet.
- **357:** audit whether public funding/open-interest coverage can be materially improved without private APIs.
- **358:** audit timestamp alignment and exchange-consensus construction as data engineering, not strategy rescue.
- **359:** decide manually whether one remediation experiment is scientifically justified.
- **360:** if accepted, preregister one finite remediation evaluation; otherwise preserve a no-go result.
- **361–362:** synthetic and fixture-only dry runs of the remediation contract.
- **363:** freeze any future real-data evaluation contract before seeing results.
- **364:** update the unified portal with the manual decision and practical explanation.
- **365:** mandatory global full-suite, integrated checkpoint and next roadmap.

## Permanent prohibition

No automatic new family, recommendation, allocation, signal, order, private account connection or capital use. Data remediation cannot retroactively rescue either closed family.
"""
    snapshot = {
        "project": "QRDS/QOS/GATE BTC",
        "baseline_phase": 355,
        "baseline_phase345_head": BASELINE_PHASE345_HEAD,
        "readiness": {"framework": 100, "evidence": 0, "operational": 0},
        "closure_navigation": {
            "negative_evidence_registered": payload["negative_evidence_registered"],
            "blocked_template_count": payload["blocked_template_count"],
            "closure_sealed": payload["closure_sealed"],
            "new_family_opened": payload["new_family_opened"],
            "active_hypotheses": payload["active_hypotheses"],
            "unified_launcher_ready": payload["unified_launcher_ready"],
            "current_portal_relative_path": payload["current_portal_relative_path"],
        },
        "targeted_tests": targeted,
        "last_global_full_suite": baseline,
        "next_tracking_checkpoint": 365,
        "next_mandatory_global_full_suite": 365,
        "next_window_decision": payload["next_window_decision"],
        "safety": payload["locks"],
    }

    write_text(tracking_dir / "QRDS_MASTER_PROGRESS_BY_TENS_PHASE355.md", master)
    write_text(tracking_dir / "QRDS_ARCHITECTURE_MERMAID_PHASE355.md", mermaid)
    write_text(tracking_dir / "QRDS_PROGRESS_TABLE_BY_TENS_PHASE355.md", table)
    write_text(tracking_dir / "QRDS_INTEGRATED_TEST_MILESTONE_346_355.md", milestone)
    write_text(tracking_dir / "QRDS_ROADMAP_356_365_RESEARCH_ONLY.md", roadmap)
    write_json(tracking_dir / "qrds_progress_snapshot_phase355.json", snapshot)


def build(
    phase_paths: dict[int, Path],
    phase345_path: Path,
    targeted_junit_path: Path,
    output_dir: Path,
    tracking_dir: Path,
) -> dict[str, Any]:
    items = {phase: read_json(path) for phase, path in phase_paths.items()}
    for phase in range(346, 355):
        validate_phase(items[phase], phase)
    p345 = read_json(phase345_path)
    validate_phase(p345, 345)
    targeted = parse_junit(targeted_junit_path)
    if not targeted["passed"]:
        raise RuntimeError(f"Targeted tests failed: {targeted}")

    if items[346].get("negative_evidence_registered") is not True:
        raise RuntimeError("Phase 346 did not register negative evidence.")
    if int(items[347].get("blocked_template_count", 0)) != 12:
        raise RuntimeError("Phase 347 did not block all 12 templates.")
    if items[350].get("closure_sealed") is not True:
        raise RuntimeError("Phase 350 did not seal closure integrity.")
    if items[352].get("new_family_opened") is not False or int(items[352].get("new_hypotheses_registered", -1)) != 0:
        raise RuntimeError("Phase 352 opened research automatically.")
    if items[354].get("readme_updated_with_marked_block") is not True or items[354].get("capital_authorized_brl") != 0:
        raise RuntimeError("Phase 354 navigation portal is inconsistent.")

    full = p345.get("global_full_suite", {})
    baseline = {
        "source_checkpoint": 345,
        "passed": bool(full.get("passed")),
        "test_files": int(full.get("test_file_count", 0)),
        "tests": int(full.get("totals", {}).get("tests", 0)),
        "failures": int(full.get("totals", {}).get("failures", 0)),
        "errors": int(full.get("totals", {}).get("errors", 0)),
        "manifest_stable": bool(full.get("manifest_stable")),
    }
    if baseline != {
        "source_checkpoint": 345,
        "passed": True,
        "test_files": 584,
        "tests": 1491,
        "failures": 0,
        "errors": 0,
        "manifest_stable": True,
    }:
        raise RuntimeError(f"Phase 345 global baseline mismatch: {baseline}")

    decision = "DATA_REMEDIATION_OR_GENUINELY_NEW_QUESTION_MANUAL_REVIEW_ONLY_RESEARCH_ONLY"
    payload = base_payload(355, "NEGATIVE_EVIDENCE_NAVIGATION_CHECKPOINT_PASS_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE355_NEGATIVE_EVIDENCE_NAVIGATION_CHECKPOINT_READY_RESEARCH_ONLY",
            "batch_gate": "PHASE346_355_NEGATIVE_EVIDENCE_NAVIGATION_PASS_RESEARCH_ONLY",
            "baseline_phase345_head": BASELINE_PHASE345_HEAD,
            "phase_chain": {
                str(phase): {
                    "gate": items[phase].get("gate"),
                    "artifact_fingerprint": items[phase].get("artifact_fingerprint"),
                }
                for phase in range(346, 355)
            },
            "negative_evidence_registered": True,
            "blocked_template_count": int(items[347]["blocked_template_count"]),
            "failure_category_count": int(items[348]["failure_category_count"]),
            "data_limitation_count": int(items[349]["limitation_count"]),
            "closure_sealed": True,
            "data_remediation_reopens_family": False,
            "new_question_proposed": False,
            "new_family_opened": False,
            "active_hypotheses": 0,
            "active_experiment_budget": 0,
            "unified_launcher_ready": True,
            "root_launcher_path": items[354]["root_launcher_path"],
            "current_portal_relative_path": items[354]["portal_relative_path"],
            "targeted_tests": targeted,
            "baseline_global_full_suite": baseline,
            "global_full_suite_run_in_this_batch": False,
            "next_window_decision": decision,
            "next_tracking_checkpoint": 365,
            "next_mandatory_global_full_suite": 365,
            "candidate_freeze_created": False,
            "forward_evidence_clock_started": False,
            "forward_evidence_credit": 0,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase355_negative_evidence_navigation_checkpoint.json", payload)
    write_summary(
        ROOT / "docs/reports/integration/phase355_negative_evidence_navigation_checkpoint_summary.md",
        title="Phase 355 — Negative-evidence and Navigation Checkpoint",
        gate=payload["gate"],
        bullets=[
            f"Targeted tests: `{targeted['tests']}`",
            f"Blocked templates: `{payload['blocked_template_count']}`",
            "Closure sealed: `True`",
            "Unified launcher ready: `True`",
            f"Last global suite: `Phase {baseline['source_checkpoint']} — {baseline['test_files']} files / {baseline['tests']} tests`",
            f"Next-window decision: `{decision}`",
            "Strategy approved: `False`",
            "Capital used: `R$ 0`",
        ],
    )
    _write_tracking(payload, tracking_dir)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    slugs = {
        346: "abstention_negative_evidence_registration",
        347: "abstention_retest_blocklist",
        348: "abstention_failure_cause_audit",
        349: "abstention_data_limitation_audit",
        350: "abstention_closure_integrity_seal",
        351: "data_remediation_decision",
        352: "new_question_governance",
        353: "portal_inventory_registry",
        354: "unified_project_entry_portal",
    }
    for phase, slug in slugs.items():
        parser.add_argument(
            f"--phase{phase}-artifact",
            type=Path,
            default=artifacts / f"phase{phase}_{slug}_research_only" / f"phase{phase}_{slug}.json",
        )
    parser.add_argument("--phase345-artifact", type=Path, default=artifacts / "phase345_abstention_full_integration_checkpoint_research_only/phase345_abstention_full_integration_checkpoint.json")
    parser.add_argument("--targeted-junit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=artifacts / "phase355_negative_evidence_navigation_checkpoint_research_only")
    parser.add_argument("--tracking-dir", type=Path, default=ROOT / "docs/reports/project_tracking")
    args = parser.parse_args()
    paths = {phase: getattr(args, f"phase{phase}_artifact") for phase in slugs}
    payload = build(paths, args.phase345_artifact, args.targeted_junit, args.output_dir, args.tracking_dir)
    print(payload["gate"])
    print("Blocked templates:", payload["blocked_template_count"])
    print("Unified launcher ready:", payload["unified_launcher_ready"])
    print("Next-window decision:", payload["next_window_decision"])
    print("Strategy approved:", payload["strategy_approved"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
