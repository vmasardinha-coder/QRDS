from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase366_375_remediation_evaluation_common import (
    BASELINE_PHASE365_HEAD,
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


def _write_tracking(payload: dict[str, Any], tracking_dir: Path) -> None:
    decision = payload["next_window_decision"]
    targeted = payload["targeted_tests"]
    baseline = payload["last_global_full_suite"]
    mode = payload["batch_result_mode"]

    master = f"""# QRDS Master Progress by Tens — Phase 375

## Current decision

`{decision}`

## Window 366–375

- Result mode: `{mode}`
- Frozen remediation review decision: `{payload['manual_review_decision']}`
- One real-data quality evaluation executed: `{payload['evaluation_executed']}`
- Data-quality contract applicable: `{payload['data_quality_contract_applicable']}`
- Data-quality contract pass: `{payload['data_quality_contract_pass']}`
- Governance pass: `{payload['governance_pass']}`
- Closed-family performance metrics used: `False`
- Public recollection started: `False`
- Registry open: `False`
- Active hypotheses: `0`
- Capital used: `R$ 0`

## Targeted validation

- Tests: `{targeted['tests']}`
- Failures: `{targeted['failures']}`
- Errors: `{targeted['errors']}`

## Last mandatory global suite

- Checkpoint: `Phase 365`
- Test files: `{baseline['test_files']}`
- Tests: `{baseline['tests']}`
- Failures: `{baseline['failures']}`
- Errors: `{baseline['errors']}`
- Manifest stable: `{baseline['manifest_stable']}`
"""

    action_node = (
        "D[One real-data quality evaluation]"
        if payload["evaluation_executed"]
        else "D[Manual rejection preserved; no evaluation]"
    )
    mermaid = f"""# QRDS Architecture Mermaid — Phase 375

```mermaid
flowchart TD
 A[Two closed scientific families] --> B[Frozen timestamp-consensus remediation]
 B --> C[Manual one-evaluation review]
 C --> {action_node}
 D --> E[Quality comparison or not-applicable record]
 E --> F[No closed-family metric proof]
 F --> G[Lineage/reproducibility audit for selected path]
 G --> H[Stop-rule closes budget]
 H --> I[Unified portal updated]
 I --> J[NO_ACTION_RESEARCH_ONLY]
```

**VOCE ESTA AQUI:** `{decision}`. Capital authorized: `R$ 0`.
"""

    table = f"""# QRDS Progress Table by Tens — Phase 375

| Range | Dominant delivery | State |
|---|---|---|
| 0–345 | Foundation and two finite scientific families | Complete; no survivor |
| 346–355 | Negative-evidence closure and unified navigation | Complete |
| 356–365 | Finite data-remediation governance and global checkpoint | Complete |
| **366–375** | **Manual frozen-remediation decision and dual-path governance** | **PASS; {mode}; {decision}** |
| 376–385 | Register result, preserve no-go or review research-only dataset | Planned |

Operational: `BLOCKED_RESEARCH_ONLY`. Capital: `R$ 0`.
"""

    milestone = f"""# QRDS Integrated Test Milestone 366–375

- Phases completed: `366–375`
- Result mode: `{mode}`
- Targeted tests: `{targeted['tests']}`
- Targeted failures: `{targeted['failures']}`
- Targeted errors: `{targeted['errors']}`
- Last global checkpoint: `Phase 365`
- Global test files at baseline: `{baseline['test_files']}`
- Global tests at baseline: `{baseline['tests']}`
- Global suite run in this batch: `False`
- Evaluation executed: `{payload['evaluation_executed']}`
- Governance pass: `{payload['governance_pass']}`
- Strategy approved: `False`
- Capital used: `R$ 0`
"""

    if payload["evaluation_executed"] and payload["data_quality_contract_pass"] and payload["governance_pass"]:
        roadmap_body = """- **376:** register the successful data-quality remediation result without promoting it to canonical data.
- **377:** manual review of whether the remediated dataset may become a research-only candidate input.
- **378:** verify that adoption would not reopen any closed family.
- **379:** freeze a candidate research-dataset schema and lineage contract.
- **380:** execute synthetic/fixture adoption dry-runs only.
- **381–383:** integrity, rollback and coexistence audit against the raw datasets.
- **384:** update the unified portal.
- **385:** mandatory global full-suite and integrated checkpoint."""
    elif not payload["evaluation_executed"]:
        roadmap_body = """- **376:** register the explicit manual rejection and the valid no-evaluation governance path.
- **377–383:** preserve raw datasets and closed families; no adoption or recollection experiment without a new explicit manual review.
- **384:** update the unified portal.
- **385:** mandatory global full-suite and integrated checkpoint."""
    else:
        roadmap_body = """- **376–379:** register the remediation no-pass and preserve raw datasets as the only research inputs.
- **380–383:** no adoption experiment unless a new manual review passes all governance gates.
- **384:** update the unified portal.
- **385:** mandatory global full-suite and integrated checkpoint."""

    roadmap = f"""# QRDS Roadmap 376–385 — Research Only

## Entering decision

`{decision}`

## Recommended sequence

{roadmap_body}

## Permanent prohibition

A remediated dataset cannot become canonical automatically, rescue closed families, create a trading signal, authorize allocation, connect a private account, place orders or use capital.
"""

    snapshot = {
        "project": "QRDS/QOS/GATE BTC",
        "baseline_phase": 375,
        "baseline_phase365_head": BASELINE_PHASE365_HEAD,
        "readiness": {"framework": 100, "evidence": 0, "operational": 0},
        "data_remediation_evaluation": {
            "batch_result_mode": mode,
            "manual_review_decision": payload["manual_review_decision"],
            "evaluation_executed": payload["evaluation_executed"],
            "data_quality_contract_applicable": payload["data_quality_contract_applicable"],
            "data_quality_contract_pass": payload["data_quality_contract_pass"],
            "governance_pass": payload["governance_pass"],
            "closed_family_performance_metric_used": False,
            "public_recollection_started": False,
            "candidate_dataset_adopted": False,
        },
        "last_global_full_suite": baseline,
        "safety": dict(LOCKS),
        "next_tracking_checkpoint": 385,
        "next_mandatory_global_full_suite": 385,
        "roadmap_window": "376-385",
    }

    tracking_dir.mkdir(parents=True, exist_ok=True)
    write_text(tracking_dir / "QRDS_MASTER_PROGRESS_BY_TENS_PHASE375.md", master)
    write_text(tracking_dir / "QRDS_ARCHITECTURE_MERMAID_PHASE375.md", mermaid)
    write_text(tracking_dir / "QRDS_PROGRESS_TABLE_BY_TENS_PHASE375.md", table)
    write_text(tracking_dir / "QRDS_INTEGRATED_TEST_MILESTONE_366_375.md", milestone)
    write_text(tracking_dir / "QRDS_ROADMAP_376_385_RESEARCH_ONLY.md", roadmap)
    write_json(tracking_dir / "qrds_progress_snapshot_phase375.json", snapshot)


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

    p365 = items[365]
    if p365.get("contract_frozen") is not True:
        raise RuntimeError("Phase 365 did not enter with a frozen remediation contract.")
    if int(p365.get("active_hypotheses", -1)) != 0:
        raise RuntimeError("Phase 365 active hypotheses are not zero.")

    targeted = parse_junit(targeted_junit_path)
    if not targeted["passed"]:
        raise RuntimeError(f"Targeted tests failed: {targeted}")

    p366, p367, p368, p369, p370, p371, p372, p373, p374 = (
        items[366], items[367], items[368], items[369], items[370],
        items[371], items[372], items[373], items[374],
    )
    approved = bool(p366.get("one_real_data_quality_evaluation_approved"))
    executed = bool(p367.get("evaluation_executed"))
    rejected = p366.get("selected_decision") == "REJECT_REAL_DATA_REMEDIATION_EVALUATION"

    integration_checks = {
        "phase369_proof_pass": p369.get("proof_pass") is True,
        "phase371_lineage_audit_pass": p371.get("lineage_audit_pass") is True,
        "phase372_reproducibility_pass": p372.get("reproducibility_pass") is True,
        "phase373_governance_pass": p373.get("governance_pass") is True,
        "phase373_registry_closed": p373.get("registry_open") is False,
        "phase373_active_budget_zero": int(p373.get("active_experiment_budget", -1)) == 0,
        "phase374_capital_zero": p374.get("capital_authorized_brl") == 0,
        "phase374_evaluation_flag_matches": bool(p374.get("evaluation_executed")) == executed,
    }

    if approved:
        path_checks = {
            "approved_path_executed": executed,
            "phase368_comparison_applicable": p368.get("comparison_applicable") is True,
            "phase371_executed_audit_mode": p371.get("audit_mode")
            == "EXECUTED_LINEAGE_AND_HASH_AUDIT",
            "phase372_executed_replay_mode": p372.get("audit_mode")
            == "EXECUTED_SAME_INPUT_REPLAY",
            "phase373_executed_governance_mode": p373.get("governance_mode")
            == "EXECUTED_ONE_EVALUATION",
        }
        result_mode = "EXECUTED_QUALITY_EVALUATION"
    else:
        path_checks = {
            "manual_rejection_is_explicit": rejected,
            "rejected_path_not_executed": executed is False,
            "phase367_skipped_schema_complete": p367.get("skipped_schema_complete") is True,
            "phase368_no_go_preserved": p368.get("manual_rejection_no_go_preserved") is True,
            "phase370_no_recollection_due_to_rejection": p370.get("decision")
            == "NO_PUBLIC_RECOLLECTION_EVALUATION_REJECTED_RESEARCH_ONLY",
            "phase371_skipped_audit_mode": p371.get("audit_mode") == "SKIPPED_NO_EVALUATION",
            "phase371_hash_fields_not_applicable": (
                p371.get("all_input_hashes_verified") is None
                and p371.get("output_hash_verified") is None
            ),
            "phase372_skipped_audit_mode": p372.get("audit_mode") == "SKIPPED_NO_EVALUATION",
            "phase373_rejection_governance_mode": p373.get("governance_mode")
            == "MANUAL_REJECTION_NO_EVALUATION",
            "phase373_rejection_decision": p373.get("next_window_decision")
            == "REAL_DATA_REMEDIATION_EVALUATION_REJECTED_NO_GO_PRESERVED_RESEARCH_ONLY",
        }
        result_mode = "MANUAL_REJECTION_NO_EVALUATION"

    checks = {**integration_checks, **path_checks}
    failed_checks = sorted(name for name, value in checks.items() if not value)
    if failed_checks:
        raise RuntimeError(
            "Phase 366-374 integration checks failed. "
            f"result_mode={result_mode!r}; failed_checks={failed_checks!r}; "
            f"phase369_failed_checks={p369.get('failed_checks', [])!r}; "
            f"phase371_failed_checks={p371.get('failed_checks', [])!r}; "
            f"phase372_failed_checks={p372.get('failed_checks', [])!r}; "
            f"phase373_failed_checks={p373.get('failed_checks', [])!r}."
        )

    last_global = dict(p365.get("global_full_suite", {}))
    baseline = {
        "source_checkpoint": 365,
        "passed": bool(last_global.get("passed")),
        "test_files": int(last_global.get("test_file_count", 0)),
        "tests": int(last_global.get("totals", {}).get("tests", 0)),
        "failures": int(last_global.get("totals", {}).get("failures", 0)),
        "errors": int(last_global.get("totals", {}).get("errors", 0)),
        "manifest_stable": bool(last_global.get("manifest_stable")),
    }
    if not baseline["passed"] or baseline["failures"] != 0 or baseline["errors"] != 0:
        raise RuntimeError("Phase 365 global baseline is not valid.")

    payload = base_payload(375, "DATA_QUALITY_REMEDIATION_INTEGRATED_CHECKPOINT_PASS_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE375_DATA_QUALITY_REMEDIATION_INTEGRATED_CHECKPOINT_READY_RESEARCH_ONLY",
            "batch_gate": "PHASE366_375_DATA_QUALITY_REMEDIATION_CHECKPOINT_PASS_RESEARCH_ONLY",
            "batch_result_mode": result_mode,
            "integration_checks": checks,
            "integration_failed_checks": [],
            "baseline_phase365_head": BASELINE_PHASE365_HEAD,
            "phase_chain": {
                str(phase): {
                    "gate": items[phase].get("gate"),
                    "artifact_fingerprint": items[phase].get("artifact_fingerprint"),
                }
                for phase in range(366, 375)
            },
            "manual_review_decision": p366.get("selected_decision"),
            "evaluation_executed": executed,
            "evaluation_id": p367.get("evaluation_id"),
            "real_historical_rows_used": int(p367.get("real_historical_rows_used", 0)),
            "provider_dataset_count": int(p367.get("provider_dataset_count", 0)),
            "raw_metrics": p368.get("raw_metrics", {}),
            "remediated_metrics": p368.get("remediated_metrics", {}),
            "data_quality_contract_applicable": bool(p368.get("comparison_applicable")),
            "data_quality_contract_pass": bool(p368.get("data_quality_contract_pass")),
            "no_closed_family_metric_proof_pass": True,
            "public_recollection_needed": bool(p370.get("public_recollection_needed")),
            "public_recollection_started": False,
            "lineage_audit_mode": p371.get("audit_mode"),
            "lineage_audit_pass": True,
            "reproducibility_audit_mode": p372.get("audit_mode"),
            "reproducibility_pass": True,
            "governance_mode": p373.get("governance_mode"),
            "governance_pass": True,
            "registry_open": False,
            "active_hypotheses": 0,
            "active_experiment_budget": 0,
            "closed_families_reopened": False,
            "candidate_dataset_adopted": False,
            "canonical_data_writes": 0,
            "targeted_tests": targeted,
            "last_global_full_suite": baseline,
            "global_full_suite_run_in_this_batch": False,
            "current_portal_relative_path": p374.get("portal_relative_path"),
            "next_window_decision": p373.get("next_window_decision"),
            "next_tracking_checkpoint": 385,
            "next_mandatory_global_full_suite": 385,
            "candidate_freeze_created": False,
            "forward_evidence_clock_started": False,
            "forward_evidence_credit": 0,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(artifact_path, payload)
    write_summary(
        documentation_path,
        title="Phase 375 — Data-quality Remediation Integrated Checkpoint",
        gate=payload["gate"],
        bullets=[
            f"Result mode: `{result_mode}`",
            f"Targeted tests: `{targeted['tests']}`",
            f"Evaluation executed: `{executed}`",
            f"Data-quality contract applicable: `{payload['data_quality_contract_applicable']}`",
            f"Data-quality contract pass: `{payload['data_quality_contract_pass']}`",
            "Closed-family performance metrics used: `False`",
            "Global suite run in this batch: `False`",
            f"Last global checkpoint: `Phase {baseline['source_checkpoint']}`",
            "Capital used: `R$ 0`",
        ],
    )
    _write_tracking(payload, tracking_dir)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    art = ROOT / "artifacts"
    definitions = {
        365: "data_remediation_full_integration_checkpoint",
        366: "manual_frozen_remediation_execution_review",
        367: "one_real_data_remediation_evaluation",
        368: "raw_vs_remediated_data_quality_comparison",
        369: "no_closed_family_performance_metric_proof",
        370: "public_recollection_need_decision",
        371: "remediation_lineage_and_hash_audit",
        372: "remediation_reproducibility_audit",
        373: "remediation_stop_rule_and_budget_audit",
        374: "data_quality_remediation_result_portal",
    }
    for phase, slug in definitions.items():
        parser.add_argument(
            f"--phase{phase}-artifact",
            type=Path,
            default=art / f"phase{phase}_{slug}_research_only" / f"phase{phase}_{slug}.json",
        )
    parser.add_argument("--targeted-junit", type=Path, required=True)
    parser.add_argument(
        "--artifact",
        type=Path,
        default=art
        / "phase375_data_quality_remediation_integrated_checkpoint_research_only"
        / "phase375_data_quality_remediation_integrated_checkpoint.json",
    )
    parser.add_argument(
        "--documentation",
        type=Path,
        default=ROOT
        / "docs/reports/integration/phase375_data_quality_remediation_integrated_checkpoint_summary.md",
    )
    parser.add_argument(
        "--tracking-dir",
        type=Path,
        default=ROOT / "docs/reports/project_tracking",
    )
    args = parser.parse_args()
    paths = {phase: getattr(args, f"phase{phase}_artifact") for phase in range(365, 375)}
    payload = build_checkpoint(
        paths,
        targeted_junit_path=args.targeted_junit,
        artifact_path=args.artifact,
        documentation_path=args.documentation,
        tracking_dir=args.tracking_dir,
    )
    print(payload["gate"])
    print("Batch result mode:", payload["batch_result_mode"])
    print("Evaluation executed:", payload["evaluation_executed"])
    print("Governance pass:", payload["governance_pass"])
    print("Next-window decision:", payload["next_window_decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
