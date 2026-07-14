from pathlib import Path

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    write_json,
)
from crypto_decision_lab.scripts.phase214_historical_replay_evidence_scorecard_research_only import (
    build_phase214,
)


def test_phase214_score_is_capped_below_decision_readiness(tmp_path: Path):
    payloads = [
        {"contract_passed": True},
        {"window_builder_passed": True},
        {"missing_data_policy_passed": True},
        {"deterministic_replay": True},
        {"checkpoint_passed": True},
        {"counterfactual_audit_passed": True},
        {"stability_audit_passed": True},
        {"regime_segmentation_passed": True},
    ]
    paths = []
    for phase, payload in zip(range(206, 214), payloads):
        path = tmp_path / f"phase{phase}.json"
        write_json(path, payload)
        paths.append(path)

    result = build_phase214(
        *paths,
        tmp_path / "phase214.json",
        tmp_path / "phase214.md",
        root=tmp_path,
    )

    assert result["score"] == 100
    assert result["evidence_scorecard_passed"] is True
    assert result["caps"]["predictive_validity_established"] is False
    assert result["caps"]["decision_layer_allowed"] is False
