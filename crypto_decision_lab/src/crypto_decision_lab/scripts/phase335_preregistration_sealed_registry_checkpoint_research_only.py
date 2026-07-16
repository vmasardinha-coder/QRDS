from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase326_335_preregistration_common import (
    BASELINE_PHASE325_HEAD,
    LOCKS,
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


def _write_tracking(
    tracking_dir: Path,
    payload: dict[str, Any],
    phase325: dict[str, Any],
) -> None:
    decision = payload["next_window_decision"]
    targeted = payload["targeted_tests"]
    baseline_global = payload["baseline_global_full_suite"]
    master = f"""# QRDS Master Progress by Tens — Phase 335

## Current state

- Phase window completed: `326–335`
- Manual question decision: `{payload['manual_question_decision']}`
- Family definition frozen: `{payload['family_definition_frozen']}`
- Non-directional target frozen: `{payload['target_label_frozen']}`
- Sealed templates: `{payload['sealed_template_count']}`
- Registry opened: `False`
- Historical evaluation started: `False`
- Next-window decision: `{decision}`
- Strategy approved: `False`
- Capital used: `R$ 0`
- Action: `NO_ACTION_RESEARCH_ONLY`

## Tests

- Targeted tests: `{targeted['tests']}`
- Failures: `{targeted['failures']}`
- Errors: `{targeted['errors']}`
- Last mandatory global suite: Phase `325`
- Global test files at Phase 325: `{baseline_global['test_files']}`
- Global tests at Phase 325: `{baseline_global['tests']}`
- Next mandatory global full-suite: Phase `345`
"""
    mermaid = f"""# QRDS Architecture Mermaid — Phase 335

```mermaid
flowchart TD
    A[Negative directional family closed] --> B[Novel abstention question]
    B --> C{{Explicit manual question decision}}
    C -->|Reject| D[Keep preregistration closed]
    C -->|Accept| E[Freeze family definition]
    E --> F[Freeze non-directional target]
    F --> G[Freeze maximum budget 12]
    G --> H[Seal 12 templates; active zero]
    H --> I[Freeze multiple-testing and stop plan]
    I --> J[Synthetic dry-run only]
    J --> K[Phase 335 checkpoint]
    D --> K
    K --> L[{decision}]
    L --> M[No strategy; no forward; no paper; no capital]
```

**VOCE ESTA AQUI:** Phase 335 checkpoint. The finite registry remains closed
until a later phase explicitly opens it under the frozen contract.
"""
    table = f"""# QRDS Progress Table by Tens — Phase 335

| Range | Dominant delivery | State |
|---|---|---|
| 0–315 | Foundation, finite directional research and stability rejection | Complete; no approved edge |
| 316–325 | Negative-evidence registry, data-quality audit and novel-question draft | Complete; manual review required |
| **326–335** | **Explicit question review, family/target freeze, sealed finite templates and synthetic dry-run** | **PASS; {decision}** |
| 336–345 | Conditional finite-registry opening and first non-directional historical evaluation | Planned; global suite at 345 |

Registry opened: `False`. Historical evaluation started: `False`.
"""
    milestone = f"""# QRDS Integrated Test Milestone 326–335

- Window phases completed: `326–335`
- Targeted tests: `{targeted['tests']}`
- Failures: `{targeted['failures']}`
- Errors: `{targeted['errors']}`
- Manual question decision: `{payload['manual_question_decision']}`
- Family definition frozen: `{payload['family_definition_frozen']}`
- Target frozen: `{payload['target_label_frozen']}`
- Sealed templates: `{payload['sealed_template_count']}`
- Synthetic dry-run pass: `{payload['synthetic_dry_run_pass']}`
- Registry opened: `False`
- Historical evaluation started: `False`
- Strategy approved: `False`
- Operational: `BLOCKED_RESEARCH_ONLY`
- Capital used: `R$ 0`
"""
    if payload["registry_opening_eligible_next_window"]:
        roadmap_body = """## Eligible path

- 336: open exactly the 12 sealed templates under the Phase 335 hashes.
- 337: build strictly as-of contemporaneous quality features.
- 338: build the frozen H8 abstention/reliability label.
- 339: run nested walk-forward with the outer holdout untouched.
- 340: apply Holm-Bonferroni, calibration and null-model comparisons.
- 341: audit regime, provider-count and missingness robustness.
- 342: measure abstention coverage versus reliability improvement, not money.
- 343: evaluate research-candidate eligibility without forward promotion.
- 344: visual interpretation portal with R$10.000 explaining that capital remains zero.
- 345: mandatory resumable global full-suite and integrated checkpoint.
"""
    else:
        roadmap_body = """## Closed path

- 336–341: remediate the failed preregistration or data-quality conditions.
- 342–344: repeat only synthetic and quality audits; no historical hypotheses.
- 345: mandatory global full-suite retaining `NO_ACTION_RESEARCH_ONLY`.
"""
    roadmap = f"""# QRDS Roadmap 336–345 — Research Only

## Entering decision

`{decision}`

{roadmap_body}

## Permanent prohibition

No recommendation, allocation, directional signal, order, private account
connection or capital use. A non-directional historical result cannot
automatically authorize forward shadow, paper trading or real execution.
"""
    snapshot = {
        "project": "QRDS/QOS/GATE BTC",
        "baseline_phase": 335,
        "baseline_phase325_head": BASELINE_PHASE325_HEAD,
        "readiness": {"framework": 100, "evidence": 0, "operational": 0},
        "last_global_full_suite": {
            "source_checkpoint": 325,
            "passed": baseline_global["passed"],
            "test_files": baseline_global["test_files"],
            "tests": baseline_global["tests"],
            "failures": baseline_global["failures"],
            "errors": baseline_global["errors"],
            "manifest_stable": baseline_global["manifest_stable"],
        },
        "preregistration": {
            "manual_question_decision": payload["manual_question_decision"],
            "family_definition_frozen": payload["family_definition_frozen"],
            "target_label_frozen": payload["target_label_frozen"],
            "sealed_template_count": payload["sealed_template_count"],
            "registry_open": False,
            "historical_evaluation_started": False,
            "registry_opening_eligible_next_window": payload[
                "registry_opening_eligible_next_window"
            ],
            "decision": decision,
        },
        "safety": dict(LOCKS),
        "next_tracking_checkpoint": 345,
        "next_mandatory_global_full_suite": 345,
        "roadmap_window": "336-345",
    }
    tracking_dir.mkdir(parents=True, exist_ok=True)
    write_text(
        tracking_dir / "QRDS_MASTER_PROGRESS_BY_TENS_PHASE335.md",
        master,
    )
    write_text(
        tracking_dir / "QRDS_ARCHITECTURE_MERMAID_PHASE335.md",
        mermaid,
    )
    write_text(
        tracking_dir / "QRDS_PROGRESS_TABLE_BY_TENS_PHASE335.md",
        table,
    )
    write_text(
        tracking_dir / "QRDS_INTEGRATED_TEST_MILESTONE_326_335.md",
        milestone,
    )
    write_text(
        tracking_dir / "QRDS_ROADMAP_336_345_RESEARCH_ONLY.md",
        roadmap,
    )
    write_json(
        tracking_dir / "qrds_progress_snapshot_phase335.json",
        snapshot,
    )


def build_checkpoint(
    paths: dict[int, Path],
    *,
    targeted_junit_path: Path,
    artifact_path: Path,
    documentation_path: Path,
    tracking_dir: Path,
) -> dict[str, Any]:
    items = {phase: read_json(path) for phase, path in paths.items()}
    for phase, item in items.items():
        validate_phase(item, phase)
    phase325 = items[325]
    targeted = parse_junit(targeted_junit_path)
    baseline_global = phase325["global_full_suite"]
    manual_accepted = (
        items[327].get("question_accepted_for_preregistration") is True
    )
    all_ready = (
        manual_accepted
        and items[328].get("family_definition_frozen") is True
        and items[329].get("target_label_frozen") is True
        and items[330].get("budget_definition_frozen") is True
        and items[331].get("sealed_template_count") == 12
        and items[331].get("registry_open") is False
        and items[332].get("statistical_plan_frozen") is True
        and items[333].get("dry_run_pass") is True
        and items[333].get("real_historical_rows_used") == 0
        and items[334].get("audit_pass") is True
        and targeted["passed"] is True
    )
    decision = (
        "FINITE_REGISTRY_OPENING_ELIGIBLE_NEXT_WINDOW_RESEARCH_ONLY"
        if all_ready
        else "KEEP_PREREGISTRATION_AND_REGISTRY_CLOSED_RESEARCH_ONLY"
    )
    payload = base_payload(
        335,
        "PREREGISTRATION_SEALED_REGISTRY_CHECKPOINT_PASS_RESEARCH_ONLY",
    )
    payload.update(
        {
            "gate": "PHASE335_PREREGISTRATION_SEALED_REGISTRY_CHECKPOINT_READY_RESEARCH_ONLY",
            "manual_question_decision": items[327].get("effective_decision"),
            "question_accepted": manual_accepted,
            "family_definition_frozen": items[328].get(
                "family_definition_frozen"
            ),
            "target_label_frozen": items[329].get("target_label_frozen"),
            "budget_definition_frozen": items[330].get(
                "budget_definition_frozen"
            ),
            "sealed_template_count": items[331].get(
                "sealed_template_count", 0
            ),
            "statistical_plan_frozen": items[332].get(
                "statistical_plan_frozen"
            ),
            "synthetic_dry_run_pass": items[333].get("dry_run_pass"),
            "anti_leakage_audit_pass": items[334].get("audit_pass"),
            "targeted_tests": targeted,
            "baseline_global_full_suite": {
                "source_checkpoint": 325,
                "passed": baseline_global.get("passed"),
                "test_files": baseline_global.get("test_file_count"),
                "tests": baseline_global.get("totals", {}).get("tests"),
                "failures": baseline_global.get("totals", {}).get("failures"),
                "errors": baseline_global.get("totals", {}).get("errors"),
                "manifest_stable": baseline_global.get("manifest_stable"),
            },
            "registry_opening_eligible_next_window": all_ready,
            "next_window_decision": decision,
            "new_family_opened": False,
            "registry_open": False,
            "active_hypotheses": 0,
            "hypotheses_registered": 0,
            "experiment_budget_opened": False,
            "historical_evaluation_started": False,
            "forward_shadow_eligible": False,
            "forward_shadow_started": False,
            "paper_trading_started": False,
            "strategy_approved": False,
            "next_tracking_checkpoint": 345,
            "next_mandatory_global_full_suite": 345,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    write_json(artifact_path, payload)
    write_summary(
        documentation_path,
        title="Phase 335 — Preregistration and Sealed-registry Checkpoint",
        gate=payload["gate"],
        bullets=[
            f"Manual decision: `{payload['manual_question_decision']}`",
            f"Family definition frozen: `{payload['family_definition_frozen']}`",
            f"Target frozen: `{payload['target_label_frozen']}`",
            f"Sealed templates: `{payload['sealed_template_count']}`",
            f"Next-window decision: `{decision}`",
            "Registry open: `False`",
            "Historical evaluation started: `False`",
            "Strategy approved: `False`",
        ],
    )
    _write_tracking(tracking_dir, payload, phase325)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    defaults = {
        325: artifacts
        / "phase325_negative_evidence_new_question_full_integration_checkpoint_research_only/"
        "phase325_negative_evidence_new_question_full_integration_checkpoint.json",
        326: artifacts
        / "phase326_human_readable_novelty_non_overlap_review_research_only/"
        "phase326_human_readable_novelty_non_overlap_review.json",
        327: artifacts
        / "phase327_manual_scientific_question_decision_contract_research_only/"
        "phase327_manual_scientific_question_decision_contract.json",
        328: artifacts
        / "phase328_new_family_definition_freeze_research_only/"
        "phase328_new_family_definition_freeze.json",
        329: artifacts
        / "phase329_non_directional_target_label_freeze_research_only/"
        "phase329_non_directional_target_label_freeze.json",
        330: artifacts
        / "phase330_finite_hypothesis_budget_envelope_research_only/"
        "phase330_finite_hypothesis_budget_envelope.json",
        331: artifacts
        / "phase331_sealed_non_directional_hypothesis_templates_research_only/"
        "phase331_sealed_non_directional_hypothesis_templates.json",
        332: artifacts
        / "phase332_statistical_multiple_testing_stop_plan_research_only/"
        "phase332_statistical_multiple_testing_stop_plan.json",
        333: artifacts
        / "phase333_synthetic_schema_pipeline_dry_run_research_only/"
        "phase333_synthetic_schema_pipeline_dry_run.json",
        334: artifacts
        / "phase334_synthetic_anti_leakage_review_portal_research_only/"
        "phase334_synthetic_anti_leakage_review_portal.json",
    }
    for phase, default in defaults.items():
        parser.add_argument(f"--phase{phase}-artifact", type=Path, default=default)
    parser.add_argument(
        "--targeted-junit",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--artifact",
        type=Path,
        default=artifacts
        / "phase335_preregistration_sealed_registry_checkpoint_research_only/"
        "phase335_preregistration_sealed_registry_checkpoint.json",
    )
    parser.add_argument(
        "--documentation",
        type=Path,
        default=ROOT
        / "docs/reports/integration/"
        "phase335_preregistration_sealed_registry_checkpoint_summary.md",
    )
    parser.add_argument(
        "--tracking-dir",
        type=Path,
        default=ROOT / "docs/reports/project_tracking",
    )
    args = parser.parse_args()
    paths = {
        phase: getattr(args, f"phase{phase}_artifact") for phase in defaults
    }
    payload = build_checkpoint(
        paths,
        targeted_junit_path=args.targeted_junit,
        artifact_path=args.artifact,
        documentation_path=args.documentation,
        tracking_dir=args.tracking_dir,
    )
    print(payload["gate"])
    print("Next-window decision:", payload["next_window_decision"])
    print("Registry open:", payload["registry_open"])
    print(
        "Historical evaluation started:",
        payload["historical_evaluation_started"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
