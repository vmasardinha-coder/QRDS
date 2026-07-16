from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase326_335_preregistration_common import (
    MAX_HYPOTHESIS_BUDGET,
    ROOT,
    base_payload,
    canonical_hash,
    fingerprint,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def build(
    phase328_path: Path,
    phase329_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    phase328 = read_json(phase328_path)
    phase329 = read_json(phase329_path)
    validate_phase(phase328, 328)
    validate_phase(phase329, 329)
    eligible = (
        phase328.get("family_definition_frozen") is True
        and phase329.get("target_label_frozen") is True
    )
    envelope = {
        "maximum_hypothesis_budget": MAX_HYPOTHESIS_BUDGET,
        "current_active_hypothesis_budget": 0,
        "current_experiments_executed": 0,
        "budget_may_not_expand_after_results": True,
        "historical_results_observed_before_budget_freeze": False,
        "manual_checkpoint_required_before_registry_opening": True,
        "automatic_opening_allowed": False,
        "multiple_testing_required": True,
        "execution_allowed": False,
    }
    frozen = eligible
    payload = base_payload(
        330,
        (
            "FINITE_HYPOTHESIS_BUDGET_ENVELOPE_FROZEN_RESEARCH_ONLY"
            if frozen
            else "FINITE_HYPOTHESIS_BUDGET_NOT_FROZEN_REJECTED_OR_BLOCKED"
        ),
    )
    payload.update(
        {
            "gate": "PHASE330_FINITE_HYPOTHESIS_BUDGET_ENVELOPE_READY_RESEARCH_ONLY",
            "budget_definition_frozen": frozen,
            "budget_envelope": envelope if frozen else None,
            "budget_envelope_sha256": (
                canonical_hash(envelope) if frozen else None
            ),
            "maximum_hypothesis_budget": (
                MAX_HYPOTHESIS_BUDGET if frozen else 0
            ),
            "active_hypothesis_budget": 0,
            "experiment_budget_opened": False,
            "hypotheses_registered": 0,
            "historical_experiments_executed": 0,
            "new_family_opened": False,
            "strategy_approved": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        output_dir / "phase330_finite_hypothesis_budget_envelope.json",
        payload,
    )
    write_summary(
        ROOT
        / "docs/reports/preregistration_v2/"
        "phase330_finite_hypothesis_budget_envelope_summary.md",
        title="Phase 330 — Finite Hypothesis-budget Envelope",
        gate=payload["gate"],
        bullets=[
            f"Budget definition frozen: `{frozen}`",
            f"Maximum future budget: `{payload['maximum_hypothesis_budget']}`",
            "Active hypothesis budget: `0`",
            "Historical experiments executed: `0`",
            "Experiment budget opened: `False`",
            "New family opened: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    parser.add_argument(
        "--phase328-artifact",
        type=Path,
        default=artifacts
        / "phase328_new_family_definition_freeze_research_only/"
        "phase328_new_family_definition_freeze.json",
    )
    parser.add_argument(
        "--phase329-artifact",
        type=Path,
        default=artifacts
        / "phase329_non_directional_target_label_freeze_research_only/"
        "phase329_non_directional_target_label_freeze.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=artifacts
        / "phase330_finite_hypothesis_budget_envelope_research_only",
    )
    args = parser.parse_args()
    payload = build(
        args.phase328_artifact,
        args.phase329_artifact,
        args.output_dir,
    )
    print(payload["gate"])
    print("Budget definition frozen:", payload["budget_definition_frozen"])
    print("Active budget:", payload["active_hypothesis_budget"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
