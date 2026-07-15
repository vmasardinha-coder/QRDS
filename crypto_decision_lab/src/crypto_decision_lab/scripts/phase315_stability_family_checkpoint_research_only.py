from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase306_315_stability_common import (
    BASELINE_PHASE305_HEAD,
    LOCKS,
    ROOT,
    artifact_identity,
    base_payload,
    fingerprint,
    parse_junit,
    read_json,
    validate_phase,
    write_json,
    write_text,
)


def _write_tracking(
    payload: dict[str, Any],
    phase305: dict[str, Any],
    phase304: dict[str, Any],
    phase314: dict[str, Any],
    tracking_dir: Path,
) -> None:
    decision = payload["current_family_decision"]
    eligible = payload["candidate_eligible"]
    failed = payload["failed_gate_count"]
    mean_brl = float(phase304["outer_metrics_10bps"]["mean_per_10000_brl"])
    lower_brl = float(phase304["outer_metrics_10bps"]["lower_95_per_10000_brl"])
    baseline_suite = phase305["global_full_suite"]
    targeted = payload["targeted_tests"]

    master = f"""# QRDS/QOS/GATE BTC — Master Progress Phase 315

## Estado executivo

- Framework readiness: `100/100`
- Evidence readiness: `0/100`
- Operational readiness: `0/100`
- Candidate: `{payload['candidate_hypothesis_id']}`
- Candidate eligible: `{eligible}`
- Failed eligibility gates: `{failed}`
- Current-family decision: `{decision}`
- Strategy approved: `False`
- Forward shadow eligible: `False`
- Forward shadow started: `False`
- Paper trading started: `False`
- Capital used: `R$ 0`
- Action: `NO_ACTION_RESEARCH_ONLY`

## Evidência em linguagem simples

Para R$10.000 teóricos, o resultado médio externo da Fase 304 foi
`R$ {mean_brl:.2f}` por operação modelada e o limite inferior de 95% foi
`R$ {lower_brl:.2f}`. A janela 306–315 auditou por que esse resultado não
pode ser promovido.

## Testes

- Last mandatory global full-suite source: `Phase 305`
- Global test files: `{baseline_suite['test_file_count']}`
- Global tests: `{baseline_suite['totals']['tests']}`
- Global failures/errors: `0/0`
- Manifest stable: `{baseline_suite['manifest_stable']}`
- Batch 306–315 targeted tests: `{targeted['tests']}`
- Targeted failures/errors: `{targeted['failures']}/{targeted['errors']}`
- Next mandatory global full-suite: `Phase 325`

The checkpoint is technically complete. It does not authorize execution.
"""
    mermaid = f"""# QRDS Architecture Mermaid — Phase 315

```mermaid
flowchart TD
    A[Public multi-source history] --> B[Controlled features v2]
    B --> C[Closed registry: 24 hypotheses]
    C --> D[Nested walk-forward v2]
    D --> E[Temporal stability audit]
    E --> F[Regime concentration audit]
    F --> G[Hypothesis dependence audit]
    G --> H[Extreme cost and liquidity audit]
    H --> I[Timestamp sensitivity audit]
    I --> J{{Eligibility gates}}
    J -->|Failed: {failed}| K[Close current family research-only]
    J -->|All pass| L[Manual freeze review only]
    K --> M[NO_ACTION_RESEARCH_ONLY]
    L --> M
    M --> N[Forward clock inactive]
    N --> O[Paper and real capital blocked]
```

**VOCE ESTA AQUI:** `{decision}`. No immutable candidate freeze exists and
historical evidence has zero credit in the forward clock.
"""
    table = f"""# QRDS Progress Table by Tens — Phase 315

| Range | Dominant delivery | State |
|---|---|---|
| 0–245 | Foundation, integrity, replay and robustness | Research framework complete |
| 246–285 | Public data, hypotheses, costs and calibration | Complete; no approved edge |
| 286–300 | Calibration, freeze/forward contracts and handoff | Complete; operations blocked |
| 301–305 | Longer history, 18 features, 24 hypotheses, nested WF and global suite | Technical PASS; strategy not approved |
| **306–315** | **Stability diagnosis, eligibility contract, scientific-decision portal** | **Checkpoint PASS; family decision = {decision}** |
| 316–325 | Negative-evidence registry or manual-freeze dry-run design; mandatory global suite at 325 | Planned, research-only |

Current family eligible: `{eligible}`. Failed eligibility gates: `{failed}`.
"""
    milestone = f"""# QRDS Integrated Test Milestone 306–315

- Window phases completed: `306–315`
- Targeted tests: `{targeted['tests']}`
- Failures: `{targeted['failures']}`
- Errors: `{targeted['errors']}`
- Candidate hypothesis: `{payload['candidate_hypothesis_id']}`
- Eligibility gates: `{payload['eligibility_gate_count']}`
- Passed gates: `{payload['passed_gate_count']}`
- Failed gates: `{payload['failed_gate_count']}`
- Candidate eligible: `{eligible}`
- Freeze created: `False`
- Forward evidence credit: `0`
- Strategy approved: `False`
- Current-family decision: `{decision}`
- Operational: `BLOCKED_RESEARCH_ONLY`
- Action: `NO_ACTION_RESEARCH_ONLY`
- Capital used: `R$ 0`

This milestone validates the software and artifact chain for the stability
diagnosis. It does not validate a tradable edge.
"""
    roadmap = f"""# QRDS Roadmap 316–325 — Research Only

## Decision entering the window

Current-family decision: `{decision}`  
Candidate eligible: `{eligible}`  
Immutable freeze created: `False`

## Conditional direction

### If the current family is closed

- 316–318: register the negative result, prohibited retest signatures and a
  failure atlas so the same 24 hypotheses are not silently recycled.
- 319–321: audit data coverage, exchange disagreement and derivatives
  missingness without creating a new strategy budget.
- 322–324: draft a new-family pre-registration contract only if a genuinely
  different scientific question is justified.
- 325: mandatory global full-suite, integrated tracking and decision on
  whether a new finite family may be opened.

### If all eligibility gates had passed

- 316–318: manual freeze-review package only; no automatic freeze.
- 319–324: dry-run validation of the forward evidence plumbing with zero
  forward credit and no paper/real execution.
- 325: mandatory global full-suite and explicit human decision.

## Permanent prohibition

No phase may generate recommendation, allocation, signal, order or capital
use. Historical data cannot start or backfill the forward evidence clock.
"""
    snapshot = {
        "project": "QRDS/QOS/GATE BTC",
        "baseline_phase": 315,
        "baseline_phase305_head": BASELINE_PHASE305_HEAD,
        "readiness": {"framework": 100, "evidence": 0, "operational": 0},
        "last_mandatory_global_suite": {
            "source_checkpoint": 305,
            "passed": baseline_suite["passed"],
            "test_files": baseline_suite["test_file_count"],
            "tests": baseline_suite["totals"]["tests"],
            "failures": baseline_suite["totals"]["failures"],
            "errors": baseline_suite["totals"]["errors"],
            "manifest_stable": baseline_suite["manifest_stable"],
        },
        "batch_306_315_targeted_tests": targeted,
        "research_result": {
            "candidate_hypothesis_id": payload["candidate_hypothesis_id"],
            "mean_result_per_10000_brl": mean_brl,
            "lower_95_per_10000_brl": lower_brl,
            "eligibility_gate_count": payload["eligibility_gate_count"],
            "passed_gate_count": payload["passed_gate_count"],
            "failed_gate_count": payload["failed_gate_count"],
            "candidate_eligible": eligible,
            "current_family_decision": decision,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
            "forward_shadow_started": False,
            "paper_trading_started": False,
        },
        "forward_evidence": {
            "clock_started": False,
            "credit": 0,
            "historical_backfill_allowed": False,
        },
        "safety": dict(LOCKS),
        "next_tracking_checkpoint": 325,
        "next_mandatory_global_full_suite": 325,
        "roadmap_window": "316-325",
    }
    write_text(tracking_dir / "QRDS_MASTER_PROGRESS_BY_TENS_PHASE315.md", master)
    write_text(tracking_dir / "QRDS_ARCHITECTURE_MERMAID_PHASE315.md", mermaid)
    write_text(tracking_dir / "QRDS_PROGRESS_TABLE_BY_TENS_PHASE315.md", table)
    write_text(tracking_dir / "QRDS_INTEGRATED_TEST_MILESTONE_306_315.md", milestone)
    write_text(tracking_dir / "QRDS_ROADMAP_316_325_RESEARCH_ONLY.md", roadmap)
    write_json(tracking_dir / "qrds_progress_snapshot_phase315.json", snapshot)


def build(
    *,
    phase305_path: Path,
    phase304_path: Path,
    phase306_path: Path,
    phase307_path: Path,
    phase308_path: Path,
    phase309_path: Path,
    phase310_path: Path,
    phase311_path: Path,
    phase312_path: Path,
    phase313_path: Path,
    phase314_path: Path,
    targeted_junit_path: Path,
    artifact_path: Path,
    documentation_path: Path,
    tracking_dir: Path,
) -> dict[str, Any]:
    paths = {
        304: phase304_path,
        305: phase305_path,
        306: phase306_path,
        307: phase307_path,
        308: phase308_path,
        309: phase309_path,
        310: phase310_path,
        311: phase311_path,
        312: phase312_path,
        313: phase313_path,
        314: phase314_path,
    }
    payloads: dict[int, dict[str, Any]] = {}
    lineage: list[dict[str, Any]] = []
    for phase, path in paths.items():
        item = read_json(path)
        validate_phase(item, phase)
        payloads[phase] = item
        lineage.append(artifact_identity(path, item))

    phase304 = payloads[304]
    phase305 = payloads[305]
    phase311 = payloads[311]
    phase312 = payloads[312]
    phase313 = payloads[313]
    phase314 = payloads[314]
    targeted = parse_junit(targeted_junit_path)
    if not targeted["passed"]:
        raise RuntimeError(f"Batch 306–315 targeted tests did not pass: {targeted}")

    expected_phases = list(range(306, 315))
    actual_phases = [payloads[number]["phase"] for number in expected_phases]
    if actual_phases != expected_phases:
        raise RuntimeError(f"Phase chain mismatch: {actual_phases}")

    candidate_eligible = bool(phase311["candidate_eligible"])
    decision = (
        "AWAIT_MANUAL_FREEZE_REVIEW_RESEARCH_ONLY"
        if candidate_eligible
        else "CLOSE_CURRENT_FAMILY_RESEARCH_ONLY"
    )
    if phase314["scientific_decision"] != decision:
        raise RuntimeError("Phase 314 scientific decision differs from eligibility contract.")
    if phase312["freeze_created"] is not False:
        raise RuntimeError("Phase 312 unexpectedly created an automatic freeze.")
    if phase313["evidence_clock_started"] is not False:
        raise RuntimeError("Phase 313 unexpectedly started the forward clock.")
    if phase313["forward_evidence_credit"] != 0:
        raise RuntimeError("Historical evidence was incorrectly credited to forward clock.")

    payload = base_payload(315, "STABILITY_FAMILY_CHECKPOINT_PASS_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE315_STABILITY_FAMILY_CHECKPOINT_READY_RESEARCH_ONLY",
            "batch_gate": "PHASE306_315_STABILITY_FAMILY_CHECKPOINT_PASS_RESEARCH_ONLY",
            "baseline_phase305_head": BASELINE_PHASE305_HEAD,
            "phase_chain": {
                str(number): {
                    "gate": payloads[number].get("gate"),
                    "artifact_fingerprint": payloads[number].get("artifact_fingerprint"),
                }
                for number in range(306, 315)
            },
            "lineage": lineage,
            "lineage_fingerprint": fingerprint(lineage),
            "targeted_tests": targeted,
            "candidate_hypothesis_id": phase311["candidate_hypothesis_id"],
            "eligibility_gate_count": phase311["eligibility_gate_count"],
            "passed_gate_count": phase311["passed_gate_count"],
            "failed_gate_count": phase311["failed_gate_count"],
            "failed_gate_ids": phase311["failed_gate_ids"],
            "candidate_eligible": candidate_eligible,
            "current_family_decision": decision,
            "current_family_closed": not candidate_eligible,
            "freeze_created": False,
            "forward_evidence_credit": 0,
            "historical_backfill_to_forward_clock": False,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
            "forward_shadow_started": False,
            "paper_trading_started": False,
            "window_integration_passed": True,
            "last_mandatory_global_suite_source": 305,
            "next_tracking_checkpoint": 325,
            "next_mandatory_global_full_suite": 325,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(artifact_path, payload)
    _write_tracking(payload, phase305, phase304, phase314, tracking_dir)
    write_text(
        documentation_path,
        f"""# Phase 315 — Stability Family Integrated Checkpoint

Gate: `{payload['gate']}`  
Batch gate: `{payload['batch_gate']}`

- Targeted tests: `{targeted['tests']}`
- Failures: `{targeted['failures']}`
- Errors: `{targeted['errors']}`
- Candidate: `{payload['candidate_hypothesis_id']}`
- Eligibility gates: `{payload['eligibility_gate_count']}`
- Passed gates: `{payload['passed_gate_count']}`
- Failed gates: `{payload['failed_gate_count']}`
- Candidate eligible: `{candidate_eligible}`
- Current-family decision: `{decision}`
- Freeze created: `False`
- Forward evidence credit: `0`
- Strategy approved: `False`
- Forward shadow started: `False`
- Paper trading started: `False`
- Operational: `BLOCKED_RESEARCH_ONLY`
- Action: `NO_ACTION_RESEARCH_ONLY`
- Capital used: `R$ 0`
- Next mandatory global full-suite: `Phase 325`

The checkpoint passes because the software, contracts and artifact lineage are
consistent. It does not mean that the strategy or family passed scientifically.
""",
    )
    return payload


def parse_args() -> argparse.Namespace:
    artifacts = ROOT / "artifacts"
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase305-artifact", type=Path, default=artifacts / "phase305_evidence_registry_v2_full_integration_checkpoint_research_only/phase305_evidence_registry_v2_full_integration_checkpoint.json")
    parser.add_argument("--phase304-artifact", type=Path, default=artifacts / "phase304_nested_walk_forward_v2_research_only/phase304_nested_walk_forward_v2.json")
    for number, name in (
        (306, "temporal_selection_stability_audit"),
        (307, "regime_concentration_audit"),
        (308, "hypothesis_dependence_audit"),
        (309, "extreme_cost_liquidity_audit"),
        (310, "timestamp_sensitivity_audit"),
    ):
        parser.add_argument(
            f"--phase{number}-artifact",
            type=Path,
            default=artifacts / f"phase{number}_{name}_research_only" / f"phase{number}_{name}.json",
        )
    parser.add_argument("--phase311-artifact", type=Path, default=artifacts / "phase311_candidate_eligibility_contract_v2_research_only/phase311_candidate_eligibility_contract_v2.json")
    parser.add_argument("--phase312-artifact", type=Path, default=artifacts / "phase312_candidate_lineage_freeze_readiness_research_only/phase312_candidate_lineage_freeze_readiness.json")
    parser.add_argument("--phase313-artifact", type=Path, default=artifacts / "phase313_forward_evidence_design_readiness_research_only/phase313_forward_evidence_design_readiness.json")
    parser.add_argument("--phase314-artifact", type=Path, default=artifacts / "phase314_scientific_decision_portal_research_only/phase314_scientific_decision_portal.json")
    parser.add_argument("--targeted-junit", type=Path, default=artifacts / "phase315_stability_family_checkpoint_research_only/targeted_batch306_315.xml")
    parser.add_argument("--artifact", type=Path, default=artifacts / "phase315_stability_family_checkpoint_research_only/phase315_stability_family_checkpoint.json")
    parser.add_argument("--documentation", type=Path, default=ROOT / "docs/reports/integration/phase315_stability_family_checkpoint_summary.md")
    parser.add_argument("--tracking-dir", type=Path, default=ROOT / "docs/reports/project_tracking")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build(
        phase305_path=args.phase305_artifact,
        phase304_path=args.phase304_artifact,
        phase306_path=args.phase306_artifact,
        phase307_path=args.phase307_artifact,
        phase308_path=args.phase308_artifact,
        phase309_path=args.phase309_artifact,
        phase310_path=args.phase310_artifact,
        phase311_path=args.phase311_artifact,
        phase312_path=args.phase312_artifact,
        phase313_path=args.phase313_artifact,
        phase314_path=args.phase314_artifact,
        targeted_junit_path=args.targeted_junit,
        artifact_path=args.artifact,
        documentation_path=args.documentation,
        tracking_dir=args.tracking_dir,
    )
    print(payload["gate"])
    print(payload["batch_gate"])
    print("Targeted tests:", payload["targeted_tests"]["tests"])
    print("Failures:", payload["targeted_tests"]["failures"])
    print("Errors:", payload["targeted_tests"]["errors"])
    print("Candidate:", payload["candidate_hypothesis_id"])
    print("Eligibility gates passed:", payload["passed_gate_count"])
    print("Eligibility gates failed:", payload["failed_gate_count"])
    print("Candidate eligible:", payload["candidate_eligible"])
    print("Current-family decision:", payload["current_family_decision"])
    print("Strategy approved:", payload["strategy_approved"])
    print("Operational:", payload["locks"]["operational_status"])
    print("Action:", payload["locks"]["action_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
