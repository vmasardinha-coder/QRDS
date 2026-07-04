from pathlib import Path

from crypto_decision_lab.reports.phase27_edge_candidate_stability_anti_overfit_pack import build_phase27_edge_candidate_stability_anti_overfit_pack


def test_phase27_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase27_edge_candidate_stability_anti_overfit_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    assert payload["gate_answer"] == "PHASE27_EDGE_CANDIDATE_STABILITY_ANTI_OVERFIT_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["edge_candidate_stability_ready"] is False
    assert payload["edge_operationally_validated"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
