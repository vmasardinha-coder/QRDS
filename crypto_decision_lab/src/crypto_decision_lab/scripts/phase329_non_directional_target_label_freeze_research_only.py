from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase326_335_preregistration_common import (
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


def build(phase328_path: Path, output_dir: Path) -> dict[str, Any]:
    phase328 = read_json(phase328_path)
    validate_phase(phase328, 328)
    allowed = phase328.get("family_definition_frozen") is True
    target_contract = {
        "target_id": TARGET_ID,
        "target_type": "NON_DIRECTIONAL_RELIABILITY_FAILURE_LABEL",
        "forecast_horizon_hours": 8,
        "positive_label": "RESEARCH_ABSTAIN",
        "negative_label": "RESEARCH_EVALUATE",
        "positive_rule": {
            "any_of": [
                "FUTURE_RETURN_SIGN_NOT_UNANIMOUS_ACROSS_ELIGIBLE_EXCHANGES",
                "FUTURE_CROSS_EXCHANGE_DISPERSION_ABOVE_TRAINING_FOLD_P95",
            ]
        },
        "minimum_eligible_exchanges": 3,
        "threshold_source": "TRAINING_FOLD_ONLY",
        "outer_holdout_threshold_selection_allowed": False,
        "feature_timestamp_rule": "FEATURES_MUST_BE_AVAILABLE_AT_OR_BEFORE_DECISION_TIME",
        "future_feature_use_allowed": False,
        "directional_return_prediction_allowed": False,
        "monetary_target_allowed": False,
        "execution_target_allowed": False,
    }
    frozen = allowed
    payload = base_payload(
        329,
        (
            "NON_DIRECTIONAL_TARGET_LABEL_FROZEN_RESEARCH_ONLY"
            if frozen
            else "TARGET_LABEL_NOT_FROZEN_REJECTED_OR_BLOCKED"
        ),
    )
    payload.update(
        {
            "gate": "PHASE329_NON_DIRECTIONAL_TARGET_LABEL_FREEZE_READY_RESEARCH_ONLY",
            "family_definition_frozen": allowed,
            "target_label_frozen": frozen,
            "target_contract": target_contract if frozen else None,
            "target_contract_sha256": (
                canonical_hash(target_contract) if frozen else None
            ),
            "real_historical_labels_created": 0,
            "new_family_opened": False,
            "hypotheses_registered": 0,
            "experiment_budget_opened": False,
            "historical_evaluation_started": False,
            "strategy_approved": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        output_dir / "phase329_non_directional_target_label_freeze.json",
        payload,
    )
    write_summary(
        ROOT
        / "docs/reports/preregistration_v2/"
        "phase329_non_directional_target_label_freeze_summary.md",
        title="Phase 329 — Non-directional Target-label Freeze",
        gate=payload["gate"],
        bullets=[
            f"Target frozen: `{frozen}`",
            f"Target ID: `{TARGET_ID if frozen else 'NONE'}`",
            "Output: `RESEARCH_ABSTAIN` or `RESEARCH_EVALUATE` only",
            "Real historical labels created: `0`",
            "New family opened: `False`",
            "Historical evaluation started: `False`",
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
        "--output-dir",
        type=Path,
        default=artifacts
        / "phase329_non_directional_target_label_freeze_research_only",
    )
    args = parser.parse_args()
    payload = build(args.phase328_artifact, args.output_dir)
    print(payload["gate"])
    print("Target label frozen:", payload["target_label_frozen"])
    print("Real historical labels:", payload["real_historical_labels_created"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
