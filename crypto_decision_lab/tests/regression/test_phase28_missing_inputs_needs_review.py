from pathlib import Path

from crypto_decision_lab.reports.phase28_regime_taxonomy_compression_failure_analysis_pack import build_phase28_regime_taxonomy_compression_failure_analysis_pack


def test_phase28_missing_inputs_needs_review_not_crash(tmp_path: Path) -> None:
    result = build_phase28_regime_taxonomy_compression_failure_analysis_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    assert payload["gate_answer"] == "PHASE28_REGIME_TAXONOMY_COMPRESSION_FAILURE_ANALYSIS_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["regime_taxonomy_compression_ready"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
