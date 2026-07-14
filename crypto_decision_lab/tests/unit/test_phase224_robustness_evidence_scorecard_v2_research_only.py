from pathlib import Path

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import write_json
from crypto_decision_lab.scripts.phase224_robustness_evidence_scorecard_v2_research_only import (
    build_phase224,
)


def test_phase224_scores_controls_but_preserves_caps(tmp_path: Path):
    entries = [
        ("provenance_completeness_passed", True),
        ("multi_source_agreement_diagnostic_passed", True),
        ("contamination_sensitivity_passed", True),
        ("window_boundary_perturbation_passed", True),
        ("robustness_checkpoint_passed", True),
        ("benchmark_comparison_passed", True),
        ("calibration_diagnostic_passed", True),
        ("cost_slippage_sensitivity_passed", True),
    ]
    paths = []
    for phase, (key, value) in zip(range(216, 224), entries):
        path = tmp_path / f"phase{phase}.json"
        write_json(path, {key: value})
        paths.append(path)

    result = build_phase224(
        paths,
        tmp_path / "phase224.json",
        tmp_path / "phase224.md",
        root=tmp_path,
    )
    assert result["robustness_scorecard_passed"] is True
    assert result["score"] == 100
    assert result["classification"] == (
        "ROBUSTNESS_EVIDENCE_COMPLETE_NO_TRUST_OR_EDGE"
    )
    assert result["caps"]["predictive_validity_established"] is False
    assert result["caps"]["decision_layer_allowed"] is False
