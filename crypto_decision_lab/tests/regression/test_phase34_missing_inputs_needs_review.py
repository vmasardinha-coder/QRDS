from pathlib import Path

from crypto_decision_lab.reports.phase34_latest_observation_regime_snapshot_pack import build_phase34_latest_observation_regime_snapshot_pack


def test_phase34_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase34_latest_observation_regime_snapshot_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    assert payload["gate_answer"] == "PHASE34_LATEST_OBSERVATION_REGIME_SNAPSHOT_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["latest_observation_regime_snapshot_ready"] is False
    assert payload["edge_validated"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
