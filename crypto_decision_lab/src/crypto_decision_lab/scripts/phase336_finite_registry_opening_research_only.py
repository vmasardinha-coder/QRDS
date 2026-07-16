from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase336_345_abstention_evaluation_common import (
    MAX_HYPOTHESIS_BUDGET,
    OPERATING_THRESHOLDS,
    PROPOSED_NEW_FAMILY_ID,
    ROOT,
    base_payload,
    canonical_hash,
    fingerprint,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def _validate_template(template: dict[str, Any]) -> bool:
    expected = template.get("template_sha256")
    body = {key: value for key, value in template.items() if key != "template_sha256"}
    return bool(expected) and canonical_hash(body) == expected


def build(
    phase328_path: Path,
    phase329_path: Path,
    phase330_path: Path,
    phase331_path: Path,
    phase332_path: Path,
    phase335_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    items = {
        328: read_json(phase328_path),
        329: read_json(phase329_path),
        330: read_json(phase330_path),
        331: read_json(phase331_path),
        332: read_json(phase332_path),
        335: read_json(phase335_path),
    }
    for phase, item in items.items():
        validate_phase(item, phase)
    templates = list(items[331].get("sealed_templates", []))
    template_hashes_valid = (
        len(templates) == MAX_HYPOTHESIS_BUDGET
        and all(_validate_template(template) for template in templates)
        and canonical_hash(templates) == items[331].get("sealed_registry_sha256")
    )
    eligible = (
        items[335].get("next_window_decision")
        == "FINITE_REGISTRY_OPENING_ELIGIBLE_NEXT_WINDOW_RESEARCH_ONLY"
        and items[328].get("family_definition_frozen") is True
        and items[329].get("target_label_frozen") is True
        and items[330].get("budget_definition_frozen") is True
        and items[330].get("maximum_hypothesis_budget") == MAX_HYPOTHESIS_BUDGET
        and items[332].get("statistical_plan_frozen") is True
        and template_hashes_valid
    )
    if not eligible:
        raise RuntimeError("The sealed finite registry is not eligible to open.")
    active_templates = []
    for template in templates:
        opened = dict(template)
        opened["registry_state"] = "OPEN_FOR_ONE_PREREGISTERED_HISTORICAL_EVALUATION"
        opened["operating_threshold"] = OPERATING_THRESHOLDS[str(template["operating_point"])]
        active_templates.append(opened)
    payload = base_payload(336, "FINITE_SEALED_REGISTRY_OPENED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE336_FINITE_REGISTRY_OPENING_READY_RESEARCH_ONLY",
            "family_id": PROPOSED_NEW_FAMILY_ID,
            "phase331_sealed_registry_sha256": items[331]["sealed_registry_sha256"],
            "template_hashes_valid": template_hashes_valid,
            "active_template_count": len(active_templates),
            "active_templates": active_templates,
            "active_registry_sha256": canonical_hash(active_templates),
            "registry_open": True,
            "registry_scope": "ONE_PREREGISTERED_HISTORICAL_EVALUATION_ONLY",
            "active_hypothesis_budget": MAX_HYPOTHESIS_BUDGET,
            "experiment_budget_opened": True,
            "historical_experiments_executed": 0,
            "historical_evaluation_started": False,
            "research_family_registry_opened": True,
            "strategy_family_opened": False,
            "directional_prediction_allowed": False,
            "automatic_budget_expansion_allowed": False,
            "automatic_promotion_allowed": False,
            "strategy_approved": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase336_finite_registry_opening.json", payload)
    write_summary(
        ROOT / "docs/reports/abstention_v1/phase336_finite_registry_opening_summary.md",
        title="Phase 336 — Finite Sealed-registry Opening",
        gate=payload["gate"],
        bullets=[
            f"Templates opened: `{len(active_templates)}`",
            "Scope: `ONE_PREREGISTERED_HISTORICAL_EVALUATION_ONLY`",
            "Directional prediction allowed: `False`",
            "Automatic budget expansion: `False`",
            "Strategy approved: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    defaults = {
        328: artifacts / "phase328_new_family_definition_freeze_research_only/phase328_new_family_definition_freeze.json",
        329: artifacts / "phase329_non_directional_target_label_freeze_research_only/phase329_non_directional_target_label_freeze.json",
        330: artifacts / "phase330_finite_hypothesis_budget_envelope_research_only/phase330_finite_hypothesis_budget_envelope.json",
        331: artifacts / "phase331_sealed_non_directional_hypothesis_templates_research_only/phase331_sealed_non_directional_hypothesis_templates.json",
        332: artifacts / "phase332_statistical_multiple_testing_stop_plan_research_only/phase332_statistical_multiple_testing_stop_plan.json",
        335: artifacts / "phase335_preregistration_sealed_registry_checkpoint_research_only/phase335_preregistration_sealed_registry_checkpoint.json",
    }
    for phase, default in defaults.items():
        parser.add_argument(f"--phase{phase}-artifact", type=Path, default=default)
    parser.add_argument("--output-dir", type=Path, default=artifacts / "phase336_finite_registry_opening_research_only")
    args = parser.parse_args()
    payload = build(
        args.phase328_artifact,
        args.phase329_artifact,
        args.phase330_artifact,
        args.phase331_artifact,
        args.phase332_artifact,
        args.phase335_artifact,
        args.output_dir,
    )
    print(payload["gate"])
    print("Registry open:", payload["registry_open"])
    print("Active templates:", payload["active_template_count"])
    print("Strategy approved:", payload["strategy_approved"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
