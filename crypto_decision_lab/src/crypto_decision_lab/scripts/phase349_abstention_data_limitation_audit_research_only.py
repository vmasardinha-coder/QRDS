from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase346_355_closure_navigation_common import (
    FAMILY_ID,
    ROOT,
    base_payload,
    fingerprint,
    phase_summary,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def build(phase345_path: Path, phase337_path: Path, phase341_path: Path, output_dir: Path) -> dict[str, Any]:
    p345 = read_json(phase345_path)
    p337 = read_json(phase337_path)
    p341 = read_json(phase341_path)
    validate_phase(p345, 345)
    validate_phase(p337, 337)
    validate_phase(p341, 341)

    limitations = [
        {
            "limitation_id": "PUBLIC_DATA_ONLY",
            "classification": "STRUCTURAL",
            "remediable_without_new_source": False,
            "meaning": "Only public no-auth market context was evaluated; private account or execution data remain prohibited.",
        },
        {
            "limitation_id": "NO_CAUSAL_LABEL",
            "classification": "STRUCTURAL",
            "remediable_without_new_question": False,
            "meaning": "The frozen H8 disagreement label is observational and does not prove causal market dysfunction.",
        },
        {
            "limitation_id": "DERIVATIVES_CONTEXT_COVERAGE",
            "classification": "DATA_QUALITY",
            "remediable_without_new_source": True,
            "meaning": "Funding and open-interest context may have missingness or provider-specific availability.",
        },
        {
            "limitation_id": "REGIME_DEPENDENCE",
            "classification": "MODEL_GENERALIZATION",
            "remediable_without_parameter_rescue": False,
            "meaning": "No template remained robust across the required strata.",
        },
        {
            "limitation_id": "MULTIPLE_TESTING_NO_SURVIVOR",
            "classification": "STATISTICAL",
            "remediable_without_new_experiment": False,
            "meaning": "Zero templates survived the pre-registered Holm gate.",
        },
    ]

    payload = base_payload(349, "ABSTENTION_DATA_LIMITATIONS_AUDITED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE349_ABSTENTION_DATA_LIMITATION_AUDIT_READY_RESEARCH_ONLY",
            "family_id": FAMILY_ID,
            "historical_quality_feature_rows": int(p337.get("row_count", p345.get("historical_rows", 0))),
            "holm_survivor_count": int(p345.get("holm_survivor_count", 0)),
            "robust_template_count": int(p341.get("robust_template_count", 0)),
            "limitations": limitations,
            "limitation_count": len(limitations),
            "data_quality_issue_proves_edge": False,
            "data_remediation_can_retroactively_rescue_family": False,
            "new_collection_started": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase349_abstention_data_limitation_audit.json", payload)
    write_summary(
        phase_summary(349, "abstention_data_limitation_audit"),
        title="Phase 349 — Abstention Data-limitation Audit",
        gate=payload["gate"],
        bullets=[
            f"Historical quality-feature rows: `{payload['historical_quality_feature_rows']}`",
            f"Documented limitations: `{payload['limitation_count']}`",
            "New data collection started: `False`",
            "Data remediation can retroactively rescue family: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase345-artifact", type=Path, default=ROOT / "artifacts/phase345_abstention_full_integration_checkpoint_research_only/phase345_abstention_full_integration_checkpoint.json")
    parser.add_argument("--phase337-artifact", type=Path, default=ROOT / "artifacts/phase337_asof_quality_feature_matrix_research_only/phase337_asof_quality_feature_matrix.json")
    parser.add_argument("--phase341-artifact", type=Path, default=ROOT / "artifacts/phase341_regime_provider_missingness_robustness_research_only/phase341_regime_provider_missingness_robustness.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/phase349_abstention_data_limitation_audit_research_only")
    args = parser.parse_args()
    payload = build(args.phase345_artifact, args.phase337_artifact, args.phase341_artifact, args.output_dir)
    print(payload["gate"])
    print("Limitations:", payload["limitation_count"])
    print("New collection started:", payload["new_collection_started"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
