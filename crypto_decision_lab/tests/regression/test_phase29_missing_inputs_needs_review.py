from pathlib import Path

from crypto_decision_lab.reports.phase29_compressed_regime_edge_retest_pack import build_phase29_compressed_regime_edge_retest_pack


def test_phase29_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase29_compressed_regime_edge_retest_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    assert payload["gate_answer"] == "PHASE29_COMPRESSED_REGIME_EDGE_RETEST_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["compressed_regime_retest_ready"] is False
    assert payload["edge_operationally_validated"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
