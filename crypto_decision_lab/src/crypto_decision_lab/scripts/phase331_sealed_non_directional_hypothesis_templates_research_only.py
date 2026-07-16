from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase326_335_preregistration_common import (
    MAX_HYPOTHESIS_BUDGET,
    PROPOSED_NEW_FAMILY_ID,
    ROOT,
    TARGET_ID,
    base_payload,
    canonical_hash,
    fingerprint,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)

FEATURE_BUNDLES = (
    "EXCHANGE_DISAGREEMENT_ONLY",
    "DERIVATIVES_DATA_QUALITY_ONLY",
    "COMBINED_DISAGREEMENT_AND_QUALITY",
)
MODEL_CLASSES = ("THRESHOLD_RULE", "LOGISTIC_REGRESSION")
OPERATING_POINTS = ("CONSERVATIVE", "STRICT")


def sealed_templates() -> list[dict[str, Any]]:
    templates: list[dict[str, Any]] = []
    index = 1
    for feature_bundle in FEATURE_BUNDLES:
        for model_class in MODEL_CLASSES:
            for operating_point in OPERATING_POINTS:
                template = {
                    "template_id": f"ABST_T{index:02d}",
                    "family_id": PROPOSED_NEW_FAMILY_ID,
                    "target_id": TARGET_ID,
                    "feature_bundle": feature_bundle,
                    "model_class": model_class,
                    "operating_point": operating_point,
                    "allowed_output": "ABSTENTION_PROBABILITY_OR_SCORE_ONLY",
                    "directional_prediction_allowed": False,
                    "price_target_allowed": False,
                    "monetary_target_allowed": False,
                    "state": "SEALED_DRAFT_NOT_ACTIVE",
                }
                template["template_sha256"] = canonical_hash(template)
                templates.append(template)
                index += 1
    return templates


def build(phase330_path: Path, output_dir: Path) -> dict[str, Any]:
    phase330 = read_json(phase330_path)
    validate_phase(phase330, 330)
    allowed = (
        phase330.get("budget_definition_frozen") is True
        and phase330.get("maximum_hypothesis_budget")
        == MAX_HYPOTHESIS_BUDGET
    )
    templates = sealed_templates() if allowed else []
    if templates and len(templates) != MAX_HYPOTHESIS_BUDGET:
        raise RuntimeError("Sealed-template count does not match the budget.")
    payload = base_payload(
        331,
        (
            "SEALED_NON_DIRECTIONAL_HYPOTHESIS_TEMPLATES_READY_RESEARCH_ONLY"
            if allowed
            else "SEALED_TEMPLATES_NOT_CREATED_REJECTED_OR_BLOCKED"
        ),
    )
    payload.update(
        {
            "gate": "PHASE331_SEALED_NON_DIRECTIONAL_HYPOTHESIS_TEMPLATES_READY_RESEARCH_ONLY",
            "sealed_template_count": len(templates),
            "sealed_templates": templates,
            "sealed_registry_sha256": (
                canonical_hash(templates) if templates else None
            ),
            "registry_state": (
                "SEALED_DRAFT_NOT_OPEN" if templates else "NOT_CREATED"
            ),
            "registry_open": False,
            "active_hypotheses": 0,
            "hypotheses_registered": 0,
            "experiment_budget_opened": False,
            "historical_experiments_executed": 0,
            "new_family_opened": False,
            "strategy_approved": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        output_dir / "phase331_sealed_non_directional_hypothesis_templates.json",
        payload,
    )
    write_summary(
        ROOT
        / "docs/reports/preregistration_v2/"
        "phase331_sealed_non_directional_hypothesis_templates_summary.md",
        title="Phase 331 — Sealed Non-directional Hypothesis Templates",
        gate=payload["gate"],
        bullets=[
            f"Sealed templates: `{len(templates)}`",
            f"Registry state: `{payload['registry_state']}`",
            "Active hypotheses: `0`",
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
        "--phase330-artifact",
        type=Path,
        default=artifacts
        / "phase330_finite_hypothesis_budget_envelope_research_only/"
        "phase330_finite_hypothesis_budget_envelope.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=artifacts
        / "phase331_sealed_non_directional_hypothesis_templates_research_only",
    )
    args = parser.parse_args()
    payload = build(args.phase330_artifact, args.output_dir)
    print(payload["gate"])
    print("Sealed templates:", payload["sealed_template_count"])
    print("Registry open:", payload["registry_open"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
